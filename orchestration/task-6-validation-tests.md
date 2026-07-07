# Task 6 Validation: Test Coverage And Offline Checks

Date: 2026-07-06

Scope: current worktree diff for Task 6 in the Graphify extraction contract and
harness calibration plan. I inspected the prompt diff, the new/changed tests for
prompt text, semantic cleanup, callflow HTML, report rendering, and analyze
surprise scoring. I did not modify project/source files; this report is the only
file written.

## Summary

The Task 6 implementation appears offline-only and the targeted tests are green,
but the committed tests do not yet prove all of Task 6's downstream acceptance
criteria.

What is covered well enough:

- The native extraction prompt now contains guided-open relation guidance and a
  canonical concept naming rule.
- `semantic_cleanup` has a direct unit test showing a `writes` relation is not
  rejected or normalized away.
- I found no accidental Task 7/live-model dependency in the Task 6 test path.

Main coverage blockers before Task 6 is fully proven:

1. Callflow HTML is only tested at the `relation_label()` helper level for
   free-form relations; no committed test sends a synthetic free-form relation
   through `write_callflow_html()` and asserts it renders in generated HTML.
2. The report test covers the Ambiguous Edges section, not the Surprising
   Connections path called out by the plan near `graphify/report.py` line ~171.
3. Most downstream tests use `writes`, which is now a preferred verb, not an
   arbitrary unknown/unlisted relation. To prove relation-agnostic behavior,
   at least one downstream test should use something like `indexes`,
   `records_to`, or another source-stated verb outside the preferred list.

## Validation run

Passed:

```bash
uv run pytest \
  tests/test_llm_prompt_contract.py \
  tests/test_semantic_cleanup.py \
  tests/test_callflow_html.py \
  tests/test_report.py \
  tests/test_analyze.py \
  -q
```

Result: 92 passed, 1 existing Hypothesis collection warning.

Passed:

```bash
uv run pytest tests/test_semantic_eval.py tests/test_file_slice.py -q
```

Result: 53 passed, 1 existing Hypothesis collection warning.

Prompt readback passed:

```bash
grep -n "writes" graphify/llm.py
grep -n "Canonical concept naming" graphify/llm.py
```

Confirmed relevant lines in `graphify/llm.py` include the preferred relation set,
`another_specific_source_stated_verb`, and canonical concept naming guidance.

I also ran a temporary offline smoke probe with an arbitrary unlisted relation
`indexes`. The first raw `python` attempt failed because `python` is not on this
shell path; retrying with `uv run python` succeeded. The smoke did not modify the
repo and confirmed current implementation behavior:

- `write_callflow_html()` generated HTML containing `indexes`.
- `surprising_connections()` preserved `relation == "indexes"`.
- `report.generate()` rendered the relation in report output.

This is useful implementation evidence, but it is not committed test coverage.

## Coverage by requested proof area

### Guided-open relation prompt

Status: partially proven by committed tests; prompt text verified by readback.

Evidence:

- `graphify/llm.py` now says semantic/document relationships should prefer a
  specific lowercase source-grounded verb, lists the preferred verbs, allows
  another specific source-stated verb, and reserves `references` /
  `conceptually_related_to` for weaker cases.
- `tests/test_llm_prompt_contract.py` asserts the key guided-open phrase,
  a subset of the preferred verbs, `another_specific_source_stated_verb`, and
  absence of the old exact closed-enum substring.

Gaps:

- The test only checks the default `_extraction_system()` path, not
  `_extraction_system(deep=True)`. Deep mode currently appends the suffix, so the
  behavior is fine today, but the contract is not locked for both modes.
- The test checks only a subset of the preferred verb list. It would not fail if
  `emits`, `records`, `converts`, `governs`, `precedes`, `produces`, or
  `requires` were accidentally removed.
- The negative assertion only rejects the old exact enum substring. It would not
  catch a different closed-enum wording such as “relation must be one of ...”.

Recommended test improvement: parameterize over `deep=False/True`, assert every
required preferred verb is present, assert the fallback wording is present, and
assert there is no restrictive “must be one of” relation sentence around the edge
schema.

### Canonical concept naming

Status: minimally proven by prompt-text test.

Evidence:

- `graphify/llm.py` contains the rule to name document-level concepts with the
  document's own noun phrase and not replace documented concepts with code
  identifiers.
- `tests/test_llm_prompt_contract.py` asserts two key substrings from that rule.

Gaps:

- The test does not assert the “singular form where natural” part.
- There is no behavioral test, but that is acceptable for Task 6 because the plan
  explicitly defers prompt behavior validation to Task 7 live A/B.

Recommended test improvement: add substring assertions for headings/definitions
and singular-form guidance so the whole acceptance text is locked.

### Semantic cleanup relation-agnostic behavior

Status: covered for the required `writes` synthetic fragment.

Evidence:

- `tests/test_semantic_cleanup.py::test_validate_and_sanitize_accept_free_form_relation_verbs`
  verifies `validate_semantic_fragment()` returns no errors and
  `sanitize_semantic_fragment()` preserves an edge with `relation: "writes"`.

Gaps:

- `writes` is now a preferred verb, so this does not prove truly arbitrary
  source-stated verbs are accepted. The implementation is relation-agnostic, but
  the test would be stronger with `records_to` or `indexes`.
- This test covers `semantic_cleanup`, not the general extraction validator.
  That matches Task 6's explicit semantic-cleanup ask, so I do not consider this
  a blocker.

### Callflow handling of unknown relation strings

Status: implementation appears OK, committed coverage is insufficient.

Evidence:

- `tests/test_callflow_html.py::test_relation_label_renders_unknown_free_form_relation`
  verifies `relation_label("writes", "en") == "writes"` and underscores are
  humanized for `records_to`.
- A temporary offline smoke showed `write_callflow_html()` can render an
  unlisted `indexes` relation into generated HTML.

Coverage blocker:

- No committed test builds a graph with a free-form relation and runs it through
  `write_callflow_html()`. The Task 6 acceptance says a synthetic free-form
  relation should render in callflow HTML without error; helper-only coverage
  does not prove the end-to-end callflow path.

Recommended test improvement: add a `write_callflow_html()` fixture with only an
`indexes` or `records_to` edge, then assert the generated HTML contains the
humanized relation label.

### Report handling of unknown relation strings

Status: implementation appears OK, committed coverage targets the wrong path.

Evidence:

- `tests/test_report.py::test_report_renders_unknown_ambiguous_relation` proves
  an ambiguous edge with `relation: "writes"` appears in the Ambiguous Edges
  section as `relation: writes`.
- A temporary offline smoke showed `report.generate()` renders an unlisted
  `indexes` relation from `surprise_list`.

Coverage blocker:

- The plan called out the Surprising Connections relation rendering path near
  `graphify/report.py` line ~171. The committed test passes an empty
  `surprise_list`, so it never exercises that path.

Recommended test improvement: pass a `surprise_list` item with
`relation: "indexes"` or `relation: "records_to"` and assert the report includes
that relation in the Surprising Connections line.

### Analyze handling of unknown relation strings

Status: partially covered.

Evidence:

- `tests/test_analyze.py::test_surprise_score_accepts_specific_free_form_relation`
  calls `_surprise_score()` with `relation: "writes"` and proves it does not
  crash or get suppressed.
- A temporary offline smoke showed public `surprising_connections()` preserves an
  arbitrary unlisted `indexes` relation.

Gaps:

- The committed test exercises the private scoring helper, not the public
  `surprising_connections()` path that report generation consumes.
- The assertion is weak (`score >= 1` and `reasons` is a list). It does not
  prove the relation is preserved in emitted analysis results.
- It uses `writes`, not an arbitrary unknown/unlisted relation.

Recommended test improvement: add a public `surprising_connections()` test
with a multi-source graph and an `indexes` or `records_to` edge, then assert the
emitted result preserves that relation and does not fall back to the
structural-only path.

### No accidental Task 7/live dependencies

Status: no live dependency found in inspected Task 6 tests.

Evidence:

- `tests/test_llm_prompt_contract.py` only imports `graphify.llm` and reads the
  prompt string.
- `tests/test_semantic_cleanup.py`, `tests/test_report.py`, and
  `tests/test_analyze.py` use handcrafted in-memory fixtures.
- `tests/test_callflow_html.py` has subprocess tests, but they invoke the local
  `python -m graphify export callflow-html` path against `tmp_path` fixtures;
  they do not call model backends.
- Search of the focused Task 6 tests did not show `ollama`, `claude`, API keys,
  `run-suite`, or judge flags.

Suggested guard command:

```bash
rg -n \
  -e ollama \
  -e claude \
  -e ANTHROPIC \
  -e OPENAI \
  -e run-suite \
  -e allow-external-judge \
  -e allow-external \
  tests/test_llm_prompt_contract.py \
  tests/test_semantic_cleanup.py \
  tests/test_callflow_html.py \
  tests/test_report.py \
  tests/test_analyze.py
```

Expected result: only benign local subprocess/backend wording, no live model
commands.

## Suggested validation commands

Current Task 6 offline validation:

```bash
uv run pytest \
  tests/test_llm_prompt_contract.py \
  tests/test_semantic_cleanup.py \
  tests/test_callflow_html.py \
  tests/test_report.py \
  tests/test_analyze.py \
  -q
uv run pytest tests/test_semantic_eval.py tests/test_file_slice.py -q
grep -n "writes" graphify/llm.py
grep -n "Canonical concept naming" graphify/llm.py
```

After adding the missing downstream tests, run the focused tests explicitly:

```bash
uv run pytest \
  tests/test_llm_prompt_contract.py \
  tests/test_semantic_cleanup.py \
  tests/test_callflow_html.py \
  tests/test_report.py \
  tests/test_analyze.py \
  -q
```

Do not run Task 7 commands as part of Task 6 validation. Live A/B commands should
remain operator-approved and separate.
