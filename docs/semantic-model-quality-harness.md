---
title: "Semantic Model Quality Harness"
kind: reference
status: active
audience: agents-maintainers-operators
canonicality: canonical
created: 2026-06-02
updated: 2026-08-05
last_verified: 2026-08-05
source_of_truth: "./semantic-model-quality-harness.md"
related:
  - "./luna-cli-semantic-evaluation-2026-07-31.md"
  - "./mase-fork-operating-model.md"
  - "../tasks/todo.md"
---

## Purpose

Use this harness for deterministic regression diagnostics on Graphify semantic
extraction. It records operational completion and useful quality dimensions, but
the current scorer and gates are **not authoritative** for choosing prompts,
models, image behavior, or production defaults.

## Current Disposition And Next Step

The 2026-08-05 audit found material decision-validity gaps:

- relationship meaning and hyperedges do not decisively affect promotion gates;
- the diagram gold prefers one representation instead of accepting equivalent
  branch nodes, edge qualifiers, or hyperedges;
- community-label and provenance checks can pass without grounded per-community
  labels or claim-level evidence;
- closed forbidden lists do not measure general hallucination precision;
- aggregate weights can hide a severe privacy, relationship, or fixture-slice
  regression; and
- one public diagram and single stochastic runs do not establish repeatability.

Current operating decisions:

- Keep `deepseek-v4-pro:cloud` as the automatic Ollama text default.
- Keep Pi explicit, uninstalled from the current source commit, and unpromoted.
- Treat Pi image output as requiring explicit upload consent and human review.
- Do not adopt either the current or pinned-upstream image prompt from the one
  blind comparison.
- `deepseek-v4-flash:0731-cloud` remains an explicit candidate only. A bounded
  blind comparison found broader architecture recovery but weaker privacy
  constraints, more noise, and 2.76 times the elapsed runtime; it is not the
  default.

The next project iteration is **plan-only evaluation-harness redesign**. The
plan must separate operational safety, semantic fidelity, and promotion
readiness; add representation-aware relationship and hyperedge scoring,
claim-level provenance, general hallucination precision, held-out fixtures,
paired repeats, and blinded qualitative review. This status grants no
implementation, prompt edit, provider-call, default-change, install, or
promotion authority.

All scorer-v1/v2/v3 numbers below remain historical or diagnostic evidence.
They must not be presented as proof of prompt or model superiority.

## Privacy And Fixture Policy

The recurring suite uses layered fixtures:

- synthetic diagnostic fixtures for controlled aliases, edges, and forbidden
  hallucinations
- public-realistic fixtures derived from committed Graphify docs/code shapes
- multimodal fixtures for image/diagram extraction
- optional private shadow evaluations kept outside git and run only with
  explicit approval

Local private repos may inspire fixture shapes, but do not copy private repo
prose, email content, customer data, operator notes, secrets, or exact
project-specific plans into committed fixtures.

Live `run` and `run-suite` calls send fixture text and images to the selected
backend. With Ollama Cloud models such as `deepseek-v4-pro:cloud` or
`glm-5.2:cloud`, that means the fixture corpus leaves the machine through
the local Ollama endpoint. Keep CI and normal tests offline by scoring
handcrafted graph fixtures instead of calling live models.

## Current Suite

Suite manifest:

```text
tests/fixtures/semantic_eval/suite.json
```

Initial fixture profiles:

| Fixture | Purpose |
|---|---|
| `payment_retry` | Synthetic workflow/runbook baseline retained from the first smoke harness. |
| `router_privacy` | Synthetic privacy-sensitive routing workflow with hallucination/forbidden-behavior checks. |
| `workflow_migration` | Synthetic multi-document agent workflow/migration semantics with alias handling. |
| `integration_gateway` | Synthetic small code/docs integration shape that tests doc-to-code relationships. |
| `graphify_public_slice` | Public-realistic slice derived from Graphify architecture/backend concepts. |
| `diagram_workflow` | Multimodal PNG workflow diagram that tests visual node/edge extraction. |

The active manifest is suite version 3. Scorer/fixture corrections and the
current Luna-versus-DeepSeek evidence are recorded in:

```text
docs/luna-cli-semantic-evaluation-2026-07-31.md
```

## Run One Fixture

Example with Ollama Cloud:

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run \
  --corpus tests/fixtures/semantic_eval/payment_retry \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out-dir .semantic-evals/deepseek-v4-pro-cloud-payment-retry \
  --backend ollama \
  --model deepseek-v4-pro:cloud \
  --timeout 300 \
  --token-budget 1200
```

The harness writes:

- `run.json`: raw command outputs and structured scores
- `EVALUATION.md`: human-readable score summary
- `corpus/graphify-out/`: Graphify artifacts from that run

## Run The Recurring Suite

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/deepseek-v4-pro-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model deepseek-v4-pro:cloud \
  --timeout 300 \
  --token-budget 1200
```

To compare a candidate:

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/glm-5.2-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model glm-5.2:cloud \
  --timeout 300 \
  --token-budget 1200
```

For image/diagram quality with Ollama models, select a vision-capable model and
set `GRAPHIFY_OLLAMA_VISION=1`; otherwise Graphify lists image paths but does
not attach pixels to the Ollama request. Record this setting in the run notes.

`run-suite` writes:

- one per-fixture subdirectory with `run.json`, `EVALUATION.md`, and copied
  `corpus/graphify-out/`
- `suite-run.json`: aggregate scores, profile scores, quality-gate state,
  timings, token counts, fixture scores, suite/contract/corpus/prompt hashes,
  non-secret operational settings, sanitized endpoint fingerprint, and Git
  state evidence
- `SUMMARY.md`: operator-readable aggregate summary

## Scorer v3 Diagnostic Contract

Scorer v3 is the current deterministic implementation, not a decision-grade
promotion instrument. It stamps score, run, run-suite, compare, and re-baseline
payloads with `scorer_version: 3` and adds two fail-closed corrections:

- expected-edge endpoints inherit aliases from exactly one matching required
  concept; ambiguous shared aliases do not expand
- forbidden positive-edge checks preserve relation polarity, so
  `must_not_store`, `cannot_store`, and `avoids_logging` do not match positive
  `stores` or `logs` requirements

Suite contract v3 also stops classifying source-grounded prohibited targets as
hallucinated concepts. Such targets are required concepts with explicit negative
expected edges and separate forbidden positive edges. Fixture endpoint and
alias contracts were corrected only where source inspection proved the old
expectation wrong or incomplete.

The final 2026-07-31 prompt-v3 runs have matching suite-contract, corpus, and
prompt hashes. Luna `high` scored 0.831 overall and 0.912 text-only versus
DeepSeek V4 Pro at 0.734 overall and 0.790 text-only. Luna won all five text
fixtures, while DeepSeek retained materially higher relation agreement. Both
runs failed the multimodal profile gate, and DeepSeek also fell below the
aggregate edge-coverage floor. The recorded Pi/Luna probe returned no visual
labels because image delivery was blocked; a later explicitly enabled native
probe proved pixel delivery and model vision capability. Subsequent Graphify
image runs remained semantically mixed, so this is capability evidence rather
than promotion evidence. The comparison covers deployable configurations—Luna
`high` through Pi/OAuth and DeepSeek reasoning-disabled through Ollama—not
isolated model weights.

## Historical Scorer v2 Calibration

Scorer v2 stamped every score, run, run-suite, and compare payload with
`scorer_version: 2`. Historical artifacts without this field are scorer-v1
numbers and should not be compared silently; the `compare` command emits a
warning when scorer versions differ.

The v2 changes are intentionally scorer-only:

- concept matching folds mechanical variants: CamelCase boundaries and simple
  trailing plurals such as `markers` -> `marker`; semantic synonyms still
  require explicit fixture aliases
- `expected_edge_coverage` now measures whether the expected concepts are
  connected by an edge, honoring `directed`
- `expected_edge_relation_agreement` separately reports whether endpoint-matched
  expected edges used one of the expected relation terms
- `expected_edge_relation_agreement` is report-only for this cycle: it is not
  part of weighted `overall` and is not a quality-gate critical dimension

The offline re-baseline for saved graph-bearing artifacts is at:

```text
.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.md
.semantic-evals/comparisons/scorer-v2-rebaseline/rebaseline.json
```

No model calls were made for that re-baseline. It processed 45 saved graphs
across 15 graph-bearing run directories and skipped the empty
`model-quality-comparison-20260614-191220/gemma4_12b` artifact directory.
Dated snapshot copies under each `graphify-out/` were excluded by using only
`**/corpus/graphify-out/graph.json`.

The full-suite v2 aggregates show model separation but still expose the old
prompt ceiling on relation terms:

| Run | New overall | Concept recall | Edge coverage | Relation agreement | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `glm-5.2-cloud-suite-amended-20260629-151816` | 0.745 | 0.689 | 0.491 | 0.118 | pass |
| `glm-5.2-cloud-suite-20260629-120625` | 0.737 | 0.714 | 0.451 | 0.132 | pass |
| `deepseek-v4-pro-cloud-suite-20260701-compare` | 0.710 | 0.612 | 0.335 | 0.117 | fail |
| `minimax-m3-cloud-suite-20260614-112409` | 0.697 | 0.693 | 0.497 | 0.220 | fail |
| `model-quality-comparison-20260614-191220/kimi-k2.7-code_cloud` | 0.697 | 0.749 | 0.448 | 0.048 | fail |
| `model-quality-comparison-20260614-191220/qwen3.5_397b-cloud` | 0.695 | 0.560 | 0.442 | 0.210 | fail |

The calibrated quality gate in `tests/fixtures/semantic_eval/suite.json` is:

- `minimum_overall`: `0.70`
- `minimum_critical_dimension`: `0.45`

Rationale: the best observed full-suite v2 run reaches 0.745 overall; keeping
0.70 makes the gate failable but reachable by the current top candidates. The
critical floor is set at 0.45 because the strongest full-suite edge-coverage
runs cluster at 0.451-0.497 while concept recall and safety/source dimensions
are higher. This avoids the old aspirational 0.80 critical floor that no saved
candidate could reach after the scorer contract changed.

## Prompt V3 Luna Candidate Decision

The dated investigation is the decision source for the current candidate:

```text
docs/luna-cli-semantic-evaluation-2026-07-31.md
```

Historical decision at that checkpoint: Luna `high` merited planning a
first-class Pi CLI text backend. That explicit print-only backend is now
implemented and transport-validated in source, but the later evaluator audit and
image/prompt experiments did not justify promotion. DeepSeek V4 Pro through
Ollama therefore remains automatic; Pi remains explicit and uninstalled from
this source closeout.

## Historical Prompt V2 Default Decision

The 2026-07-07 prompt-v2 A/B artifacts selected the still-active production
default before the prompt-v3 Luna investigation. They are retained at:

```text
.semantic-evals/comparisons/prompt-v2-ab/TASK_7_SUMMARY.md
.semantic-evals/comparisons/prompt-v2-ab/task-7-summary.json
```

Decision: use `deepseek-v4-pro:cloud` as Mase's built-in Ollama default for
Graphify semantic extraction for this cycle. It is the cleanest full-suite
prompt-v2 candidate: the run completed without extraction failures, passed the
calibrated gate, improved endpoint edge coverage and relation quality, and did
not regress forbidden-concept, forbidden-edge, or source-coverage dimensions.

| Model | Artifact | Overall | Edge coverage | Relation agreement | Gate | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `deepseek-v4-pro:cloud` | `.semantic-evals/prompt-v2-ab-deepseek-v4-pro-cloud-suite-20260707-100708/suite-run.json` | 0.771 | 0.539 | 0.603 | pass | default/reference |
| `glm-5.2:cloud` | `.semantic-evals/prompt-v2-ab-glm-5.2-cloud-suite-20260707-100946/suite-run.json` | 0.753 | 0.537 | 0.337 | pass | fallback; privacy caution |
| `deepseek-v4-flash:cloud` | `.semantic-evals/prompt-v2-ab-deepseek-v4-flash-cloud-suite-20260707-121043/suite-run.json` | 0.738 | 0.402 | 0.900 | fail | available; not default |
| `claude-cli` Sonnet `integration_gateway` | `.semantic-evals/prompt-v2-ab-claude-cli-sonnet-integration-gateway-20260707-101715/run.json` | 0.898 | 0.800 | 1.000 | pass | strong-reference smoke |

Cautions and follow-ups:

- `deepseek-v4-pro:cloud` is an Ollama extra-high usage model; it is selected
  here for quality despite cost. Use explicit `--model` or `OLLAMA_MODEL` to
  choose cheaper candidates for bounded experiments.
- `glm-5.2:cloud` is close on aggregate quality but repeatedly extracted the
  forbidden `Raw Mailbox Exports` concept in `router_privacy`, so it is not the
  clean default for privacy-sensitive corpora.
- `deepseek-v4-flash:cloud` is available and completed the suite, but failed the
  calibrated gate on `expected_edge_coverage`.
- Relation vocabulary remains somewhat sprawly; record this as a follow-up
  rather than changing scorer logic or gate floors in this cycle.

## Current Candidate Baselines

These are scorer-v1 historical baselines and are superseded for model-gate
decisions by the scorer-v2 re-baseline above. They remain useful only as a
record of the saved local artifacts that anchored earlier model comparisons.
`.semantic-evals/` is intentionally ignored, so rerun or copy the needed
artifacts before making a durable policy change.

| Model | Backend | Local artifact | Overall | Gate | Notes |
|---|---|---|---:|---|---|
| `kimi-k2.7-code:cloud` | Ollama Cloud | `.semantic-evals/model-quality-comparison-20260614-191220/kimi-k2.7-code_cloud/suite-run.json` | 0.632 | fail | Former comparison point, not a passing baseline. |
| `qwen3.5:397b-cloud` | Ollama Cloud | `.semantic-evals/model-quality-comparison-20260614-191220/qwen3.5_397b-cloud/suite-run.json` | 0.648 | fail | Slightly higher than Kimi in the saved run, still below gate. |
| `minimax-m3:cloud` | Ollama Cloud | `.semantic-evals/minimax-m3-cloud-suite-20260614-112409/suite-run.json` | 0.630 | fail | Retained because it was the previous comparison baseline. |
| `glm-5.2:cloud` | Ollama Cloud | `.semantic-evals/glm-5.2-cloud-suite-amended-20260629-151816/suite-run.json` | 0.679 | fail | Best saved overall after amendment, but still has critical regressions. |
| `deepseek-v4-flash:cloud` | Ollama Cloud | `.semantic-evals/deepseek-v4-flash-cloud-suite-20260701-133000/suite-run.json` | none | fail | Access works for simple/probe calls, but the full suite failed every fixture with Ollama OpenAI-compatible `APIConnectionError`; this is a transport/extraction failure, not a quality score. |
| `deepseek-v4-pro:cloud` | Ollama Cloud | `.semantic-evals/deepseek-v4-pro-cloud-suite-20260701-compare/suite-run.json` | 0.655 | fail | Completed the full suite through Ollama; above Kimi/Qwen/MiniMax overall, below GLM, and still fails on concept recall and expected-edge coverage. |
| DeepSeek direct API candidate | DeepSeek API | not run | none | not evaluated | Recommended next diagnostic path if `DEEPSEEK_API_KEY` is available, to separate model quality from Ollama Cloud proxy behavior. |

As of 2026-07-01, every scored saved candidate in this historical table failed
the suite quality gate. Do not promote any of these scorer-v1-era artifacts as
the clean default from aggregate score alone; use the prompt-v2 decision section
above for the current default. The DeepSeek row above is normalized with current
fail-closed gate semantics; the original ignored local artifact was generated
before fixture failures were counted as gate failures and may still show
`gate_passed: true` in its JSON.
Follow-up probes on 2026-07-01 showed `deepseek-v4-flash:cloud` returning
Ollama Cloud HTTP 503 overloads through both `/v1/chat/completions` and native
`/api/chat`, while `deepseek-v4-pro:cloud` returned a simple response through
both routes. That established Ollama as a viable DeepSeek transport. A later
2026-07-07 prompt-v2 Flash run completed, but failed the calibrated gate on
`expected_edge_coverage`; see the prompt-v2 decision section above.

The 2026-07-01 V4 Pro suite confirms the DeepSeek Ollama path is operational
for the recurring harness: all fixtures completed in 132.02s with 6,428 input /
16,304 output tokens. It is fast and low-output compared with the saved
baselines, but it still does not clear the model-selection gate.

Graphify's Ollama request shape should stay aligned with Ollama's documented
OpenAI-compatible chat fields: use `max_tokens` for output budget and
`reasoning_effort` for thinking control. The local fork defaults DeepSeek V4
Ollama models to `reasoning_effort=none` for semantic extraction so the model
does not wrap JSON in thinking text; set `GRAPHIFY_OLLAMA_REASONING_EFFORT` to
`low`, `medium`, `high`, or `max` only for an explicit quality experiment.

Historical DeepSeek Flash diagnostic command:

```bash
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 GRAPHIFY_OLLAMA_REASONING_EFFORT=none uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/deepseek-v4-flash-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model deepseek-v4-flash:cloud \
  --timeout 900 \
  --token-budget 60000
```

If Flash returns transport errors again, run a single-fixture Pro smoke through
the same Ollama path before judging the backend. Pro working while Flash fails
means the issue is Ollama Cloud model availability, not Graphify's Ollama
transport.

```bash
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 GRAPHIFY_OLLAMA_REASONING_EFFORT=none uv run python -m graphify.semantic_eval run \
  --corpus tests/fixtures/semantic_eval/payment_retry \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out-dir .semantic-evals/deepseek-v4-pro-cloud-payment-retry-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model deepseek-v4-pro:cloud \
  --timeout 900 \
  --token-budget 60000
```

The 2026-07-01 Pro smoke completed the `payment_retry` fixture through Ollama in
about 19s total command time, producing 10 nodes, 13 edges, and an overall score
of 0.81. Treat that as transport evidence only; it is not a suite-level model
selection result.

If that path still fails before scoring, test the same fixture through a direct
DeepSeek backend before judging the model itself. If the direct path succeeds,
the fix belongs in the Ollama/OpenAI-compatible request handling or timeout
path; if it also fails, inspect model output shape, reasoning content, and JSON
repair behavior before adding ensemble complexity.

Direct DeepSeek diagnostic command, when `DEEPSEEK_API_KEY` is available. If the
account exposes a different model id, set `GRAPHIFY_DEEPSEEK_MODEL` or change
`--model` explicitly.

```bash
GRAPHIFY_LLM_TRACE=1 uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/deepseek-v4-flash-direct-suite-$(date +%Y%m%d-%H%M%S) \
  --backend deepseek \
  --model deepseek-v4-flash \
  --timeout 900 \
  --token-budget 60000
```

## Compare Two Saved Suite Runs

After running baseline and candidate suites, compare the saved artifacts without
calling any model:

```bash
uv run python -m graphify.semantic_eval compare \
  --baseline .semantic-evals/deepseek-v4-pro-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --candidate .semantic-evals/glm-5.2-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out .semantic-evals/comparisons/deepseek-v4-pro-vs-glm-5.2.json
```

This writes JSON plus a sibling Markdown comparison with aggregate deltas,
fixture-level deltas, and regressions.

## Add Strong LLM Judges

Deterministic scoring is a reproducible diagnostic layer, not a hard semantic or
promotion authority. Strong judge models can provide additional opt-in evidence,
but their verdicts also require source inspection and blinded human synthesis.
After the redesign, serious default-model decisions should use paired repeats,
held-out fixtures, and independent judge families when practical—for example a
GPT-family judge and a Claude/Opus-family judge.

Pointwise judge for one suite run, using subscription-authenticated local agent
CLIs instead of raw API keys:

```bash
uv run python -m graphify.semantic_eval judge-suite \
  --suite-run .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out-dir .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/judge \
  --judge pi:openai-codex/gpt-5.5:high \
  --judge claude-cli:opus \
  --allow-external-judge
```

The `pi` judge backend shells out to a minimal, no-session Pi process and can
use Pi's configured `openai-codex` ChatGPT-subscription provider. The
`claude-cli` judge backend shells out to `claude -p` and can use Claude Code's
Claude.ai Pro/Max subscription auth. These are programmatic agent CLI calls, not
raw OpenAI/Anthropic SDK calls.

API-key-backed judge specs are still supported when the relevant environment
keys are set, for example:

```bash
uv run python -m graphify.semantic_eval judge-suite \
  --suite-run .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out-dir .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/judge-api \
  --judge openai:gpt-5.1 \
  --judge claude:claude-opus-4-5 \
  --allow-external-judge
```

Pairwise judge for baseline versus candidate:

```bash
uv run python -m graphify.semantic_eval judge-compare \
  --baseline .semantic-evals/deepseek-v4-pro-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --candidate .semantic-evals/glm-5.2-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out-dir .semantic-evals/comparisons/deepseek-v4-pro-vs-glm-5.2-judges \
  --judge pi:openai-codex/gpt-5.5:high \
  --judge claude-cli:opus \
  --allow-external-judge
```

Judge commands require `--allow-external-judge` because they send fixture source
text, expected contracts, graph samples, and optionally images to the judge
backend. For private shadow suites, do not use this flag until the export is
explicitly approved.

Judge specs use `backend:model`. The first `:` separates backend from model, so
Ollama-style and Pi-style model names with colons still work after the backend
prefix, e.g. `ollama:deepseek-v4-pro:cloud` or
`pi:openai-codex/gpt-5.5:high`.

Images are not attached to judge requests by default. Add `--include-images`
only when visual quality is intentionally in scope and the judge backend/model is
vision-capable. API-backed non-vision backends receive image path notes but no
pixels. CLI-backed judges such as `pi` and `claude-cli` receive only isolated
temporary copies of approved fixture image files; the Claude CLI is granted
`Read` access only to that temporary image directory, not the original fixture
directory.

The pointwise judge prompt includes a Graphify primer, common failure modes,
general 1-5 score anchors, and dimension-specific rubric anchors. It scores
these dimensions:

- faithfulness
- semantic completeness
- relation quality
- abstraction quality
- graph usefulness
- community label quality
- source grounding
- risk handling

The pointwise judge must also return an `executive_summary`, strengths,
weaknesses, evidence examples, critical failures, a recommended decision
(`accept`, `reject`, or `needs_human_review`), and confidence. Scores alone are
not considered interpretable enough for model-selection decisions.

The pairwise judge sees anonymized Graph A / Graph B outputs and runs both
orders to reduce position bias: baseline-as-A and candidate-as-A. The output
normalizes votes back to `baseline`, `candidate`, or `tie`, and also requires a
natural-language comparison summary, per-graph strengths/weaknesses, candidate
regressions if identifiable, and a human-review flag.

Judge outputs are artifacts, not truth. Do not let judge preference override a
critical deterministic failure. If two judges disagree, or if a candidate wins
only by judge preference while deterministic slices regress, require human
review.

## Score An Existing Graph

```bash
uv run python -m graphify.semantic_eval score \
  --graph tests/fixtures/semantic_eval/payment_retry_graph/graphify-out/graph.json \
  --labels tests/fixtures/semantic_eval/payment_retry_graph/graphify-out/.graphify_labels.json \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out /tmp/payment-retry-score.json
```

Use handcrafted graph fixtures for offline scoring tests. Existing legacy
fixtures may mirror `graphify-out/` paths, while new fixtures can use plain
`graph.json` and `labels.json` files to avoid repository-wide `graphify-out/`
ignore rules. They are not model outputs; they exist to keep metric tests
deterministic and network-free.

## Expected Contract Schema

Every fixture has an `expected.json`. The old string-only shape is still valid:

```json
{
  "required_concepts": ["Payment Retry Policy", "Billing Service"],
  "dedup_watchlist": ["Retry Schedule"],
  "expected_community_label_terms": [["payment", "retry"]],
  "generic_relations": ["references"]
}
```

Richer contracts can use:

- `required_concepts`: strings or objects with `name`, `aliases`, and `weight`.
  Aliases must be equivalent labels for the same concept, not merely related or
  broader/narrower concepts.
- `dedup_watchlist`: concepts that should not appear as duplicate semantic
  nodes, with alias-aware matching.
- `expected_edges`: important relationships. Each entry has `source`, `target`,
  optional `relation_terms`, optional `directed`, optional `polarity`
  (`positive` or `negative`), and optional `weight`. A top-level
  `expected_edges_directed: true` makes fixture edges directed unless an entry
  overrides it.
- `forbidden_concepts`: hallucinated or unsafe concepts that the source does
  not establish and that must not appear. Do not put an explicitly named
  prohibited target here merely because the source says it must not be used.
- `forbidden_edges`: unsafe positive relationships that must not appear.
  Source-grounded prohibitions should instead use required concepts plus a
  negative expected edge and a separately forbidden positive edge.
- `expected_source_files`: files that should be represented in node or edge
  source attribution.
- `expected_community_label_terms`: term groups that should appear in generated
  community labels.
- `generic_relations`: relation names treated as low-specificity.
- `score_weights`: per-dimension weights used for the fixture overall score.

The suite manifest can also define a `quality_gate` with critical dimensions and
minimum aggregate floors. The current scorer-v3 gate requires weighted overall
`>= 0.70` and every present critical dimension `>= 0.45`; the critical
dimensions are `concept_recall`, `expected_edge_coverage`,
`forbidden_concepts_absent`, `forbidden_edges_absent`, and `source_coverage`.
The active suite also requires the `multimodal` profile to reach 0.70, so a
text-heavy aggregate cannot hide total image failure. Negative-polarity
expected edges contribute to endpoint coverage only when the extracted edge is
also negative. `expected_edge_relation_agreement` remains report-only.
`run-suite` exits non-zero when a fixture command fails or the quality gate
fails.

When a required concept is missed, the scorer also records diagnostic
near-matches from extracted node labels. Near-matches are explanatory only:
they help identify conservative aliases or real model wording failures, but
they do not improve the score unless the expected contract is updated with an
explicit alias.

When an expected edge is missed, the scorer records why: missing source
endpoint, missing target endpoint, missing both endpoints, required-polarity
mismatch, relation mismatch between otherwise matched endpoint concepts, or no
edge between the matched endpoint concepts. These diagnostics are explanatory;
required polarity and endpoint presence affect edge coverage, while the
relation-vocabulary agreement score remains report-only.

Scored dimensions currently include:

- concept recall
- duplicate avoidance
- community-label coverage
- relation specificity
- inferred-confidence calibration
- expected-edge coverage
- forbidden-concept absence
- forbidden-edge absence
- source coverage

## Fixture Curation Checklist

When adding a fixture:

1. Pick a repo-shaped profile Graphify actually needs to handle.
2. Write small synthetic docs/code that expose cross-file concepts and
   relationships.
3. Add aliases for terms real models may reasonably phrase differently.
4. Add expected edges for the relationships that matter operationally.
5. Add forbidden concepts/edges for privacy, safety, or hallucination failure
   modes.
6. Add community-label terms for high-level graph usefulness.
7. Add at least one handcrafted good or degraded graph fixture when adding new
   scoring behavior.
8. Run offline tests before any live model call.

## Model Comparison Protocol

Current production standard: keep `deepseek-v4-pro:cloud` as the built-in
Ollama default. The explicit Pi/Luna backend and DeepSeek V4 Flash 0731 are
candidates, not accepted replacements. Prompt-v2/v3 scores and gates are
historical diagnostics only; the 2026-08-05 blind qualitative evidence and
known scorer defects supersede score-only promotion claims.

Until the plan-only redesign is reviewed and approved, do not use this protocol
to change a default. `glm-5.2:cloud`, the older
`deepseek-v4-flash:cloud`, and `deepseek-v4-flash:0731-cloud` remain explicit
comparison points only.

Keep ensemble extraction on hold. Do not add a hybrid workflow unless benchmark
evidence shows that a single available model cannot meet the prioritized quality
target. If a cheaper or faster single model clearly outperforms DeepSeek V4 Pro
on the calibrated suite without privacy/source regressions, prefer that single
model instead of adding ensemble complexity.

For a serious candidate comparison:

1. Freeze the expected contracts before candidate generation. Use a separate
   held-out slice for promotion evidence after prompt/fixture calibration.
2. Run baseline and candidate with matching suite-contract, corpus, and prompt
   hashes. Record the intentionally different operational settings rather than
   calling unlike reasoning configurations identical model tests.
3. Repeat volatile or close-call fixtures 3-5 times and compare paired deltas,
   not just independent averages.
4. Inspect profile scores (`synthetic`, `public-realistic`, `multimodal`,
   `privacy`, `doc-to-code`, etc.) so aggregate quality does not hide slice
   regressions. The suite also reports a derived `text-only` profile for
   fixtures that are not tagged as `multimodal`, `image`, `diagram`, or
   `vision`; use it to separate text semantic quality from image/diagram
   capability.
5. Run pointwise and pairwise judge passes with one or two independent strong
   judge models.
6. Do a short human review of changed wins/losses before changing defaults,
   especially when judges disagree.
7. Record model, backend, judge models, vision settings, timeout, token budget,
   suite version, contract/corpus/prompt hashes, Git evidence, and artifact
   paths.

After the evaluation redesign, a candidate should not replace the default
unless it:

- completes the suite without extraction, parse, cluster, or wiki failures;
- passes redesigned non-compensating semantic gates rather than only the current
  aggregate score;
- is non-inferior to `deepseek-v4-pro:cloud` across relationship meaning,
  conditional and negative semantics, hyperedges, hallucination precision,
  claim-level provenance, and grounded community labels;
- has no severe regression in any privacy, safety, multimodal, or held-out
  fixture slice;
- avoids systematic duplicate nodes, noisy document hubs, or overconfident
  inferred edges;
- remains acceptable across paired repeats and blinded qualitative review; and
- has acceptable runtime for Mase's workflows.

Runtime, output tokens, and cost are useful comparison data, but they should not
override clear quality regressions.

## Validation

Offline harness validation:

```bash
uv run pytest tests/test_semantic_eval.py
```

Live suite runs are manual/operator-approved because they call the selected LLM
backend. Record live comparisons as dated artifacts under `.semantic-evals/` and
summarize material decisions in a dated comparison note when changing model
policy.
