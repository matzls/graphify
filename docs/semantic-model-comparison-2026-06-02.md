---
title: "Semantic Model Comparison"
kind: "validation-note"
status: "active"
created: 2026-06-02
updated: 2026-06-02
audience: "maintainers"
---

# Semantic Model Comparison

## Scope

Tiny Graphify semantic harness run on:

```text
tests/fixtures/semantic_eval/payment_retry/
```

This is a smoke-quality comparison, not a production benchmark.

## Models Tested

All three models generated successfully through the local Ollama daemon:

- `minimax-m3:cloud`
- `gemma4:31b-cloud`
- `gpt-oss:120b-cloud`

## Scores

| Model | Overall | Concept Recall | Dedup | Labels | Relation Specificity | Confidence Calibration |
|---|---:|---:|---:|---:|---:|---:|
| `minimax-m3:cloud` | 0.621 | 0.636 | 0.500 | 0.500 | 0.467 | 1.000 |
| `gemma4:31b-cloud` | 0.580 | 0.364 | 1.000 | 0.250 | 0.286 | 1.000 |
| `gpt-oss:120b-cloud` | 0.523 | 0.364 | 0.500 | 1.000 | 0.750 | 0.000 |

## Runtime And Token Observations

| Model | Extract Time | Label Time | Extract Tokens |
|---|---:|---:|---|
| `minimax-m3:cloud` | 71.51s | 10.71s | 601 in / 3,161 out |
| `gemma4:31b-cloud` | 14.01s | 1.00s | 484 in / 1,311 out |
| `gpt-oss:120b-cloud` | 14.75s | 2.78s | 511 in / 1,961 out |

Graphify currently reports Ollama backend cost as `$0.0000`; do not treat that
as real Ollama Cloud cost tracking.

## Findings

### MiniMax M3

Best overall score on this tiny fixture. It captured more required concepts
than the other two and avoided overconfident inferred edges.

Weaknesses:

- Slowest run by a large margin.
- Still missed `card payments`, `attempt number`, `gateway response`, and
  `account risk`.
- Community labels missed the support and gateway themes.
- Relation specificity stayed mediocre.

### Gemma 4 31B Cloud

Fastest and cleanest on duplicate-node behavior, but too shallow for this
semantic extraction task.

Weaknesses:

- Low concept recall.
- Weak community labels.
- Generic relation labels.

### GPT OSS 120B Cloud

Good labels and better relation specificity, but weak concept recall in the
controlled harness run and poor confidence calibration.

Weaknesses:

- Missed many required concepts.
- Duplicated watched concepts.
- Assigned `1.0` confidence to all inferred edges.

## Provisional Decision

For the next controlled comparison, `minimax-m3:cloud` is the best of these
three Ollama Cloud candidates on quality, despite being slow.

The local fork now uses `minimax-m3:cloud` as the default Ollama semantic model
for evaluation. Treat this as a reversible local default, not a final production
model choice.

## Direct Live Repo Run

Target repo:

```text
/Users/mase/Codebase/Personal-Projects/hushmail-agent-router
```

Privacy handling:

- The direct full-repo run was explicitly approved after noting that it would
  send the included repo corpus to Ollama Cloud.
- A repo-local `.graphifyignore` excluded obvious private/runtime/generated
  paths: `.env`, `config.local.toml`, `data/`, `reports/`, `logs/`,
  `graphify-out/`, venv/cache/build directories, and raw mailbox formats.
- The stale May 17 `graphify-out/` was preserved outside the repo before the
  fresh run so the test would not reuse incremental state.

Fresh direct run scope:

| Item | Count |
|---|---:|
| Code files | 45 |
| Docs | 73 |
| Papers/images | 0 |
| Total detected files | 118 |
| Approx words | 103,476 |

Fresh direct run result:

| Artifact/Metric | Result |
|---|---|
| Extraction chunks | 30/30 completed |
| Adaptive retry events | 4 truncation/invalid-JSON events, all recovered |
| Final graph | 1,941 nodes, 4,836 edges, 19 hyperedges |
| Communities | 71 named communities |
| Semantic tokens | 147,752 input / 399,208 output |
| HTML | `graphify-out/graph.html` regenerated with named community labels |
| Report | `graphify-out/GRAPH_REPORT.md` regenerated |
| Wiki | 81 articles written to `graphify-out/wiki/` |
| Placeholder labels | 0 |
| Invalid confidence values after repair | 0 |

Representative community labels:

- `Core Classification Components`
- `Peer Review Engine`
- `Forwarding Rules Retry`
- `IMAP Client Operations`
- `Config And Audit`
- `Forwarding Ramp Plan`
- `Model Fallback Classification`
- `Live Forwarding Orchestration`

Representative god nodes:

- `MessageView` — 155 connections
- `Classification` — 108 connections
- `LocalModelConfig` — 87 connections
- `RuleConfig` — 72 connections
- `AppConfig` — 67 connections
- `hushmail_agent_router.cli` — 64 connections

Quality read:

- The fresh artifacts are internally consistent: graph community IDs, label
  file, report, HTML, and wiki all use named communities rather than numeric
  placeholders.
- CLI navigation works on the generated graph; `graphify explain "MessageView"`
  and `graphify query "forwarding retry"` returned useful scoped subgraphs.
- The semantic labels are mostly useful and domain-specific, but the labeler
  still produced duplicate names for several small similar communities, such as
  `Review Closure Summary`, `Review Issue Analysis`, `Coverage Summary`, and
  `Disposition Matrix Data`.
- Graphify's adaptive retry path worked in production: MiniMax returned
  truncated or invalid JSON four times, and Graphify split the chunks and
  recovered without writing malformed chunk data.

Operational read:

- MiniMax M3 can produce a rich full-repo semantic graph, but it is slow and
  very verbose. Some chunks emitted more than 20k output tokens.
- Full repo refreshes with MiniMax are viable for deliberate deep analysis, not
  lightweight routine refreshes.
- The output is good enough to review and navigate, but MiniMax should still be
  compared against faster candidates before becoming the permanent everyday
  default.

Implementation notes:

- The live run exposed a model typo, `INTRACTED`, in an edge confidence field.
  The fork now normalizes invalid confidence values to `AMBIGUOUS` with a
  capped confidence score before graph artifacts are written.
- The earlier bounded run exposed a CLI bug where
  `graphify extract <single-file.md>` tried to create
  `<single-file.md>/graphify-out`. The fork now supports single-file scan
  targets and writes `graphify-out/` beside the file.

## Bounded Live-Content Follow-Up

Before the full direct repo run, a smaller live-content run was used to validate
the backend path on copied docs from:

```text
/Users/mase/Codebase/Personal-Projects/hushmail-agent-router/docs/
```

Bounded content:

- `docs/DECISIONS.md`
- `docs/second-brain-contract.md`

Bounded result:

| Step | Result |
|---|---|
| Extract | 30 nodes, 50 edges, 5 communities |
| Tokens | 2,788 input / 10,636 output |
| Chunk 1 | 155.69s, 18 nodes, 30 edges, 7 hyperedges |
| Chunk 2 | 104.86s, 12 nodes, 21 edges |
| Cluster/label | Passed |
| Wiki export | 15 articles |

Quality read:

- Community names were coherent: `Assistant Inbox System`, `Router Contract
  Specification`, `Hushmail Email Forwarding`, `Gmail Second Brain Ingestion`,
  and `Classification Rules Engine`.
- God nodes were useful and aligned with the source docs: `Second Brain Router
  Contract`, `Hushmail Router Project`, `Structured JSONL Fields`, and `SMTP
  Forwarding`.
- The report surfaced reviewable uncertainty rather than hiding it, especially
  inferred JSONL-field relationships and weakly connected local LLM/privacy
  nodes.

Operational read:

- MiniMax M3 produced rich, usable semantic output even on the bounded slice.
- Latency was visible even before the full repo run: the two-doc run took
  multiple minutes.
