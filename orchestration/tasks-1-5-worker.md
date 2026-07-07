# Tasks 1-5 Worker Report

Implemented Tasks 1-5 from `docs/plans/graphify-extraction-contract-and-harness-calibration-plan.md` and stopped at Checkpoint A.

## Result

Checkpoint A is reached:

- worktree was clean before implementation began
- semantic-eval scorer v2 is implemented and tested
- saved graph-bearing artifacts were re-scored offline with no model calls
- rebaseline Markdown and JSON exist under `.semantic-evals/comparisons/scorer-v2-rebaseline/`
- quality gate floors are calibrated from the rebaseline table
- `graphify/llm.py` is untouched
- Task 6 prompt work and Task 7 live A/B were not started

## What changed

- `graphify/semantic_eval.py`
  - Added scorer version stamping.
  - Added CamelCase splitting and conservative trailing-plural folding for matching.
  - Split endpoint-based `expected_edge_coverage` from report-only `expected_edge_relation_agreement`.
  - Added relation mismatch diagnostics while keeping relation agreement out of weighted `overall`.
  - Added mixed-scorer-version warnings in `compare`.
  - Added offline `rebaseline-saved` support with scorer-v1 compatibility scoring for old/new comparison.
- `tests/test_semantic_eval.py`
  - Added/updated offline tests for normalization, endpoint/relation split, scorer version, compare warning, and gate behavior.
- `tests/fixtures/semantic_eval/suite.json`
  - Recalibrated `minimum_critical_dimension` from `0.8` to `0.45`; `minimum_overall` remains `0.7`.
- `docs/semantic-model-quality-harness.md`
  - Documented scorer v2, endpoint/relation split semantics, scorer-version compatibility, rebaseline location, and gate rationale.
  - Marked the old candidate baseline table as scorer-v1/superseded for gate decisions.
- `.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.json`
- `.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.md`
  - Offline rebaseline artifacts. These are ignored by git but present on disk.

## Rebaseline summary

No model calls were made. The offline rebaseline processed 45 saved graph-bearing artifacts across 15 run directories and skipped one empty artifact directory:

- `.semantic-evals/model-quality-comparison-20260614-191220/gemma4_12b` — no graph-bearing artifacts found

Full-suite v2 aggregate highlights:

| Run | Overall | Concept recall | Edge coverage | Relation agreement | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `glm-5.2-cloud-suite-amended-20260629-151816` | 0.745 | 0.689 | 0.491 | 0.118 | pass |
| `glm-5.2-cloud-suite-20260629-120625` | 0.737 | 0.714 | 0.451 | 0.132 | pass |
| `deepseek-v4-pro-cloud-suite-20260701-compare` | 0.710 | 0.612 | 0.335 | 0.117 | fail |
| `minimax-m3-cloud-suite-20260614-112409` | 0.697 | 0.693 | 0.497 | 0.220 | fail |
| `model-quality-comparison-20260614-191220/kimi-k2.7-code_cloud` | 0.697 | 0.749 | 0.448 | 0.048 | fail |
| `model-quality-comparison-20260614-191220/qwen3.5_397b-cloud` | 0.695 | 0.560 | 0.442 | 0.210 | fail |

Sonnet integration-gateway spot check: v2 `expected_edge_coverage` is `0.35`, up from scorer-v1 `0.0`.

## Validation

- `uv run pytest tests/test_semantic_eval.py -q` passed: 28 passed, 1 existing Hypothesis collection warning.
- `git diff --check` passed.
- `git diff -- graphify/llm.py --exit-code` passed, confirming no prompt changes.
- Rebaseline deterministic rerun passed by diffing `rebaseline.json` after two consecutive runs.
- `git diff --cached --quiet` passed: no staged files.

## What Mase should review before authorizing Tasks 6-8

1. Gate floors: `minimum_overall = 0.70`, `minimum_critical_dimension = 0.45`.
2. Whether GLM being the only full-suite passer under these floors matches operator intent.
3. The low relation-agreement values, which confirm Task 6 prompt work is still needed before live A/B.
4. The Sonnet single-fixture edge coverage improvement to `0.35`, which is below the Task 7 target of `>= 0.4` but confirms the structural floor is partly removed.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "scope",
      "status": "satisfied",
      "evidence": "Implemented only Tasks 1-5; git diff shows no changes to graphify/llm.py; no commits, pushes, installs, reinstalls, or live run/run-suite backend calls were performed."
    },
    {
      "id": "scorer",
      "status": "satisfied",
      "evidence": "graphify/semantic_eval.py now implements mechanical CamelCase/plural matching, endpoint-based expected_edge_coverage, report-only expected_edge_relation_agreement, relation mismatch diagnostics, scorer_version stamping, and compare warnings for mixed scorer versions."
    },
    {
      "id": "rebaseline",
      "status": "satisfied",
      "evidence": "Offline rebaseline artifacts written to .semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.json and rebaseline.md; 45 graph-bearing saved artifacts processed; one empty artifact directory skipped; deterministic rerun diff passed."
    },
    {
      "id": "gate-docs",
      "status": "satisfied",
      "evidence": "tests/fixtures/semantic_eval/suite.json and docs/semantic-model-quality-harness.md agree on minimum_overall 0.70 and minimum_critical_dimension 0.45, justified from the scorer-v2 rebaseline table; scorer-v1 baselines are marked superseded."
    },
    {
      "id": "checkpoint-a",
      "status": "satisfied",
      "evidence": "Offline tests are green, rebaseline table exists, gate floors are justified from data, and no prompt changes or live A/B work were started."
    }
  ],
  "changedFiles": [
    "docs/semantic-model-quality-harness.md",
    "graphify/semantic_eval.py",
    "tests/fixtures/semantic_eval/suite.json",
    "tests/test_semantic_eval.py",
    ".semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.json",
    ".semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.md",
    "orchestration/tasks-1-5-worker.md"
  ],
  "testsAddedOrUpdated": [
    "tests/test_semantic_eval.py::test_score_graph_folds_plural_and_camelcase_mechanical_variants",
    "tests/test_semantic_eval.py::test_score_graph_keeps_mechanical_folding_conservative",
    "tests/test_semantic_eval.py::test_score_graph_reports_expected_edge_relation_mismatch",
    "tests/test_semantic_eval.py::test_score_graph_reports_expected_edge_missing_endpoint",
    "tests/test_semantic_eval.py::test_compare_suite_runs_warns_when_scorer_versions_differ",
    "tests/test_semantic_eval.py::test_score_graph_cli_outputs_json",
    "tests/test_semantic_eval.py::test_run_suite_aggregates_fixture_scores_without_live_model_calls"
  ],
  "commandsRun": [
    {
      "command": "git status --short --branch",
      "result": "passed",
      "summary": "Initial status was clean on mase/local-fixes before edits."
    },
    {
      "command": "uv run pytest tests/test_semantic_eval.py -q",
      "result": "passed",
      "summary": "28 passed, 1 existing Hypothesis collection warning."
    },
    {
      "command": "uv run python -m graphify.semantic_eval rebaseline-saved --root .semantic-evals --suite tests/fixtures/semantic_eval/suite.json --out-dir .semantic-evals/comparisons/scorer-v2-rebaseline",
      "result": "passed",
      "summary": "Offline rebaseline completed with 45 processed graphs, 15 processed runs, and 1 skipped empty artifact directory."
    },
    {
      "command": "cp rebaseline.json to /tmp, rerun rebaseline-saved, diff -q copied JSON against regenerated JSON",
      "result": "passed",
      "summary": "Deterministic rerun check passed with no diff."
    },
    {
      "command": "git diff --check && git diff -- graphify/llm.py --exit-code && git status --short",
      "result": "passed",
      "summary": "Whitespace check passed; graphify/llm.py has no diff; tracked dirty files are the expected docs/scorer/test/suite files."
    },
    {
      "command": "git diff --cached --quiet",
      "result": "passed",
      "summary": "No staged files."
    }
  ],
  "validationOutput": [
    "tests/test_semantic_eval.py: 28 passed, 1 warning in 0.20s",
    "rebaseline summary: processed_graphs=45, processed_runs=15, skipped_artifacts=1, sonnet_integration_gateway_new_edge_coverage=0.35",
    "full-suite v2 passers under calibrated gate: glm-5.2-cloud-suite-20260629-120625 and glm-5.2-cloud-suite-amended-20260629-151816",
    "git diff -- graphify/llm.py --exit-code produced no diff"
  ],
  "residualRisks": [
    "The scorer-v1 compatibility implementation is local to graphify.semantic_eval for offline comparison; it is not a general historical scorer framework.",
    "Single-fixture rebaseline rows can pass the aggregate gate when a critical dimension is absent; the documented gate rationale is based on full-suite rows only.",
    "Relation agreement remains low across saved runs, so Task 6 prompt work is still necessary before live A/B validation."
  ],
  "noStagedFiles": true,
  "diffSummary": "Semantic scorer v2 now separates endpoint coverage from relation agreement, folds mechanical label variants, stamps scorer versions, warns on mixed-version compare, and can offline rebaseline saved graph artifacts; suite gate/docs are calibrated from the generated scorer-v2 table.",
  "reviewFindings": [],
  "manualNotes": "Requested context.md and plan.md were not present in the repo; the canonical plan at docs/plans/graphify-extraction-contract-and-harness-calibration-plan.md was used. .semantic-evals outputs are ignored by git but present on disk.",
  "notes": "Checkpoint A reached. Review the gate floors and rebaseline table before authorizing Tasks 6-8."
}
```
