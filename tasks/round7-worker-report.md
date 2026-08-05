---
title: "Pi Backend Repair Round 7 Worker Report"
kind: report
status: done
audience: agents-maintainers
canonicality: historical
created: 2026-08-04
updated: 2026-08-05
source_of_truth: "./round7-worker-report.md"
related:
  - "./plan.md"
  - "./todo.md"
  - "./round7-review-report.md"
---

> Historical worker checkpoint. The independent reviewer gate recorded as
> pending below later completed without a blocker; `tasks/todo.md` and lifecycle
> state are authoritative for final status.

## Summary

Implemented the macOS CP-1 final CLI graph-publication identity repair.

## Changed paths

- `graphify/cli.py`
  - Carries adapter-captured raster identities through the private CLI publication boundary without serializing identity objects.
  - Rechecks identities immediately before and after both clustered and `--no-cluster` graph publication, plus before marker finalization.
  - On replacement, marks the run partial, removes the invalidated source from manifest stamping, scrubs source-owned nodes/edges/hyperedges from an already-written graph, and skips clustered sidecars derived from the unsanitized graph.
  - Existing cache/provenance and ordinary text/non-image paths remain unchanged.
- `tests/test_cli_semantic_fail_closed.py`
  - Added deterministic parametrized regressions for clustered and `--no-cluster` graph-writer replacement races.
  - Both assert no `A-semantics` graph node, a partial semantic marker, and no semantic manifest stamp.

Pre-existing dirty paths were not reverted or modified for this round.

## Validation evidence

- `uv run --frozen pytest -q tests/test_pi_cli_backend.py tests/test_image_vision.py tests/test_cli_semantic_fail_closed.py tests/test_cache.py tests/test_extract_cli.py -k 'not windows'`: **225 passed, 6 deselected**.
- `uv run --frozen pytest -q tests/test_llm_backends.py tests/test_word_count_cache.py tests/test_cli_export.py -k 'not windows'`: **148 passed**.
- Focused post-edit race/cache regressions: **3 passed, 25 deselected**.
- `uv run --frozen ruff check graphify/cli.py tests/test_cli_semantic_fail_closed.py`: passed.
- `uv run --frozen pyright graphify/cli.py tests/test_cli_semantic_fail_closed.py`: **0 errors, 0 warnings, 0 informations**.
- `uv run --frozen python -m py_compile graphify/cli.py tests/test_cli_semantic_fail_closed.py`: passed.
- `git diff --check`: passed.
- `git diff --cached --name-only`: empty; no staged files.
- No live calls, installs, commits, pushes, global edits, or subagent runs.

The bare `python -m py_compile` probe was unavailable (`python: command not found`); the equivalent frozen-uv compile check passed.

## Remaining concerns

- Native Windows runtime behavior remains outside this macOS CP-1 acceptance scope and was not exercised.
- The publication guard is fail-closed at the durable graph/marker/manifest boundary; a replacement occurring after the final check and before a subsequent unrelated side effect is outside this bounded repair.
- Required independent reviewer gate remains pending.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Only graphify/cli.py publication handling and its focused CLI regression file were changed for the requested CP-1 race; no CP-2/later, install, global, or Git mutation was performed."
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "The clustered and --no-cluster deterministic regressions both replace the source during graph publication and verify no A-semantics node, partial marker status, and unstamped manifest; 225 CP-1-focused tests, 148 compatibility tests, Ruff, Pyright, compile, and diff checks passed."
    }
  ],
  "changedFiles": [
    "graphify/cli.py",
    "tests/test_cli_semantic_fail_closed.py",
    "tasks/round7-worker-report.md"
  ],
  "testsAddedOrUpdated": [
    "tests/test_cli_semantic_fail_closed.py::test_extract_graph_publication_identity_race_is_partial[no-cluster]",
    "tests/test_cli_semantic_fail_closed.py::test_extract_graph_publication_identity_race_is_partial[clustered]"
  ],
  "commandsRun": [
    {
      "command": "uv run --frozen pytest -q tests/test_pi_cli_backend.py tests/test_image_vision.py tests/test_cli_semantic_fail_closed.py tests/test_cache.py tests/test_extract_cli.py -k 'not windows'",
      "result": "passed",
      "summary": "225 passed, 6 deselected"
    },
    {
      "command": "uv run --frozen pytest -q tests/test_llm_backends.py tests/test_word_count_cache.py tests/test_cli_export.py -k 'not windows'",
      "result": "passed",
      "summary": "148 passed"
    },
    {
      "command": "uv run --frozen pytest -q tests/test_cli_semantic_fail_closed.py -k 'graph_publication_identity_race or late_pixel_cache_identity_mismatch'",
      "result": "passed",
      "summary": "3 passed, 25 deselected"
    },
    {
      "command": "uv run --frozen ruff check graphify/cli.py tests/test_cli_semantic_fail_closed.py",
      "result": "passed",
      "summary": "All checks passed"
    },
    {
      "command": "uv run --frozen pyright graphify/cli.py tests/test_cli_semantic_fail_closed.py",
      "result": "passed",
      "summary": "0 errors, 0 warnings, 0 informations"
    },
    {
      "command": "uv run --frozen python -m py_compile graphify/cli.py tests/test_cli_semantic_fail_closed.py",
      "result": "passed",
      "summary": "Compilation passed"
    },
    {
      "command": "git diff --check && git diff --cached --name-only",
      "result": "passed",
      "summary": "Diff clean; staged path list empty"
    },
    {
      "command": "python -m py_compile graphify/cli.py",
      "result": "failed",
      "summary": "System python command is unavailable; frozen-uv equivalent passed"
    }
  ],
  "validationOutput": [
    "Both graph publication modes remove A-semantics after deterministic A-to-B replacement.",
    "Partial marker and unstamped manifest are preserved across both modes.",
    "Existing cache/image/text compatibility suites passed."
  ],
  "residualRisks": [
    "Native Windows runtime identity behavior was not exercised under the macOS-only CP-1 scope.",
    "Independent reviewer gate is still pending."
  ],
  "noStagedFiles": true,
  "diffSummary": "Private CLI publication identity tracking, before/after publication reconciliation, fail-partial graph scrubbing, manifest/marker protection, and clustered/no-cluster deterministic regressions.",
  "reviewFindings": [
    "no blocker found in worker validation; independent required review remains pending"
  ],
  "manualNotes": "Pre-existing dirty worktree paths were preserved. No live calls, installs, commits, pushes, global edits, or subagent runs were performed."
}
```
