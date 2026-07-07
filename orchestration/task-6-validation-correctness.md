# Task 6 validation correctness review

## Scope

Reviewed the current Task 6 diff for:

- `graphify/llm.py`
- `tests/test_llm_prompt_contract.py`
- `tests/test_semantic_cleanup.py`
- `tests/test_callflow_html.py`
- `tests/test_report.py`
- `tests/test_analyze.py`

The broader Tasks 1-5 diff is present but was not reviewed except where needed for Task 6 validation commands.

## Blockers

None found.

## Correct

- Prompt contract is updated with the planned guided-open relation wording and canonical concept naming rule. Evidence: `graphify/llm.py:614` prefers source-grounded lowercase verbs and lists the preferred set; `graphify/llm.py:616` preserves document noun phrases and separates code identifiers from document concepts; `graphify/llm.py:621` updates the schema example to include the preferred verbs and an open-ended placeholder.
- The prompt test checks the new contract text and guards against the old contiguous closed-enum string. Evidence: `tests/test_llm_prompt_contract.py:6-14`.
- Semantic cleanup is relation-agnostic as required: validation checks only edge shape/endpoints, not a relation enum, and sanitize preserves surviving edge dicts unchanged. Evidence: `graphify/semantic_cleanup.py:83-88`, `graphify/semantic_cleanup.py:258-265`; regression test at `tests/test_semantic_cleanup.py:368-382`.
- Callflow relation labels have a neutral fallback for unknown strings via `relation.replace("_", " ")`, and the new unit test covers `writes` and `records_to`. Evidence: `graphify/callflow_html.py:525-553`, `tests/test_callflow_html.py:56-58`.
- Analyze/report consumers do not reject free-form relations. Analyze only filters known low-value structural relations, so `writes` is eligible for scoring; report interpolates the relation string in the ambiguous-edge section. Evidence: `graphify/analyze.py:286-301`, `tests/test_analyze.py:214-238`, `graphify/report.py:233-241`, `tests/test_report.py:119-150`.
- Checkpoint B is functionally reachable without live calls: the Task 6 prompt/downstream contract is covered by offline tests and a local temp-file callflow smoke; no backend/model commands were run.

## Non-blocking concerns

1. There is unnecessary broad test churn in `tests/test_analyze.py` beyond the free-form relation regression: fixture loading was refactored (`tests/test_analyze.py:13-19`), several boolean assertions were restyled (`tests/test_analyze.py:296-305`, `tests/test_analyze.py:501-510`), and the parametrized npm dependency-block test was collapsed into a loop (`tests/test_analyze.py:516-570`). This still tests the cases, but it is unrelated to Task 6 and loses per-parameter pytest reporting. Prefer reverting or splitting that churn if the goal is a minimal Task 6 diff.
2. Task 6 says the edge-direction rules should remain unchanged, but the prompt also changes that block by adding `cites` to the imports/references line and adding a new `domain verbs` direction rule. Evidence: `graphify/llm.py:608-612`. The change is reasonable for free-form relation orientation, but it should be consciously accepted as part of the prompt contract rather than accidental scope drift.
3. The committed callflow test only checks `relation_label()`, not a full `write_callflow_html()` fixture containing `writes`. I manually smoked that path with a temporary graph and confirmed `callflow.html` was written and contained `writes`, but adding that as a small regression test would align more directly with the Task 6 acceptance text.
4. `preferred_edges()` still treats new domain verbs as neither primary nor secondary, so free-form relation edges render when no preferred structural edge exists but may be omitted from representative section diagrams when calls/imports are present. Evidence: `graphify/callflow_html.py:556-569`. This appears consistent with the existing callflow prioritization, but it is worth watching during Task 7 if semantic/document edges are expected to be visible in mixed diagrams.

## Validation run

- `uv run pytest tests/test_llm_prompt_contract.py tests/test_semantic_cleanup.py tests/test_callflow_html.py tests/test_report.py tests/test_analyze.py tests/test_semantic_eval.py tests/test_file_slice.py -q` → 145 passed, 1 existing Hypothesis collection warning.
- Temp local smoke with `uv run python` created a synthetic `graphify-out/graph.json` containing a `writes` edge and called `write_callflow_html(...)` → wrote `callflow.html`; output contained `writes`.
- `git diff --check -- graphify/llm.py tests/test_llm_prompt_contract.py tests/test_semantic_cleanup.py tests/test_callflow_html.py tests/test_report.py tests/test_analyze.py` → no whitespace errors reported.

## Recommended next action

If keeping Task 6 minimal, clean up or explicitly accept the unrelated `tests/test_analyze.py` churn, and optionally add the tiny end-to-end callflow `writes` regression. After that, Task 6 is ready to pause at Checkpoint B; proceed to Task 7 only with operator approval for live A/B calls.
