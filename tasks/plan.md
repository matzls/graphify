---
title: "First-Class Pi CLI Print Transport Implementation Plan"
kind: plan
status: done
audience: "agents-operators"
canonicality: canonical
created: 2026-07-31
updated: 2026-08-05
source_of_truth: "./plan.md"
related:
  - "../SPEC.md"
  - "../docs/plans/autonomous-build-packets/graphify-pi-cli-backend-autonomous-build-packet.md"
  - "./todo.md"
tags:
  - graphify
  - pi
  - print-transport
  - semantic-backend
  - multimodal
  - privacy
revision: 8
approved_revision: 8
approved_by: Mase
approved_at: "2026-08-04T16:25:35Z"
approval_scope:
  - T-001
  - T-002
  - T-003
  - T-005
  - T-006
live_scope_approved: []
platform_scope: macos-only
windows_support: deferred
spec_status: implemented-explicit-unpromoted
spec_path: "../SPEC.md"
spec_sha256: "c5ff59f8b6ae2aeead74f8a65707cf9f4b1c35eb90784d473a69908f765d742c"
next_lane: "plan-only evaluation-harness redesign"
review_mode: linked-workflow-plan-gate
review_status: complete
planning_peer_review_call_limit: 5
initial_budget_amendment_review_call_limit: 1
codex_budget_amendment_recovery_call_limit: 3
implementation_review_call_limit: 5
implementation_repair_round_limit: 5
---

> Canonical revision 8 plan. It supersedes revision 7's JSON-event transport
> mechanics and approval state. `tasks/todo.md` is a derived checklist only.

## Completion And Supersession

Revision 8 and the linked revision 12 packet are completed historical execution
contracts. The final print-only Pi backend is implemented and offline-validated
in source; a bounded live campaign verified transport and privacy controls but
failed the image semantic gate. Later prompt and model comparisons found mixed
precision/recall tradeoffs, and an independent audit established that the
current scorer is diagnostic rather than promotion-grade.

Ollama Pro remains automatic. Pi remains explicit, uninstalled from the current
source commit, and unpromoted. The next project iteration is **plan-only
evaluation-harness redesign**. This completed plan grants no redesign
implementation, prompt edit, provider-call, default-change, install, or
promotion authority. Detailed task text below is retained as historical
execution rationale; current routing lives in `tasks/todo.md` and
`.agent-skills/lifecycle-state.json`.

## Goal

Replace Graphify's current Pi JSON-event adapter with one bounded final
`pi --print` response per request, revalidate text, labels, images, campaign
receipts, and cleanup, and stop before any live call or default promotion.
Ollama remains the automatic backend; Pi remains explicit.

## Observable Success State

An explicit `graphify extract <path> --backend pi` or explicit Pi label command
uses one isolated print-only child, accepts one bounded final response, and
fails closed on malformed/event-shaped output, subprocess failure, timeout, or
cleanup failure. Image pixels leave the machine only with command-local consent,
T-004 cache provenance remains intact, and unavailable print-mode response
metadata is represented as unavailable rather than fabricated. All focused and
broader offline checks pass before the controller stops for separate T-007 live
canary authority.

## Mental Model

- `graphify/llm.py` is the transport owner: it launches one isolated print child,
  bounds stdout/stderr, validates the final response, stages images, and cleans
  the process tree. It does not invent event metadata that print mode does not
  provide.
- `graphify/cli.py`, `graphify/report.py`, and `graphify/__main__.py` keep
  operator-visible usage/probe output truthful; `graphify/pi_canary.py` and the
  driver count attempts and receipts without claiming unavailable metadata.
- Revision 8 first repairs and proves the explicit Pi path offline. A separately
  authorized T-007 campaign may then produce evidence for Mase, but CP-3 still
  stops before T-008 or any automatic-default change.

## Accepted Direction And Current Evidence

Mase's current direction for this draft is:

- use final `pi --print` only;
- retain no JSON-event or RPC fallback;
- accept unavailable provider/model/usage/stop metadata and never reconstruct it;
- keep Ollama automatic and Pi explicit through `--backend pi`;
- preserve explicit Ollama behavior and prohibit automatic Pi-to-Ollama fallback;
- reopen T-001, T-002, T-003, T-005, T-006, and T-007;
- preserve T-004 cache provenance; and
- keep T-008 through T-013 blocked.

The installed Pi docs state that `--print` prints a response and exits, while
JSON mode emits all session events and RPC streams events over JSONL. The prior
public-safe diagnostic stopped at `output_stdout_stream` before a terminal
assistant event. The isolated synthetic print probe passed exact final JSON; its
sanitized `0600` receipt hashes to:

```text
02148cc1426367b20872ba9bbe691de9e0a09db51881aff3bc581a4667f4d64c
```

This is feasibility evidence only. Real Graphify extraction, labels, native
attachments, the revised bound, and renewed campaign remain unverified.

## Resolved Revision 8 Decisions

### D-1 — Final Print Transport Only

Use one subprocess per Pi request with `--print`, the existing isolation flags,
stdin prompt delivery, and native staged `@image` arguments. Do not pass
`--mode json` or `--mode rpc`; do not keep fallback parsers.

### D-2 — One Raw Final-Response Cap

For positive Graphify output budget `N`:

```text
final_response_limit = max(1_048_576, 16 * N) bytes
stderr_stream_limit  = 65_536 bytes
```

All bytes count. Exact-limit output is accepted; the next byte terminates and
reaps the child. There are no JSONL-record, assistant-delta, terminal-message,
or event-stream limits in the print adapter.

### D-3 — Strict Extraction JSON

After zero exit and complete bounded drain, decode stdout as strict UTF-8 and
parse the complete response with one `json.loads`. JSON whitespace is allowed;
prose, fences, JSONL/events, partial events, concatenated objects, and trailing
non-whitespace are rejected. Existing Graphify sanitization, schema, hollow,
source-binding, retry, partial, cache, shrink, graph-publication, and wiki gates
remain binding. Plain-text labels use the same process/byte bounds and their
existing substantive-label parser.

### D-4 — Metadata Is Explicitly Unavailable

Print mode does not supply supported terminal event metadata. Pi results and
receipts must not claim actual provider, response model, token usage, cache
usage, reasoning usage, or stop reason. Requested backend/model/thinking and
elapsed wall time may be recorded as Graphify-owned configuration/timing.
Operator output, reports, markers, cost tracking, and canary receipts must carry
an explicit unavailable signal rather than present compatibility zeroes as
actual usage.

### D-5 — Ollama Remains Automatic

`detect_backend()` continues to return Ollama. Revision 8 changes no explicit
Ollama request, endpoint, model, retry, vision, pricing, or fallback behavior.
A Pi failure never launches Ollama automatically.

### D-6 — One Later Five-Attempt Campaign, Separately Authorized

No prior T-007 authority carries forward. After CP-2 and separate explicit Mase
authorization, one campaign may attempt at most five Pi model calls: doctor,
text extract, text label, image extract, image label. It uses Luna/high, timeout
540 seconds, Graphify output budget 32,768, the resulting 1 MiB final-response
cap, the packet-hashed public fixtures, disabled retries, at most one authorized
image upload, and one reservation-only sixth denial before child creation.

## Scope And Responsibility Boundaries

### In Scope For Offline Implementation

- `graphify/llm.py`: print-only invocation, strict final response, raw byte
  bounds, cleanup, image staging, metadata-unavailable signaling, and Pi
  serialization.
- `graphify/__main__.py`: truthful Pi doctor/probe presentation.
- `graphify/cli.py` and `graphify/report.py`: truthful unavailable-usage
  aggregation, persistence, and operator presentation.
- `graphify/pi_canary.py` and `scripts/pi_backend_canary.py`: metadata-free
  attempt completion, exact stage sequencing, receipt safety, and sixth denial.
- The focused tests explicitly named in T-001 through T-006.
- Mechanical status updates to `tasks/todo.md` and
  `.agent-skills/lifecycle-state.json` after evidence exists.

### Preserved, Validation-Only Surfaces

- `graphify/cache.py` and T-004 raster provenance are not implementation targets.
- Explicit Ollama runtime code is not an implementation target.
- Current image source-identity/publication guards remain authoritative.
- T-008 through T-013 remain blocked and are not part of the revision 12 packet.

### Non-Goals

- Automatic Pi promotion or any default change.
- JSON-event/RPC fallback or recovery of event metadata.
- A general token/accounting schema migration for other backends.
- A reusable multi-CLI framework.
- Windows runtime support in this macOS-only packet.
- Global docs/settings/auth, installs, skills, commits, pushes, releases,
  Graphify self-analysis, or propagation.

## Authority And Stop Gates

Approval of this plan and the linked revision 12 packet records agreement with
the planning package only. It does not start implementation. A later explicit
implementation activation may authorize only the packet's offline serial scope.

Even after offline activation:

- the activation controller consumes revision 12's five-task packet
  `approval_scope`; this plan's `live_scope_approved` remains empty;
- T-007 requires separate explicit live-call and image-upload authority;
- CP-3 is evidence review only and cannot promote Pi;
- T-008 through T-013 require a later reviewed plan/packet amendment;
- global edits, installation, commit, push, and propagation remain unapproved;
- any fabricated metadata, JSON/RPC fallback, Ollama behavior change, broader
  path scope, or privacy-boundary change stops for Mase; and
- substantive r8/r12 changes invalidate review and approval.

## Dependency Graph

```text
reviewed and approved r8/r12 planning package
  -> separate offline implementation activation
      -> pre-writer broader offline baseline
          -> one scoped pre-r8 overlap snapshot
              -> T-001 print-only adapter
              -> T-002 bounds, cleanup, unavailable metadata
                  -> T-003 print-mode image revalidation
                      -> CP-1 focused explicit-Pi gate
                          -> T-004 provenance preservation check
                              -> T-005 label/serialization revalidation
                                  -> T-006 ledger/driver/receipt amendment
                                      -> CP-2 broader offline gate + review
                                          -> stop for separate T-007 authority
                                              -> T-007 one five-attempt campaign
                                                  -> CP-3 no-promotion decision
                                                      -> T-008..T-013 blocked
```

## T-001 — Replace JSON Events With Final Print Response

**Scope and responsibility boundary:** Change the Pi request/parser boundary in
`graphify/llm.py` and its fake-process contract in
`tests/test_pi_cli_backend.py`. Remove JSON-event/RPC parsing and fallback; do
not change automatic backend selection.

**Done when:** Explicit Pi extraction and plain-text calls use final `--print`
only and accept complete final output through Graphify's existing result shapes.

**Traceability:** SC-1, SC-2, SC-3, SC-4, SC-7, SC-8.

**Acceptance criteria:**

- [ ] Exact fake argv contains `--print` plus required isolation/model/thinking
      flags, contains no JSON/RPC mode, and sends source only through stdin.
- [ ] Extraction parses one complete strict Graphify JSON object; event JSONL,
      partial events, fences, prose, concatenated objects, malformed UTF-8/JSON,
      invalid shape, and hollow output fail closed.
- [ ] Plain-text Pi calls return bounded final text for existing label/lightweight
      parsers without treating thinking/event text as output.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_pi_cli_backend.py -k 'print or final_response or strict_json or jsonl or partial_event or invocation or plain_text'`
      — print-only argv and strict final-response cases pass.
- [ ] Bounded manual probe: inspect one fake child argv/env/stdin capture; source
      appears only on stdin and no JSON/RPC fallback path is reachable.

**Dependencies:** Separate offline activation and packet preflight.

**Dependency rationale:** Every later bound, image, label, and canary task relies
on one stable print request owner.

**Outcome/E2E:** A fake explicit Pi extraction returns a source-bound graph from
one final JSON response; the historical event stream is rejected.

**Near-miss checks:** One valid object plus a second object, one terminal newline
plus prose, and a JSON event object that is not a Graphify result all fail.

**Blockers/decisions:** None within the accepted print-only direction.

**Estimated scope:** M — one runtime owner and one dedicated contract suite.

## T-002 — Enforce Final Bounds, Cleanup, And Truthful Metadata

**Scope and responsibility boundary:** Enforce stdout/stderr/deadline/process
contracts in `graphify/llm.py`; present unavailable Pi usage truthfully through
`graphify/__main__.py`, `graphify/cli.py`, and `graphify/report.py`; update
focused cases in `tests/test_pi_cli_backend.py`,
`tests/test_cli_semantic_fail_closed.py`, `tests/test_extract_cli.py`, and
`tests/test_report.py`. Other backends retain their current numeric metadata.

**Done when:** Every Pi process outcome is bounded and cleaned, and no
operator/persisted surface claims zero or reconstructed event metadata as actual
Pi usage.

**Traceability:** SC-3, SC-8, SC-9, SC-13.

**Acceptance criteria:**

- [ ] `max(1_048_576, 16 * N)` stdout and 65,536-byte total stderr caps are
      incremental, accept the exact boundary, reject the next byte, and clean the
      process group/temp project on every outcome.
- [ ] Nonzero exit, incomplete stdin, malformed UTF-8, pipe failure, timeout,
      interruption, and lingering descendants fail with fixed safe diagnostics
      and cannot produce clean cache/marker state.
- [ ] Pi extraction, labels, doctor output, reports, semantic markers, and cost
      tracking expose `usage_available: false` or equivalent explicit unknown
      state; they omit actual provider/model/usage/stop claims and do not parse
      stderr for replacements.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_pi_cli_backend.py tests/test_cli_semantic_fail_closed.py -k 'bound or stderr or stdin or timeout or cleanup or process_group or metadata or usage'`
      — deterministic transport, cleanup, and fail-closed cases pass.
- [ ] `uv run --frozen pytest -q tests/test_extract_cli.py tests/test_report.py -k 'usage_unavailable or pi_metadata or cost or semantic_marker'`
      — persisted and rendered usage is explicitly unavailable rather than zero.
- [ ] Bounded manual probe: fake Pi emits exactly cap bytes and then cap-plus-one
      on stdout and stderr; only the former reaches validation and no child/temp
      state survives either run.

**Dependencies:** T-001.

**Dependency rationale:** Bounds and truthful downstream presentation must wrap
the final-response owner rather than recreate transport logic elsewhere.

**Outcome/E2E:** A successful explicit Pi extraction produces valid graph output
and an operator report that says usage metadata is unavailable; a timeout or
next-byte breach leaves no clean result.

**Near-miss checks:** Requested Luna/high is labeled requested configuration,
not actual response metadata; compatibility zero counters never render as actual
usage or cost.

**Blockers/decisions:** Stop if truthful unknown metadata requires a general
cross-backend schema migration beyond the named surfaces.

**Estimated scope:** L — eight tightly coupled runtime/test files across one
transport-observability boundary; broader refactoring is prohibited.

## T-003 — Revalidate Print-Mode Images And Consent

**Scope and responsibility boundary:** Revalidate existing consent, secure image
snapshot/staging, native attachment, source-identity, pixel provenance, and
cleanup through `graphify/llm.py`, `tests/test_pi_cli_backend.py`, and
`tests/test_image_vision.py`. `graphify/cache.py` remains unchanged.

**Done when:** An authorized fake print child receives only the secure staged
raster and returns strict Graphify JSON; unauthorized or changed image paths
cannot dispatch or become pixel-derived.

**Traceability:** SC-3, SC-5, SC-6, SC-8, SC-12.

**Acceptance criteria:**

- [ ] Consent produces a native absolute staged `@image` argument and only the
      temporary project permits image sending; cleanup removes staged bytes and
      settings after success/failure/timeout.
- [ ] No consent performs no fresh Pi dispatch, and source replacement before,
      during, or after staging remains partial/not pixel-cacheable.
- [ ] Pixel-derived provenance comes only from adapter-observed successful
      attachment delivery plus strict final Graphify JSON, never filenames or
      model text.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_pi_cli_backend.py tests/test_image_vision.py -k 'image or consent or attachment or source_identity or provenance or cleanup'`
      — print-mode attachment and privacy cases pass.
- [ ] Bounded manual probe: compare authorized and unauthorized fake argv/temp
      settings; only the authorized case contains the staged raster.

**Dependencies:** T-002.

**Dependency rationale:** Image proof must use the final bounded print process
before the preserved cache can trust successful pixel delivery.

**Outcome/E2E:** The fake diagram path yields strict Graphify JSON and
pixel-derived provenance with consent; the same cold path without consent makes
zero Pi calls.

**Near-miss checks:** SVG remains text, malformed/inaccessible/out-of-root images
are rejected, and global/target settings remain byte-unchanged.

**Blockers/decisions:** Any needed `graphify/cache.py` behavior change stops for
scope review; T-004 is preservation-only.

**Estimated scope:** S — existing adapter and two image-focused test owners.

## Checkpoint CP-1 — Focused Print Transport And Privacy Gate

Run after T-003, with no live provider call:

```bash
uv run --frozen pytest -q \
  tests/test_pi_cli_backend.py \
  tests/test_image_vision.py \
  tests/test_cli_semantic_fail_closed.py \
  tests/test_extract_cli.py \
  tests/test_report.py \
  -k 'not windows'
uv run --frozen ruff check \
  graphify/llm.py graphify/cli.py graphify/__main__.py graphify/report.py \
  tests/test_pi_cli_backend.py tests/test_image_vision.py \
  tests/test_cli_semantic_fail_closed.py tests/test_extract_cli.py \
  tests/test_report.py
```

Expected: exact print-only argv; strict final JSON; final stdout/stderr boundaries;
cleanup; no live call; no global/target mutation; no fabricated metadata; no
Ollama default change. Stop on any failure requiring a path or contract outside
T-001 through T-003.

## T-004 — Preserve Raster Cache Provenance

**Current state:** Preserved from revision 7; not reopened for implementation.

**Scope and responsibility boundary:** `graphify/cache.py` remains unchanged.
Run focused cache and integration regressions to prove print transport did not
weaken pixel-derived, reference-only, unknown, source-identity, or consent rules.

**Done when:** Existing T-004 tests remain green with no cache source edit.

**Traceability:** SC-6, SC-12.

**Acceptance criteria:**

- [x] Backward-compatible raster provenance exists in the current dirty campaign.
- [ ] Print-mode regression proves only proven pixel-derived cache satisfies Pi
      image capability; unknown/reference-only stays miss/partial.
- [ ] `--force` still requires fresh consent and cross-backend cache reuse is not
      described as fallback.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_cache.py tests/test_extract_cli.py -k 'semantic and (image or provenance or identity or legacy or force or partial)'`
      — preservation regressions pass.
- [ ] Bounded manual probe: synthetic pixel-derived/reference-only/unknown entries
      yield exactly one eligible Pi cache hit.

**Dependencies:** CP-1.

**Dependency rationale:** The transport must prove trusted delivery before the
existing cache eligibility contract is rechecked.

**Outcome/E2E:** Warm proven cache avoids upload; ambiguous cache cannot satisfy
an explicit Pi image run.

**Near-miss checks:** No source edit to `graphify/cache.py`; a failure that needs
one stops for Mase.

**Blockers/decisions:** Preservation failure outside the print adapter/test
surface is a stop gate.

**Estimated scope:** XS — validation only.

## T-005 — Revalidate Labels And Pi Serialization

**Scope and responsibility boundary:** Revalidate print-mode `_call_llm()`, label
batch serialization, deterministic hub fallback, command-local backend/model
selection, and unavailable usage through `graphify/llm.py`, `graphify/cli.py`,
`graphify/report.py`, `tests/test_labeling.py`, and
`tests/test_pi_cli_backend.py`.

**Done when:** Explicit Pi labels use bounded final text serially, substantive
labels may replace hubs, failures retain hubs, and usage is unknown rather than
fabricated.

**Traceability:** SC-1, SC-7, SC-8, SC-9, SC-11.

**Acceptance criteria:**

- [ ] Pi label batches run at concurrency one within a command and never invoke
      JSON/RPC parsing.
- [ ] Malformed, hollow, oversized, failed, or unsubstantive responses retain
      hub labels, do not persist placeholder-only sidecars, and do not alter
      extraction partial state.
- [ ] Explicit Ollama labels launch no Pi child; requested Pi model remains
      command-local; label usage renders unavailable in print mode.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_labeling.py tests/test_pi_cli_backend.py tests/test_cli_semantic_fail_closed.py tests/test_report.py -k 'label or serial or placeholder or hub or plain_text or usage_unavailable or command_local or ollama'`
      — label behavior, isolation, and presentation pass.
- [ ] Bounded manual probe: fake Pi tracks concurrent label children with
      requested concurrency eight; observed peak is one.

**Dependencies:** T-004 preservation check.

**Dependency rationale:** The renewed campaign needs both extraction and the
separate label owner on the final print transport.

**Outcome/E2E:** Fake explicit Pi extraction followed by explicit Pi labels
produces a graph and substantive names without claiming token metadata.

**Near-miss checks:** A placeholder cannot overwrite a hub; a later command does
not inherit the prior backend/model.

**Blockers/decisions:** None within named paths.

**Estimated scope:** M — existing label/adapter/presentation boundary.

## T-006 — Amend The Campaign Ledger, Driver, And Receipt

**Scope and responsibility boundary:** Update `graphify/pi_canary.py`,
`scripts/pi_backend_canary.py`, `graphify/llm.py`,
`tests/test_pi_canary.py`, and `tests/test_pi_cli_backend.py` so successful print
attempts complete without provider/model/usage/stop metadata while preserving
atomic pre-dispatch reservation and safe receipts.

**Done when:** Offline tests prove one five-attempt ledger, metadata-free success
records, exact fixture/stage planning, disabled retries, sanitized receipt, and
sixth denial before child creation.

**Traceability:** SC-8, SC-9, SC-10, SC-13.

**Acceptance criteria:**

- [ ] A completed attempt stores number/status, elapsed wall time, and
      `response_metadata_available: false`; failure stores a fixed payload-free
      code. No attempt stores fabricated actual provider/model/usage/stop data.
- [ ] Requested model/thinking exist only at campaign configuration/receipt
      level and are not labeled as actual response identity.
- [ ] One atomic counter reserves before the sole Pi `Popen`, counts failed or
      crashed attempts, rejects malformed/stale/exhausted state, and denies six
      without increment or child creation.
- [ ] Driver preflight proves the packet-hashed text and diagram fixtures fit one
      extraction chunk and one label batch per stage; fake execution writes only
      the sanitized revised receipt.

**Verification:**

- [ ] `uv run --frozen pytest -q tests/test_pi_canary.py tests/test_pi_cli_backend.py -k 'campaign or counter or reserve or sixth or metadata or receipt or dispatch or retry or print'`
      — reservation, receipt, and metadata-free completion pass.
- [ ] `uv run --frozen python scripts/pi_backend_canary.py --help`
      — help is inert and exposes an explicit live switch.
- [ ] Bounded manual probe: six concurrent reservation-only workers against one
      ledger yield five reservations and one pre-dispatch denial.

**Dependencies:** T-005.

**Dependency rationale:** The driver can safely plan live proof only after both
final print paths share one centralized dispatch and truthful metadata contract.

**Outcome/E2E:** Five fake Graphify commands share one safe ledger/receipt and a
sixth attempt cannot reach fake `Popen`.

**Near-miss checks:** Missing/incomplete environment is inactive or fails closed
as appropriate; wrong campaign, corrupt JSON, rollback, stale lock, and payload-
like metadata all fail.

**Blockers/decisions:** No live execution in this task.

**Estimated scope:** M — five files around one validation-only control boundary.

## Checkpoint CP-2 — Complete Offline Readiness Gate

First run focused and related suites:

```bash
uv run --frozen pytest -q \
  tests/test_pi_cli_backend.py \
  tests/test_pi_canary.py \
  tests/test_image_vision.py \
  tests/test_labeling.py \
  tests/test_cli_semantic_fail_closed.py \
  tests/test_extract_cli.py \
  tests/test_report.py \
  tests/test_cache.py \
  -k 'not windows'
uv run --frozen pytest -q \
  tests/test_llm_backends.py \
  tests/test_ollama_retry_cap.py \
  tests/test_claude_cli_backend.py \
  tests/test_community_hub_labels.py \
  tests/test_semantic_eval.py \
  -k 'not windows'
uv run --frozen ruff check \
  graphify/llm.py graphify/cli.py graphify/__main__.py graphify/report.py \
  graphify/pi_canary.py scripts/pi_backend_canary.py \
  tests/test_pi_cli_backend.py tests/test_pi_canary.py \
  tests/test_image_vision.py tests/test_labeling.py \
  tests/test_cli_semantic_fail_closed.py tests/test_extract_cli.py \
  tests/test_report.py
```

Then run the one broader offline regression gate:

```bash
uv run --frozen pytest tests/ -q -k 'not windows'
```

Also run primary LSP diagnostics on touched Python files and current-turn Pi Lens
diagnostics. A fresh combined read-only code review must inspect print transport,
privacy/image provenance, unknown metadata, ledger/receipt safety, Ollama
preservation, tests, and separation from pre-r8 dirty bytes.

Expected: all checks pass, review has no blocker, no live/model call occurred,
and the final diff is contained in the revision 12 write allowlist. After CP-2,
stop for separate T-007 authority.

## T-007 — Bounded Print-Mode Campaign Outcome

A separately authorized five-call campaign completed doctor, text extraction,
text labeling, consented image extraction, and image labeling. Transport,
privacy assertions, call accounting, cleanup, pixel provenance, and the
reservation-only sixth denial passed. The image semantic gate failed, so the
campaign stopped without retry, prompt tuning, fixture substitution, or
promotion. Its authority is consumed.

## Checkpoint CP-3 — Evidence Review, No Promotion

CP-3 retained Ollama as automatic and Pi as explicit. Subsequent bounded prompt
and model comparisons did not establish a generally superior prompt or backend.
The evaluator audit then blocked score-based promotion decisions. T-008 remains
unauthorized pending a redesigned evaluation foundation and later reviewed
evidence.

## Blocked Stable IDs T-008 Through T-013

The stable IDs remain reserved but are outside revision 8 implementation and
revision 12 authority:

- **T-008:** automatic Pi promotion — not authorized; reconsider only after the
  evaluation foundation is redesigned and new evidence is reviewed.
- **T-009:** canonical Pi/Codex guidance changes — blocked on T-008.
- **T-010:** generated Pi/Codex mirrors — blocked on T-009.
- **T-011:** repository operator documentation — blocked on T-008/T-009.
- **T-012:** translations and external global guide — blocked on separate global
  edit authority and promoted behavior.
- **T-013:** promoted-default final validation — blocked on T-008 through T-012.

No r7/r11 authority for these tasks carries into r8/r12.

## Success-Criterion Traceability

- **SC-1:** T-001, T-005.
- **SC-2:** T-001, T-002.
- **SC-3:** T-001, T-002, T-003.
- **SC-4:** T-001, T-007.
- **SC-5:** T-003, T-007.
- **SC-6:** T-003, T-004, T-007.
- **SC-7:** T-005, T-007.
- **SC-8:** T-001, T-002, T-003, T-005, T-006.
- **SC-9:** T-002, T-005, T-006, T-007.
- **SC-10:** T-006, T-007, CP-3.
- **SC-11:** CP-1, CP-2, T-005.
- **SC-12:** T-003, T-004, T-007.
- **SC-13:** CP-1, CP-2, linked review, T-007.

## Outcome Evaluation Scenarios

### OE-1 — Explicit Print Text And Labels

An operator explicitly selects Pi for the committed text fixture and later for
labels. One final response per request yields source-bound graph output and
substantive labels, while usage is visibly unavailable.

### OE-2 — Authorized Print Image

An operator explicitly selects Pi and consents to the committed diagram. The
native staged attachment yields required concepts/directed branches and
pixel-derived provenance with no global/target mutation.

### OE-3 — Consent And Cache Boundary

Proven local pixel-derived cache reuses without upload. Unknown, reference-only,
changed, or cold image paths cannot produce clean Pi image semantics without
fresh consent.

### OE-4 — Event And Process Failure

JSONL/partial events, malformed/fenced output, bounds, nonzero exit, timeout,
interruption, or cleanup failure remain partial/failed with no clean cache or
marker.

### OE-5 — Ollama Preservation

Bare and explicit Ollama extraction/labels follow the existing path and launch
no Pi child. Explicit Pi failure does not fall back.

### OE-6 — Metadata-Free Campaign Ceiling

Five fixed stages complete under one ledger without actual event metadata, and
request six is denied before dispatch. The receipt distinguishes requested
configuration from unavailable response metadata.

## Risks And Stop Conditions

- **False metadata:** Stop if any surface requires requested config or zeroes to
  be presented as actual provider/model/usage/stop data.
- **Transport drift:** Stop if final print output cannot satisfy strict Graphify
  JSON/plain-text label contracts without event/RPC fallback.
- **Bound mismatch:** A real T-007 response outside the reviewed cap fails the
  campaign; do not enlarge it during a live run.
- **Image ambiguity:** Only adapter-observed staged-pixel success may produce
  pixel-derived provenance.
- **Ollama drift:** Any automatic-default or explicit Ollama behavior change is
  outside r8.
- **Dirty overlap:** Stop if new work cannot be separated from the one scoped
  pre-r8 overlap snapshot or requires whole-worktree normalization.
- **Repair scope:** More than five packet-bounded serial repair passes or any
  path outside the r12 allowlist requires Mase.
- **Authority:** Stop for live calls, promotion, global edits, install, commit,
  push, or propagation without their separate authority.

## Linked Review And Approval Handoff

Revision 8 and revision 12 must receive one fresh linked workflow-plan review.
The revision 12 packet is the review target and binds the exact draft SHA-256 of
this plan, this spec amendment, and the derived todo. The review must inspect all
linked inputs and cover transport, autonomy/repairs, privacy/image consent,
cache provenance, Ollama preservation, renewed live budget, and dirty-work scope
separation. Historical r7/r11 reviews do not satisfy this gate.

The original five-attempt planning-review budget is exhausted. The separately
authorized one-attempt Claude budget-amendment pool is also exhausted: its only
attempt failed with `claude_session_limit` and produced no review findings.

Mase then authorized up to three explicit Codex budget-amendment recovery
attempts. Each completed, failed, timed-out, or started-then-aborted attempt
counts; stop after the first proceedable current sidecar, and do not fall back to
Claude or borrow from another pool.

Mase also separately authorized up to five read-only implementation-review
attempts. That reserve is usable only after explicit pair approval and separate
offline activation, cannot be borrowed for planning or amendment review, and
grants no implementation, live, promotion, global, install, commit, push, or
propagation authority. Lifecycle state tracks all four non-borrowable budgets
and is authoritative.

Revision 8 was approved by Mase at `2026-08-04T16:25:35Z` for T-001, T-002,
T-003, T-005, and T-006, with T-004 preservation-only. Mase separately activated
the linked revision 12 offline implementation in the same instruction. That
offline authority and all review/repair pools are now completed or closed. T-007
later ran under separate consumed authority and stopped without promotion. No
install, push, propagation, or redesign implementation authority carries
forward.
