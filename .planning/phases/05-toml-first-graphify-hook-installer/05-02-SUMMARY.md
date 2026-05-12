---
phase: 05-toml-first-graphify-hook-installer
plan: 02
subsystem: cli-installer
tags: [codex, hooks, toml, uninstall, startup-json]
requires:
  - phase: 05-toml-first-graphify-hook-installer
    provides: TOML-first Graphify Codex hook helpers
provides:
  - TOML-first install convergence for Graphify Codex hooks
  - uninstall cleanup for owned TOML blocks and legacy JSON entries
  - targeted regression coverage for install, uninstall, startup JSON, and stale semantic refresh behavior
affects: [codex-hook-installer, codex-session-start, hook-rollout-hygiene]
tech-stack:
  added: []
  patterns: [toml-first-codex-hook-install, safe-legacy-hook-cleanup]
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_install.py
    - tests/test_hooks.py
key-decisions:
  - "Fresh Codex installs no longer create .codex/hooks.json for Graphify hooks."
  - "Install and uninstall share the same strict legacy JSON cleanup path."
patterns-established:
  - "Use .codex/config.toml as the single active Graphify Codex hook representation."
  - "Keep startup semantic-refresh guidance in SessionStart JSON, not PreToolUse hook-check output."
requirements-completed: [HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, START-01, START-02, START-03, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05]
duration: 45 min
completed: 2026-05-12
---

# Phase 05 Plan 02: TOML-First Installer Wiring Summary

**Codex install and uninstall now converge Graphify-owned hooks to `.codex/config.toml` while preserving unrelated user hooks**

## Performance

- **Duration:** 45 min
- **Started:** 2026-05-12T16:37:54Z
- **Completed:** 2026-05-12T17:22:32Z
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments

- Wired `_install_codex_hook()` to write both Graphify SessionStart and PreToolUse/Bash hooks into `.codex/config.toml`.
- Changed fresh Codex installs so Graphify does not create `.codex/hooks.json`.
- Wired uninstall to remove owned TOML blocks and Graphify-owned legacy JSON entries while preserving unrelated JSON and TOML content.
- Added end-to-end tests for duplicate TOML collapse, both-present migration, uninstall preservation, invalid JSON preservation, and startup refresh context.

## Task Commits

1. **Task 1: Add end-to-end install, migration, dedupe, and uninstall tests** - `831ef0b`
2. **Task 2: Wire TOML-first behavior into install and uninstall** - `831ef0b`
3. **Task 3: Preserve startup JSON and semantic refresh marker behavior** - `831ef0b`
4. **Task 4: Run targeted Phase 5 verification** - `831ef0b`

## Files Created/Modified

- `graphify/__main__.py` - Updates Codex install/uninstall behavior and concise migration reporting.
- `tests/test_install.py` - Adds end-to-end installer, migration, dedupe, uninstall, and invalid JSON coverage.
- `tests/test_hooks.py` - Adds explicit startup-context assertion for the code-only refresh caveat.

## Decisions Made

- `.codex/hooks.json` is migration input only for Codex; Graphify-owned active hooks are rendered into `.codex/config.toml`.
- Invalid legacy JSON is a manual-review state, not a reason to overwrite or delete existing hook data.

## Deviations from Plan

Process deviation: inline Codex execution completed Wave 1 and Wave 2 in one production commit instead of one commit per task. Product scope stayed within the plan.

## Issues Encountered

The first pytest command failed because the project environment did not include the `pytest` executable. Verification was rerun successfully with `uv run --with pytest pytest ...`.

## Verification

- `uv run --with pytest pytest tests/test_install.py -q` - 54 passed.
- `uv run --with pytest pytest tests/test_install.py tests/test_hooks.py tests/test_watch.py -q` - 93 passed.
- Manual smoke: `PYTHONPATH=/Users/mase/Codebase/Personal-Projects/graphify-hook-rollout-hygiene python3 -m graphify codex install` in a temp repo created `.codex/config.toml` with one SessionStart marker, one PreToolUse marker, and no `.codex/hooks.json`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 5 targeted behavior is ready for workflow verification and any downstream rollout planning.

---
*Phase: 05-toml-first-graphify-hook-installer*
*Completed: 2026-05-12*
