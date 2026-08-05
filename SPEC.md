---
title: "First-Class Pi CLI Semantic Backend"
kind: spec
status: done
audience: agents-maintainers
canonicality: canonical
created: 2026-07-31
updated: 2026-08-05
source_of_truth: "./SPEC.md"
related:
  - "./tasks/plan.md"
  - "./tasks/todo.md"
  - "./docs/semantic-model-quality-harness.md"
  - "./docs/plans/autonomous-build-packets/graphify-pi-cli-backend-autonomous-build-packet.md"
---

## Revision 8 Transport Amendment Status

Revision 8 superseded revision 7's Pi JSON-event and RPC transport assumptions.
The final-`pi --print` backend is now implemented and offline-validated in this
source checkout. A bounded live campaign verified transport, call accounting,
privacy, image delivery, and cleanup, but failed the image semantic quality gate.
Pi therefore remains explicit, uninstalled from the current source commit, and
unpromoted; Ollama Pro remains automatic.

This specification and its implementation authority are complete. The next
project iteration is **plan-only evaluation-harness redesign**. This status
grants no redesign implementation, prompt edit, provider-call, default-change,
install, push, propagation, or promotion authority.

## Proportionality

Classification: **high-risk/runtime**.

The Pi backend launches an authenticated external CLI and sends repository text
and, with explicit consent, image pixels to a hosted model. The contract must
therefore remain explicit about subprocess isolation, bounded output, strict
response validation, privacy, cleanup, image consent, cache provenance, and
separate promotion authority.

## Objective

Maintain `pi` as a first-class explicit Graphify semantic backend using the
locally installed, ChatGPT-authenticated Pi CLI without extracting or replaying
OAuth tokens. Replace the current JSON-event adapter with one final-response
`pi --print` subprocess per model request.

The configured Pi model remains `openai-codex/gpt-5.6-luna` with thinking level
`high` unless an explicit command or supported environment override changes it.
Those values are requested configuration, not proof of the provider/model that
actually served a print-mode call.

Ollama remains the automatic semantic backend. Pi remains explicit through
`--backend pi`; the completed T-007/CP-3 evidence did not justify promotion.
Explicit Ollama behavior remains unchanged, and Graphify must never fall back
automatically from Pi to Ollama.

Observable success for this amendment means:

- explicit Pi extraction and labeling use one isolated `pi --print` child per
  request and accept only its bounded final response;
- extraction accepts exactly one complete Graphify JSON object and rejects event
  streams, partial event output, prose, code fences, malformed JSON, hollow
  output, and out-of-contract shapes;
- print-mode image attachments preserve per-run consent, secure staging,
  pixel-derived provenance, and cleanup;
- unavailable print-mode provider/model/usage/stop metadata is represented as
  unavailable and is never reconstructed from stderr, requested configuration,
  timing, or undocumented behavior;
- missing authentication/model access, nonzero exit, output breach, timeout,
  interruption, and invalid final output fail closed through Graphify's existing
  retry/partial/cache/write guards; and
- bare Graphify semantic commands continue to select Ollama unless and until a
  later promotion plan is reviewed and approved.

## Current Evidence

Post-implementation evidence supersedes score-only conclusions. The print-only
adapter completed all bounded live transport stages without retries or privacy
failure, but image semantics were incomplete. A later audit found material
relationship, hyperedge, representation, label, provenance, hallucination, and
repeatability defects in scorer v3. Its numeric results are diagnostic only and
cannot authorize prompt or backend promotion.

The frozen scorer-v3 comparison had identified Luna as the numeric text winner
over the current DeepSeek/Ollama configuration: text-only score `0.912` versus
`0.790`. That result is retained as historical calibration evidence, not proof
of superiority or authority to promote Pi.

The native image probe and later Graphify campaign established that Pi/Luna can
receive the committed diagram when image upload is explicitly authorized. The
adapter recorded pixel-derived provenance correctly; the remaining blocker is
semantic fidelity, not transport capability.

Three prior JSON-event campaigns stopped during text extraction. A bounded
public-safe diagnostic identified `output_stdout_stream` before a terminal
assistant event. Those results demonstrate that JSON-event output includes
partial event traffic and must not be retried as the r8 transport.

One separately authorized synthetic `pi --print` feasibility probe passed an
exact final-JSON assertion with Luna/high. Its sanitized receipt is:

```text
.semantic-evals/pi-print-mode-probe/02148cc1426367b2/receipt.json
SHA-256: 02148cc1426367b20872ba9bbe691de9e0a09db51881aff3bc581a4667f4d64c
```

The receipt contains no prompt, response, raw output, credential, byte count, or
session identifier. At that checkpoint it proved only synthetic final-response
feasibility. The later bounded campaign exercised real Graphify extraction,
labels, native image attachments, the final byte bounds, and reservation denial;
it still did not establish promotion readiness.

## Operator Commands

These commands describe the source implementation. The active installed CLI has
not been refreshed for this commit and may not expose `--backend pi`. Do not
reinstall or promote it without separate authority.

Explicit Pi extraction:

```bash
graphify extract <path> \
  --backend pi \
  --model openai-codex/gpt-5.6-luna
```

Explicit Pi extraction with fresh image upload consent:

```bash
graphify extract <path> \
  --backend pi \
  --allow-image-upload
```

Explicit Pi community labeling remains a separate command:

```bash
graphify cluster-only <path> --backend pi
```

Ollama remains automatic for bare semantic commands and remains explicitly
selectable on every command:

```bash
graphify extract <path> --backend ollama
graphify cluster-only <path> --backend ollama
```

Backend and model choices remain command-local. A later label command must
repeat `--backend pi`, `--backend ollama`, or a non-default model when that is
the operator's intent.

Readiness probe:

```bash
graphify doctor --backend pi --probe
```

The probe may make one bounded text-only Pi request only when separately
authorized. It must not read or print OAuth credentials and must report
print-mode event metadata as unavailable.

## Configuration

- `GRAPHIFY_PI_MODEL`: requested Pi model; default
  `openai-codex/gpt-5.6-luna`.
- `GRAPHIFY_PI_THINKING`: requested Pi thinking level; default `high`; validate
  against Pi-supported values.
- `GRAPHIFY_API_TIMEOUT`: complete Pi child-process deadline.
- `GRAPHIFY_MAX_OUTPUT_TOKENS`: planning input for the final-response byte cap;
  it is not reported usage and must not be presented as actual output tokens.
- `--model`: existing command-level override, authoritative over
  `GRAPHIFY_PI_MODEL`.
- `--allow-image-upload`: per-run authority for fresh Pi pixel transfer. It does
  not mutate global or target-project Pi settings.

No OAuth token, bearer token, API key, endpoint secret, source content, complete
model response, image bytes, raw stderr, or parent session identifier may be
written to diagnostics or canary receipts.

## Revision 8 Print Transport Contract

### Invocation

Each Pi model request launches one child with an argument list equivalent to:

```text
pi --print --no-session --no-tools --no-extensions --no-skills
   --no-prompt-templates --no-themes --no-context-files
   --model MODEL --thinking LEVEL [@STAGED_IMAGE ...]
```

The complete prompt is sent through stdin. The child runs from a
Graphify-controlled temporary directory with only the narrowly required local
settings. Pi/Graphify retries are disabled for controlled canaries. Parent Pi
session identifiers are removed from the child environment.

The adapter must not pass `--mode json`, `--mode rpc`, or retain a JSON-event or
RPC fallback. Capability checks must require the exact print/isolation/model
flags used by the adapter rather than a minimum version string.

### Final stdout bound

Let `N` be the positive per-call output budget after Graphify's existing output
budget resolver and any smaller label-specific budget. The raw stdout cap is:

```text
final_response_limit = max(1_048_576, 16 * N) bytes
```

All stdout bytes count, including leading/trailing JSON whitespace and a final
newline. Exactly-at-limit output is accepted for validation; the next byte
terminates the process group and returns a deterministic output-bound failure.
The 16-byte multiplier retains the existing conservative four-characters-per-
token planning heuristic times the four-byte maximum UTF-8 code-point width.
The 1 MiB floor matches the bounded synthetic feasibility envelope without
claiming an exact tokenizer relationship.

The adapter drains stdout incrementally into a bounded buffer. It does not use
JSONL record, assistant-delta, event-stream, or terminal-message limits.

### Stderr bound

All stderr bytes count against:

```text
stderr_stream_limit = 65_536 bytes
```

Exactly-at-limit stderr may be drained; the next byte terminates the child as a
transport failure. Stderr is not response data and is not parsed for
provider/model/usage/stop metadata. Raw stderr is not persisted in receipts or
reported with source-bearing diagnostics.

### Final response validation

After a zero exit and complete pipe drain:

- decode stdout as strict UTF-8;
- reject empty or whitespace-only output;
- for extraction, parse the complete stdout with one `json.loads` operation;
  JSON-standard surrounding whitespace is allowed, but prose, markdown fences,
  concatenated objects, JSONL/event records, trailing non-whitespace, and
  partial event output are rejected;
- require one object and pass it through Graphify's existing extraction
  sanitization, schema, hollow-response, source-binding, adaptive retry,
  partial-marker, cache, shrink-guard, and write gates; and
- for plain-text labels/lightweight calls, apply the same byte/process bounds,
  then use the existing substantive-label parser and fallback behavior.

A nonzero exit, incomplete stdin write, malformed UTF-8, malformed/fenced/event
output, invalid Graphify shape, hollow response, timeout, interruption, or pipe
failure cannot create a clean cache or clean semantic marker.

### Process cleanup

Stdout and stderr are drained concurrently under one request deadline. On
success, failure, timeout, interruption, byte breach, or parser failure, the
adapter closes pipes, terminates any surviving process group/tree, reaps the
direct child, removes staged image bytes and temporary settings, and leaves the
parent Pi session untouched.

## Unavailable Metadata Contract

Pi print mode's supported contract provides final response text, not terminal
event metadata. Therefore:

- do not infer or claim actual provider, response model, token usage, reasoning
  usage, cache usage, or stop reason;
- do not treat requested model/thinking as actual response metadata;
- do not parse stderr or undocumented output for missing metadata;
- per-call Pi results omit provider/model/usage/stop fields and carry an explicit
  `usage_available: false` compatibility signal;
- aggregate Graphify token counters may count only reported usage. Pi-only
  operator output, reports, semantic markers, and cost tracking must display or
  persist `unavailable`, not claim zero actual usage; and
- elapsed wall time and requested backend/model/thinking may be recorded as
  Graphify-owned execution configuration, clearly distinguished from response
  metadata.

Canary attempt records likewise contain attempt number, completion/failure,
fixed failure code when applicable, elapsed wall time, and
`response_metadata_available: false`. Requested model/thinking belong only to
the campaign configuration. Receipts must not include fabricated actual
provider/model/usage/stop fields.

## Runtime Ownership

- `graphify/llm.py` owns Pi registration, requested model/thinking resolution,
  executable/capability checks, print invocation, final stdout/stderr bounds,
  strict final-response parsing, image staging, process cleanup, unavailable
  metadata signaling, and Pi serialization.
- `graphify/cli.py` owns image consent, cache-aware preflight, command-local
  backend/model selection, unavailable-usage presentation/persistence, and
  existing partial/write behavior.
- `graphify/report.py` owns truthful operator presentation of unavailable token
  usage.
- `graphify/__main__.py` owns help and doctor/probe presentation.
- `graphify/pi_canary.py` and `scripts/pi_backend_canary.py` own validation-only
  attempt reservation, stage sequencing, safe metadata-free receipts, and the
  pre-dispatch sixth denial.

## Existing Contracts That Remain Authoritative

- `extract_files_direct()` remains the semantic dispatch boundary.
- `_call_llm()` remains the plain-text boundary for labels and lightweight calls.
- `extract_corpus_parallel()` and `label_communities()` retain adaptive retry,
  merge, partial-result, and serialization behavior; Pi concurrency remains one.
- Extraction writes placeholder community names; `cluster-only` and `label`
  remain the separate naming owners. Label failure retains deterministic hub
  labels, does not persist placeholder-only labels, and does not retroactively
  mark extraction partial.
- Existing image partitioning, secure `_ImageRef` snapshots, source-identity
  guards, cache provenance, partial markers, shrink guards, and wiki gating are
  preserved.
- T-004's backward-compatible raster provenance is preserved. No general
  backend/model/thinking cache-key migration is added.
- `detect_backend()` continues to return Ollama in revision 8.

## Testing Strategy

### Focused fake-process tests

Deterministically cover:

- exact print argv and absence of JSON/RPC flags or fallback;
- prompt delivery through stdin and native staged image arguments;
- final response exact-limit acceptance and next-byte denial;
- total stderr exact-limit acceptance and next-byte denial;
- concurrent pipe draining, stalled stdin, timeout, interruption, process-tree
  cleanup, and temporary-state cleanup;
- strict Graphify JSON acceptance and rejection of JSONL/events, partial events,
  fences, prose, concatenated objects, malformed UTF-8, invalid shapes, hollow
  output, and nonzero exits;
- plain-text label behavior under print mode;
- explicit unavailable metadata in extraction, labels, doctor output, reports,
  semantic markers, cost tracking, ledger state, and canary receipts;
- image consent, secure staging, source replacement, pixel provenance, and
  cleanup; and
- unchanged automatic/explicit Ollama behavior with no Pi-to-Ollama fallback.

### Offline integration and regression tests

Revalidate source binding, adaptive splitting, cache writes, partial markers,
image provenance, graph publication, community labels, full Pi serialization,
campaign reservation, receipt sanitization, and explicit Ollama behavior. Run
one broader macOS offline regression gate before any renewed live campaign.

### Historical Renewed Live Validation Protocol

T-007 later ran under separate explicit Mase authority and consumed its full
five-call budget. The following is the executed protocol, not callable current
authority:

1. one text-only doctor probe;
2. one forced text-extraction chunk;
3. one text-label batch;
4. one forced authorized image-extraction chunk; and
5. one image-label batch.

Use `openai-codex/gpt-5.6-luna`, thinking `high`, API timeout 540 seconds,
Graphify output budget 32,768, the resulting 1 MiB final-response cap, disabled
Pi/Graphify retries, the committed public-safe text and diagram fixtures, and at
most one upload of the packet-hashed `diagram.png`. A failed attempt consumes
its reservation and stops the campaign. A reservation-only sixth check must fail
before child creation and is not a model attempt.

The live receipt proves requested configuration, stage outcomes, fixture hashes,
call count, score gates, image provenance, cleanup/isolation, and the sixth
denial. It does not prove unavailable actual response metadata.

## Boundaries

### Always required

- Use the installed Pi CLI and its existing authenticated session.
- Keep each Pi call ephemeral, serialized, tool/context/session free, bounded,
  and rooted in a controlled temporary project.
- Treat stdout, stderr, final model text, and parsed JSON as untrusted.
- Preserve fail-closed cache, retry, partial-marker, shrink, graph-publication,
  and wiki behavior.
- Preserve command-local explicit Ollama and Pi selection.

### Ask first

- Any Graphify/Pi live provider call, including the renewed T-007 campaign.
- Any automatic-default promotion or T-008 through T-013 work.
- Global Pi settings/auth changes, package/install changes, active CLI/global
  skill refresh, global-guide edits, commits, pushes, or propagation.
- Any corpus or image outside the exact public-safe packet fixtures.

### Never

- Extract or replay Pi OAuth tokens.
- Fabricate actual provider/model/usage/stop metadata.
- Parse stderr as undocumented metadata.
- Accept JSON-event/RPC fallback or partial event output as a final response.
- Silently downgrade images to filename-only clean semantics.
- Silently fall back from Pi to Ollama or another backend.
- Mutate global/target Pi settings for image delivery.
- Weaken tests, error handling, partial markers, provenance, or quality gates to
  manufacture success.

## Non-Goals

- Automatic Pi promotion in revision 8.
- Removing or rewriting Ollama.
- Automatic Pi-to-Ollama fallback.
- Generalizing a reusable multi-CLI framework.
- A broad cache migration.
- Repeating the Luna/DeepSeek quality campaign.
- Recovering unavailable print-mode event metadata.
- Installation, global changes, commits, pushes, releases, or propagation.

## Scenarios

### S-1 — Explicit text extraction

An operator runs `graphify extract <path> --backend pi`. One bounded print child
returns one valid Graphify JSON object. Graphify accepts the graph, records usage
metadata as unavailable, and preserves source binding and downstream behavior.

### S-2 — Explicit community labels

The operator runs `graphify cluster-only <path> --backend pi`. One bounded
plain-text print call per serialized label batch may replace deterministic hub
labels only with substantive output. Usage remains unavailable.

### S-3 — Authorized image extraction

With `--allow-image-upload`, Graphify securely stages the packet-hashed raster,
passes a native `@image` argument to the print child, validates final Graphify
JSON, records pixel-derived provenance, and cleans all temporary state.

### S-4 — Unauthorized or ambiguous image

Without consent, or with changed/unknown/reference-only image bytes, Graphify
performs no unauthorized fresh upload and fails or remains partial according to
existing rules. Proven local pixel-derived cache may be reused without upload.

### S-5 — Invalid final output

JSONL events, a partial event, prose, fences, concatenated objects, malformed
UTF-8/JSON, invalid Graphify shape, hollow output, output breach, timeout, or
nonzero exit fail closed and cannot create clean derived state.

### S-6 — Explicit Ollama and automatic default

Bare semantic commands continue to use Ollama. Explicit Ollama commands follow
the existing endpoint/model/retry/vision path without a Pi child. An explicit Pi
failure never launches Ollama automatically.

### S-7 — Renewed bounded campaign

After separate authorization, the five fixed stages use one ledger and stop on
any failure. A sixth reservation is denied before dispatch. Passing evidence
returns to Mase for a later CP-3 promotion decision; it does not promote Pi.

## Success Criteria

- **SC-1 — First-class explicit backend:** `pi` remains registered and usable
  explicitly for extraction, labels, help, and doctor/probe while Ollama remains
  automatic.
- **SC-2 — Subscription auth boundary:** Pi uses existing authentication without
  Graphify reading, printing, storing, or replaying credentials.
- **SC-3 — Isolated print transport:** Every Pi call uses final `--print` only,
  with no JSON/RPC fallback, under the exact isolation, byte, deadline, and
  cleanup contract above.
- **SC-4 — Text extraction:** The committed text fixture produces strict,
  non-hollow, source-bound Graphify JSON through the real print adapter.
- **SC-5 — Multimodal extraction:** With per-run consent, the committed diagram
  recovers its required concepts and directed branches through native staged
  attachments and records pixel-derived provenance.
- **SC-6 — Image privacy:** Unauthorized, changed, unknown-provenance, and
  reference-only image paths cannot appear as clean pixel-derived extraction.
- **SC-7 — Labels and serialization:** Explicit Pi labels remain substantive,
  command-local, hub-safe, and serialized within a Graphify command.
- **SC-8 — Failure semantics:** Missing capability/auth/model, nonzero exit,
  malformed or event-shaped final output, hollow response, stdout/stderr breach,
  timeout, and interruption fail deterministically and preserve existing
  adaptive retry, partial, cache, and write guards.
- **SC-9 — Truthful observability:** Graphify records elapsed wall time and
  requested configuration as its own facts, marks response metadata unavailable,
  and never fabricates actual provider/model/usage/stop data.
- **SC-10 — Promotion remains gated:** The separately authorized five-call
  campaign completed safely but failed the image semantic gate. CP-3 retained
  Ollama as automatic and Pi as explicit. Any later promotion requires a
  redesigned evaluation foundation and new reviewed evidence.
- **SC-11 — Ollama preservation:** `detect_backend()` remains Ollama; explicit
  Ollama behavior is unchanged; no silent fallback or command-to-command backend
  persistence is added.
- **SC-12 — Cache and consent:** Text and proven pixel-derived image cache remain
  backend-independent; fresh pixel transfer still requires consent; T-004
  provenance remains intact.
- **SC-13 — Proportionate proof:** Focused adapter tests, one broader offline
  regression gate, one fresh combined review, and at most one separately
  authorized five-attempt campaign are sufficient; no broad benchmark is rerun.

## Approval Boundary

The revision 8 implementation and separately authorized T-007 campaign are
complete and their authority is consumed. Mase separately authorized the local
closeout commit containing this work. No provider call, prompt/default change,
evaluation-redesign implementation, global edit, install, push, release, or
propagation authority carries forward.
