---
title: "Semantic Model Quality Harness"
kind: "operator-guide"
status: "active"
created: 2026-06-02
updated: 2026-07-01
audience: "maintainers"
---

# Semantic Model Quality Harness

Use this harness to compare LLM backends for Graphify semantic extraction on a
small, repeatable, privacy-safe corpus suite before choosing a production
semantic model.

Quality is the primary decision signal. Runtime and token counts are recorded,
but speed is a tiebreaker unless candidate quality is operationally equivalent.

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
backend. With Ollama Cloud models such as `kimi-k2.7-code:cloud` or
`minimax-m3:cloud`, that means the fixture corpus leaves the machine through
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

## Run One Fixture

Example with Ollama Cloud:

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run \
  --corpus tests/fixtures/semantic_eval/payment_retry \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out-dir .semantic-evals/kimi-k2.7-code-cloud-payment-retry \
  --backend ollama \
  --model kimi-k2.7-code:cloud \
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
  --out-dir .semantic-evals/kimi-k2.7-code-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model kimi-k2.7-code:cloud \
  --timeout 300 \
  --token-budget 1200
```

To compare a candidate:

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/kimi-k2.7-code-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model kimi-k2.7-code:cloud \
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
  timings, token counts, and fixture scores
- `SUMMARY.md`: operator-readable aggregate summary

## Current Candidate Baselines

These are the latest local suite artifacts that should anchor the next model
decision. `.semantic-evals/` is intentionally ignored, so rerun or copy the
needed artifacts before making a durable policy change.

| Model | Backend | Local artifact | Overall | Gate | Notes |
|---|---|---|---:|---|---|
| `kimi-k2.7-code:cloud` | Ollama Cloud | `.semantic-evals/model-quality-comparison-20260614-191220/kimi-k2.7-code_cloud/suite-run.json` | 0.632 | fail | Incumbent comparison point, not a passing baseline. |
| `qwen3.5:397b-cloud` | Ollama Cloud | `.semantic-evals/model-quality-comparison-20260614-191220/qwen3.5_397b-cloud/suite-run.json` | 0.648 | fail | Slightly higher than Kimi in the saved run, still below gate. |
| `minimax-m3:cloud` | Ollama Cloud | `.semantic-evals/minimax-m3-cloud-suite-20260614-112409/suite-run.json` | 0.630 | fail | Retained because it was the previous comparison baseline. |
| `glm-5.2:cloud` | Ollama Cloud | `.semantic-evals/glm-5.2-cloud-suite-amended-20260629-151816/suite-run.json` | 0.679 | fail | Best saved overall after amendment, but still has critical regressions. |
| `deepseek-v4-flash:cloud` | Ollama Cloud | `.semantic-evals/deepseek-v4-flash-cloud-suite-20260701-133000/suite-run.json` | none | fail | Access works for simple/probe calls, but the full suite failed every fixture with Ollama OpenAI-compatible `APIConnectionError`; this is a transport/extraction failure, not a quality score. |
| `deepseek-v4-pro:cloud` | Ollama Cloud | `.semantic-evals/deepseek-v4-pro-cloud-suite-20260701-compare/suite-run.json` | 0.655 | fail | Completed the full suite through Ollama; above Kimi/Qwen/MiniMax overall, below GLM, and still fails on concept recall and expected-edge coverage. |
| DeepSeek direct API candidate | DeepSeek API | not run | none | not evaluated | Recommended next diagnostic path if `DEEPSEEK_API_KEY` is available, to separate model quality from Ollama Cloud proxy behavior. |

As of 2026-07-01, every scored saved candidate fails the suite quality gate.
Do not promote any of these models as the clean default from aggregate score
alone. DeepSeek Flash is still worth testing because Ollama lists
`deepseek-v4-flash` as a cloud model with tool and thinking support, but the
Graphify suite must first complete without extraction or transport failures.
The DeepSeek row above is normalized with current fail-closed gate semantics;
the original ignored local artifact was generated before fixture failures were
counted as gate failures and may still show `gate_passed: true` in its JSON.
Follow-up probes on 2026-07-01 showed `deepseek-v4-flash:cloud` returning
Ollama Cloud HTTP 503 overloads through both `/v1/chat/completions` and native
`/api/chat`, while `deepseek-v4-pro:cloud` returned a simple response through
both routes. That makes Ollama a viable DeepSeek transport, but Flash
availability is currently the blocker.

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

DeepSeek Flash rerun command:

```bash
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 GRAPHIFY_OLLAMA_REASONING_EFFORT=none uv run python -m graphify.semantic_eval run-suite \
  --suite tests/fixtures/semantic_eval/suite.json \
  --out-dir .semantic-evals/deepseek-v4-flash-cloud-suite-$(date +%Y%m%d-%H%M%S) \
  --backend ollama \
  --model deepseek-v4-flash:cloud \
  --timeout 900 \
  --token-budget 60000
```

If Flash keeps returning 503 overloads, run a single-fixture Pro smoke through
the same Ollama path before changing the default model. Pro working while Flash
fails means the issue is Ollama Cloud model availability, not Graphify's Ollama
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
  --baseline .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --candidate .semantic-evals/kimi-k2.7-code-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out .semantic-evals/comparisons/minimax-vs-kimi-k2.7-code.json
```

This writes JSON plus a sibling Markdown comparison with aggregate deltas,
fixture-level deltas, and regressions.

## Add Strong LLM Judges

Deterministic scoring is the hard measurement layer. For semantic judgment,
attach one or two strong judge models as an additional, opt-in layer. Quick
iteration can use one fresh strong judge. Default-model changes should use two
independent judge families when possible, for example a GPT-family judge and a
Claude/Opus-family judge.

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
  --baseline .semantic-evals/minimax-m3-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --candidate .semantic-evals/kimi-k2.7-code-cloud-suite-YYYYMMDD-HHMMSS/suite-run.json \
  --out-dir .semantic-evals/comparisons/minimax-vs-kimi-k2.7-code-judges \
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
prefix, e.g. `ollama:kimi-k2.7-code:cloud` or
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
  optional `relation_terms`, optional `directed`, and optional `weight`.
- `forbidden_concepts`: hallucinated or unsafe concepts that must not appear.
- `forbidden_edges`: unsafe relationships that must not appear.
- `expected_source_files`: files that should be represented in node or edge
  source attribution.
- `expected_community_label_terms`: term groups that should appear in generated
  community labels.
- `generic_relations`: relation names treated as low-specificity.
- `score_weights`: per-dimension weights used for the fixture overall score.

The suite manifest can also define a `quality_gate` with critical dimensions and
minimum aggregate floors. `run-suite` exits non-zero when a fixture command fails
or the quality gate fails.

When a required concept is missed, the scorer also records diagnostic
near-matches from extracted node labels. Near-matches are explanatory only:
they help identify conservative aliases or real model wording failures, but
they do not improve the score unless the expected contract is updated with an
explicit alias.

When an expected edge is missed, the scorer records why: missing source
endpoint, missing target endpoint, missing both endpoints, relation mismatch
between otherwise matched endpoint concepts, or no edge between the matched
endpoint concepts. These diagnostics are explanatory only and do not change the
expected-edge score.

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

Current interim standard: treat `kimi-k2.7-code:cloud` as the incumbent
comparison point, not as a passing quality baseline. The 2026-06-14 suite showed
Kimi slightly ahead of `minimax-m3:cloud` on prioritized concept recall and
relation specificity, but all saved scored candidates failed the gate. DeepSeek
Flash should be compared against Kimi only after the suite produces scored
fixtures instead of transport failures.

Keep the proposed hybrid workflow on hold: Kimi primary extraction plus Minimax
secondary edge augmentation should not be implemented unless benchmark evidence
shows that a single available model cannot meet the prioritized quality target.
If Qwen or another model clearly outperforms Kimi, prefer that single model
instead of adding ensemble complexity.

For a serious candidate comparison:

1. Run baseline and candidate on the same suite version.
2. Repeat volatile or close-call fixtures 3-5 times and compare paired deltas,
   not just independent averages.
3. Inspect profile scores (`synthetic`, `public-realistic`, `multimodal`,
   `privacy`, `doc-to-code`, etc.) so aggregate quality does not hide slice
   regressions. The suite also reports a derived `text-only` profile for
   fixtures that are not tagged as `multimodal`, `image`, `diagram`, or
   `vision`; use it to separate text semantic quality from image/diagram
   capability.
4. Run pointwise and pairwise judge passes with one or two independent strong
   judge models.
5. Do a short human review of changed wins/losses before changing defaults,
   especially when judges disagree.
6. Record model, backend, judge models, vision settings, timeout, token budget,
   suite version, and artifact paths.

A candidate should not replace the default unless it:

- completes the suite without extraction, parse, cluster, or wiki failures
- passes the suite quality gate
- beats the active standard model (`kimi-k2.7-code:cloud` as of 2026-06-14) on
  prioritized quality dimensions or is clearly non-inferior while materially
  improving operational concerns
- has no severe regression in critical dimensions: concept recall, expected-edge
  coverage, forbidden-concept absence, forbidden-edge absence, and source
  coverage
- avoids systematic duplicate-node or overconfident inferred-edge behavior
- is preferred or accepted as non-inferior by the independent judge layer
- has acceptable runtime for Mase's workflows

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
