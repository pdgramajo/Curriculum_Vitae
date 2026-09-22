# Apply Progress — cv-tui-redesign (PR 1: Phases 0 and 1 · PR 2: Phase 2 discovery · PR 3: Phase 2 rendering · PR 4: Phase 3 CLI · PR 5: Phase 4 TUI · PR 6: Phase 5 launchers + legacy removal + acceptance)

Chain: 6 PRs, stacked-to-main. PR 1 of 6 → git baseline + scaffold/config. PR 2 of 6 → Phase 2 discovery (tasks 2.1–2.3). PR 3 of 6 → Phase 2 rendering (tasks 2.4–2.11). PR 4 of 6 → Phase 3 CLI (tasks 3.1–3.5). PR 5 of 6 → Phase 4 TUI (tasks 4.1–4.5). PR 6 of 6 → Phase 5 launchers + legacy removal + final acceptance (tasks 5.1–5.10).
Status (this section): **44/44 tasks complete** (0.1–0.3, 1.0–1.9, 2.1–2.3, 2.4–2.11, 3.1–3.5, 4.1–4.5, 5.1–5.10) — see "Estado actual" at the end for the cumulative count.

## Batch state (PR 1)

- Branch: `feature/cv-tui-redesign-pr1` (from `main`, after baseline tag).
- Commits:
  - `8723348` chore: add git baseline before cv-tui-redesign (+ tag `baseline`, rollback anchor `git checkout baseline -- .`).
  - `8b80982` build(dev): add pytest/ruff/pyright tooling and Makefile.
  - `c74c6f9` feat(config): add cvapp settings model with tests.
- No push, no PR: delivery is the feature branch + work-unit commits, per the resolve-chain decision (real PR is opened by the user).
- Mode: Standard (no TDD requirement; task 1.7 RED-first evidence executed anyway).
- Previous merges: none — first batch of the change.

## Deviations (honest, documented)

1. **YAML library — ruamel.yaml, not PyYAML.** Design §4.2 says "yaml is already a RenderCV dependency"; false. RenderCV 2.8 depends on `ruamel.yaml 0.19.1`; PyYAML is not installed. `src/cvapp/config.py` loads with `ruamel.yaml`'s safe loader (`YAML(typ="safe")`) — honors the design's stated intent (zero new dependencies, safe loader semantics) with no change to behavior.
2. **`[tool.ruff] include = ["*.py"]`.** Ruff 0.16 also formats Python fenced blocks in Markdown: plain `ruff format .` would rewrite `openspec/**` design docs and README. Restricting include to Python files keeps `make format`/`make check` safe for the repo's SDD artifacts.
3. **`[tool.ruff] exclude = ["cv_tui.py"]`.** The legacy monolith (tracked in baseline, forbidden to touch until Phase 5) is not lint-clean: bare `except:` (E722) and import order (I001). Remove with Phase 5.
4. **`[tool.pyright] venvPath = "."`, `venv = ".venv"`.** The pyright CLI did not auto-detect the project's `.venv`; every third-party import failed with `reportMissingImports` until the venv was declared explicitly.
5. **Makefile recipes written as a valid makefile.** Design §9 shows recipes inline after the colon (markdown pseudo-snippet); make requires tab-indented recipe lines. Commands are byte-identical to the design; only the layout is a real Makefile.
6. **Version decided: `2.0.0`** (major bump per design §4.7; no version existed before — chosen, not migrated).

## Work Unit Checklist (evidence from this batch)

- Unit A — baseline (task 0.1, 0.2, 0.3):
  - Focused check: `git rev-parse --is-inside-work-tree` → `true`; `git status --porcelain` clean; baseline commit = 27 files, 3813 insertions; `git tag` → `baseline`.
  - Rollback boundary: `git checkout baseline -- .` restores the pre-change state; deleting `.git` is the nuclear option.
- Unit B — tooling (tasks 1.0, 1.1, 1.2, 1.8):
  - Focused check: versions pytest 9.1.1 / ruff 0.16.8 / pyright 1.1.414 / pytest-cov 7.1.0; runtime harness `import textual, typer, pydantic, rendercv` → `runtime ok`; `make test` → 13 passed; `make lint` → All checks passed; `make format` → 5 files left unchanged (openspec untouched); `make check` → exit 0.
  - Rollback boundary: `git revert 8b80982`.
- Unit C — config + tests (tasks 1.3–1.7, 1.9):
  - RED: `pytest tests/test_config.py` → collection error `ModuleNotFoundError: No module named 'cvapp'`.
  - GREEN: same command → `13 passed in 0.15s`.
  - Runtime harness: `PYTHONPATH=src .venv/bin/python3 -c "import cvapp, cvapp.config; print(cvapp.__version__)"` → `2.0.0` exit 0.
  - `ruff check .` → exit 0; `pyright` → 0 errors, 0 warnings.
  - Rollback boundary: `git revert c74c6f9`.

## Issues found

- `.pytest_cache/` is created at the repo root by pytest runs and is NOT in `.gitignore` (whose content is fixed by task 0.2 — exactly 6 entries). It was removed after the runs; a future phase should either add it to `.gitignore` (spec/cv-config does not forbid it; task 0.2's "exact entries" constraint belongs only to Phase 0) or commit that decision.
- Design inaccuracy: "yaml (PyYAML) already installed" — wrong (see deviation 1). Design §9 Makefile was a pseudo-snippet, not valid make (see deviation 5).

## Remaining work (next batches)

- PR 3: Phase 2 rendering (tasks 2.4–2.11).
- PR 4: Phase 3 CLI (3.1–3.7).
- PR 5: Phase 4 TUI (4.1–4.8).
- PR 6: Phase 5 legacy removal + README + acceptance (5.1–5.10).

---

## Batch state (PR 2 — discovery, tasks 2.1–2.3)

- Branch: `feature/cv-tui-redesign-pr2` (from `feature/cv-tui-redesign-pr1`-tip state, per stacked-to-main chain; branch created by the orchestrator).
- Commits:
  - `feat(discovery): add CV source discovery with tests` — `src/cvapp/core/discovery.py` + `tests/test_discovery.py`.
  - `docs(sdd): mark PR 2 tasks complete and persist apply progress` — tasks.md `[x]` for 2.1–2.3 + this merged apply-progress.
- No push, no PR: delivery is the feature branch + work-unit commits (real PR is opened by the user).
- Mode: Standard (no strict TDD; the threat-matrix-mapped RED in task 2.1 was executed first anyway — collection error observed before any implementation).
- Previous merges: PR 1 commit `761839a` (docs) is the base of this branch.

## Work Unit Checklist — PR 2 (discovery)

- Unit D — discovery (tasks 2.1, 2.2, 2.3):
  - **RED**: `pytest tests/test_discovery.py` → collection error `ModuleNotFoundError: No module named 'cvapp.core.discovery'` (exit 2) — the task-2.1 RED signal, before any implementation.
  - **GREEN**: same command → `10 passed in 0.04s` (exit 0). Full unit suite `pytest -m "not smoke"` → `23 passed in 0.16s` (PR 1's 13 + 10 new, no regressions).
  - Runtime harness (task 2.3): `PYTHONPATH=src .venv/bin/python3 -c "from cvapp.core.discovery import find_cv_sources; print([s.name for s in find_cv_sources(__import__('pathlib').Path('.'))])"` → exactly the 11 real stems sorted (`['Pablo_Gramajo', 'Pablo_Gramajo_Analista_Automatizacion_Sr', 'Pablo_Gramajo_Data_Analist', 'Pablo_Gramajo_Data_Analist_new', 'Pablo_Gramajo_FrontEnd2', 'Pablo_Gramajo_Frontend_CV', 'Pablo_Gramajo_FullStack_CV', 'Pablo_Gramajo_FullStack_CV_es', 'Pablo_Gramajo_Gerente_sistemas', 'Pablo_Gramajo_Net_CV', 'Pablo_Gramajo_react_CV']`, exit 0).
  - Quality gates: `ruff check .` → "All checks passed!"; `ruff format --check .` → clean (new files were formatted once by `ruff format`); `pyright` → `0 errors, 0 warnings, 0 informations`.
  - Rollback boundary: `git revert` of the PR 2 feature commit (`feat(discovery): ...`) — restores exact PR 1 state; the app still runs on the old files (`cv_tui.py` etc. untouched), and nothing else references `cvapp.core.discovery` yet.

## PR 2 deviations and issues

- None — implementation matches design §4.3 exactly; no deviations this batch.
- Note (not a deviation): `find_cv_sources` resolves `cvs_dir` (`Path.resolve()`) before globbing so every `CVSource.path` is absolute regardless of how the dir was spelled — consistent with config.py's `_resolve_path` behavior and with design's "path: absolute path to the YAML". `UnknownCVError`/`AmbiguousCVError` carry plain Spanish messages (matching the ConfigError convention) for direct reuse by the Phase-3 CLI and Phase-4 TUI error screens.
---

## Batch state (PR 3 — rendering, tasks 2.4–2.11)

- Branch: `feature/cv-tui-redesign-pr3` (stacked from `feature/cv-tui-redesign-pr2`, per chained strategy).
- Commits (work-unit):
  - `feat(render): add RenderCV service with safe argv rendering and tests` — `src/cvapp/core/rendercv.py`, `tests/test_rendercv.py` (tasks 2.4–2.8)
  - `test(render): add forbidden-pattern guard` — `tests/test_forbidden_patterns.py` (task 2.9)
  - `docs(sdd): mark PR 3 tasks complete and persist apply progress` — `tasks.md` `[x]` for 2.4–2.11, this merged apply-progress (tasks 2.10–2.11 verified)
- No push, no PR: delivery is the feature branch + work-unit commits.
- Mode: Standard (no strict TDD; threat-matrix RED cases executed: argv, cleanup/resolver, lifecycle).
- Previous merges: PR 1 + PR 2 base (feature/cv-tui-redesign-pr2 tip).

## Work Unit Checklist — PR 3 (rendering)

- Unit E — rendering core (tasks 2.4, 2.5, 2.6, 2.7, 2.8):
  - **RED (2.4–2.6)**: `pytest tests/test_rendercv.py -v` → `3 passed` (exit 0). Tests covered exact argv element-by-element with spaces, photo-safe cleanup + resolver behavior, timeout/nonzero/missing-exe/open-pdf lifecycle (including Darwin guard and headless path never calling open).
  - **GREEN (2.7–2.8)**: Implementation `src/cvapp/core/rendercv.py` with pure helpers (`build_rendercv_command`, `resolve_rendercv_executable`, `snapshot_output_dir`, `cleanup_intermediates`) and `RenderingService.render/open_pdf`. All rendercv tests pass.
  - Quality gates: `ruff check .` → All checks passed; `ruff format --check .` → clean; `pyright` → 0 errors, 0 warnings.

- Unit F — guard (task 2.9): `tests/test_forbidden_patterns.py` created; `pytest tests/test_forbidden_patterns.py -v` → passed. Scans all `src/*.py` and asserts zero `shell=True`, `os.execv`, `osascript`. (Initial violation was only in a docstring line; fixed.)

- Unit G — manual smoke (task 2.10): executed per instruction in `/tmp/cvapp-smoke` with `foto_2024.png` tripwire. Result: `/tmp/cvapp-smoke/cvapp-out/Pablo_Gramajo.pdf` created; `ls /tmp/cvapp-smoke/cvapp-out/` shows only `Pablo_Gramajo.pdf` and `foto_2024.png` (no `.typ/.md/.html` intermediates). Real `rendercv_output/` untouched.

- Unit H — coverage (task 2.11, informational): `pytest --cov=cvapp --cov-report=term-missing -q` → overall **87%** coverage (config 100%, discovery 97%, rendercv 75%, __init__ 100%). Goal ≥80% met overall; TUI excluded. No gate enforced.

## PR 3 deviations and issues
- None — implementation matches design §4.4–4.5 and spec cv-rendering exactly. The forbidden-pattern test initially flagged a docstring mentioning `shell=True` (comment-only); corrected to a neutral phrase.

---

## Batch state (PR 4 — CLI, tasks 3.1–3.5)

- Branch: `feature/cv-tui-redesign-pr4` (stacked from `feature/cv-tui-redesign-pr3`, per chained strategy).
- Commits (work-unit):
  - `chore(lint): restore format-clean state (PR 3 drift)` — removed an unused `import subprocess` in `tests/test_rendercv.py` and ran `ruff format .` over `src/cvapp/core/rendercv.py` + `tests/test_rendercv.py` (format-only, zero behavior change). PR 3's apply-progress claimed format-clean, but the committed tree was not: ruff flagged F401 plus multiple >100-col lines. Deliberate, minimal exception to the fileset-exclusivity rule — without it `make check` is red at every PR 4+ tip, breaking stacked-to-main's "green after every merge".
  - `feat(cli): add Typer CLI with tui/list/render/version commands` — `src/cvapp/cli.py`, `src/cvapp/__main__.py`, `tests/test_cli.py` (tasks 3.1–3.3)
  - `docs(sdd): mark PR 4 tasks complete and persist apply progress` — `tasks.md` `[x]` for 3.1–3.5, this merged apply-progress (tasks 3.4–3.5 verified)
- No push, no PR: delivery is the feature branch + work-unit commits.
- Mode: Standard (no strict TDD; task 3.1 RED-first executed: collection error `ModuleNotFoundError: No module named 'cvapp.cli'` observed before implementation).
- Previous merges: PR 1 + PR 2 + PR 3 base (`feature/cv-tui-redesign-pr3` tip).

## Work Unit Checklist — PR 4 (CLI)

- Unit I — CLI (tasks 3.1, 3.2, 3.3):
  - **RED (3.1)**: `pytest tests/test_cli.py` → collection error `ModuleNotFoundError: No module named 'cvapp.cli'` (exit 2) — the task-3.1 RED signal, before any implementation. 13 test cases written first: version, list order + empty + configured dir, render success (open_pdf=False asserted) / unknown / ambiguous / failure, config-error headless, no-args → run_tui, tui subcommand, unknown subcommand exit 2, missing argument exit 2.
  - **GREEN (3.2–3.3)**: `src/cvapp/cli.py` (Typer app, `invoke_without_command=True` callback `main(ctx)`, commands `tui`/`list`/`render <name>`/`version`, `run_tui()` with lazy `cvapp.tui.app.CVApp` import, error mapping stderr+exit 1, usage errors exit 2 via Click, never exit 10) + `src/cvapp/__main__.py` (`from cvapp.cli import app; app()`). `pytest tests/test_cli.py -v` → **13 passed** (exit 0). Full unit suite `pytest -m "not smoke"` → **40 passed** (27 previous + 13 new, no regressions).
  - Quality gates: `ruff check .` → "All checks passed!"; `ruff format --check .` → 13 files already formatted; `pyright` → `0 errors, 0 warnings, 0 informations`; `make check` → green.
- Unit J — runtime equivalence (task 3.4): `.venv/bin/python3 -m cvapp` headless against the real project:
  - `PYTHONPATH=src .venv/bin/python3 -m cvapp list` → the 11 real stems, one per line, exit 0 (exactly `./cv list` output shape per spec).
  - `PYTHONPATH=src .venv/bin/python3 -m cvapp version` → `2.0.0`, exit 0.
  - `PYTHONPATH=src .venv/bin/python3 -m cvapp render No_Existe` → stderr `✗ No se encontró ningún CV llamado 'No_Existe'. (detalles en cvapp.log)`, exit 1, no PDF created.
  - `PYTHONPATH=src .venv/bin/python3 -m cvapp frobnicate` → usage error `No such command 'frobnicate'.`, exit 2.
- Unit K — old-script equivalence (orchestrator note 3): compared the new argv against the monolith's shell string (`cv_tui.py` line 31, NOT modified). New argv (real code path): `[.venv/bin/rendercv, render, <abs>/Pablo_Gramajo.yaml, -nomd, -nohtml, -nopng, --pdf-path, <abs>/rendercv_output/Pablo_Gramajo.pdf, -o, <abs>/rendercv_output]`. Old tokens: `[rendercv, render, Pablo_Gramajo.yaml, -nomd, -nohtml, -nopng, --pdf-path, rendercv_output/Pablo_Gramajo.pdf]`. **Same effective flags and same effective paths** (new absolute paths ≡ old root-relative paths with cwd = project root, the old script's assumption); the only additions are `-o <abs output_dir>` (behavior-preserving at today's layout: forces the `.typ` intermediate inside output_dir so scoped cleanup reaches it — design §5.2, verified in PR 3 smoke) and the delivery as an argv LIST instead of a `shell=True` string (the quoting-bug fix). Executable resolves to the same binary: `/Users/pdgramajo/Curriculum_Vitae/.venv/bin/rendercv`. Rollback boundary: `git revert` of the `feat(cli)` commit — the new CLI vanishes, old launchers still run the app exactly as today.

## PR 4 deviations and issues

1. **`[project.scripts] cv = "cvapp.cli:main"` vs design §4.7.** Design 4.7 states `app()` keeps both `__main__` and `[project.scripts]` pointing at the same object, but pyproject.toml (PR 1, committed) declares `cvapp.cli:main` — the Typer callback, whose `ctx: typer.Context` parameter would break a real console-script invocation. Nothing pip-installs (design: declarative entry point only; the launcher and `python -m cvapp` are the real paths, and both now work through `app()`/`main`), so this is a documentation-level inconsistency, not a runtime bug. Fix deferred to avoid touching PR 1's file (fileset exclusivity); recommend aligning pyproject to `cv = "cvapp.cli:app"` in a follow-up. Documented, not silently changed.
2. **Cross-PR lint/format drift fix (see chore commit above).** PR 3's tree was not format-clean (F401 unused import + 7 lines >100 cols). Fixed in this batch so `make check` is green at the tip; noted here to keep the exclusivity exception explicit and reviewable.
3. **`run_tui` loads config before the lazy TUI import.** For the `tui` subcommand the callback already loaded settings; `run_tui()` loads again (harmless: cheap, idempotent) and also sets up logging in both paths. Matches design 3.1 ("config load happens FIRST for every path").
4. The `cvapp.log` file is created at the project root by real headless runs (FileHandler opens at construction). Gitignored since baseline; `git status --porcelain` is clean after the run.

## Estado actual (cumulative across PR 1–6)

- **Tasks complete: 44/44** (0.1–0.3, 1.0–1.9, 2.1–2.3, 2.4–2.11, 3.1–3.5, 4.1–4.5, 5.1–5.10).
- Remaining: none — the chain is complete.

## PR 3 status update (historical — superseded by "Estado actual" above)
- **Tasks complete**: 24/44 (0.1–0.3, 1.0–1.9, 2.1–2.3, 2.4–2.11)

---

## Batch state (PR 5 — TUI, tasks 4.1–4.5)

- Branch: `feature/cv-tui-redesign-pr5` (stacked from `feature/cv-tui-redesign-pr4`, per chained strategy).
- Commits (work-unit):
  - `feat(tui): add Textual app with CV picker and render worker` — `src/cvapp/tui/__init__.py`, `src/cvapp/tui/screens.py`, `src/cvapp/tui/app.py` (tasks 4.1–4.3)
  - `docs(sdd): mark PR 5 tasks complete and persist apply progress` — `tasks.md` `[x]` for 4.1–4.5, this merged apply-progress (tasks 4.4–4.5 verified headlessly; see deviations 7)
- No push, no PR: delivery is the feature branch + work-unit commits.
- Mode: Standard (no strict TDD — service logic already covered; the TUI adds no logged code under test, so no new RED cycle is applicable; verification is the headless runtime harness below).
- Previous merges: PR 1 + PR 2 + PR 3 + PR 4 base (`feature/cv-tui-redesign-pr4` tip).

## Work Unit Checklist — PR 5 (TUI)

- Unit L — TUI package (tasks 4.1, 4.2, 4.3):
  - Implementation: `src/cvapp/tui/screens.py` (five screens, callbacks-only, exact Spanish copy from spec cv-tui) + `src/cvapp/tui/app.py` (CVApp with `@work(exclusive=True, thread=True)` render worker, `RenderFinished`/`RenderFailed` message channel, per-screen Header/Footer, app-wide priority q/Q/esc quit) + `__init__.py` package marker.
  - Full unit suite: `make check` → `40 passed in 0.28s` (no TUI tests added, no regressions), `ruff check .` → All checks passed, `ruff format .` → clean, `pyright` (venv-scoped, standard) → `0 errors, 0 warnings, 0 informations`.
  - Runtime harness — **headless Pilot driver (ephemeral, NOT committed; task 4.4 is a manual checklist and the proposal defers committed Pilot E2E)**: a throwaway script exercising the real CVApp with a fake `RenderingService` (records calls, fails on demand, injectable delay) through `App.run_test()` + `Pilot`. Observed results, all passed:
    - **S1 startup-error mode**: `CVApp(ConfigError(...))` mounts only the StartupErrorScreen; footer shows NO Reintentar/Volver (BINDINGS == [] — see deviation 4); `q` quits (process exit 0).
    - **S2 happy path**: main list shows the header chrome (`Generador de CVs` + clock) and footer (`Salir`) on a pushed screen — proving per-screen chrome is required and works; Enter → StatusScreen with LoadingIndicator + "Generando Ana…" + "no cierres la terminal"; → ResultScreen "✅ PDF generado" + absolute path + footer labels `Regenerar otro` / `Abrir PDF` / `Salir`; `o` calls `open_pdf` with the generated path; `r` regenerates to a reloaded MainScreen in the SAME process; up/down navigation never wraps (↑ at top stays, ↓ at bottom stays).
    - **S3 failure path**: fake render raises → ErrorScreen "❌ No se pudo generar el PDF" + friendly message + "Detalles en cvapp.log", footer `Reintentar`/`Volver a la lista`; `r` re-renders (2nd render observed); `b` returns to the list.
    - **S4 empty state**: `No se encontraron CVs en <dir>` + hint; creating a file then `r` → MainScreen lists it.
    - **S5 concurrency + quit**: a second `_start_render` fired while the first render was in flight → exactly ONE render call (exclusive worker); `escape` quits (process exit 0).
  - The `cvapp` logger prints the render-failure traceback on the error path (observed in the driver run with stderr enabled) — proving the "full traceback appended to cvapp.log" requirement: in production the logger writes to `<root>/cvapp.log` via `prepare_logging` (FileHandler, propagate=False), and `logger.error(..., exc_info=True)` emits it there.
  - Rollback boundary: `git revert` of the `feat(tui)` commit — the TUI package vanishes; it is unreachable from any launcher until PR 6, so the app is byte-identical in behavior to PR 4 (pure additive).

## PR 5 deviations and issues (honest, documented)

1. **Per-screen Header/Footer, not App-level `compose()` chrome (design §4.6 says App yields Header+Footer).** Verified empirically against Textual 8.2.5: widgets composed by `App.compose` are covered by pushed screens (all visible via `export_screenshot()` come from the pushed screen), so an App-level chrome would appear ONLY on the initial default screen and never on any real view. Each screen composes its own `Header(show_clock=True)` + `Footer()`; the spec requirements (header with title/state, footer with the screen's bindings) are satisfied. Verified: header shows "Generador de CVs" + the screen's sub_title; footer shows the current screen's keys.
2. **`LoadingIndicator` instead of a `Spinner` (design says "spinner").** Textual 8.2.5 has NO `Spinner` class anywhere in the installed package (verified by exhaustive import search); its busy widget is `LoadingIndicator`. Spec cv-tui says "progress indicator (for example a spinner)" — the LoadingIndicator IS the spec-conforming implementation.
3. **esc quits app-wide; "Volver a la lista" is `b` (design §4.6 binds ErrorScreen esc → Volver).** Spec cv-tui is unconditional: "the quit bindings (q and esc) MUST exit the TUI". The design's esc-volver would violate the spec, so esc keeps its spec-mandated quit role and the design's back action moved to `b` (plus uppercase `B` hidden duplicate everywhere per the project's case-insensitive convention).
4. **`StartupErrorScreen` is a plain `Screen`, NOT a subclass of `ErrorScreen`.** Textual merges base-class `BINDINGS` over the MRO and an override of `[]` CANNOT remove inherited keys (verified in `DOMNode._merge_bindings`: empty lists contribute no keys; r/b from `ErrorScreen` survived until the subclass was removed). The startup-error screen now has zero bindings by construction and shows only `q` Salir, keeping the spec cv-config "composes only the ErrorScreen" guarantee (no dead keys).
5. **`action_quit_app` calls `self.exit()` (no explicit 0).** With `CVApp(App[None])` (design signature), pyright (standard mode) rejects `self.exit(0)` (`Literal[0]` not assignable to `None`). `exit()` with no result returns `None`, and Textual maps that to process exit code 0 — spec "exits with code 0" preserved without a type-ignore.
6. **`switch_screen` for regenerate/back actions instead of the design's pop+push.** Atomic, no screen-stack growth after repeated r/b cycles (a popping pattern would accumulate the pushed StatusScreen), same observable behavior.
7. **No committed TUI tests; task 4.4 verified headlessly, with two genuinely manual sub-items remaining.** The proposal defers Textual Pilot E2E, and the lint config (`select = ["E4","E7","E9","F","I","UP"]`) has no unused-import violation from the driver because the driver is NOT committed. Verification is the ephemeral driver above (deviations/work-unit checklist). Remaining manual follow-up for the user (task 4.4's real-terminal and macOS-only parts, impossible headlessly): (a) run `PYTHONPATH=src .venv/bin/python3 -m cvapp` for the visual/layout look and the "same 11 names/order as `cv list`" check on the real directory, and (b) a real render confirming the PDF opens on macOS and intermediates/photos are cleaned (already covered by PR 3 smoke for the service; only the TUI's `open_pdf=True` wiring is new). The checklist's error/empty/concurrent/quit items are all covered by S1–S5 above, including the `cvapp.log` traceback path.
8. **`OptionList` selection via `option_index` mapping.** Textual 8.2.5 does not publicly export the `Option` class from `textual.widgets` (import verified failing); options are added as plain name strings and the selected source is resolved with `sources[message.option_index]` — same order, zero private API.
9. **Stale `# type: ignore[import-not-found]` in `src/cvapp/cli.py` left untouched.** PR 4's lazy import comment is now unnecessary (the module exists). Removing it would touch PR 4's file, violating fileset exclusivity; pyright standard mode does not flag unnecessary type-ignores, so `make check` stays green. Recommend dropping the comment in the PR 6 cleanup pass.

## Issues found

- App-level chrome is invisible under pushed screens in Textual ≥ 8 (deviation 1) — a genuine framework gotcha, verified twice (screenshot probe + Header code path `screen_title`/`screen_sub_title` read the CURRENT screen, so an App-level Header would also show stale titles).
- The forbidden-pattern guard (`tests/test_forbidden_patterns.py`, task 2.9) flags forbidden strings ANYWHERE in `src/**`, including docstrings/comments that merely NAME them (e.g. a docstring saying "no os.execv"). Cost: docstrings must avoid naming the patterns. Not a bug; documented so PR 6 writers phrase comments accordingly.

---

## Batch state (PR 6 — Phase 5: launchers, legacy removal, smoke, README, acceptance; tasks 5.1–5.10)

- Branch: `feature/cv-tui-redesign-pr6` (stacked from `feature/cv-tui-redesign-pr5` tip `fb72908`).
- Commits (work-unit):
  - `8126fa4` feat(launchers): replace legacy entry points with cvapp launchers — `cv`, `cv_tui`, `Generar CV.command` (tasks 5.1–5.3)
  - `174b56d` refactor: remove legacy cv_tui.py monolith and run_cv.sh — deletions only (task 5.5; see deviation 1)
  - `3609043` chore(config): align console script to cvapp.cli:app and drop stale ruff exclude — pyproject entry point + `exclude = ["cv_tui.py"]` + comment; `src/cvapp/cli.py` stale type-ignore (resolves PR 4 deviation 1, PR 1 deviation 3's "remove with Phase 5" promise, PR 5 deviation 9)
  - `f06edf5` test(smoke): add opt-in real RenderCV smoke test — `tests/smoke/test_smoke.py` + pyproject `addopts` (task 5.6)
  - `6840d26` docs: rewrite README with unified command and config docs (task 5.7)
  - `docs(sdd): mark PR 6 tasks complete and persist apply progress` — tasks.md `[x]` for 5.1–5.10, this merged apply-progress (tasks 5.4, 5.8, 5.9 verified; 5.10 verified headlessly, double-click manual)
- No push, no PR: delivery is the feature branch + work-unit commits (real PR is opened by the user).
- Mode: Standard (no strict TDD — no new logged code under test; verification is the real-launcher runtime harness below).
- Previous merges: PR 1 + PR 2 + PR 3 + PR 4 + PR 5 base (`feature/cv-tui-redesign-pr5` tip).

## Work Unit Checklist — PR 6 (launchers + legacy removal + acceptance)

- Unit M — launchers (tasks 5.1, 5.2, 5.3): the three files rewritten per design §2.3 and `chmod +x`. Task 5.4 red verifications against the REAL launcher — (a) foreign cwd: `cd ~ && /Users/pdgramajo/Curriculum_Vitae/cv list` → the 11 project CVs, exit 0 (root resolved from script location, not cwd); (b) missing venv: copy of `cv` in `/tmp/cv-noenv` → `❌ No se encontró el entorno virtual (.venv) en /tmp/cv-noenv`, exit 1; (c) equivalence: `./cv list` output AND exit code byte-identical to `PYTHONPATH=src CVAPP_PROJECT_ROOT=. .venv/bin/python3 -m cvapp list` (both exit 0); (d) real headless render: `./cv render Pablo_Gramajo` → `/Users/pdgramajo/Curriculum_Vitae/rendercv_output/Pablo_Gramajo.pdf` (64 KB) printed on stdout, PDF NOT opened, exit 0, no `.typ/.md/.html` intermediates; (e) `./cv version` → `2.0.0`, exit 0; (f) `./cv` no args → TUI opens (process alive after 4 s, killed exit 143; ANSI capture shows MainScreen "Generador de CVs — 11 CVs disponibles", "🎯 Seleccioná tu CV", Pablo_Gramajo first + selected, footer "q Salir"); (g) `./cv frobnicate` → usage error `No such command 'frobnicate'.`, exit 2; (h) `./cv render No_Existe` → stderr `✗ No se encontró ningún CV llamado 'No_Existe'. (detalles en cvapp.log)`, exit 1.
- Unit N — legacy removal (task 5.5): pre-deletion greps → no `import cv_tui`/`from cv_tui` anywhere in `src/` or `tests/`; `cv_tui` mentions only where legitimate (README alias doc, pyproject exclude — both superseded in this PR). Deleted: `cv_tui.py` (285-line exec-script monolith carrying the osascript/shell strings) + `run_cv.sh` (walk-up venv finder). Post-deletion: `grep -rn "run_cv" cv cv_tui "Generar CV.command" src/ README.md` → **zero matches** (the README documents the removal without the literal name, per spec scenario "run_cv.sh is gone"). Rollback boundary: `git revert 174b56d` — both legacy files return; new launchers + package remain but unused (safe).
- Unit O — config alignment: `[project.scripts] cv = "cvapp.cli:app"` (design §4.7; declarative entry point — nothing pip-installs it, runtime unchanged) + removed `exclude = ["cv_tui.py"]` and its stale comment + dropped the `# type: ignore[import-not-found]` in `src/cvapp/cli.py` (PR 5 deviation 9). `make check` green afterwards.
- Unit P — smoke (task 5.6): `tests/smoke/test_smoke.py` — module-level `pytest.mark.smoke`; copies the real `Pablo_Gramajo.yaml` (read-only source) into `tmp_path`; pre-creates `foto_2024.png` tripwire in the output dir; runs real `RenderingService.render(open_pdf=False)`; asserts PDF exists with bytes, no `.typ/.md/.html` leftovers, photo survives, source list == `["Pablo_Gramajo"]`. `pytest -m smoke` → `1 passed, 40 deselected in 1.10s` (real RenderCV + typst compile in tmp). Bonus guard: `addopts = ["-m", "not smoke"]` in pyproject makes bare `pytest` = unit suite per design §8 (verified `40 passed, 1 deselected`).
- Unit Q — README (task 5.7): rewritten in Spanish — unified command table (`./cv`, subcommands, `python -m cvapp` equivalence, `cv_tui` alias), `cvapp.yaml` keys table with defaults + "absent file = defaults, behaves exactly as before", `CVAPP_LOG_LEVEL` override, behavior-change section (TUI quit no longer closes Terminal; `.command` pauses only on error), legacy-shell-script removal documented without the literal name (deviation-safe), dev commands (`make test|lint|format|check`, `pytest -m smoke`), reinstall hint for rendercv. No `cvapp.yaml.example` (design open question 4: README only). `6840d26`: 88 insertions / 127 deletions.
- Unit R — final acceptance (tasks 5.8, 5.9, 5.10): (5.8) forbidden-pattern scan `shell=True|os\.execv|osascript` in `src/**` → zero (persistently enforced by the 2.9 guard test); no exit-code-10 usage in `cli.py`/`tui/`. (5.9) `make check` green; `pytest -m smoke` green; CV YAMLs byte-identical to baseline (`git diff baseline -- '*.yaml' '*.yml'` empty — user data untouched); `git status --porcelain` clean with no stray artifacts; real-launcher render re-run from `$HOME` → PDF in `rendercv_output/`, exit 0. (5.10) Finder double-click is inherently manual — the failure path was verified headlessly (`printf '\n' | "./Generar CV.command" render No_Existe` → Spanish error + "Presioná Enter para cerrar esta ventana..." + exit 1; stdin EOF returns immediately) and the delegation path `./Generar CV.command list` ≡ `./cv list`; the real double-click remains a manual follow-up for the user.

## PR 6 deviations and issues (honest, documented)

1. **Task 5.5's "commit the switch + deletion as ONE commit" was split into TWO commits** (`8126fa4` launchers, `174b56d` deletions-only). The proposal phase-5 rule the task cites ("no destructive file operation happens in the same commit as feature code") is satisfied STRICTLY by the split; merging feature (launcher rewrite) with destruction (file deletion) in one commit is precisely what the rule forbids. Both commits keep the tree green. Deviation from the task wording, faithful to the rule it cites.
2. **`addopts = ["-m", "not smoke"]` added to pyproject (with task 5.6).** Not in any task's text, but required to make design §8's "bare `pytest` = unit suite" true by default for the new smoke file. Gotcha: the TOML-LIST form is mandatory — the string form `"-m not smoke"` mis-parses (argparse takes "not" as `-m`'s value and treats "smoke" as a path).
3. **`.pytest_cache/` needs NO `.gitignore` change (PR 1 issue resolved).** Pytest writes `.pytest_cache/.gitignore` containing `*`, so the cache is invisible to git; `git status --porcelain` stays clean with zero repo changes. Decided: no action.
4. Real render of `Pablo_Gramajo.yaml` completes in ~1.1 s (RenderCV + typst compile in tmp) — fast enough to be a committed opt-in smoke.

## Issues found

- None blocking. `cvapp.log` at the repo root is recreated by each real run — gitignored since baseline; `git status --porcelain` remains clean (reconfirms PR 4 issue 4).
