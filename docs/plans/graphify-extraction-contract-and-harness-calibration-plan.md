---
title: "Graphify Extraction Contract And Harness Calibration Plan"
kind: plan
status: review
audience: "agents-operators"
canonicality: canonical
created: 2026-07-06
updated: 2026-07-06
source_of_truth: "./graphify-extraction-contract-and-harness-calibration-plan.md"
related:
  - "../../AGENTS.md"
  - "../mase-fork-operating-model.md"
  - "../semantic-model-quality-harness.md"
  - "../../ARCHITECTURE.md"
tags:
  - graphify
  - semantic-eval
  - extraction-prompt
  - local-fork
---

## Summary

The fork-local semantic quality harness currently cannot distinguish capable
models from weak ones, because two of its gate dimensions are structurally
unpassable under the current extraction prompt:

- The extraction prompt (`graphify/llm.py`, `_EXTRACTION_SYSTEM`, schema line
  near line 591) restricts every edge to a closed enum of 7 relations
  (`calls, implements, references, cites, conceptually_related_to,
  shares_data_with, semantically_similar_to`).
- The harness fixtures (`tests/fixtures/semantic_eval/*/expected.json`) expect
  source-grounded verbs (`feeds, routes, writes, stores, validates, gates,
  maps, preserves, governs, ...`) that the prompt forbids, and
  `_edge_matches()` (`graphify/semantic_eval.py:242`) requires BOTH endpoint
  match AND relation-term match, so `expected_edge_coverage` reads ~0 for any
  obedient model.
- Concept matching is exact normalized equality (`_norm`,
  `semantic_eval.py:35`): plural and CamelCase variants at 0.9–0.97 measured
  similarity count as full misses ("Stale-State Markers" vs
  "stale state marker"; "EmbeddingJob" vs "embedding job").

Empirical proof (2026-07-06 live run, artifacts in
`.semantic-evals/claude-cli-sonnet-integration-gateway-20260706/`): the
`claude-cli` backend with Sonnet — far stronger than every saved Ollama Cloud
candidate — scored overall 0.695 with `expected_edge_coverage` exactly 0.0 on
`integration_gateway`, the same band as `glm-5.2:cloud` (0.666) and
`deepseek-v4-pro:cloud` (0.655). When a top model and mid models score
identically, the ceiling is the contract, not the model.

This plan fixes both sides in a fixed order: calibrate the harness first (so
there is a trustworthy instrument and a free offline re-baseline), then change
the extraction prompt (relation vocabulary + canonical concept naming), then
run a live A/B validation through the calibrated harness.

Upstream check (2026-07-06, `upstream/v8`): the extraction prompt there is
identical (same 7-relation enum), and upstream has no structured-output,
gleaning, or harness equivalent. The harness (`graphify/semantic_eval.py`) is
fork-local. The prompt change is a fork delta and a future upstream PR
candidate; the harness changes never conflict with upstream.

## Goal

Make the semantic quality harness produce realistic, model-discriminating
scores, and remove the prompt-imposed ceiling on relation quality, so the
operator can rank candidate models on evidence.

## Success State

- Offline harness tests pass (`uv run pytest tests/test_semantic_eval.py`).
- `expected_edge_coverage` measures whether the model connected the right
  concepts (endpoint match); relation vocabulary is scored as a separate,
  visible signal, not folded into edge coverage as zeros.
- Mechanical label variants (plural, CamelCase) no longer count as concept
  misses; genuinely different concepts still never match (negative tests
  prove both directions).
- All saved `.semantic-evals/` graphs are re-scored offline (no model calls)
  into one comparison table; model ranking under the calibrated scorer is
  documented.
- The extraction prompt allows and encourages source-grounded relation verbs
  and document-canonical concept names; downstream consumers render unknown
  relation strings gracefully.
- A live A/B (same model, old-prompt saved graphs vs new-prompt fresh run)
  shows edge coverage and relation specificity materially above the old
  structural floor, with no regression in forbidden-concept/edge or source
  coverage dimensions.
- Quality-gate floors in `tests/fixtures/semantic_eval/suite.json` are
  recalibrated from re-scored evidence and the harness doc reflects the new
  semantics.
- The active `graphify` CLI is reinstalled from this checkout after tests
  pass (fork operating model requirement).

## Non-Goals

- No gleaning/second-pass extraction, no provider-native structured output
  (`response_format`/JSON schema), no role-specific model routing, no
  ensemble extraction. These are recorded follow-ups, deliberately out of
  scope to keep this change measurable.
- No semantic-cache versioning machinery. The semantic cache is deliberately
  unversioned (`graphify/cache.py` design comment); this plan only documents
  the operator consequence of a prompt change.
- No loosening of the fail-closed alias policy for genuine synonyms in
  expected contracts. Only mechanical variant folding moves into the scorer.
- No dedup pipeline changes (`graphify/dedup.py` already scores 0.88–1.0).
- No upstream PR in this cycle; the prompt delta is documented for a later
  candidate PR.
- No changes to the node-ID format or hyperedge rules in the prompt.

## Preconditions

- If there is in-flight slicing/timeout work (adaptive retry in
  `graphify/llm.py`, stale-flag cleanup in `graphify/__main__.py`, tests in
  `tests/test_file_slice.py`), commit it separately first (prefer
  `my-git-smart-commit`) so this plan's diffs stay isolated and revertible.
  Do not mix the two changesets in one commit.
- Live runs (Task 7 only) call external backends and send committed,
  public-safe fixture text; they remain operator-approved per the harness
  privacy policy. All other tasks are offline.

## Responsibility Boundaries

- `graphify/semantic_eval.py` owns matching/scoring semantics and is
  fork-local. Tasks 2–4 change only this module plus its tests/fixtures.
- `graphify/llm.py` owns the extraction prompt contract (`_EXTRACTION_SYSTEM`)
  and is shared with upstream; Task 6 is the only task that touches it.
- `tests/fixtures/semantic_eval/` owns expected contracts and the quality
  gate (`suite.json`).
- `graphify/callflow_html.py`, `graphify/analyze.py`, `graphify/report.py`
  are read-only consumers of relation values in this plan: verify graceful
  handling of unknown relations, add a fallback only if one is missing.
- `docs/semantic-model-quality-harness.md` is the operator guide that must
  stay in sync (Tasks 5, 8).

## Architecture Decisions

1. **Harness before prompt.** Saved graphs re-scored offline become the
   old-prompt A/B arm for free; changing both sides at once would make the
   A/B unreadable.
2. **Split edge scoring.** `expected_edge_coverage` becomes endpoint-based;
   a new `expected_edge_relation_agreement` dimension reports, among
   endpoint-matched expected edges, the fraction whose relation matches
   `relation_terms`. Rationale: "connected the right things" and "used a
   specific verb" are different failure modes; today the second zeroes the
   first, and relation vagueness is already measured by
   `relation_specificity`.
3. **Report-only first.** `expected_edge_relation_agreement` is reported and
   recorded but stays out of the weighted overall and out of
   `critical_dimensions` for this cycle; promotion is a later, evidence-based
   gate change.
4. **Conservative mechanical folding only.** The scorer folds CamelCase and
   trailing-plural variants; it must prefer missing a plural over a false
   match. Semantic equivalence stays in explicit fixture aliases
   (fail-closed).
5. **Guided-open relation vocabulary.** The prompt names a preferred verb set
   and allows other specific lowercase verbs; generic relations remain legal
   but explicitly discouraged. No hard normalization map yet — relation
   sprawl is monitored in Task 7 and a mapping layer is added later only if
   sprawl demonstrably harms downstream views.
6. **Scorer version stamp.** Score payloads gain a `scorer_version` field so
   old and new artifacts are never silently compared.

## Task List

### Task 1: Isolate in-flight worktree changes

Commit the existing uncommitted slicing/timeout work as its own commit(s) on
`mase/local-fixes` before any plan work starts.

Acceptance criteria:
- `git status --short` is clean before Task 2 begins.
- The slicing/timeout commit passes its own tests.

Verify:
- `uv run pytest tests/test_file_slice.py -q`
- `git status --short`

### Task 2: Scorer normalization — mechanical variant folding (tests first)

In `graphify/semantic_eval.py`:

- Extend normalization so that, before lowercasing, CamelCase boundaries are
  split (`EmbeddingJob` → `embedding job`); `_WORD_RE` already splits hyphens
  and punctuation.
- Add conservative token-level plural folding at comparison time: fold a
  trailing `s` when the token has length > 3 and does not end in `ss`
  (`markers` → `marker`; `address` unchanged). Apply symmetrically to
  expected and candidate norms everywhere `_norm` output is compared
  (`_matching_nodes`, `_concept_norms`/`_node_norms`, dedup-watchlist
  matching, near-match diagnostics).
- Keep raw `_norm` for display in diagnostics so operators still see actual
  labels.

Tests first, in `tests/test_semantic_eval.py` (offline, handcrafted graphs):
- positive: plural fold, CamelCase fold, combined ("Stale-State Markers"
  matches "stale state marker"; "EmbeddingJob" matches "embedding job").
- negative (near-miss must NOT match): "retry limit" vs "retry policy";
  "address" vs "addresses" may miss but "address" vs "addres" must not
  match; "GatewayService" vs "integration gateway" stays a miss.
- existing handcrafted-fixture score expectations updated deliberately, with
  the delta explained in the test diff.

Acceptance criteria:
- All new tests pass; no live model calls anywhere in the test path.
- Near-match diagnostics still list the raw labels and similarities.

Verify:
- `uv run pytest tests/test_semantic_eval.py -q`

### Task 3: Split expected-edge scoring; stamp scorer version

In `graphify/semantic_eval.py`:

- `expected_edge_coverage`: an expected edge counts as covered when its
  endpoints match (`_edge_endpoint_matches` semantics, honoring `directed`).
- New `expected_edge_relation_agreement`: over endpoint-covered expected
  edges that define `relation_terms`, the fraction where
  `_edge_relation_matches` also passes. `None` when no expected edge with
  relation terms is endpoint-covered.
- Missing-edge diagnostics now record the reason split: `endpoint_miss`
  (which endpoint) vs `relation_mismatch` (endpoints matched, relation did
  not — include the actual relation found).
- Add `scorer_version` (e.g. `2`) to every score payload (`score`, `run`,
  `run-suite`, `compare` outputs); `compare` warns when versions differ.
- Weighted overall: `expected_edge_coverage` keeps its current weight;
  `expected_edge_relation_agreement` is excluded from overall this cycle
  (Decision 3).

Tests (offline): endpoint-only edge scores as covered with relation recorded
as mismatch; fully matched edge scores in both dimensions; undirected edges;
version stamp present; compare-version warning.

Acceptance criteria:
- A handcrafted graph with correct endpoints but generic relations scores
  `expected_edge_coverage` > 0 and low `expected_edge_relation_agreement`,
  with `relation_mismatch` diagnostics naming the found relation.

Verify:
- `uv run pytest tests/test_semantic_eval.py -q`

### Task 4: Offline re-baseline of all saved artifacts

No model calls. For every saved run under `.semantic-evals/` that contains
`corpus/graphify-out/graph.json`, re-score with the calibrated scorer:

- graph: `<run>/<fixture>/corpus/graphify-out/graph.json`
- labels: `<run>/<fixture>/corpus/graphify-out/.graphify_labels.json`
- expected: `tests/fixtures/semantic_eval/<fixture>/expected.json`

Layout facts (verified 2026-07-06, so no discovery needed):

- Suite runs have one subdirectory per fixture; single-fixture runs (e.g.
  the Sonnet baseline) have `corpus/` directly under the run dir, with the
  fixture name recoverable from the run dir name or `run.json`.
- Use only the top-level `corpus/graphify-out/graph.json`. Each
  `graphify-out/` also contains a dated snapshot subdirectory (e.g.
  `graphify-out/2026-07-06/graph.json`) — exclude these or every graph is
  double-counted.
- `.graphify_labels.json` is confirmed present in all runs listed below.
- Per-fixture, per-dimension reporting is sufficient for the decision;
  recomputing weighted suite aggregates (fixture weights live in
  `suite.json`) is optional, not required.

Include at minimum: `glm-5.2-cloud-suite-amended-20260629-151816`,
`deepseek-v4-pro-cloud-suite-20260701-compare`,
`minimax-m3-cloud-suite-20260614-112409`,
`model-quality-comparison-20260614-191220/*`, and
`claude-cli-sonnet-integration-gateway-20260706`.

Implementation preference: a documented shell/python loop over the existing
`score` subcommand; add a `rescore` subcommand only if the loop proves
awkward (open question 2).

Output: one comparison table (Markdown + JSON) under
`.semantic-evals/comparisons/scorer-v2-rebaseline/` with per-model,
per-fixture, per-dimension scores, old vs new scorer side by side.

Acceptance criteria:
- Every listed run re-scored; table shows whether models now separate on
  `expected_edge_coverage` and `concept_recall` (either outcome is a valid
  finding and must be stated).

Verify:
- deterministic re-run of the loop produces identical JSON
- spot-check: Sonnet `integration_gateway` re-score shows
  `expected_edge_coverage` > 0 (its `EmbeddingJob → VectorIndex` edge has
  matching endpoints).

### Task 5: Recalibrate quality gate and harness doc (part 1)

- Set `minimum_overall` and `minimum_critical_dimension` in
  `tests/fixtures/semantic_eval/suite.json` from the Task 4 distribution:
  floors should be failable-but-reachable (e.g. near the best observed
  candidate's level on critical dimensions), and the chosen numbers must be
  justified in the doc from the re-baseline table, not aspiration.
- Update `docs/semantic-model-quality-harness.md`: new dimension list,
  endpoint/relation split semantics, scorer_version note, re-baseline table
  location, and mark the old "Current Candidate Baselines" table as
  superseded (old aggregates are scorer-v1 numbers).

Acceptance criteria:
- `run-suite` gate logic honors the new floors; offline tests covering gate
  pass/fail behavior updated.

Verify:
- `uv run pytest tests/test_semantic_eval.py -q`
- readback of the doc section against `suite.json` values

### Task 6: Extraction prompt contract change

In `graphify/llm.py` `_EXTRACTION_SYSTEM` only (deep-mode suffix, node-ID
format, edge-direction rules, hyperedge rules, security block unchanged):

- **Relation vocabulary**: replace the closed enum in the schema line with
  guided-open guidance. Keep the structural code relations (`calls`,
  `implements`, `imports`, `references`, `cites`) and instruct: prefer a
  specific lowercase verb grounded in the source text — name a preferred set
  (`writes`, `stores`, `routes`, `validates`, `gates`, `feeds`, `emits`,
  `records`, `converts`, `governs`, `precedes`, `produces`, `requires`) and
  allow "another specific verb the source states"; use `references` /
  `conceptually_related_to` only when the source states nothing more
  specific.
- **Canonical concept naming**: add a rule — name document-level concepts
  with the document's own noun phrase (headings, defined terms), singular
  form; never substitute a code identifier for a documented concept name
  (the code entity keeps its identifier and links to the concept).
- **Downstream check**: verify unknown relation strings render gracefully in
  `graphify/callflow_html.py` (relation display maps and `secondary` set
  near lines 536–559), `graphify/analyze.py` (relation checks near lines
  220–252), and `graphify/report.py` (line ~171). Add a neutral fallback
  only where an unknown relation would crash or disappear; do not redesign
  these modules.
- Confirm `validate_semantic_fragment` / `sanitize_semantic_fragment`
  (`graphify/semantic_cleanup.py`) are relation-agnostic (they are today —
  assert with a test, not a comment).

Testing posture: unit tests for any downstream fallback added; prompt-text
change itself is validated end-to-end in Task 7.

Acceptance criteria:
- Prompt contains the guided-open vocabulary and canonical-naming rules.
- A synthetic fragment with a free-form relation (`writes`) passes
  validation/sanitization and renders in callflow HTML without error.

Verify:
- `uv run pytest tests/test_semantic_eval.py tests/test_file_slice.py -q`
  plus the nearest existing test files for callflow/report if present
- `grep -n "writes" graphify/llm.py` readback of the schema line

### Task 7: Live A/B validation (operator-approved; E2E gate)

Old-prompt arm: the Task 4 re-scored saved suite runs (no new calls).
New-prompt arm, per the harness doc command patterns:

- `run-suite` with `deepseek-v4-pro:cloud` (backend `ollama`) — the fastest
  saved full-suite candidate.
- `run-suite` with `glm-5.2:cloud` (backend `ollama`) — the best saved
  candidate.
- one fixture (`integration_gateway`) with `claude-cli` (Sonnet) as the
  strong-model reference, mirroring the 2026-07-06 baseline run.

Operational gotcha (hit live on 2026-07-06): when the implementer itself runs
inside a Claude Code / agent session, the inherited environment breaks the
spawned `claude` CLI. Unset `ANTHROPIC_BASE_URL`, `CLAUDECODE`, and
`CLAUDE_CODE_ENTRYPOINT` in the environment of any `claude-cli`-backend
command (probe first: `claude -p "Reply with exactly: OK" --model haiku`).
Set the Sonnet model via `GRAPHIFY_CLAUDE_CLI_MODEL=sonnet` — the claude-cli
backend reads the model from that env var, not from `--model`.

Then `semantic_eval compare` old vs new arm per model, plus a relation
histogram of the new-arm graphs (sprawl check, Decision 5). Repeat volatile
or close-call fixtures 3x per the harness doc protocol before reading
deltas. Optional: one pointwise judge pass (`--allow-external-judge`) if the
deterministic deltas are ambiguous.

Acceptance criteria:
- New-prompt arm completes without extraction/parse/cluster failures.
- `expected_edge_coverage` and `relation_specificity` improve materially vs
  the re-scored old arm for at least the strong reference model; target for
  the reference model on doc-to-code fixtures: edge coverage ≥ 0.4.
- No regression in `forbidden_concepts_absent`, `forbidden_edges_absent`,
  `source_coverage`; `deduplication` stays ≥ 0.85.
- Relation histogram shows a bounded vocabulary (rough guide: ≤ ~25 distinct
  relations across the suite), else record sprawl as a follow-up finding.

Verify:
- `suite-run.json` gate state per arm; `compare` JSON/Markdown outputs saved
  under `.semantic-evals/comparisons/prompt-v2-ab/`

### Task 8: Closeout — docs, baselines, CLI reinstall

- Update `docs/semantic-model-quality-harness.md` baselines table with the
  new-arm artifacts (model, backend, artifact path, overall, gate state).
- Record a dated decision note (comparison summary + which models look
  capable under the calibrated harness) per the harness doc's comparison
  protocol.
- Note the cache consequence in the harness doc and fork operating model
  doc: the semantic cache is content-keyed, so existing project graphs keep
  old-vocabulary edges until files change or the operator forces a semantic
  refresh; recommend a one-time forced refresh only for repos where relation
  quality matters.
- Reinstall the active CLI from this checkout after all tests pass.
- Mark this plan `status: complete` (or record deviations).

Verify:
- `uv run pytest tests/ -q` (nearest broader suite; record runtime)
- `graphify --version` resolves to the checkout install
- readback of updated docs

## Checkpoints

### Checkpoint A: Instrument calibrated (after Tasks 1–5)

Offline tests green; re-baseline table exists; gate floors justified from
data. No prompt changes yet. Safe pause point.

### Checkpoint B: Contract updated (after Task 6)

Prompt delta merged on `mase/local-fixes`; downstream consumers verified;
still no live spend. Safe pause point.

### Checkpoint C: Evidence in hand (after Tasks 7–8)

A/B artifacts saved and compared; gate recalibrated; docs and baselines
updated; CLI reinstalled. Model-selection decisions are now evidence-based.

## Risks And Mitigations

- **Historical score incompatibility.** All prior aggregates become
  scorer-v1 numbers. Mitigation: `scorer_version` stamp, compare-version
  warning, superseded marker in the doc, full offline re-baseline (Task 4).
- **Folding false positives.** Plural/CamelCase folding could merge distinct
  concepts. Mitigation: conservative rules (Decision 4) plus mandatory
  negative tests (Task 2); any observed false positive is a blocker, not a
  tweak.
- **Relation sprawl.** Free-form verbs may fragment the relation vocabulary.
  Mitigation: preferred-verb list in the prompt, histogram check in Task 7,
  explicit deferred option of a normalization map.
- **Downstream rendering of unknown relations.** Callflow/report views may
  hide or mis-render new verbs. Mitigation: Task 6 verification with a
  synthetic free-form-relation fragment before any live run.
- **Stale semantic caches in real repos.** Prompt changes do not invalidate
  the content-keyed semantic cache; mixed-vocabulary graphs persist.
  Mitigation: documented operator guidance (Task 8); no cache machinery.
- **Live-run cost/availability.** Ollama Cloud models 503 intermittently
  (DeepSeek Flash history). Mitigation: models chosen from saved-working
  candidates; single-fixture smoke before full suite per harness doc.
- **Entanglement with in-flight worktree changes.** Mitigation: Task 1
  commits them first; plan diffs stay separable.

## Open Questions

1. Exact gate floor values — decided in Task 5 from Task 4 data, not now.
2. Shell loop vs `rescore` subcommand for Task 4 — implementer's call;
   prefer the loop unless label/path resolution gets messy.
3. Whether `expected_edge_relation_agreement` later joins the weighted
   overall and/or `critical_dimensions` — revisit after one full A/B cycle.
4. Upstream PR for the prompt delta — decide after Task 7 evidence exists.

## Recommended Next Action

Run Task 1 (commit the in-flight slicing/timeout work), then start Task 2
with the tests-first scorer changes. Tasks 1–5 are offline and free; pause at
Checkpoint A for operator review before the prompt change and any live spend.
