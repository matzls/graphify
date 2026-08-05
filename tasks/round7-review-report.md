---
title: "Pi Backend Round 7 Review Report"
kind: report
status: done
audience: agents-maintainers
canonicality: historical
created: 2026-08-04
updated: 2026-08-05
source_of_truth: "./round7-review-report.md"
related:
  - "./plan.md"
  - "./todo.md"
  - "./round7-worker-report.md"
---

## Findings

- Correct: **No blocker.** For the scoped source swap during either graph writer, the guard does not leave A-semantics published as B with clean state. The raw path checks immediately before and after `write_json_atomic`, then scrubs the just-written graph on post-write invalidation (`graphify/cli.py:2176-2182`). The clustered path does the same around `to_json` (`graphify/cli.py:2348-2351`).
- Correct: On detection, reconciliation removes the stale image payload from `merged`, records the source as partial/identity-invalidated, marks extraction incomplete, increments the partial count once, and rebuilds manifest scope (`graphify/cli.py:1953-1966`). The on-disk scrub removes invalidated-source nodes and their related edges/hyperedges (`graphify/cli.py:1974-2020`).
- Correct: Marker and manifest finalization fail closed. Both paths perform another identity check before marker publication and pass the updated `semantic_partial_chunks` to the marker (`graphify/cli.py:2209-2222`, `graphify/cli.py:2369-2382`). Manifest scope excludes partial sources and places omitted dispatched sources in `clear_semantic` (`graphify/cli.py:1928-1938`), which is then supplied to manifest save (`graphify/cli.py:2225-2234`, `graphify/cli.py:2455-2464`). The parameterized test injects the swap inside both writer variants (`tests/test_cli_semantic_fail_closed.py:1169-1268`) and asserts A-semantics absent, marker status `partial`, and no image semantic hash (`tests/test_cli_semantic_fail_closed.py:1270-1278`).
- Note: Residual risk is limited to cases outside this review's exact scenario: the test covers successful writer and scrub operations, not I/O failure in the post-write scrub, nor a source replacement after the final identity check while marker/manifest publication itself is underway. Tests were not run, as instructed.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "review-findings cite graphify/cli.py:1928-2020, 2176-2234, 2348-2464 and tests/test_cli_semantic_fail_closed.py:1169-1278; residual-risks are stated explicitly"
    }
  ],
  "changedFiles": [
    "tasks/round7-review-report.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "nl -ba graphify/cli.py | sed -n '1915,2020p;2175,2245p;2340,2470p'",
      "result": "passed",
      "summary": "Read-only line-numbered inspection of the requested guard and publication/finalization calls."
    },
    {
      "command": "nl -ba tests/test_cli_semantic_fail_closed.py | sed -n '1078,1278p'",
      "result": "passed",
      "summary": "Read-only line-numbered inspection of the requested tests."
    },
    {
      "command": "pytest (not run per task instruction)",
      "result": "not-run",
      "summary": "The task expressly prohibited running tests."
    }
  ],
  "validationOutput": [
    "Manual inspection shows post-writer reconciliation and on-disk scrubbing in both raw and clustered paths.",
    "Manual inspection shows publication invalidation forces a partial marker and clears/excludes the image semantic hash from the manifest.",
    "The parameterized test asserts these outcomes for both writer variants, but was not executed."
  ],
  "residualRisks": [
    "No runtime test execution was permitted.",
    "The inspected test does not cover post-write scrub I/O failure or a replacement during marker/manifest publication after the final identity check."
  ],
  "noStagedFiles": true,
  "diffSummary": "Review-only: no source or test edits; wrote the required review report artifact.",
  "reviewFindings": [
    "no blocker: graphify/cli.py:2176-2234 and 2348-2464 - writer-time source swaps are detected after publication, stale image semantics are scrubbed, the marker is partial, and the manifest semantic hash is cleared",
    "verified coverage: tests/test_cli_semantic_fail_closed.py:1169-1278 - both raw and clustered writer swaps assert no A-semantics, partial marker status, and no diagram semantic hash"
  ],
  "manualNotes": "No repository scan, git-state inspection, subagents, or tests were run. noStagedFiles means this reviewer staged no files; existing repository staging state was intentionally not inspected."
}
```
