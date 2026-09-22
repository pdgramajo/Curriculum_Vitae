# Design: CV TUI Redesign — One Command, One Professional Interface

Change: `cv-tui-redesign`
Specs: `cv-cli`, `cv-tui`, `cv-rendering`, `cv-config` (all read)
Proposal: `openspec/changes/cv-tui-redesign/proposal.md`
Date: 2026-09-22

---

## 1. Executive Summary

We replace the 258-line monolith `cv_tui.py` and its four fragile Bash wrappers with a small Python package, `src/cvapp/`, split into five clear responsibilities: configuration, CV discovery, PDF rendering, the command-line interface, and the Textual TUI. Each module is small, each has one job, and each is testable in isolation. The user experience does not change shape: one command (`./cv`) opens the TUI, you pick a CV, you get a PDF — but now every fragile piece (shell-quoting, cleanup that deletes photos, Terminal-quitting hacks, untested globals) has a tested, explicit replacement.

The architecture is deliberately simple and pedagogical. There is **one** service object (`RenderingService`) that knows how to talk to RenderCV; the TUI is a thin presentation layer that calls it from a Textual **worker thread** so the interface never freezes; discover is a pure function that returns a clean list of CV sources; config is a pydantic model whose parsing errors name the exact offending key. There are no layers "for the sake of architecture": if a module does not exist to isolate a real failure mode or a real test surface, it does not exist.

Every technology choice was verified against the actual machine: Textual 8.2.5, Typer 0.24.1, RenderCV 2.8, Python 3.12.13 are already installed in `.venv`; pydantic 2.13 is already there as a RenderCV dependency (so config validation costs zero new dependencies); pytest, Ruff and Pyright are the only additions, all dev-time only. A key finding from reading RenderCV 2.8's source: `--pdf-path` is resolved **relative to the input YAML file** unless it is absolute, and RenderCV copies the user's photo into the output folder during rendering — two facts that drive the absolute-path and snapshot-cleanup decisions below.

---

## 2. Folder / Package Structure

### 2.1 Target tree

```
Curriculum_Vitae/
├── cv                         # MODIFIED: thin bash launcher (was: numeric menu script)
├── cv_tui                     # MODIFIED: one-line bash alias that execs ./cv "$@"
├── Generar CV.command         # MODIFIED: thin double-click launcher -> ./cv + pause on error
├── cv_tui.py                  # REMOVED: the 258-line monolith (superseded by src/cvapp/)
├── run_cv.sh                  # REMOVED: superseded by the cv launcher
├── cvapp.yaml                 # OPTIONAL (NOT shipped): user config; absent = defaults
├── .gitignore                 # NEW: .venv/, rendercv-env/, rendercv_output/, __pycache__/, cvapp.log, .DS_Store
├── pyproject.toml             # NEW: declared entry point + dev-tool config (pytest/ruff/pyright) — see 2.2
├── src/
│   └── cvapp/
│       ├── __init__.py        # __version__ = "2.0.0" — single source of truth for the version
│       ├── __main__.py        # python -m cvapp -> cli.main() (3 lines)
│       ├── cli.py             # Typer app: tui/list/render/version, exit codes, error reporting
│       ├── config.py          # Settings pydantic model + cvapp.yaml loading + path resolution + logging setup
│       ├── core/
│       │   ├── __init__.py    # empty marker (namespace)
│       │   ├── discovery.py   # find_cv_sources() + resolve_cv_by_name() — pure, no I/O side effects beyond glob
│       │   └── rendercv.py    # RenderingService: build argv, run subprocess, timeout, cleanup, open PDF
│       └── tui/
│           ├── __init__.py    # empty marker
│           ├── app.py         # CVApp (Textual App): bindings, screen routing, worker launch, message handlers
│           └── screens.py     # MainScreen, EmptyStateScreen, StatusScreen, ResultScreen, ErrorScreen
├── tests/
│   ├── conftest.py            # shared fixtures (project root factory, sample CV files, fake subprocess)
│   ├── test_discovery.py      # unit tests for core/discovery.py
│   ├── test_config.py         # unit tests for config.py
│   ├── test_rendercv.py       # unit tests for RenderingService (argv, cleanup, timeout, open)
│   ├── test_cli.py            # unit tests for cli.py (subcommands, exit codes)
│   └── smoke/
│       └── test_smoke.py      # OPT-IN (pytest -m smoke): real RenderCV render in tmp dir
├── *.yaml / *.yml  (10+ CVs)  # KEPT byte-identical — user data, single source of truth
├── rendercv_output/           # KEPT — runtime artifacts, gitignored
├── .venv/                     # KEPT — sole runtime venv (Textual, Typer, Rich, RenderCV + new dev deps)
└── rendercv-env/              # KEPT on disk but UNUSED and gitignored (decision in 4.8)
```

What lives in each file is one line in the tree above; section 4 expands each module with signatures and rationale.

### 2.2 `pyproject.toml` — entry point declaration + dev tools

```toml
[project]
name = "cvapp"
version = "2.0.0"          # kept in sync with src/cvapp/__init__.py (see 4.7)

[project.scripts]
cv = "cvapp.cli:main"     # declares the canonical entry point

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["smoke: opt-in real RenderCV render (invoke with pytest -m smoke)"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP"]

[tool.ruff.format]
quote-style = "double"

[tool.pyright]
typeCheckingMode = "standard"
```

Two things to understand here (pedagogical note):

- `[project.scripts]` declares *what the `cv` command is* — it documents the intended entry point in one authoritative place, exactly what the spec's "version defined in one place" requirement asks for. It does **not** mean the app is installed with `pip`: there is no `[build-system]`, and nothing runs `pip install` anywhere. At runtime, the `cv` launcher puts `src/` on `PYTHONPATH` and calls the same `cvapp.cli:main` through `python -m cvapp`. Both paths reach the same function — declarative entry point and script runner agree.
- `[tool.ruff.lint] select` is deliberately the **safety subset**, not the full rule zoo: `E4/E7/E9` catch real style errors like tab/space mixes and `continue` outside loops; `F` (pyflakes) catches undefined names and unused imports — the highest-value checks for a learner; `I` (isort) and `UP` (pyupgrade) keep imports sorted and nudge toward modern syntax, and both are auto-fixable with `ruff check --fix`. Line-length is set to 100 instead of the default 88 to avoid style fights on `--pdf-path` lines; `ruff format` handles formatting so linting stays focused on bugs.

### 2.3 Launcher `cv` (final content)

```bash
#!/bin/bash
# Thin launcher: resolves the project from ITS OWN location, runs the app in .venv.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -x "$SCRIPT_DIR/.venv/bin/python3" ]; then
    echo "❌ No se encontró el entorno virtual (.venv) en $SCRIPT_DIR" >&2
    exit 1
fi

export PATH="$SCRIPT_DIR/.venv/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export CVAPP_PROJECT_ROOT="$SCRIPT_DIR"

exec "$SCRIPT_DIR/.venv/bin/python3" -m cvapp "$@"
```

Why each line exists (mapped to the `cv-cli` spec):

- `SCRIPT_DIR=...` — the spec requires root resolution from the launcher's own location, never the caller's cwd. The old `run_cv.sh` walked *up* from cwd looking for `.venv`; we resolve *down* from `BASH_SOURCE[0]`, which is correct even when invoked by absolute path from `$HOME`.
- `PATH="$SCRIPT_DIR/.venv/bin:$PATH"` — the old scripts used `source activate` which prepended the venv's `bin/` to `PATH`, making `rendercv` findable. We `exec` the interpreter directly instead of sourcing activate (cleaner: no shell-state side effects, no `deactivate` bookkeeping), so we must export the venv `bin` dir ourselves. `RenderingService` also resolves the executable Python-side (4.5), so this export is defense in depth, not a single point of failure.
- `PYTHONPATH="$SCRIPT_DIR/src..."` — makes `cvapp` importable without `pip install`, per the proposal's "unpackaged scripts" convention. `":${PYTHONPATH:+...}"` preserves any pre-existing value instead of clobbering it.
- `CVAPP_PROJECT_ROOT` — the app needs to know the project root (where `cvapp.yaml`, the CVs and `rendercv_output/` live). The launcher is the authoritative source; bare `python -m cvapp` falls back to the current directory (documented in 4.2). See the env-var note in section 8 (risks).
- `exec ... "$@"` — `exec` replaces the bash process with the Python one, so the app's exit code propagates untouched (spec: "MUST propagate the application's exit code").
- `set -euo pipefail` — any launcher-internal failure (e.g. missing venv) exits non-zero loudly instead of running halfway.

`cv_tui` (alias) becomes:

```bash
#!/bin/bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cv" "$@"
```

`Generar CV.command` becomes:

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/cv" "$@"
EXIT_CODE=$?
if [ "$EXIT_CODE" -ne 0 ]; then
    echo ""
    echo "❌ Ocurrió un error (código $EXIT_CODE). Mirá cvapp.log para más detalle."
    read -p "Presioná Enter para cerrar esta ventana..."
fi
exit "$EXIT_CODE"
```

The `.command` blocks the window with `read -p` only on failure, so drag-and-drop users can read the error (spec: "keeps its window open with a pause after an error"). On success the window closes the instant the TUI quits — `exit "$EXIT_CODE"` propagates the real code.

---

## 3. Flow Diagrams

### 3.1 Startup (`./cv` → config → TUI)

```
./cv (any cwd)
  │  resolve SCRIPT_DIR from own location
  │  export PATH=.venv/bin:$PATH, PYTHONPATH=src, CVAPP_PROJECT_ROOT
  │  exec .venv/bin/python3 -m cvapp "$@"
  ▼
cvapp.__main__.py
  │  cli.main()
  ▼
cli.py (Typer app)
  ├─ no subcommand? ──────────────► run TUI
  ├─ tui       ──► run TUI (same path)
  ├─ list      ──► discovery → print names, exit 0
  ├─ render X  ──► resolve name → RenderingService → print PDF path, exit 0/1
  └─ version   ──► print __version__, exit 0
        │
        ▼  (config load happens FIRST, for every path)
  config.load(CVAPP_PROJECT_ROOT)          ── cvapp.yaml found? merge over defaults
        │                                     ── malformed/invalid? 
        ▼                                     ConfigError → startup error screen (TUI) / stderr+exit 1 (headless)
  logging.setup(settings)  → cvapp.log (append, level from config/env)
        ▼
  Textual CVApp.run(settings)
        │
        ▼
  discovery.find_cv_sources(settings.cvs_dir)
        ├─ 0 results ──► EmptyStateScreen ("No se encontraron CVs en <dir>", refresh/quit)
        └─ N results ──► MainScreen (OptionList, same order as `cv list`)
```

### 3.2 Render (TUI worker) and headless

```
TUI: Enter on selected CV                 CLI: ./cv render <name>
  │                                          │
  ▼                                          ▼
push_screen(StatusScreen)                resolve_cv_by_name(sources, name)
"Generando <nombre>…" + spinner              ├─ 0 matches ──► stderr error, exit 1
  │                                          └─ >1 matches ─► stderr error, exit 1
  ▼                                          ▼
run_worker(thread=True, exclusive=True)   RenderingService.render(cv)
  │                                          │
  ▼                                          ▼
RenderingService.render(cv)               [same service as the worker — one code path]
  │  snapshot = set(filenames in output_dir) before the run
  │  argv = build_rendercv_command(cv)     # pure function, unit-tested
  │  subprocess.run(argv, capture_output=True, text=True, timeout=timeout_seconds)
  │     ├─ FileNotFoundError ──► RenderError("no se encontró rendercv")
  │     ├─ TimeoutExpired ─────► RenderError("timeout después de Ns")
  │     └─ returncode != 0 ────► RenderError(stderr tail, exit code)
  │  verify pdf exists
  │  cleanup_intermediates(output_dir, snapshot, pdf_path)   # photo-safe, scoped (4.5)
  │  open_pdf(pdf)  (TUI flow + open_pdf_after, macOS only; failure = warning only)
  ▼
post_message(RenderFinished(pdf))   /   post_message(RenderFailed(error))
  ▼                                         ▼
ResultScreen (Regenerar otro /        ErrorScreen (Reintentar / Volver a la lista / Salir)
Abrir PDF / Salir)                    friendly SPANISH message + "detalles en cvapp.log"
```

### 3.3 Error flow (any failure → same shape)

```
RenderCV fails (bad YAML, timeout, missing exe)
  │
  ▼
RenderingService raises RenderError(message)
  │  logger.error(message, exc_info=True)   → full traceback appended to cvapp.log
  ▼
TUI: worker catches → post RenderFailed → ErrorScreen   (app alive, process still running)
CLI: cli.py catches → stderr "✗ <message> (detalles en cvapp.log)" → exit 1
```

---

## 4. Module by Module

### 4.1 `cli.py` — Typer app

**Responsibilities**: parse subcommands; decide TUI vs headless; load config once; map errors to messages + exit codes; the hook that makes "no arguments = TUI" work.

```python
app = typer.Typer(help="Generador de CVs con RenderCV.", no_args_is_help=False)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
) -> None:
    """Entry point. With no subcommand, opens the interactive TUI."""
    if ctx.invoked_subcommand is None:
        run_tui()                      # local function: load config, start CVApp
    else:
        prepare_logging(load_config()) # headless still needs logging + fail-fast config

@app.command()
def tui() -> None: ...                 # explicit alias of the no-arg path

@app.command()
def list() -> None: ...                # discovery -> print cv.name per line; exit 0 even when empty

@app.command()
def render(name: str) -> None: ...     # resolve -> render -> print absolute pdf path; errors exit 1

@app.command()
def version() -> None: ...             # print __version__ from cvapp; exit 0
```

Key decisions:

- **`invoke_without_command=True` + `ctx.invoked_subcommand is None`** is the canonical Typer pattern for "no args = default behavior". It preserves `--help`, gives free usage errors for unknown subcommands (`./cv frobnicate` → Click's usage error, non-zero exit), and adds zero custom parsing code.
- **Exit codes**: `0` success (including TUI quit and empty `list`), `1` application errors (unknown CV name, ambiguous name, failed render, config error), `2` usage errors (unknown subcommand, missing argument) — Click's default. `10` is never produced anywhere (spec).
- **Config is loaded once in `main`**, before any subcommand runs, so fail-fast applies to every path uniformly (spec `cv-config`: "MUST NOT proceed with rendering").
- **`render` never opens the PDF** (spec `cv-rendering`: headless never opens, regardless of config): the headless path calls `service.render()` and skips `open_pdf`.

### 4.2 `config.py` — Settings + `cvapp.yaml` loading

**Responsibilities**: the `Settings` value object; locating and parsing `cvapp.yaml` at the project root; resolving relative paths against the project root; translating parse/validation failures into one clear `ConfigError(message)`; logging setup.

```python
class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")      # unknown keys are ignored per spec

    cvs_dir: Path = Path(".")                      # resolved against project root
    output_dir: Path = Path("rendercv_output")
    open_pdf_after: bool = True
    cleanup_intermediate: bool = True
    rendercv_extra_flags: list[str] = []
    timeout_seconds: int = 120
    log_level: str = "INFO"

    project_root: Path                             # set after load; never from the file

def load(project_root: Path) -> Settings: ...      # reads cvapp.yaml if present, raises ConfigError
def setup_logging(settings: Settings) -> None: ... # FileHandler cvapp.log, append, CVAPP_LOG_LEVEL wins
```

**Decision: pydantic over dataclass.**

- **Choice**: `pydantic.BaseModel` (v2, already installed at 2.13.3 — a RenderCV dependency, so **zero new dependencies**).
- **Alternatives considered**: `@dataclass` + hand-written validation.
- **Rationale**: the `cv-config` spec demands "fail fast with a clear error naming the file and the offending key or value". Pydantic produces exactly that for free (`ValidationError` names the field and the bad value), plus type coercion for the seven simple keys, plus a one-line `extra="ignore"` for the unknown-keys requirement. A dataclass would need ~40 lines of hand-rolled coercion and error strings — more code for a worse result, and bool coercion (`open_pdf_after: "si"`) is precisely where hand-rolled parsing goes wrong. The pedagogical cost ("magic") is bounded: the model is a flat seven-field declaration the user can read end to end. Validation is the one job pydantic is unbeatable at; we do not use it anywhere else.
- **Guardrail**: `timeout_seconds` is constrained with `Field(gt=0)` so a zero/negative timeout fails fast, and `log_level` is validated against `{DEBUG, INFO, WARNING, ERROR}` to avoid silent misconfiguration.

How loading works:

1. `project_root = Path(CVAPP_PROJECT_ROOT) if set else Path.cwd()` — launcher sets the env var; bare `python -m cvapp` (spec-equivalence path) is documented to run from the project root.
2. If `cvapp.yaml` exists at `project_root / "cvapp.yaml"`, `yaml.safe_load` it (`yaml` is already a RenderCV dependency — no new import; if the parse throws, raise `ConfigError("cvapp.yaml no es YAML válido: <detail>")`).
3. Validate through `Settings(**data)`; wrap `ValidationError` into `ConfigError` that quotes the file and the offending key: *"cvapp.yaml: el valor de 'open_pdf_after' no es válido: ..."*.
4. **Path resolution rule**: only `cvs_dir` and `output_dir` are paths; a *relative* value is resolved as `project_root / value` (spec: resolved against the project, never the caller's cwd); an *absolute* value is used as-is; the result is stored absolute. This single rule makes every downstream consumer cwd-immune.
5. Effective log level: `CVAPP_LOG_LEVEL` env var **wins** over the config key (spec scenario), which wins over `INFO` default.

### 4.3 `core/discovery.py` — CV source discovery

**Responsibilities**: find CV YAMLs; resolve a name to exactly one source. Pure logic, trivially unit-testable.

```python
@dataclass(frozen=True)
class CVSource:
    id: str        # same as name; kept so call sites read "id" where they mean identity
    name: str      # stem of the filename, e.g. "Pablo_Gramajo"
    path: Path     # absolute path to the YAML

def find_cv_sources(cvs_dir: Path) -> list[CVSource]:
    """*.yaml + *.yml, non-recursive, dotfiles excluded, regular files only, sorted by name."""

class UnknownCVError(Exception): ...
class AmbiguousCVError(Exception): ...

def resolve_cv_by_name(sources: list[CVSource], name: str) -> CVSource:
    """Exactly one match, else raise; drives `render <name>` (0 and >1 are both errors)."""
```

Implementation notes (each mapped to a spec scenario):

- Two globs (`*.yaml`, `*.yml`), unioned, deduped, filtered (`f.is_file()`, `not f.name.startswith(".")` — glob already skips dotfiles, the filter is belt-and-braces and documents intent), then `sorted(key=lambda p: p.name)`. Sorted by **filename** = same order for `list`, TUI and `render` (they all call this one function — one source of truth for ordering).
- Non-recursive by construction: `Path.glob` with a single pattern does not descend.
- `resolve_cv_by_name` matches on `path.stem`. With both `Mi_CV.yaml` and `Mi_CV.yml` present, discovery returns two sources and the name is ambiguous → `AmbiguousCVError`; no name → `UnknownCVError`. Both become exit-1 headless errors and a friendly message in the TUI. Spec scenario "Ambiguous CV name is rejected" is only reachable from `cv render`; the TUI lists both files as separate rows (visible stems differ by nothing, which is fine — user data).

### 4.4 `core/rendercv.py` — `RenderingService`

**Responsibilities**: the only module allowed to touch the subprocess boundary. Builds the argv, runs it with timeout, captures output, verifies the PDF, cleans intermediates photo-safely, and opens the PDF on macOS when asked.

```python
class RenderError(Exception):
    """User-facing render failure. .message is safe to show in the TUI."""

class RenderingService:
    def __init__(self, settings: Settings) -> None: ...

    def render(self, cv: CVSource, *, open_pdf: bool = False) -> Path:
        """Render cv -> <output_dir>/<stem>.pdf. Raises RenderError on any failure.
        Returns the absolute PDF path. open_pdf is True ONLY from the TUI flow."""

    def open_pdf(self, pdf_path: Path) -> None:
        """macOS 'open' only; failure logs a warning, never fails the render."""

# Pure helpers (module-level, unit-tested without subprocess):
def build_rendercv_command(source: CVSource, output_dir: Path, pdf_path: Path,
                           extra_flags: list[str]) -> list[str]: ...
def resolve_rendercv_executable() -> Path: ...
def cleanup_intermediates(output_dir: Path, before: set[str], pdf_path: Path) -> list[Path]: ...
def snapshot_output_dir(output_dir: Path) -> set[str]: ...
```

`render()` flow, with the failure mapping:

1. `resolve_rendercv_executable()`: `Path(sys.executable).with_name("rendercv")` when it exists (the console script sits next to our interpreter in the venv), else `shutil.which("rendercv")`; if neither → `RenderError("No se encontró el ejecutable de RenderCV (rendercv). Reinstalalo en .venv.")` (spec: "Missing RenderCV executable is a clear failure"). Resolving from `sys.executable` is what makes the render robust even if the launcher's PATH export were missing.
2. `snapshot_output_dir(output_dir)` → `set(p.name for p in output_dir.iterdir())` (empty set if the dir doesn't exist yet — we do **not** create it pre-emptively; RenderCV creates it via `mkdir(parents=True, exist_ok=True)` in `resolve_rendercv_file_path`).
3. Build argv via the pure `build_rendercv_command` (exact content in section 5).
4. `subprocess.run(argv, capture_output=True, text=True, timeout=settings.timeout_seconds)`.
   - `FileNotFoundError` → RenderError (from step 1 this is nearly unreachable, but keep the guard for the type).
   - `subprocess.TimeoutExpired` → `RenderError(f"El render tardó más de {timeout}s y se canceló.")` (spec: timeout scenario).
   - `returncode != 0` → `RenderError` with the captured stderr (last ~400 chars; full output goes to the log).
5. Verify `pdf_path.is_file()`; if absent despite exit 0 → RenderError("RenderCV terminó sin error pero no generó el PDF...").
6. `cleanup_intermediates(output_dir, snapshot, pdf_path)` (photo-safe, section 4.5 detail).
7. `open_pdf(pdf_path)` only when `open_pdf=True` (TUI flow) **and** `settings.open_pdf_after`; headless never calls it (spec).

**Decision: argument list, never a shell string.**

- **Choice**: `subprocess.run([...])` with every token a separate list element; `shell=False` is the default and never overridden.
- **Alternatives considered**: the current `cmd = f'rendercv render "{filename}" ...'` with `shell=True, executable="/bin/zsh"`.
- **Rationale**: shell strings are unquoted-concatenation bugs waiting for a space in a path, an injection surface by default, and impossible to unit-test without a shell. The argv built by a pure function is inspectable in a test with a plain `assert` — the spec's "extra flags MUST be visible in the invocation" scenario is a one-line test. Zero rendering behavior changes: the flags are byte-identical to today's working command plus one behavior-preserving addition (section 5).

### 4.5 `cleanup_intermediates` — the photo-safe cleanup pattern

The old code removed `rendercv_output/*.typ *.md *.html *_*.png` — the `*_*.png` glob also deletes the user's photo: RenderCV 2.8 **copies the CV photo into the output folder** during PDF generation (`copy_photo_next_to_typst_file`, verified in the installed source at `rendercv/renderer/pdf_png.py`), and a photo named `foto_2024.png` matches `*_*.png`. That is the exact bug this change fixes.

The replacement is a **before/after snapshot**:

```python
def cleanup_intermediates(output_dir: Path, before: set[str], pdf_path: Path) -> list[Path]:
    """Delete ONLY files created by this run, matching intermediate extensions.
    Never touches anything that existed before the run (photos, other CVs' files),
    never touches the PDF (matched by exact name), never leaves output_dir."""
    removed: list[Path] = []
    for candidate in output_dir.iterdir():
        if candidate.name in before:
            continue                        # pre-existing file: photo, other CV's output → skip
        if candidate == pdf_path.resolve():
            continue                        # the deliverable → keep
        if candidate.suffix.lower() in {".typ", ".md", ".html", ".png"}:
            candidate.unlink(missing_ok=True)
            removed.append(candidate)
    return removed
```

Why this beats every glob-based rule:

- **Pre-existing user files survive by construction** (the photo scenario from the spec, and "rendering one CV does not touch another CV's files"): anything present before the run is in `before` and skipped — no pattern can accidentally match it.
- **Files outside `output_dir` are untouchable**: we only ever iterate `output_dir.iterdir()`; the dir itself is absolute (resolved in config), so cleanup can never reach the project root.
- **The PDF is protected by exact name** (`candidate == pdf_path`), not by "is not a pdf".
- **It stays correct if RenderCV changes its naming**: the `.typ` intermediate is actually named after the YAML `name` field (`<Name_Snake>_CV.typ`), *not* the input stem — a stem-glob like `<stem>.*` would miss it entirely. The snapshot knows nothing about names, only "did this file exist before the run".
- The transient photo *copy* that this run created (a new `.png` in the dir) is removed — correct: the original photo lives elsewhere untouched, and the copy would otherwise accumulate.

Failure cleanup: specs require the same scoping on failure — the snapshot logic runs inside `render()`'s `finally`-style tail after `subprocess.run` regardless of exit code, so a failed render still removes its own intermediates and still cannot touch pre-existing files.

**Decision: `open_pdf` via macOS `open`, guarded.**

```python
def open_pdf(self, pdf_path: Path) -> None:
    if platform.system() != "Darwin":
        logger.warning("open_pdf_after está activo pero no estamos en macOS; no se abre el PDF.")
        return
    try:
        subprocess.run(["open", str(pdf_path)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("No se pudo abrir el PDF con 'open': %s", exc)   # render stays successful
```

`subprocess.run(["open", path])` is the macOS-native opener (what the old code already used) — no `webbrowser` indirection, no `osascript`, nothing that can close the Terminal. Platform guard + warning-only failure implement the two non-macOS/open-failure spec scenarios. `shutil.open` was considered — it does not exist in stdlib (the myth comes from `shutil.copy` confusion); `subprocess ["open"]` is the real macOS primitive.

### 4.6 `tui/app.py` + `tui/screens.py` — the Textual TUI

**One decision up front**: the TUI is split in two files (proposal tree showed a single `tui/app.py`). Rationale: the App object (bindings, routing, worker, message handlers) and the five screens (widget trees, each small) are different concerns; two files of ~110 and ~160 lines beat one file of ~270 for a learner opening a file to find one thing. `tui/app.py` holds zero widget composition; `tui/screens.py` holds zero logic — screens only call callbacks passed by the App.

**`app.py` shape:**

```python
class CVApp(App[None]):
    """Thin presentation layer: routes screens, launches the worker, owns no logic."""

    BINDINGS = [
        Binding("q", "quit_app", "Salir", priority=True),
        Binding("escape", "quit_app", "Salir", priority=True),
        # screen-local bindings (r/R, o/O, backspace, enter) live on the screens
    ]

    def __init__(self, settings: Settings) -> None: ...

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        # main screen is pushed in on_mount via push_screen

    @work(exclusive=True, thread=True)
    def render_worker(self, cv: CVSource) -> None:
        try:
            pdf = self.rendering.render(cv, open_pdf=True)
        except RenderError as exc:
            self.post_message(RenderFailed(exc.message))
        else:
            self.post_message(RenderFinished(pdf))

    def on_render_finished(self, msg: RenderFinished) -> None: ...
    def on_render_failed(self, msg: RenderFailed) -> None: ...
    def action_regenerate_another(self) -> None: ...   # push_screen(MainScreen(reload))
    def action_quit_app(self) -> None: self.exit(0)    # THAT'S IT — no osascript, no execv

class RenderFinished(Message): ...
class RenderFailed(Message): ...
```

**Decision: Textual worker threads for rendering.**

- **Choice**: a `@work(exclusive=True, thread=True)` method that runs `RenderingService.render()` (a blocking `subprocess.run`) and `post_message`s a result to the App.
- **Alternatives considered**: (a) synchronous render in the Enter key handler — the UI freezes for up to `timeout_seconds` (120 s): no spinner, no repaint, looks crashed; (b) `asyncio.create_subprocess_exec` — idiomatic async but requires rewriting the service in async style and complicates the unit tests, for zero user-visible gain over a thread.
- **Rationale**: the spec demands the TUI "keeps responding and shows status while rendering". A thread worker is the documented Textual pattern, keeps the well-tested synchronous `RenderingService` untouched, and `exclusive=True` is exactly the spec's "no second render while one is in progress" — the App silently ignores Enter while a worker is active. Custom message classes (`RenderFinished(pdf)`, `RenderFailed(message)`) are the specified worker→UI channel (`post_message`); screen handlers (`on_render_finished`/`on_render_failed` on the App) do the two-line routing to `ResultScreen`/`ErrorScreen`.

**Screens (all UI copy in Spanish, Rioplatense, per spec):**

| Screen | Contents | Bindings / actions |
|---|---|---|
| `MainScreen` | `Header` (title "Generador de CVs", status), title "🎯 Seleccioná tu CV", `OptionList` with the CV names, `Footer` | ↑/↓/Enter built into `OptionList` (no wrap — cursor stays at top/bottom, Textual's default); `q`/`esc` quit |
| `EmptyStateScreen` | "No se encontraron CVs en <directorio>" + hint | `r` re-scan (re-runs discovery, shows MainScreen), `q` quit |
| `StatusScreen` | spinner + "Generando <nombre>…" + muted hint "no cierres la terminal" | none (render in progress) |
| `ResultScreen` | "✅ PDF generado" + absolute PDF path + "¿Qué hacés ahora?" | `r` Regenerar otro (→ MainScreen reload, same process), `o` Abrir PDF (calls `service.open_pdf`), `q`/`esc` Salir |
| `ErrorScreen` | "❌ No se pudo generar el PDF" + one-line friendly message + "Detalles en cvapp.log" | `r` Reintentar (re-run same CV), `b`/`esc` Volver a la lista, `q` Salir |

- **MainScreen uses `OptionList`** (a Textual built-in) instead of hand-rolled `Static` rows plus a `selected_idx` — the old app reimplemented selection with string `▸` prefixes and manual CSS swapping; `OptionList` ships highlight, keyboard nav and no-wrap for free. The app logic shrinks to: `on_option_list_option_selected` → push `StatusScreen` + `run_worker`.
- **"Regenerar otro" never re-executes**: `action_regenerate_another` pops back to the main screen and calls `pop_screen`/`push_screen(MainScreen(reload=True))` which re-runs discovery — in-process by construction (spec: "no process restart, no os.execv"). The old `os.execv(sys.executable, [sys.executable, __file__])` is gone; the Textual App's composition is re-usable.
- **Quit semantics**: `q`/`esc` call `self.exit(0)`. Textual returns control to the calling shell normally; Terminal stays open because nothing ever touches it (spec: no `osascript`, no `os.execv`, no exit 10). This is a deliberate behavior change from today (old code quit the Terminal) — user-approved in the proposal's open questions; the `.command` launcher's pause covers Finder users who previously relied on the autoclose.
- **Startup config errors in TUI mode**: `run_tui()` loads config first; on `ConfigError` it starts the app in a "startup error" state that composes only the `ErrorScreen` with the message (spec `cv-config`: "the TUI shows the error screen"). No render is attempted, exit 0 on quit.

### 4.7 `__init__.py` / `__main__.py` / `version`

```python
# src/cvapp/__init__.py
__version__ = "2.0.0"     # THE single source of truth

# src/cvapp/__main__.py
from cvapp.cli import app
app()                      # python -m cvapp === ./cv
```

- Version `2.0.0`: major bump signals the behavior change (one command, new TUI, safer quit). The `version` subcommand prints `__version__` and exits 0; the launcher has no version string of its own — `cv version` and `python -m cvapp version` read the same constant (spec: "defined in exactly one place").
- `app()` (Typer's callable instance) instead of `main()` keeps both `__main__` and `[project.scripts]` pointing at the same object; `typer.main` errors become exit code 1 par with the rest.

### 4.8 `rendercv-env` — decision

- **Choice**: keep the directory on disk, unused; add `rendercv-env/` to `.gitignore`; reference it nowhere in code or scripts.
- **Alternatives considered**: delete it now; keep using it.
- **Rationale**: `.venv` holds everything the app needs (Textual 8.2.5, Typer 0.24.1, RenderCV 2.8, Rich), so the duplicate is dead weight (~200 MB) and a confusion vector ("which venv do I activate?"). But deleting it is destructive, out of this change's scope, and the proposal already classified it "kept (unused) as fallback". The design freezes that: it must not appear in any code path, and its removal is a separate, user-approved follow-up (flagged in section 8).

---

## 5. Integration with RenderCV

### 5.1 The exact command

From `build_rendercv_command` (pure function — this is the contract tests assert against):

```python
def build_rendercv_command(source, output_dir, pdf_path, extra_flags) -> list[str]:
    return [
        str(resolve_rendercv_executable()),
        "render",
        str(source.path),                 # ABSOLUTE path to the input YAML
        "-nomd",                          # no markdown (today's flags, unchanged)
        "-nohtml",                        # no html
        "-nopng",                         # no page PNGs
        "--pdf-path", str(pdf_path),      # ABSOLUTE: <output_dir>/<stem>.pdf
        "-o", str(output_dir),            # ABSOLUTE base output folder (see 5.2)
        *extra_flags,                     # config rendercv_extra_flags, appended last (spec)
    ]
```

Concrete example for `Pablo_Gramajo.yaml` with defaults:

```text
/Users/pdgramajo/Curriculum_Vitae/.venv/bin/rendercv render \
  /Users/pdgramajo/Curriculum_Vitae/Pablo_Gramajo.yaml \
  -nomd -nohtml -nopng \
  --pdf-path /Users/pdgramajo/Curriculum_Vitae/rendercv_output/Pablo_Gramajo.pdf \
  -o /Users/pdgramajo/Curriculum_Vitae/rendercv_output
```

### 5.2 Why absolute paths (verified against RenderCV 2.8 source)

Two facts from reading the installed package (`rendercv/schema/models/path.py` and `renderer/path_resolver.py`):

1. **`PlannedPathRelativeToInput` resolves relative `--pdf-path` against the *input file's parent directory*** — not the cwd. Today the input files sit at the project root, so `rendercv_output/X.pdf` happened to land correctly. But with any `cvs_dir` configuration, a relative `--pdf-path` would silently land inside `cvs_dir`. Absolute paths bypass the ambiguity entirely: the validator passes absolute paths through unchanged (`if not path.is_absolute(): ...`).
2. **Intermediates resolve against the same base**: with cvs_dir ≠ root, the `.typ` intermediate would drift out of `rendercv_output/` — landing where our scoped cleanup (which only touches `output_dir`) could never remove it. That is why `-o <absolute output_dir>` is added: it forces the `OUTPUT_FOLDER` placeholder (and thus the `.typ` intermediate) to resolve inside the configured output directory. With today's layout (cvs_dir = root, output = `rendercv_output`) the flag is behavior-preserving — same effective paths as the current working command; the proposal's "keep the exact same flags" risk is honored in effect, and the smoke test (section 8) proves it on a real render.

`-notyp` was considered and **rejected**: RenderCV's help states "Disabling Typst generation implicitly disables PDF and PNG" — the Typst intermediate is mandatory for PDF output, which is exactly why cleanup exists.

### 5.3 Missing RenderCV, timeout, flags passthrough

- Missing executable → `RenderError` with a clear Spanish message (5.1's resolver never returns a nonexistent path; the error path is still tested by monkeypatching the resolver).
- Timeout → `subprocess.run(timeout=...)` → `TimeoutExpired` → `RenderError` naming the seconds (spec scenario).
- `rendercv_extra_flags` → appended after the standard flags; the appendix ends up a unit test asserting list membership and order (spec scenario). No shell quoting applies — each flag is already its own argv element.

---

## 6. Configuration

### 6.1 Schema

| Key | Type | Default | Effect |
|---|---|---|---|
| `cvs_dir` | path | project root | Directory scanned for CV YAML sources (`*.yaml`/`*.yml`, non-recursive) |
| `output_dir` | path | `rendercv_output` | Where PDFs (and transient intermediates) are written |
| `open_pdf_after` | boolean | `true` | Open the PDF after a successful TUI render (macOS only) |
| `cleanup_intermediate` | boolean | `true` | Remove this run's intermediates after a completed attempt |
| `rendercv_extra_flags` | list of strings | `[]` | Appended to the RenderCV argv after the standard flags |
| `timeout_seconds` | number (int > 0) | `120` | Max duration of one render |
| `log_level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` | Verbosity of `cvapp.log` |

Unknown keys are ignored (log warning); `CVAPP_LOG_LEVEL` env var overrides `log_level`.

### 6.2 Where it is found and precedence

`cvapp.yaml` → `<project_root>/cvapp.yaml` (project root = `CVAPP_PROJECT_ROOT` env from the launcher, else cwd for bare `python -m cvapp`). Precedence: **defaults < cvapp.yaml < environment (`CVAPP_LOG_LEVEL`)**. There are no CLI config flags (not in scope of any spec).

### 6.3 Annotated example (for the README / user)

```yaml
# cvapp.yaml — configuración opcional de la app de CVs.
# Sin este archivo, la app se comporta exactamente como hoy:
#   CVs en la raíz, PDFs en rendercv_output/, todo con valores por defecto.

cvs_dir: "."                    # dónde buscar los YAML de CVs (relativo a la raíz del proyecto)
output_dir: rendercv_output     # dónde se escriben los PDFs
open_pdf_after: true            # abrir el PDF tras un render exitoso en la TUI (solo macOS)
cleanup_intermediate: true      # borrar los archivos intermedios de este render (.typ, copia de foto)
rendercv_extra_flags: []        # flags extra que se agregan al comando de rendercv
timeout_seconds: 120            # máximo de segundos por render
log_level: INFO                 # DEBUG | INFO | WARNING | ERROR (CVAPP_LOG_LEVEL tiene prioridad)
```

---

## 7. Errors and Logging

**Strategy**: stdlib `logging` behind a module logger `"cvapp"`; exactly one log file; the app never prints tracebacks anywhere except that file.

- Log file: `<project_root>/cvapp.log`, **append** mode (`FileHandler(file, mode="a")`), created lazily at first write. Level: config `log_level` unless `CVAPP_LOG_LEVEL` is set (env wins). Format `%(asctime)s %(levelname)s %(name)s: %(message)s`.
- What goes to the log per level:

| Level | Content |
|---|---|
| `DEBUG` | resolved settings, discovery result count, exact RenderCV argv, timing of the run |
| `INFO` | config loaded, render started/finished, PDF path, cleanup results |
| `WARNING` | unknown config keys, open-PDF failure, non-macOS skip of `open_pdf_after` |
| `ERROR` | any `RenderError`/`ConfigError`/unexpected exception — always with `exc_info=True` so the full traceback lands in the file (spec) |

- **User errors vs internal errors**: `RenderError` and `ConfigError` are *expected* failures — their `.message` is written in plain Spanish and shown directly (TUI error screen or headless stderr). Everything else (bugs) is "internal": same friendly message *"Ocurrió un error inesperado. Detalles en cvapp.log"* plus the logged traceback, so the user never sees a raw Python traceback in the terminal.
- **Headless reporting**: messages go to **stderr** (`rich.print` styled, plain text), success output (list names, PDF path, version) to **stdout**. Exit codes: `0` success, `1` expected/application failure, `2` usage (Click default). `10` never produced.
- **TUI reporting**: error screen with the friendly one-liner + "Detalles en cvapp.log"; the app stays alive (retry/back/quit still work) — spec "application process is still running normally".
- Never log CV *content* (YAML bodies, names are fine; content is private user data).

**Decision: file-only logging.** No console handler: headless messages are explicitly printed by the CLI (which controls their wording and stream), and the TUI replaces console output entirely. A console handler would double-print in headless mode with different wording — one writer per channel is simpler to reason about.

---

## 8. Testing Strategy

Fixture plan (`tests/conftest.py`):

- `project_factory` — builds a `tmp_path` project with optional `cvapp.yaml`, optional CV yamls, optional `rendercv_output/` photos.
- `sample_sources` — writes the 10 real stems as empty files (names only matter) for order/listing tests; the real CV YAMLs are never read by unit tests.
- `fake_run` — a `monkeypatch`-able `subprocess.run` recording `args` and returning a scripted `CompletedProcess` (or raising scripted `TimeoutExpired`/`FileNotFoundError`).

| Module | What is tested | Approach |
|---|---|---|
| `discovery` | finds `.yaml`+`.yml`, sorted; dotfiles excluded; subdirs not scanned; empty dir → `[]`; name resolution: exact, unknown, ambiguous (`Mi_CV.yaml`+`Mi_CV.yml`) | pure functions, `tmp_path` fixtures |
| `config` | defaults with no file; partial merge; unknown keys ignored; malformed YAML → `ConfigError` naming file; `open_pdf_after: "si"` → error naming key; `CVAPP_LOG_LEVEL` beats file; relative `cvs_dir`/`output_dir` resolve against project root; absolute values pass through | `project_factory` |
| `rendercv` | `build_rendercv_command` exact argv (flags, order, absolute paths, extra flags appended); `resolve_rendercv_executable` finds venv sibling, falls back to `shutil.which`, raises clean error; cleanup: photo `foto_2024.png` pre-existing survives, another CV's files survive, PDF kept by exact name, only this-run intermediates removed, files outside `output_dir` never touched; timeout → `RenderError` naming seconds; nonzero exit → `RenderError` with stderr; missing exe → clear message; `open_pdf` only on Darwin (patch `platform.system`), failure → warning and render still success; headless path never calls `open_pdf` | `fake_run`, monkeypatch |
| `cli` | `version` prints `__version__` (from the package) exit 0; `list` prints names in discovery order, empty → no output exit 0; `render` success → prints absolute PDF path exit 0; unknown name → stderr error exit 1, no render attempted; ambiguous → exit 1; failed render → stderr + exit 1; no args → TUI entry invoked (patch `run_tui`) | `monkeypatch` the service, `CliRunner`-style calls via `typer.testing.CliRunner` |
| smoke (opt-in) | real RenderCV run of a minimal CV in `tmp_path`: PDF exists at `<output_dir>/<stem>.pdf`, exit 0, cleanup removed the `.typ` intermediate and left the PDF | `@pytest.mark.smoke`, runs only with `pytest -m smoke` |

Edge cases pulled from the specs, made explicit (each maps to at least one named test above):

1. **Protected photo** — `foto_2024.png` inside `output_dir` (matches old `*_*.png`) survives cleanup.
2. **Timeout** — fake `subprocess.run` raises `TimeoutExpired`; error names the seconds.
3. **Unknown name** — `render No_Existe` → exit 1, no render, clear stderr.
4. **No YAMLs** — `list` and TUI empty state both handle `[]`.
5. **Paths with spaces** — a CV name and project path containing spaces: argv built by the pure function is asserted element-by-element (no quoting can break it — this is the shell=True bug's own regression test).

Command: `pytest` (unit suite); `pytest -m smoke` (opt-in real render); coverage goal **≥ 80%** on `config.py`, `core/*`, `cli.py` (measured with `pytest --cov=cvapp`, `pytest-cov` an optional dev dep), TUI excluded from the coverage gate (verified manually, per proposal scope).

**Decision: Textual Pilot E2E deferred** (proposal, out of scope): TUI behavior is verified manually against the acceptance checklist; the logic underneath is 100% unit-tested, which is what Pilot would have exercised anyway through the same service boundary.

---

## 9. Linting / Type Checking / Format

| Tool | Config (in `pyproject.toml`) | Command | Why |
|---|---|---|---|
| Ruff lint | `select = ["E4","E7","E9","F","I","UP"]`, `line-length = 100`, `target-version = "py312"` | `ruff check .` | Safety subset: style errors with teeth (E), undefined names/unused imports (F — catches real bugs), sorted imports (I), modern syntax (UP). Auto-fix with `ruff check --fix`. |
| Ruff format | `quote-style = "double"` | `ruff format .` | Zero-config formatter; `cvapp` code is `format`-clean or CI-failing. |
| Pyright | `typeCheckingMode = "standard"` (explicit, not default-implied) | `pyright` | **Decision: standard, not strict.** Strict mode doubles annotation burden (every helper, every `None` edge, decoration variance) and produces beginner-hostile noise on Textual's generics for near-zero extra safety on a 5-module fresh codebase. "Standard" still catches the real bug classes (wrong arg types, `None` misuse) with clear messages. Strict is a documented future step once the codebase is comfortable. |

Dev workflow (a `Makefile` at root with 6 lines, optional but recommended):

```makefile
.PHONY: test lint format check
test:   .venv/bin/pytest -m "not smoke"
lint:   .venv/bin/ruff check .
format: .venv/bin/ruff format .
check:  test lint format pyright
pyright: .venv/bin/pyright
```

Dev deps to install once (additive, no upgrades of pinned runtime deps): `pip install pytest ruff pyright` (+ optional `pytest-cov`) inside `.venv`. Verify runtime untouched with `./cv version` after install (proposal rollback-check).

---

## 10. Keep / Replace / Delete

| Path | Action | Why / What |
|---|---|---|
| `cv` | **Replace** | Numeric-menu bash script → thin launcher (2.3), resolves root/venv/PYTHONPATH itself |
| `cv_tui` | **Replace** | Duplicated venv logic → one-line alias `exec .../cv "$@"` (spec: behaves like `cv`) |
| `Generar CV.command` | **Replace** | Delegate to `cv` + `read -p` pause on error; keeps double-click working (spec) |
| `cv_tui.py` | **Delete** | Monolith superseded by `src/cvapp/`; the switch happens only after the new path passes the checklist (rollback plan) |
| `run_cv.sh` | **Delete** | Superseded; zero references may remain (spec scenario) |
| `src/cvapp/**` | **Create** | The package (tree in section 2.1) |
| `pyproject.toml` | **Create** | Entry-point declaration + dev-tool config (2.2) |
| `.gitignore` | **Create** | `.venv/`, `rendercv-env/`, `rendercv_output/`, `__pycache__/`, `cvapp.log`, `.DS_Store` |
| `cvapp.log` | **Runtime** | Created at first run whenever anything is logged (gitignored) |
| `*.yaml` / `*.yml` (10+) | **Keep** | Byte-identical user data (success criterion) |
| `rendercv_output/` | **Keep** | Runtime PDFs, gitignored |
| `.venv` | **Keep** | Sole runtime venv; + dev deps |
| `rendercv-env` | **Keep, unused** | Gitignored; deletion deferred (4.8) |
| `openspec/` | **Keep** | SDD artifacts; untouched by implementation |

---

## 11. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `git init` not approved → no rollback anchor | High (pending user answer) | Phase 0 is blocked on the user's yes; the baseline commit `git checkout baseline -- .` is the entire rollback plan — do not start Phase 1 without it |
| Launcher break → CV generation blocked entirely | Med | Launcher is ~15 lines, structurally identical to the verified wrapper; old files stay untouched until the new path passes the checklist, and the switch is a single commit |
| Behavior change: quitting no longer closes Terminal (`osascript` gone) | Certain (by design) | Explicit product decision (proposal Q6, safer); `.command` pause covers Finder users; document in README |
| `rendercv-env` duplicate confusion | Med | Never referenced by code; gitignored; removal flagged as optional follow-up |
| New `-o`/absolute-path flags change RenderCV behavior | Low | Verified against 2.8 source (pass-through of absolute paths; `OUTPUT_FOLDER` placeholder); behavior-preserving for today's layout; smoke test proves a real render |
| `CVAPP_PROJECT_ROOT`/`PYTHONPATH` env collisions | Low | Launcher prefixes without clobbering (`${PYTHONPATH:+...}`), docs name the variables |
| Bare `python -m cvapp` from a foreign cwd uses cwd as root | Low | Documented: run from the project root (spec's equivalence scenario is from the project root); the launcher is the cwd-independent path |
| Textual worker misuse → frozen UI | Med | Minimal documented pattern: one `@work(exclusive=True)` + `post_message`; manual checklist covers spinner responsiveness |
| Review budget: this change adds ~1,200+ lines (package + tests + launchers) | High | Forecast to sdd-tasks: chained PRs recommended or explicit single-PR exception under ask-on-risk (delivery strategy) — the 400-line budget will be exceeded by the whole change; phase-batched PRs (F1–F5) are natural chained slices |
| Photo deletion regression | Certain if naive glob survives | Cleanup is snapshot-based (4.5) + explicit RED test `foto_2024.png` survives |

---

## 12. Acceptance Criteria (top level; the exhaustive checklist is produced by sdd-tasks)

- [ ] `./cv` with no args opens the Textual TUI listing exactly the same CVs, same order, as today's glob (10+ files) — and exits 0 on quit.
- [ ] `./cv list` prints the same names, one per line, exit 0; empty discovery prints nothing, exit 0.
- [ ] `./cv render Pablo_Gramajo` produces `rendercv_output/Pablo_Gramajo.pdf` (absolute-path safe from any cwd), prints the path, exit 0, PDF NOT opened.
- [ ] `./cv render <unknown|ambiguous>` → clear stderr error, exit 1, nothing rendered.
- [ ] `./cv version` and `.venv/bin/python3 -m cvapp version` print the same string, exit 0.
- [ ] `.venv/bin/python3 -m cvapp <cmd>` behaves identically to `./cv <cmd>`.
- [ ] TUI: select → spinner status ("Generando …"), PDF generated, opened on macOS (config on), intermediates cleaned, `foto_*.png` in `rendercv_output/` untouched; "Regenerar otro" returns to the list in-process.
- [ ] Corrupted YAML / missing RenderCV / timeout: TUI error screen (Spanish, one-liner) with "Detalles en cvapp.log", full traceback appended to `cvapp.log`, app alive with retry/back/quit.
- [ ] Zero occurrences of `shell=True`, `os.execv`, `osascript`, exit code 10 in `src/` (grep-able acceptance).
- [ ] `pytest` green (unit); `pytest -m smoke` green (opt-in real render); `ruff check .`, `ruff format --check .`, `pyright` clean.
- [ ] All CV YAML files byte-identical before/after.
- [ ] `Generar CV.command` double-click still generates a CV and pauses on error.
- [ ] `run_cv.sh` and every reference to it are gone.
- [ ] Baseline git commit exists (blocked on user's `git init` yes).

---

## 13. Phased Implementation Plan (orients sdd-tasks)

| Phase | Contents | Files | Verification |
|---|---|---|---|
| **F0 — Baseline** | `git init`, `.gitignore`, commit current state | `.gitignore` (+ git) | `git log` shows `baseline`; rollback anchor exists |
| **F1 — Scaffolding + config** | package skeleton, `pyproject.toml`, `config.py` + tests, logging | `src/cvapp/{__init__,__main__}.py`, `config.py`, `core/__init__.py`, `pyproject.toml`, `tests/test_config.py` | `pytest tests/test_config.py`; `./cv version` (via temp launcher or `PYTHONPATH=src .venv/bin/python3 -m cvapp version`) |
| **F2 — Core: discovery + rendering** | pure discovery, `RenderingService`, argv/cleanup/open + tests | `core/discovery.py`, `core/rendercv.py`, `tests/{test_discovery,test_rendercv}.py` | `pytest`; smoke test manually run once with a real CV in tmp |
| **F3 — CLI** | Typer commands, exit codes, error mapping, headless tests | `cli.py`, `tests/test_cli.py` | `./cv list` matches today's glob; `render`/`version` behave; `pytest` |
| **F4 — TUI** | `tui/app.py` + `tui/screens.py`, worker, bindings, Spanish copy, startup error screen | `tui/__init__.py`, `tui/app.py`, `tui/screens.py` | Manual checklist 3.1/3.2/3.3 flows + quit behavior; `pytest` (service already covered) |
| **F5 — Launchers + legacy removal** | rewrite `cv`, `cv_tui`, `Generar CV.command`; delete `cv_tui.py`, `run_cv.sh`; final checklist | root launchers (3 files), `-2` files | Full acceptance checklist 12; `grep` for forbidden patterns; final `pytest`, `pytest -m smoke`, ruff, pyright |

Every phase is independently reviewable; F1–F3 are the natural chained-PR slices if the 400-line review budget forces splitting (F0+F1, F2, F3, F4, F5+cleanup).

---

## Threat Matrix

The change replaces shell-string subprocess calls with argument lists, rewrites executable launchers, and injects `PYTHONPATH`/`PATH`/`CVAPP_PROJECT_ROOT` — the subprocess and executable-classification boundaries apply. The stock rows for VCS/PR automation do not (this change affects no git workflow code).

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Documentation-like paths | `requirements.txt`, executable Markdown, `README.sh` | N/A — no executable-markdown or doc-execution path exists or is introduced | — | — |
| Git repository selection | `git -C`, relative/absolute paths | N/A — the app runs no git commands; `git init` is a manual Phase-0 step, not code | — | — |
| Commit state | staged, `commit -a`, empty index | N/A — no commit automation in the change | — | — |
| Push state | tracking branch, first push, explicit refspec | N/A — no push automation in the change | — | — |
| PR commands | explicit `--head`, env prefix, composed commands | N/A — no PR automation in the change | — | — |
| Subprocess invocation | `shell=True` reintroduction; argv with spaces; timeout; missing executable | **Applicable** — rendering is a subprocess boundary | Argument list only (`shell=False` default, never overridden); pure `build_rendercv_command`; venv-sibling resolution of `rendercv`; `timeout=`; captured output | RED: argv built for a name with spaces; no `shell=True` anywhere in `src/` (assert-string scan); missing-exe → `RenderError` naming `rendercv`; timeout → `RenderError` naming seconds; cleanup can never leave `output_dir` |
| Executable-file classification / launcher env | launcher run from foreign cwd; launcher run by absolute path; `.command` double-click; missing `.venv` | **Applicable** — `cv`, `cv_tui`, `Generar CV.command` are executable entry points with env injection | Root resolved from `BASH_SOURCE[0]`, not cwd; `exec` passes exit codes; clear Spanish error when `.venv` missing; `PYTHONPATH`/`PATH` preprend without clobbering | RED: launcher invoked from `$HOME` by absolute path lists the project's CVs; missing-venv case prints the Spanish error and exits 1; `.command` non-zero run leaves the window open (manual, Finder) |

Applicable rows propagate to `tasks.md` and to RED tests before production changes (per skill rules). Expected behavior for applicable rows: safe invocation (explicit argv, no shell), clear failure messages (missing exe / timeout / missing venv), zero side effects outside `output_dir` / project root.

---

## Migration / Rollout

No data migration: CV YAMLs are untouched user data. Rollout follows the proposal's rollback plan: baseline commit → build new package while old files remain functional → switch launchers in one commit → removal commit. Rollback is a single `git checkout baseline -- .`.

## Open Questions (for user approval before implementation)

1. `git init` — recommended **yes**; Phase 0 is blocked on this (proposal Q1).
2. Quit behavior change (no Terminal close) — already recommended yes in proposal Q6; confirm.
3. `rendercv-env` — keep on disk (design default) vs delete now; recommended keep.
4. Ship `cvapp.yaml.example` next to the app for discoverability, or leave config documentation in the README only; recommended README only (absent file = defaults, one less file to maintain).
5. Phase-batched chained PRs (F1–F5) vs one exception-approved PR for the whole change — the 400-line review budget will be exceeded either way; recommend chained slices.