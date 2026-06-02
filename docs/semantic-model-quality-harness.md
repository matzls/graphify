---
title: "Semantic Model Quality Harness"
kind: "operator-guide"
status: "active"
created: 2026-06-02
updated: 2026-06-02
audience: "maintainers"
---

# Semantic Model Quality Harness

Use this harness to compare LLM backends for Graphify semantic extraction on a
small, repeatable corpus before choosing a production semantic model.

## Fixture

The first fixture is:

```text
tests/fixtures/semantic_eval/payment_retry/
```

It contains two short markdown files about payment retries and support workflow,
plus `expected.json`, which defines the concepts and quality checks the output
should satisfy.

## Run A Model

Example with Ollama Cloud:

```bash
OLLAMA_API_KEY=ollama uv run python -m graphify.semantic_eval run \
  --corpus tests/fixtures/semantic_eval/payment_retry \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out-dir .semantic-evals/gpt-oss-120b-cloud-payment-retry \
  --backend ollama \
  --model gpt-oss:120b-cloud \
  --timeout 180 \
  --token-budget 1200
```

Example with Gemini:

```bash
GEMINI_API_KEY=<key> uv run python -m graphify.semantic_eval run \
  --corpus tests/fixtures/semantic_eval/payment_retry \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out-dir .semantic-evals/gemini-3-5-flash-payment-retry \
  --backend gemini \
  --model gemini-3.5-flash \
  --timeout 180 \
  --token-budget 1200
```

The harness writes:

- `run.json`: raw command outputs and structured scores
- `EVALUATION.md`: human-readable score summary
- `corpus/graphify-out/`: Graphify artifacts from that run

## Score An Existing Run

```bash
uv run python -m graphify.semantic_eval score \
  --graph .semantic-evals/gpt-oss-120b-cloud-payment-retry/corpus/graphify-out/graph.json \
  --labels .semantic-evals/gpt-oss-120b-cloud-payment-retry/corpus/graphify-out/.graphify_labels.json \
  --expected tests/fixtures/semantic_eval/payment_retry/expected.json \
  --out .semantic-evals/gpt-oss-120b-cloud-payment-retry/score.json
```

## What It Scores

- Required concept recall
- Duplicate same-concept nodes for watched concepts
- Community label coverage
- Relation specificity versus generic `references`
- Overconfident inferred edges

These scores are not a universal truth. They are a small regression-style
signal to compare models consistently before running a larger, more expensive
Graphify refresh.

## Decision Rule

For a model to become the default semantic candidate, expect:

- no failed Graphify commands
- parseable JSON and wiki export
- high concept recall
- low duplicate-node count on watched concepts
- meaningful community labels
- fewer generic relation labels than the baseline
- no systematic `1.0` confidence on every inferred edge
