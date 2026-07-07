# Tasks 1-5 Validation: Correctness Review

## Review

### Correct

- Scorer v2 implements the intended scorer split: endpoint coverage is now independent of relation-term agreement, and relation agreement is excluded from fixture `overall` weighting. Evidence: `graphify/semantic_eval.py:438-507` computes `expected_edge_coverage` from endpoint edges and `expected_edge_relation_agreement` separately; `graphify/semantic_eval.py:683-700` excludes `expected_edge_relation_agreement` from weighted dimensions.
- Mechanical label folding is conservative in the covered paths. Evidence: `_norm`, `_comparison_norm`, `_concept_norms`, and `_node_norms` are updated in `graphify/semantic_eval.py:29-139`; tests cover positive CamelCase/plural cases and negative near-misses in `tests/test_semantic_eval.py:84-154`.
- Relation-mismatch diagnostics include actual candidate relations. Evidence: `graphify/semantic_eval.py:491-502`; test coverage at `tests/test_semantic_eval.py:189-247`.
- Scope boundary is respected for Tasks 1-5. `git diff --name-only` shows only `docs/semantic-model-quality-harness.md`, `graphify/semantic_eval.py`, `tests/fixtures/semantic_eval/suite.json`, and `tests/test_semantic_eval.py`; `git diff -- graphify/llm.py --exit-code` produced no diff. No Task 6/7 prompt or live-run changes were present.
- Rebaseline artifacts exist and are data-grounded. Evidence: `.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.md:1-28` reports 45 processed graphs, 15 processed runs, 1 skipped empty artifact, full-suite separation, and the Sonnet spot check at 0.35 edge coverage. I also re-ran `rebaseline-saved` to `/tmp/graphify-rebaseline-check`; repeated runs were byte-identical, and the generated payload matched the checked-in artifact except for the `artifact_dir` path.
- Gate calibration is grounded in the v2 full-suite distribution. Evidence: `tests/fixtures/semantic_eval/suite.json:5-15` sets `minimum_overall: 0.7` and `minimum_critical_dimension: 0.45`; `docs/semantic-model-quality-harness.md:151-170` justifies these against the rebaseline table. Under those floors, only the two GLM full-suite rows pass, while DeepSeek/Kimi/Qwen fail on edge coverage and MiniMax fails overall.

### Blocker

- Checkpoint A is not fully satisfied until scorer-version stamping is completed for all planned outputs. The plan requires `scorer_version` on `score`, `run`, `run-suite`, and `compare` outputs. `score_graph` and `run-suite` are stamped, but `run_harness` writes `run.json` without a top-level `scorer_version` at `graphify/semantic_eval.py:896-897` and its failure-path summary is also unstamped at `graphify/semantic_eval.py:883-884`. `compare_suite_runs` returns embedded baseline/candidate versions and warnings, but the comparison artifact itself has no top-level `scorer_version` at `graphify/semantic_eval.py:1273-1295`. This also makes the doc claim at `docs/semantic-model-quality-harness.md:118-121` partially false for compare payloads. Add the missing stamps and tests before treating Checkpoint A as complete.

### Non-blocking concerns

- Existing tests did not catch the stamping gap. The compare-version warning is tested in `tests/test_semantic_eval.py:590-606`, but there is no assertion that `run`/`run.json` or compare output carries its own top-level `scorer_version`.
- Current state cannot independently prove Task 1's historical pre-Task-2 clean worktree; the worker report claims it, but the present checkout is dirty with the expected Task 2-5 tracked diffs plus untracked orchestration files.
- The rebaseline Markdown includes single-fixture gate states that can pass even when no expected-edge critical dimension is present, e.g. `.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.md:15` and `:24`. The harness doc's gate rationale correctly uses full-suite rows, so this is not a blocker; just avoid using single-fixture gate pass rows as model-selection evidence.

## Validation run

- `uv run pytest tests/test_semantic_eval.py -q` — passed: 28 passed, 1 existing Hypothesis warning.
- `git diff --check` — passed.
- `git diff -- graphify/llm.py --exit-code` — passed/no diff.
- `uv run python -m graphify.semantic_eval rebaseline-saved --root .semantic-evals --suite tests/fixtures/semantic_eval/suite.json --out-dir /tmp/graphify-rebaseline-check` twice, then `diff -q` — deterministic.
- Sonnet spot check via `score` CLI confirmed scorer v2 edge coverage `0.35`, relation agreement `0.0`, concept recall `0.769`.

## Recommended next action

Make a small Task 3 completion fix: add top-level `scorer_version: SCORER_VERSION` to `run_harness` success and failure summaries and to `compare_suite_runs` output, add targeted tests, then rerun `uv run pytest tests/test_semantic_eval.py -q`, `git diff --check`, and the `/tmp` deterministic rebaseline check. After that, Checkpoint A can be considered reached and Tasks 6-8 can remain gated for operator approval.
