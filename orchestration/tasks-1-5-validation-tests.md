# Tasks 1-5 Validation: Tests, Fixtures, Commands, Offline Artifacts

Date: 2026-07-06

Scope: current repo diff for Tasks 1-5 of
`docs/plans/graphify-extraction-contract-and-harness-calibration-plan.md`.
This validation inspected the changed tests, scorer code, suite fixture gate,
harness docs, and saved offline rebaseline artifacts. I did not modify project
source files.

## Summary

Tasks 1-5 are mostly covered and the main offline validation is green:

- `uv run pytest tests/test_semantic_eval.py -q` passed: 28 passed, 1 existing
  Hypothesis collection warning.
- `git diff --check` passed.
- `git diff -- graphify/llm.py --exit-code` passed, so Task 6 prompt work has
  not started in this diff.
- The saved rebaseline artifacts exist under
  `.semantic-evals/comparisons/scorer-v2-rebaseline/` and report 45 processed
  graph-bearing artifacts across 15 run groups, with 1 skipped empty artifact
  directory.
- Re-running `rebaseline-saved` twice to the same temporary output directory
  produced byte-identical `rebaseline.json` and `rebaseline.md`.
- I found no evidence of live model calls in the tested paths; `run-suite` tests
  monkeypatch `run_harness`, judge tests monkeypatch model calls/subprocess, and
  `rebaseline-saved` scores saved graph files only.

However, there are two acceptance/coverage issues worth fixing before calling
Checkpoint A fully sealed.

## Blockers / likely acceptance gaps

### 1. `scorer_version` is not stamped on every promised output payload

The plan says `scorer_version` should be added to every `score`, `run`,
`run-suite`, and `compare` output. The implementation stamps:

- score payloads: yes (`score_graph()` returns `scorer_version: 2`)
- run-suite payloads: yes (`_aggregate_suite()` returns `scorer_version: 2`)
- rebaseline payloads: yes
- run payloads: only the nested `score` object is stamped; `run.json` top level
  is not stamped
- compare payloads: baseline/candidate nested metadata include versions, and
  warnings work, but the compare payload itself has no top-level
  `scorer_version`

Evidence inspected:

- `graphify/semantic_eval.py:708-722` stamps `score_graph()`.
- `graphify/semantic_eval.py:896` writes run summary as
  `{backend, model, commands, score}` with no top-level scorer version.
- `graphify/semantic_eval.py:1273-1295` returns compare output with
  `baseline.scorer_version`, `candidate.scorer_version`, and `warnings`, but no
  top-level `scorer_version`.
- A temporary `compare_suite_runs()` probe printed `top scorer_version None`.

Suggested fix: add top-level `scorer_version: SCORER_VERSION` to `run_harness()`
summary and `compare_suite_runs()` output, then assert both via tests.

### 2. Gate behavior tests are too narrow for the recalibrated gate

The suite fixture gate was updated to `minimum_overall: 0.7` and
`minimum_critical_dimension: 0.45`, and docs match those values. Existing tests
exercise failing `run-suite` behavior, but not a passing gate or a specific
critical-dimension failure under the new floors.

Current coverage:

- `test_run_suite_aggregates_fixture_scores_without_live_model_calls` asserts a
  failure because weighted overall is `0.562`.
- Failure cases for fixture failure/no completed fixtures are covered.
- I did not find a unit test that proves a run at/above `0.70` overall and
  `0.45` critical dimensions passes.
- I did not find a unit test that proves overall can pass while a critical
  dimension below `0.45` fails with the expected gate failure.

Suggested fix: add two narrow `run_suite()` tests using a temporary suite or
monkeypatched fixture scores:

1. all present critical dimensions at `0.45` and overall `0.70` passes;
2. overall `>= 0.70` but `expected_edge_coverage == 0.449` fails with the
   `minimum_critical_dimension 0.45` message.

## Coverage assessment by requested focus area

### Mechanical folding positives / negatives

Covered, with minor gaps.

Existing positive coverage:

- `test_score_graph_folds_plural_and_camelcase_mechanical_variants` covers:
  - `Stale-State Markers` -> `stale state marker`
  - `EmbeddingJob` -> `embedding job`
  - dedup watchlist matching through plural folding

Existing negative coverage:

- `test_score_graph_keeps_mechanical_folding_conservative` covers:
  - `retry limit` does not match `Retry Policy`
  - `address` does not match `Addres`
  - `integration gateway` does not match `GatewayService`
- `test_score_graph_reports_near_misses_without_counting_them` still proves raw
  labels appear in diagnostics.

Gaps:

- No explicit test for `address` vs `addresses` being allowed to miss.
- No explicit test that mechanical folding applies safely to forbidden edge or
  forbidden concept comparisons. The implementation does apply comparison norms
  through `_matching_nodes()`/`_edge_matches()`, so this is behaviorally likely,
  but not directly locked.

Priority: medium. Current positive/negative concept coverage is adequate for the
core bug, but forbidden-path coverage would reduce regression risk.

### Edge coverage / relation split

Partially covered.

Covered:

- `test_score_graph_reports_expected_edge_relation_mismatch` verifies correct
  endpoints with generic relation now produce:
  - `expected_edge_coverage == 1.0`
  - `expected_edge_relation_agreement == 0.0`
  - `overall == 1.0`, proving relation agreement is excluded from weighted
    overall for that fixture
  - relation mismatch diagnostics include the found candidate relation
- `test_score_graph_reports_expected_edge_missing_endpoint` verifies
  `endpoint_miss` and `endpoint_miss == target` diagnostics.

Behavior manually spot-checked in a temporary graph:

- undirected reversed edge with matching relation scored edge coverage `1.0` and
  relation agreement `1.0`;
- directed reversed edge scored edge coverage `0.0` and relation agreement
  `None`.

Gaps:

- No committed test explicitly covers fully matched relation agreement `1.0`.
- No committed test explicitly covers undirected reversed endpoint matching.
- No committed test covers the `edge_miss` diagnostic path where both endpoints
  exist but no edge connects them.

Priority: high. The implementation behaved correctly in a manual temp probe,
but Task 3 explicitly requested fully matched and undirected tests.

### `scorer_version` / compare warning

Partially covered, with one blocker above.

Covered:

- score CLI output asserts `payload["scorer_version"] == SCORER_VERSION`.
- `run_suite()` aggregate asserts top-level `scorer_version`.
- `test_compare_suite_runs_warns_when_scorer_versions_differ` verifies mixed
  scorer versions emit the expected warning and expose baseline/candidate
  versions.

Gaps:

- compare output itself lacks a top-level `scorer_version`.
- run output itself lacks a top-level `scorer_version`.
- compare CLI test does not assert warnings are written to the Markdown report,
  though `_comparison_markdown()` appears to render them.

Priority: high for top-level payload stamping; low/medium for Markdown warning
assertion.

### Gate behavior

Partially covered.

Covered:

- suite fixture values are updated and docs match:
  - `minimum_overall: 0.7`
  - `minimum_critical_dimension: 0.45`
- `run-suite` non-zero/fail behavior is still covered for low overall and
  fixture failures.
- Rebaseline artifacts apply the configured gate and show the intended
  full-suite separation: two GLM full-suite runs pass; DeepSeek/minimax/Kimi/Qwen
  rows fail for overall and/or edge-coverage floor.

Gaps:

- No unit test for a passing gate at the new floors.
- No unit test for a critical-dimension-only failure under the new floors.
- `_run_gate()` used by rebaseline aggregates is not directly tested.

Priority: high because Task 5 acceptance explicitly calls out gate pass/fail
behavior.

### Deterministic rebaseline

Covered by command validation, but not by a committed test.

Artifact inspection:

- `.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.json` exists
  and is ignored by git.
- Summary reports:
  - `processed_graphs: 45`
  - `processed_runs: 15`
  - `skipped_artifacts: 1`
  - Sonnet `integration_gateway` v2 edge coverage spot check: `0.35`, up from
    v1 `0.0`
- Direct graph glob count is 45.
- Dated snapshot graph count is 44 and is excluded by the `**/corpus/graphify-out/graph.json`
  glob.
- Required runs are present and graph-bearing where expected:
  - `glm-5.2-cloud-suite-amended-20260629-151816`: 6 graphs
  - `deepseek-v4-pro-cloud-suite-20260701-compare`: 6 graphs
  - `minimax-m3-cloud-suite-20260614-112409`: 6 graphs
  - `claude-cli-sonnet-integration-gateway-20260706`: 1 graph
  - `model-quality-comparison-20260614-191220`: 12 graphs, with empty
    `gemma4_12b` skipped

Command validation:

- Two reruns to the same temp out dir were byte-identical for JSON and Markdown.
- Two reruns to different output dirs differ only because `artifact_dir` embeds
  the chosen output path. That is acceptable for same-output deterministic
  reruns, but it means cross-output byte identity should not be expected.

Gap:

- No committed unit/CLI test covers `rebaseline-saved` on a tiny temp
  `.semantic-evals` tree. The full local artifact validation is useful but not
  portable in CI.

Priority: medium. Add a small synthetic rebaseline test if this subcommand is
intended to be durable.

### No live model calls

Covered by inspection and command behavior.

Verified:

- `uv run pytest tests/test_semantic_eval.py -q` did not invoke live backends.
- `run_suite()` tests monkeypatch `semantic_eval.run_harness`.
- judge tests monkeypatch `_call_judge_model` or `semantic_eval.subprocess.run`.
- `rebaseline_saved_artifacts()` reads saved `graph.json`, `.graphify_labels.json`,
  and expected contracts; it does not call `run_harness()` or `_run_cmd()`.
- Rebaseline artifact methodology records `model_calls: false`.

Residual risk:

- `test_score_graph_cli_outputs_json` uses a local Python subprocess, which is
  fine; it is not a model call.
- Judge helper tests still cover command construction, but subprocess is mocked.

## Suggested targeted validation before Checkpoint A closeout

- Add/verify top-level `scorer_version` on `run` and `compare` payloads.
- Add unit tests for:
  - relation agreement `1.0` when endpoints and relation both match;
  - undirected reversed edge matching;
  - gate pass at `0.70`/`0.45` floors;
  - gate fail when only one critical dimension is below `0.45`;
  - optional tiny `rebaseline-saved` fixture tree proving no snapshot double
    count and deterministic output.
- Re-run:

```bash
uv run pytest tests/test_semantic_eval.py -q
git diff --check
git diff -- graphify/llm.py --exit-code
```

- If keeping `rebaseline-saved` as a durable operator command, run a same-output
  deterministic check in `/tmp` again and record that cross-output JSON differs
  only by `artifact_dir`.
