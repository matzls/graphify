---
title: "Ollama Cloud Smoke Tests"
kind: "validation-note"
status: "active"
created: 2026-06-02
updated: 2026-06-02
audience: "maintainers"
---

# Ollama Cloud Smoke Tests

## Goal

Check which Ollama Cloud models Mase's current sign-in can use without an
additional subscription, then run a tiny Graphify semantic smoke test with the
best available candidate.

## Access Results

Pulling/registering a cloud model is not enough to prove access. Actual
generation must succeed.

| Model | Pull/register | Generation | Result |
|---|---:|---:|---|
| `gpt-oss:20b-cloud` | already present | passed | accessible |
| `gpt-oss:120b-cloud` | passed | passed | accessible; best available candidate |
| `qwen3.5:397b-cloud` | passed | failed | blocked by subscription requirement |
| `minimax-m2.7:cloud` | already present | failed | blocked by subscription requirement |
| `deepseek-v4-flash:cloud` | passed | failed | blocked by subscription requirement |
| `gemma4:cloud` | failed | not tested | no model manifest |

## Commands Run

```bash
ollama pull qwen3.5:397b-cloud
ollama run qwen3.5:397b-cloud "Return exactly: qwen-cloud-access-ok"
ollama run gpt-oss:20b-cloud "Return exactly: cloud-access-ok"
ollama pull gpt-oss:120b-cloud
ollama run gpt-oss:120b-cloud "Return exactly: cloud-access-ok"
ollama run minimax-m2.7:cloud "Return exactly: cloud-access-ok"
ollama pull deepseek-v4-flash:cloud
ollama run deepseek-v4-flash:cloud "Return exactly: cloud-access-ok"
ollama pull gemma4:cloud
ollama list
```

## Observed Evidence

- `qwen3.5:397b-cloud`, `gpt-oss:120b-cloud`, and
  `deepseek-v4-flash:cloud` all registered locally.
- `ollama list` shows cloud tags including:

```text
qwen3.5:397b-cloud    a7bf6f7891c3    -    2026-06-02
gpt-oss:120b-cloud     569662207105    -    2026-06-02
gpt-oss:20b-cloud      875e8e3a629a    -    2026-06-02
minimax-m2.7:cloud     06daa293c105    -    2026-06-02
deepseek-v4-flash:cloud ea027821675c   -    2026-06-02
```

- Subscription-blocked models returned:

```text
Error: 403 Forbidden: this model requires a subscription, upgrade for access: https://ollama.com/upgrade
```

- `gemma4:cloud` returned:

```text
Error: pull model manifest: file does not exist
```

## Controlled Graphify Smoke

Selected model: `gpt-oss:120b-cloud`

Reason: it is the strongest cloud model that actually generated on the current
account without an additional subscription.

Corpus: two small non-private markdown files under
`/private/tmp/graphify-ollama-cloud-smoke`.

Commands:

```bash
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify extract /private/tmp/graphify-ollama-cloud-smoke \
  --backend ollama --model gpt-oss:120b-cloud --token-budget 1200 \
  --max-concurrency 1 --api-timeout 180

OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify cluster-only /private/tmp/graphify-ollama-cloud-smoke \
  --backend ollama --model gpt-oss:120b-cloud --no-viz

graphify export wiki \
  --graph /private/tmp/graphify-ollama-cloud-smoke/graphify-out/graph.json \
  --labels /private/tmp/graphify-ollama-cloud-smoke/graphify-out/.graphify_labels.json
```

Result:

- Extraction completed in one chunk.
- Trace reported `511` input tokens and `3,218` output tokens.
- Graph output: `20` nodes, `23` edges, `6` communities.
- Community labels were meaningful:
  - `Payment Failure Support`
  - `Payment Retry Engine`
  - `Grace Period`
  - `Retry Schedule`
  - `Subscription Management`
  - `Gateway Response`
- Wiki export completed: `16` articles.

## Caveats

- The regular `ollama run` CLI prints visible reasoning for `gpt-oss` models.
  Graphify's OpenAI-compatible API path still produced parseable JSON in this
  smoke test.
- Graphify currently estimates Ollama backend cost as `$0.0000`, which is not
  reliable for Ollama Cloud usage accounting.
- This was a tiny smoke test, not a quality benchmark. A real model decision
  should compare outputs on a bounded representative repo/docs slice.

## Quality Evaluation

Overall quality: usable smoke-test quality, not yet production-proven.

Strengths:

- Extracted the core concepts from the two source files without obvious
  hallucinated business objects.
- Correctly identified the two central source documents as the load-bearing
  nodes: `Support Runbook` and `Payment Retry Policy`.
- Community labels were meaningful and human-readable:
  `Payment Failure Support`, `Payment Retry Engine`, `Grace Period`,
  `Retry Schedule`, `Subscription Management`, and `Gateway Response`.
- Cross-file relationships were directionally useful, especially the link
  between gateway response, subscription, grace period, and retry schedule
  across the policy/runbook files.
- Wiki export was navigable at the community level.

Weaknesses:

- Duplicate same-concept nodes appeared across files, for example
  `Retry Schedule`, `Subscription`, and `Grace Period` each exist once per
  source file and are then connected by inferred `shares_data_with` edges.
  This is understandable for source-preserving extraction, but it makes the
  wiki noisy by creating suffixed pages such as `Retry_Schedule_2.md`.
- The model was overconfident: all inferred edges had confidence score `1.0`.
  For semantic similarity and same-concept links, that should probably be less
  absolute.
- Some relation labels are generic (`references`) rather than behavior-rich.
  For example, the retry policy could express `defines_retry_schedule` or
  `records_gateway_response`, but the output stayed at a broad relation level.
- The report token line after `cluster-only` shows `0 input / 0 output`
  because clustering rewrote the report with zero token accounting, even though
  extraction trace showed `511` input and `3,218` output tokens.
- The generated wiki is useful for navigation, but not deeply explanatory; it
  mostly lists graph structure rather than synthesizing a prose explanation.

Provisional score for this tiny corpus:

| Dimension | Score | Notes |
|---|---:|---|
| Access/runtime reliability | 4/5 | End-to-end extraction, labels, and wiki worked. |
| JSON/Graphify compatibility | 5/5 | Parseable output with valid graph artifacts. |
| Concept precision | 4/5 | Core entities were correct; no major hallucinations seen. |
| Relationship precision | 3/5 | Useful but generic and overconfident. |
| Deduplication quality | 2/5 | Same concepts duplicated across files. |
| Wiki usefulness | 3/5 | Navigable, but noisy around duplicate concepts. |

Decision from quality check: `gpt-oss:120b-cloud` is good enough for a
controlled larger comparison, but not yet good enough to declare as the
production semantic model. The next comparison should use a representative repo
slice and score duplicate nodes, relation specificity, and community label
quality against either Gemini or a stronger paid Ollama Cloud model.

## Decision

Use `gpt-oss:120b-cloud` as the current no-extra-subscription Ollama Cloud
candidate for controlled Graphify semantic tests.

Do not use `qwen3.5:397b-cloud`, `minimax-m2.7:cloud`, or
`deepseek-v4-flash:cloud` unless Ollama account access changes.
