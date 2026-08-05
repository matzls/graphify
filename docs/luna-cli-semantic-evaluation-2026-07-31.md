---
title: "Luna CLI Semantic Evaluation — 2026-07-31"
kind: investigation
status: done
audience: agents-maintainers-operators
canonicality: historical
created: 2026-07-31
updated: 2026-08-05
source_of_truth: "./luna-cli-semantic-evaluation-2026-07-31.md"
superseded_by: "./semantic-model-quality-harness.md"
related:
  - "./semantic-model-quality-harness.md"
  - "./codex-pi-semantic-refresh.md"
  - "./plans/graphify-extraction-contract-and-harness-calibration-plan.md"
---

> Dated evidence for deciding whether subscription-authenticated GPT-5.6 Luna
> merits a Graphify CLI backend. This does not authorize backend implementation,
> Ollama removal, installation changes, or propagation.

## Supersession Notice

This document preserves the 2026-07-31 investigation as historical evidence.
Later work implemented the explicit final-`pi --print` backend in source and
validated live transport and image delivery, but also found material scorer,
fixture, gate, provenance, hyperedge, and repeatability defects. The original
numeric winner and promotion recommendation are therefore not current authority.

Current disposition: keep DeepSeek V4 Pro automatic, keep Pi explicit,
uninstalled from the current source commit, and unpromoted, require human review
for Pi image semantics, and make **plan-only evaluation-harness redesign** the
next project iteration before further prompt/model decisions.

## Summary

GPT-5.6 Luna through an isolated Pi CLI subprocess delivered materially better
text semantic graphs than the matched DeepSeek V4 Pro Ollama baseline after the
extraction contract and quality harness were corrected.

The matched prompt-v3/scorer-v3 full-suite result was:

| Model | Overall | Text only | Runtime | Gate |
| --- | ---: | ---: | ---: | --- |
| Luna `high` | 0.831 | 0.912 | 724.98s | fail: image input blocked |
| DeepSeek V4 Pro | 0.734 | 0.790 | 197.59s | fail: edge + multimodal |

Luna improved five of the six fixtures. The remaining fixture was the image
workflow: both recorded runs failed to recover its visual concepts. Follow-up
isolated the Luna result to Pi's active global `images.blockImages: true`
privacy setting rather than a model limitation. With image sending enabled in
a temporary project override, native `pi -p @diagram.png` recovered every
expected visual node and all six directed workflow edges.

Historical decision at this checkpoint: Luna quality and capability were
sufficient to specify a first-class, subscription-backed Pi backend for text and
images. The later implementation passed transport checks but did not produce
promotion-grade semantic evidence. The current decision is to keep Ollama Pro
automatic and Pi explicit.

## Evaluation Contract Corrections

Scorer v3 and suite contract v3 correct false measurements found during the
Luna calibration:

- expected-edge endpoints inherit unambiguous aliases declared by required
  concepts
- ambiguous shared aliases fail closed instead of matching multiple concepts
- relation terms match token phrases rather than arbitrary substrings
- forbidden positive edges no longer match explicit negative relations such as
  `must_not_store`, `does_not_store`, `cannot_store`, or `avoids_logging`
- negative expected edges require negative polarity, and source-explicit fixture
  flows use directed matching
- prohibited targets explicitly named by source documents are represented as
  required concepts plus negative expected edges, rather than being mislabeled
  as hallucinated forbidden concepts
- fixture edges were aligned with the source actor/acted-upon contract
- source-faithful label variants were added explicitly rather than accepted by
  broad fuzzy matching

These changes explain why early Luna safety scores were invalid. For example,
`Message Router --must_not_store--> Raw Mailbox Export` and
`Trace Event --avoids_logging--> Raw Document Text` preserve source policy;
they do not assert unsafe storage or logging.

## Matched Full-Suite Comparison

Both matched runs used:

- suite version 3
- scorer version 3
- the prompt-v3 selective/polarity extraction contract
- one semantic extraction worker
- a 60,000-token input budget
- provider retries disabled
- normal extraction, clustering, community labels, and wiki export

| Dimension | Luna | DeepSeek | Delta |
| --- | ---: | ---: | ---: |
| Overall | 0.831 | 0.734 | +0.097 |
| Concept recall | 0.739 | 0.635 | +0.104 |
| Expected-edge coverage | 0.663 | 0.433 | +0.230 |
| Relation agreement | 0.733 | 0.968 | -0.235 |
| Deduplication | 0.953 | 0.836 | +0.117 |
| Community labels | 0.594 | 0.422 | +0.172 |
| Relation specificity | 0.984 | 0.896 | +0.088 |
| Forbidden concepts absent | 1.000 | 1.000 | 0.000 |
| Forbidden edges absent | 1.000 | 1.000 | 0.000 |
| Source coverage | 1.000 | 1.000 | 0.000 |

Fixture-level overall scores:

| Fixture | Luna | DeepSeek | Delta |
| --- | ---: | ---: | ---: |
| Payment retry | 0.759 | 0.722 | +0.037 |
| Router privacy | 0.886 | 0.879 | +0.007 |
| Workflow migration | 0.977 | 0.835 | +0.142 |
| Integration gateway | 0.973 | 0.826 | +0.147 |
| Graphify public slice | 0.934 | 0.677 | +0.257 |
| Diagram workflow | 0.481 | 0.494 | -0.013 |

Luna's relation-agreement deficit is material, not a rounding difference. It
extracts more useful endpoints but uses a less contract-aligned verb on some
edges. Source inspection remains required before promotion; aggregate scores
alone are not sufficient. The final artifacts fail the multimodal profile gate as executed, and DeepSeek
also falls below the aggregate edge-coverage floor. The Luna multimodal score
must be interpreted as a blocked-input configuration result, not evidence that
Luna lacks image capability.

The final artifacts record matching suite, corpus, and prompt hashes plus the
same Git HEAD and dirty-diff hash. They differ intentionally in operational
configuration: Luna used Pi/OAuth with `high` reasoning, while DeepSeek used
Ollama with reasoning disabled. This is a comparison of deployable
configurations, not isolated model weights.

## Exploratory Repeatability

Before the contract was frozen and fingerprinted, `router_privacy` and
`graphify_public_slice` received two additional runs per backend, for three
observations per model and fixture. The fixture sources were byte-identical and
the results support the qualitative preference, but these pre-freeze artifacts
are calibration evidence rather than an unbiased held-out promotion gate.

| Fixture/model | Run 1 | Run 2 | Run 3 | Mean |
| --- | ---: | ---: | ---: | ---: |
| Router / Luna | 0.962 | 0.948 | 0.916 | 0.942 |
| Router / DeepSeek | 0.865 | 0.899 | 0.818 | 0.861 |
| Graphify / Luna | 0.976 | 0.847 | 0.889 | 0.904 |
| Graphify / DeepSeek | 0.725 | 0.699 | 0.837 | 0.754 |

Every exploratory Luna repeat remained above every DeepSeek repeat on the same
fixture. Variance remains visible, especially in edge coverage and community
labels. A future promotion gate should use a frozen held-out corpus rather than
reusing these calibration fixtures.

## Vision Finding and Correction

The recorded Luna suite's image request contained one staged PNG attachment,
but Mase's global Pi configuration had `images.blockImages: true`. Pi retained
the image in the local user-message event while blocking its pixels from the
provider, which explains both the suite failure and the original direct probe's
empty result.

A second probe used Pi's documented native image syntax and a temporary,
project-scoped `images.blockImages: false` override without changing the global
setting or repository:

```text
pi --model openai-codex/gpt-5.6-luna --thinking high --mode json \
  --print --no-session --no-tools --no-extensions --no-skills \
  --no-prompt-templates --no-context-files --approve \
  @diagram.png "Inspect the attached diagram directly ..."
```

Luna returned every expected visual concept and all six expected directed
edges: Intake Queue → Redaction Gate → Classifier Branch, both Auto Route and
Review Queue branches, and both paths into Audit Trail. This confirms that
Luna and Pi are multimodal on the tested native path.

The implementation must not silently override Pi's image privacy setting.
Graphify should detect or clearly surface blocked image delivery and require an
explicit operator-controlled way to permit cloud image processing. A
Graphify-formatted image extraction canary remains part of backend integration
validation, but model capability is no longer an open blocker.

## Operational Findings

- Luna `max` reasoning was rejected: extraction took roughly 8–10 minutes per
  small fixture and produced denser, less useful graphs.
- Luna `off` reasoning was rejected: it was faster but missed concepts and
  edges or over-pruned the graph.
- Luna `high` was the best tested quality/runtime setting.
- The final Luna suite was about 3.7 times slower than DeepSeek end to end.
- Pi-backed calls were serialized to avoid shared OAuth/session contention.
- The temporary compatibility proxy estimated token counts from characters;
  its token/cost figures are not authoritative usage evidence.
- The retained final artifacts identify transport mode and trace host but
  predate the harness's sanitized `endpoint_sha256` field. Future runs record
  that fingerprint without exposing endpoint configuration.
- No OAuth token was extracted or replayed. Every Luna call used the existing
  authenticated Pi CLI.

## Historical Remaining Gates

Items 1-6 below were superseded or completed by the final print-only
implementation and bounded live campaign. Item 7 was not accepted because image
semantics and the evaluator were not promotion-grade; item 8 remains unstarted.
The operative next gate is a reviewed **plan-only evaluation-harness redesign**.

Before changing Graphify's backend default, this investigation originally
listed:

1. Design and implement a first-class Pi CLI backend without the temporary HTTP
   compatibility proxy.
2. Parse Pi JSON events for provider/model, real usage, terminal stop reason,
   malformed output, and provider errors.
3. Enforce timeout and output bounds, and preserve Graphify's adaptive split and
   fail-closed partial-cache behavior.
4. Serialize extraction and community-label calls.
5. Support native Pi image attachments, respect Pi's image privacy gate, and
   fail clearly rather than silently producing filename-only semantics when
   pixels are blocked.
6. Canary text and image extraction through the real Graphify skill path from
   an outer Pi session.
7. Make Pi the default after implementation and proportionate backend tests
   pass; keep explicit Ollama selection unchanged.
8. Keep Ollama removal as a separate short-to-mid-term decision after migration
   evidence.

## Evidence

Ignored local run artifacts:

```text
.semantic-evals/prompt-v3-final-luna-high-suite-20260731-122011/
.semantic-evals/prompt-v3-final-deepseek-v4-pro-cloud-suite-20260731-123235/
.semantic-evals/prompt-v3-luna-high-repeats-20260731-114423/
.semantic-evals/prompt-v3-deepseek-v4-pro-repeats-20260731-115557/
```

Comparison and diagnostic artifacts:

```text
/tmp/graphify-prompt-v3-final-luna-vs-deepseek-20260731.json
/tmp/graphify-scorer-v3-rebaseline-final-20260731-114005/
/tmp/luna-direct-vision-probe-20260731.txt
/tmp/graphify-pi-luna-image-enabled-probe/result.jsonl
```
