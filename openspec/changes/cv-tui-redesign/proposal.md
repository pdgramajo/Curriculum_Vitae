# Proposal: CV TUI Redesign — One Command, One Professional Interface

**Plain-language benefit**: `./cv` opens a polished, keyboard-driven Textual interface where you pick a CV, press Enter, and get your PDF — no more juggling four different scripts, worrying about a broken shell command, or losing the Terminal window by accident.

## Intent

Rebuild the CV generator from a single monolithic script (`cv_tui.py`, 258 lines that mix UI, business logic, shell building, cleanup and macOS side-effects) into a small, well-separated Python package. The user experience becomes: one command (`cv`) → professional TUI → select CV → render → PDF opens. RenderCV remains the rendering engine — we never replace it, we only wrap it cleanly.

The goal is **simple professional architecture**: enough separation to test, read and extend, but no layers, abstractions or patterns "for the sake of architecture". Every module must earn its place.

## Why now

| Pain today | Consequence |
|---|---|
| `cv_tui.py` mixes discovery, command-building, subprocess, cleanup, `open` and TUI in one file | Any change risks breaking everything; nothing is testable in isolation |
| 4 entry points (`cv`, `cv_tui`, `run_cv.sh`, `Generar CV.command`) duplicate venv-detection logic in Bash | Fragile: a broken launcher blocks CV generation entirely; `./cv` with no args just lists files and exits with code 1 instead of doing anything useful |
| Rendering runs `subprocess.run(shell=True, executable="/bin/zsh")` with a command built as a string | Shell-quoting bugs, no error capture, unsafe by default, impossible to unit-test |
| `os.execv` restart, `osascript` to quit Terminal, exit code 10 | MacOS-bound hacks: quitting the app also quits the user's Terminal |
| Cleanup of `.typ/.md/.html/png` files is hardcoded inside the render function | Hidden side-effects; PNG cleanup pattern `*_*.png` also deletes the CV's own photo |
| Zero tests, zero linting, zero type checking, zero logs, no config file, no git history | Every change is a leap of faith; there is no safety net and no way to see why something failed |

## Scope

### In Scope

- New Python package `src/cvapp/` with separated modules: `cli`, `config`, `core/discovery`, `core/rendercv`, `tui`.
- Single unified command: `cv` (thin launcher) and `python -m cvapp` (equivalent).
- Typer-based CLI with subcommands: `tui` (default), `list`, `render <name>`, `version`.
- Professional Textual TUI: main selection screen, generation status (spinner/worker), result screen, error screen, keyboard navigation (↑↓, Enter, R, Q, Esc). UI copy stays in Spanish (Rioplatense), per project convention.
- Config file `cvapp.yaml` at the project root (minimal keys + sensible defaults).
- Error handling and logging: friendly errors in the TUI, full traceback to a log file, non-zero exit codes for headless commands.
- Test suite with pytest for all pure logic; RenderCV smoke test (opt-in, never auto-run).
- Ruff (lint + format) and Pyright (type checking), configured in `pyproject.toml`.
- `git init` + `.gitignore` as the safety net (recommended, pending user approval).
- Thin `Generar CV.command` double-click launcher that reuses `cv` and pauses on error.

### Out of Scope

- Replacing RenderCV or the YAML format/structure of CVs.
- Editing any of the 10+ existing CV YAML files (they are user data; byte-identical after the change).
- Converting the project to full Python packaging with `pip install` (kept as unpackaged scripts with a thin launcher, matching current convention).
- Web, database, API, cloud, multiuser features — everything non-terminal.
- Automated TUI end-to-end testing via Textual Pilot (deferred; unit tests cover the logic, the TUI is verified manually).
- Wine, Docker, or any RenderCV alternative backend (none present, none wanted).

## Capabilities

> `openspec/specs/` is currently empty — there are no existing capabilities. All capabilities below are **new** and will each get a full spec at `openspec/changes/cv-tui-redesign/specs/<name>/spec.md` during the spec phase.

### New Capabilities

- `cv-cli`: single entry point (`cv` / `python -m cvapp`) with Typer subcommands (`tui`, `list`, `render <name>`, `version`), exit codes, and the thin launcher's venv resolution.
- `cv-tui`: the Textual interface — CV list screen, generation status, result/error screens, keyboard bindings, Spanish copy.
- `cv-rendering`: CV source discovery (glob `*.yaml`/`*.yml`, exclude dotfiles), RenderCV invocation via argument list (no `shell=True`), output to `rendercv_output/`, intermediate-file cleanup, and the option to open the generated PDF.
- `cv-config`: `cvapp.yaml` loading with defaults, minimal validation, and logging-level configuration.

### Modified Capabilities

None — no capabilities exist yet.

## Approach

### Target structure

```
src/cvapp/
├── __init__.py          # __version__ (single source of truth)
├── __main__.py          # python -m cvapp -> cli.main()
├── cli.py               # Typer app: tui / list / render / version
├── config.py            # Settings dataclass + cvapp.yaml loading
├── core/
│   ├── __init__.py
│   ├── discovery.py     # find_cv_sources(root) -> list[Path]  (pure)
│   └── rendercv.py      # RendercvService: build command, run, cleanup, open
└── tui/
    ├── __init__.py
    └── app.py           # Textual App: screens + workers
cvapp.yaml               # optional config (defaults apply if absent)
tests/                   # pytest suite
pyproject.toml           # dev-tool config only (pytest/ruff/pyright)
.gitignore               # .venv/, rendercv-env/, rendercv_output/, __pycache__/
```

`python -m cvapp` works without `pip install`: the `cv` launcher resolves the script directory and exports `PYTHONPATH=src` before exec'ing venv python — zero packaging, consistent with the project's existing "unpackaged scripts" convention.

### Technology choices (and WHY)

| Choice | Why |
|---|---|
| **Textual 8.2.5** (already in `.venv`) | The current TUI already uses it — proven on this machine; no new dependency; idiomatic widgets/workers for status and result screens |
| **Typer 0.24.1** (already installed in BOTH venvs as a RenderCV dependency) | Zero new dependencies; auto `--help`, argument parsing and clear errors with almost no code; built on Click, already present |
| **stdlib `logging`** | Zero dependency; `cvapp.log` full tracebacks, friendly one-line error in the TUI |
| **`subprocess.run([...argv...])` instead of `shell=True` + string** | No shell quoting bugs, no shell-injection surface, trivially testable; command built by a pure function `build_rendercv_command(...) -> list[str]` |
| **pytest** (new dev dependency) | User explicitly wants a testing strategy; config.yaml itself recommends pytest; there is zero test infra today |
| **Ruff** (new dev dependency) | One fast tool for lint + format; near-zero config; catches beginner mistakes immediately |
| **Pyright** (new dev dependency) | Clear, concise type errors; great for a non-expert author; works without config |
| **No new RUNTIME dependencies** | Typer, Rich and Textual are already installed; pytest/Ruff/Pyright are dev-time only and never touch the runtime path |

### How it will work (flow)

1. `./cv` → launcher resolves project root, activates `.venv` (existing behavior), runs `python -m cvapp`.
2. Typer sees no subcommand → enters the TUI.
3. TUI loads CV sources via `core.discovery` (same glob as today: `*.yaml` + `*.yml`, sorted, dotfiles excluded) and shows the list with keyboard navigation.
4. User selects a CV → `RendercvService.render(yaml_path)` runs in a Textual worker (UI stays responsive, status shown).
5. Service builds the argv list, runs `rendercv render <file> -nomd -nohtml -nopng --pdf-path rendercv_output/<basename>.pdf`, cleans intermediate files (created by this run only), and (per config) opens the PDF.
6. Result screen: success (PDF path, "generate another"/"quit") or error (friendly message; full traceback in `cvapp.log`; retry).
7. Quitting just quits — no `osascript`, no `os.execv`, no exit code 10. "Generate another" resets app state in-process.

`./cv render Pablo_Gramajo` runs the same service headless: generates, prints the output path, exits 0/1 — scriptable and testable without a terminal.

### Error handling and logging

- Headless commands: clear stderr message + non-zero exit code.
- TUI: error screen with a readable message; traceback always written to `cvapp.log` (append, one file, next to the project).
- Log level configurable via `cvapp.yaml` or `CVAPP_LOG_LEVEL` env var (default INFO).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `cv_tui.py` | Removed | Monolith replaced by `src/cvapp/` package |
| `src/cvapp/` | New | Package: `cli.py`, `config.py`, `core/discovery.py`, `core/rendercv.py`, `tui/app.py`, `__main__.py` |
| `cv` | Modified | Becomes thin launcher: resolve venv → `PYTHONPATH=src` → `python -m cvapp "$@"` |
| `cv_tui` | Modified | Becomes a one-line alias to `cv` (kept for muscle memory; removal is an open question) |
| `run_cv.sh` | Removed | Superseded by `cv`; its `find_project_dir` walk-up logic is replaced by script-dir resolution in the launcher |
| `Generar CV.command` | Modified | Thin launcher that calls `cv`; adds a `read -p` pause on error so the Finder double-click window doesn't vanish |
| `rendercv_output/` | Kept | Unchanged output location (runtime artifacts, gitignored) |
| `*.yaml` / `*.yml` (10+ CV files) | Kept | Untouched — user data, single source of truth |
| `cvapp.yaml` | New | Optional config: `output_dir`, `open_pdf_after`, `cleanup_intermediate`, `log_level` |
| `pyproject.toml` | New | Dev-tool configuration only (pytest, Ruff, Pyright) |
| `tests/` | New | pytest suite (unit + opt-in smoke) |
| `.gitignore` | New | Excludes venvs, `rendercv_output/`, `__pycache__/`, logs |
| `.venv` | Kept | Sole runtime venv (already has Textual, RenderCV, Typer, Rich) |
| `rendercv-env` | Kept (unused) | Kept on disk as fallback but no longer referenced; optional cleanup later |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Launcher breaks → CV generation blocked entirely (config rule: rollback plan required for wrapper changes) | Med | Launcher stays tiny and structurally identical to the verified `cv_tui` wrapper; old scripts remain functional until the new path passes the full success checklist; single-commit switch so rollback is one `git checkout` |
| No git history → no recovery if something goes wrong | High | `git init` + initial commit of the current state BEFORE any code change; that commit is the rollback anchor |
| Removing `shell=True` changes how RenderCV receives arguments (flag/quoting differences) | Low-Med | Command builder is a pure, unit-tested function; keep the exact same flags that work today; opt-in smoke test renders a real PDF in a temp dir |
| New dev deps (pytest/Ruff/Pyright) install into `.venv` and disturb runtime | Low | Additive `pip install` only, no upgrades of pinned versions; verify `python -m cvapp --version` after install |
| Textual async worker pattern misused → stuck/unresponsive UI | Med | Keep the worker minimal and copy the documented pattern; status bar shows progress; smoke test covers a real render |
| Removing `osascript` changes behavior: quitting the app no longer quits Terminal | Low | Explicit product decision (safer UX); `Generar CV.command` keeps the window open with a pause so double-click users aren't surprised |

## Rollback Plan

1. **Step 0 (before touching anything)**: `git init`, add `.gitignore`, commit the current state as `baseline`. This commit is the anchor.
2. Build the new package alongside the old files — `cv_tui.py`, `cv`, `cv_tui`, `run_cv.sh` stay untouched until the new `cv` launcher passes the success checklist.
3. Only after verification: run the removal task (delete `cv_tui.py` + `run_cv.sh`, rewrite `cv`), committed separately from the feature work.
4. If anything breaks: one `git checkout baseline -- .` restores the exact pre-change state — the app works exactly as it does today because the old files were never modified until the switch.
5. No destructive file operation happens in the same commit as the feature code.

## Dependencies

- `pytest`, `ruff`, `pyright` — dev-only additions to `.venv` (no new runtime deps; Typer/Rich/Textual/RenderCV already installed).
- `git` — available on macOS; wait for user approval of `git init`.
- RenderCV 2.8 — unchanged engine; pinned in `.venv` already.

## Open Questions (for user approval, not assumed)

1. `git init` before implementation — recommended: **yes**.
2. Keep `cv_tui` as an alias to `cv`, or remove it — recommended: keep (free, avoids muscle-memory breakage).
3. Remove `run_cv.sh` — recommended: **yes** (superseded).
4. Keep `Generar CV.command` as thin double-click launcher with a pause — recommended: **yes**.
5. Config at root as `cvapp.yaml` — recommended: **yes** (visible next to the CVs, versionable).
6. Quitting the TUI no longer closes Terminal (osascript removed) — acceptable? Recommended: **yes** (safer).

## Success Criteria

- [ ] `./cv` (no arguments) opens the Textual TUI listing exactly the CVs found by today's glob (same 10+ files, same order).
- [ ] `./cv list` prints the same CV names, one per line, exit code 0.
- [ ] `./cv render Pablo_Gramajo` generates `rendercv_output/Pablo_Gramajo.pdf` without opening it, exit code 0.
- [ ] `./cv render <non-existent-name>` prints a clear error and exits non-zero.
- [ ] `./cv version` prints the version and exits 0.
- [ ] `.venv/bin/python -m cvapp` behaves identically to `./cv`.
- [ ] From the TUI: select a CV → PDF generates, opens, and post-run intermediate files are cleaned; "generate another" returns to the list without reloading the process.
- [ ] Corrupted YAML / missing RenderCV: TUI shows a friendly error screen, app does not crash, traceback lands in `cvapp.log`.
- [ ] Zero occurrences of `shell=True`, `os.execv`, `osascript`, or exit code 10 in `src/`.
- [ ] `pytest` passes (unit suite); `ruff check .` and `pyright` clean.
- [ ] All existing CV YAML files byte-identical before/after the change.
- [ ] Double-clicking `Generar CV.command` still generates a CV.