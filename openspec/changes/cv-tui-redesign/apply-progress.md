# Apply Progress — cv-tui-redesign (PR 1: Phases 0 and 1 · PR 2: Phase 2 discovery)

Chain: 6 PRs, stacked-to-main. PR 1 of 6 → git baseline + scaffold/config. PR 2 of 6 → Phase 2 discovery (tasks 2.1–2.3).
Status: **16/44 tasks complete** (0.1–0.3, 1.0–1.9, 2.1–2.3).

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

## Status update
- **Tasks complete**: 24/44 (0.1–0.3, 1.0–1.9, 2.1–2.3, 2.4–2.11)
