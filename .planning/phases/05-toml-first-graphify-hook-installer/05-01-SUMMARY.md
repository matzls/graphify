---
phase: 05-toml-first-graphify-hook-installer
plan: 01
subsystem: cli-installer
tags: [codex, hooks, toml, migration, tests]
requires: []
provides:
  - TOML marker helpers for Graphify Codex SessionStart and PreToolUse hooks
  - strict Graphify-owned hook detection for legacy hooks.json migration
  - focused regression coverage for fresh install and legacy JSON cleanup
affects: [codex-hook-installer, hook-rollout-hygiene]
tech-stack:
  added: []
  patterns: [marker-block-toml-ownership, conservative-json-hook-migration]
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - tests/test_install.py
key-decisions:
  - "Use explicit Graphify TOML marker blocks for owned Codex hooks."
  - "Treat legacy hooks.json as migration input and remove only entries with strict Graphify command or marker evidence."
patterns-established:
  - "Render owned TOML hooks from private helpers using _resolve_graphify_exe()."
  - "Fail closed on invalid legacy hooks.json by preserving the file for manual repair."
requirements-completed: [HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05]
duration: 45 min
completed: 2026-05-12
---

# Phase 05 Plan 01: TOML-First Hook Helper Summary

**TOML-owned Codex hook helpers with conservative legacy JSON migration coverage**

## Performance

- **Duration:** 45 min
- **Started:** 2026-05-12T16:37:54Z
- **Completed:** 2026-05-12T17:22:32Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added explicit PreToolUse TOML marker constants alongside the existing SessionStart markers.
- Added private render, marker replacement, ownership detection, and legacy JSON cleanup helpers.
- Added focused install tests proving fresh Codex installs write `.codex/config.toml` only and migrate Graphify-owned legacy JSON safely.

## Task Commits

1. **Task 1: Add tests for TOML-first fresh install shape** - `831ef0b`
2. **Task 2: Add tests for legacy JSON ownership classification** - `831ef0b`
3. **Task 3: Implement private ownership, rendering, and cleanup helpers** - `831ef0b`

## Files Created/Modified

- `graphify/__main__.py` - Adds private Codex TOML rendering, marker replacement, strict ownership detection, and legacy JSON cleanup helpers.
- `tests/test_install.py` - Adds focused fresh-install and legacy JSON migration assertions.

## Decisions Made

- Marker-block replacement stayed the TOML editing strategy to avoid introducing a TOML writer dependency.
- Invalid legacy `.codex/hooks.json` is preserved and reported for manual repair instead of being overwritten.

## Deviations from Plan

Process deviation: inline Codex execution completed Wave 1 and Wave 2 in one production commit instead of one commit per task. Product scope stayed within the plan.

## Issues Encountered

The repo environment did not include `pytest` as a project dependency. Verification used `uv run --with pytest pytest ...`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 05-02 wiring and end-to-end verification.

---
*Phase: 05-toml-first-graphify-hook-installer*
*Completed: 2026-05-12*
