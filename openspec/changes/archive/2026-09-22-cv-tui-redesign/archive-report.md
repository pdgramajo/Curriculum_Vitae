# Archive Report — cv-tui-redesign

**Change**: cv-tui-redesign
**Archived**: 2026-09-22
**From**: `openspec/changes/cv-tui-redesign/`
**To**: `openspec/changes/archive/2026-09-22-cv-tui-redesign/`
**Store**: openspec (Engram mirror: `sdd/cv-tui-redesign/apply-progress`)

## Final State (authority: source of truth hierarchy)

This report records the state of the change AT CLOSE. Final-state facts outrank intermediate snapshots (`apply-progress`).

### Implementation: COMPLETE — 44/44 tasks

- **44 of 44 tasks checked** in the persisted `tasks.md` (highest-rank source, observed).
- Dispatcher native status at archive: `taskProgress {total: 44, completed: 44, allComplete: true}`, `applyState: all_done`, `nextRecommended: archive`, `blockedReasons: []`.
- Delivered as **6 stacked PRs** on GitHub `pdgramajo/Curriculum_Vitae` (public): #1 baseline+config, #2 discovery, #3 rendering, #4 CLI, #5 TUI, #6 launchers+legacy removal. All open at archive time; merge remains the user's decision under ordinary repository policy.
- Verified: `make check` green (pytest + ruff + pyright 0 errors), smoke test real RenderCV → PDF 64KB, TUI headless Pilot 5 scenarios, manual user test "funciona todo".

### Work completed after intermediate snapshots (final-state authority)

- `apply-progress.md` was the last intermediate snapshot (44/44 through PR 6). Since then:
  - User manually tested the TUI → confirmed working.
  - 6 PRs opened on GitHub (after all apply progress was written).
  - No source changes after the final apply-progress write; the snapshot and final state agree on implementation. No stale claims to correct.

## Delta Specs Synced (full specs → main)

The directory `openspec/specs/` was empty, so every delta spec was a **full spec** (not a delta). Each was copied mechanically with `cp` + `diff -r` readback (empty diffs, verbatim below):

| Domain | Action | File |
|--------|--------|------|
| cv-cli | Created (164 lines) | `openspec/specs/cv-cli/spec.md` |
| cv-config | Created (103 lines) | `openspec/specs/cv-config/spec.md` |
| cv-rendering | Created (160 lines) | `openspec/specs/cv-rendering/spec.md` |
| cv-tui | Created (148 lines) | `openspec/specs/cv-tui/spec.md` |

Readback output (verbatim):

```
READBACK OK: cv-cli
READBACK OK: cv-config
READBACK OK: cv-rendering
READBACK OK: cv-tui
```

## Mechanical Copy Verification

- Move `git mv openspec/changes/cv-tui-redesign openspec/changes/archive/2026-09-22-cv-tui-redesign`, preceded by recursive snapshot `cp -R` and followed by `diff -r "$snapshot_root/source" "$destination"`.
- Result: `ARCHIVE READBACK OK (empty diff)`. No differences — byte-identity preserved.
- The `archive-report.md` (this file) is additive and excluded from that comparison (it did not exist in the source snapshot).

## Archive Contents (observed)

- `proposal.md`: present
- `specs/`: present — 4 domains (cv-cli, cv-config, cv-rendering, cv-tui)
- `design.md`: present
- `tasks.md`: present — **44/44 complete**, 0 unfinished
- `apply-progress.md`: present (intermediate snapshot, preserved for history)

## Verification

- **sdd-verify** was not run during this change (diagnostic, optional; completed implementation went to archive by design).
- Functional verification was performed at phase boundaries: 40 unit tests + 1 smoke test passing, ruff format/lint clean, pyright standard 0 errors, real RenderCV smoke (PDF 64KB) and headless TUI pilot (5 scenarios).
- User-accepted manual TUI test.

## Unresolved findings / unfinished work

- **None observed in implementation.** The 44/44 tasks are complete.
- Operations remaining are delivery decisions belonging to the user under ordinary repository policy: merge PRs #1→#6, optional manual double-click test of `Generar CV.command`, optional GitHub Actions CI. Not SDD unfinished work.

## Deviations recorded during the cycle (from apply-progress, preserved)

- RenderCV 2.8 uses ruamel.yaml, not PyYAML (design §4.2 corrected during implementation).
- ruff 0.16 formats Markdown fences → `include = ["*.py"]`.
- pyright standard mode requires explicit `venvPath/venv`.
- Textual 8.2.5: LoadingIndicator instead of Spinner; per-screen chrome (app-level compose not applicable).
- `esc`/`q` exit app-wide (spec wins over design).
- Task 5.5 (switch + deletion) split into two commits (proposal forbids destruction alongside feature code).
- Config archive rule "repo has no git history" is stale: the repo is now a git repo with a `baseline` tag and 6 feature branches.

## SDD Cycle Complete

The change is archived. Implementation: **complete (44/44)**. Verification: functional checks passed with evidence; optional sdd-verify not run. Unfinished tasks: none. Unresolved findings: none in code; delivery decisions remain with the user.