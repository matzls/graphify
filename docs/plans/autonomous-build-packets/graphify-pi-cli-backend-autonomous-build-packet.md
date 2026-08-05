---
title: "Autonomous Build Packet: Pi CLI Print Transport Amendment"
kind: plan
status: done
audience: "agents-operators"
canonicality: canonical
doc_id: "graphify-pi-cli-backend-autonomous-build-packet"
owners:
  - mase
created: 2026-07-31
updated: 2026-08-05
source_of_truth: "./graphify-pi-cli-backend-autonomous-build-packet.md"
revision: 12
approved_revision: 12
approved_by: Mase
approved_at: "2026-08-04T16:25:35Z"
approval_scope:
  - T-001
  - T-002
  - T-003
  - T-005
  - T-006
implementation_activation_required: true
implementation_activation_status: completed
governing_spec_status: implemented-explicit-unpromoted
governing_spec_sha256: "c5ff59f8b6ae2aeead74f8a65707cf9f4b1c35eb90784d473a69908f765d742c"
governing_plan_revision: 8
governing_plan_status: done
governing_plan_reviewed_sha256: "1103e612c6968586551eccbf074c6a230b3fa2b7750254612ed13abac9f70f22"
governing_plan_approved_sha256: "c55458d866da47668ce34e22ad8b28d365748a669de861e3c678e4b5331147df"
governing_todo_reviewed_sha256: "2230eb6576bbb8e6a25111757f4c16292bb2fb7821c7e17a4bf8bb1068b71b98"
linked_review_status: complete
planning_peer_review_call_limit: 5
initial_budget_amendment_review_call_limit: 1
codex_budget_amendment_recovery_call_limit: 3
implementation_review_call_limit: 5
implementation_repair_round_limit: 5
requested_scope:
  - T-001
  - T-002
  - T-003
  - T-005
  - T-006
live_scope_requested: []
related:
  - "../../../SPEC.md"
  - "../../../tasks/plan.md"
  - "../../../tasks/todo.md"
  - "../_peer-reviews/graphify-pi-cli-backend-autonomous-build-packet-peer-review.json"
tags:
  - graphify
  - pi
  - print-transport
  - autonomous-build
  - privacy
---

## Packet Status

Revision 12 is a completed historical execution packet. Its offline scope,
review pools, and repair envelope are exhausted or closed. The print-only Pi
backend is implemented and validated in source; a separately authorized live
campaign later verified transport and privacy controls but failed the image
semantic gate. Pi remains explicit, uninstalled from the current source commit,
and unpromoted. Ollama Pro remains automatic.

The next project iteration is **plan-only evaluation-harness redesign**. This
packet grants no redesign implementation, prompt edit, provider-call,
default-change, install, push, propagation, or promotion authority. Current
routing lives in `tasks/todo.md` and `.agent-skills/lifecycle-state.json`.

Revision 12 supersedes revision 11 in full. Revision 11's JSON-event transport,
terminal metadata requirements, JSONL limits, approval, repair authority, live
campaign authority, global-guide authority, and activation mechanics are
historical only and grant nothing to this packet.

Revision 12 was a linked draft derived from `SPEC.md` and `tasks/plan.md`
revision 8. Its historical bounded **offline** autonomous implementation
required two separate operator decisions:

1. Mase approves the freshly reviewed r8/r12 planning package; and
2. Mase later gives an explicit implementation activation instruction for r12.

Pair approval does not start implementation. Offline activation does not
authorize T-007, image upload, automatic promotion, global edits, installation,
commits, pushes, or propagation.

## 1. Objective

Replace the current Pi JSON-event adapter with final `pi --print` response
transport, prove the explicit Pi text/label/image/campaign paths offline, preserve
T-004 cache provenance and automatic/explicit Ollama behavior, and leave the
worktree in a reviewed offline-ready state for a separate T-007 decision.

Visible offline success means:

- T-001, T-002, T-003, T-005, and T-006 pass in dependency order;
- T-004 preservation regressions pass with no cache source edit;
- CP-1 and CP-2 pass, including one broader macOS offline regression gate;
- Pi uses final print only, strict final Graphify JSON, exact raw byte bounds,
  deterministic cleanup, and explicit metadata-unavailable reporting;
- image consent/provenance, label fallback/serialization, and the five-attempt
  ledger/sixth denial remain fail closed;
- Ollama remains the automatic backend and explicit Ollama remains unchanged;
- final diff review has no blocker and separates r12 changes from the one scoped
  pre-r8 overlap snapshot; and
- no live/provider call, promotion, global/install/commit/push/propagation side
  effect occurs.

## 2. Governing Linked Package

This packet is the single formal workflow-plan review target. Its frontmatter
binds the exact draft hashes of:

- `SPEC.md` r8 transport amendment:
  `c5ff59f8b6ae2aeead74f8a65707cf9f4b1c35eb90784d473a69908f765d742c`;
- `tasks/plan.md` revision 8:
  `1103e612c6968586551eccbf074c6a230b3fa2b7750254612ed13abac9f70f22`;
- `tasks/todo.md` derived revision 8:
  `2230eb6576bbb8e6a25111757f4c16292bb2fb7821c7e17a4bf8bb1068b71b98`.

One fresh `workflow-plan-gate` review must target this packet and explicitly
inspect all three bound inputs plus this packet. The review focus must cover:

- print-only transport, strict final response, byte/process cleanup, and
  unavailable response metadata;
- serial autonomy, the five-pass repair envelope, validation, and authority
  boundaries;
- privacy, native image consent, source identity, and T-004 cache provenance;
- automatic/explicit Ollama preservation and no fallback;
- the separately gated five-attempt T-007 envelope; and
- dirty-work separation through one scoped overlap snapshot rather than repeated
  whole-worktree baselines.

The existing r7 and r11 sidecars are historical and do not satisfy this gate.
Any bound-input change requires updating this packet, resetting approval, and
rerunning the one linked review.

## 3. Requested Offline Scope

### Execution Sequence

After separate implementation activation:

1. **Preflight:** verify approved hashes/Git state and create one scoped pre-r8
   overlap snapshot.
2. **Slice A:** T-001, T-002, T-003, then CP-1 focused validation.
3. **Slice B:** T-004 preservation checks, T-005, T-006, then CP-2 focused,
   related, broader offline, diagnostics, review, and scope validation.
4. **Closeout:** update status mirrors, report offline readiness, and stop before
   T-007 or promotion.

The governing plan's acceptance, near-miss, dependency, outcome, and verification
contracts remain binding. This packet narrows execution mechanics and authority;
it does not weaken r8.

### Exact Writer Allowlist

The single implementation writer may modify only:

```text
graphify/llm.py
graphify/__main__.py
graphify/cli.py
graphify/report.py
graphify/pi_canary.py
scripts/pi_backend_canary.py
tests/test_pi_cli_backend.py
tests/test_pi_canary.py
tests/test_image_vision.py
tests/test_labeling.py
tests/test_cli_semantic_fail_closed.py
tests/test_extract_cli.py
tests/test_report.py
```

The parent may make mechanical evidence-backed status updates only to:

```text
tasks/todo.md
.agent-skills/lifecycle-state.json
```

`tasks/plan.md`, this packet, and `SPEC.md` are frozen during implementation.
Reviewer output is inline/read-only; it must not create another writer path or
modify source/status files.

### Validation-Only Paths

The controller may read and run existing tests against, but must not edit:

```text
graphify/cache.py
tests/test_cache.py
tests/test_llm_backends.py
tests/test_ollama_retry_cap.py
tests/test_claude_cli_backend.py
tests/test_community_hub_labels.py
tests/test_semantic_eval.py
```

A required change to any validation-only or unlisted path is a stop gate, not an
in-scope repair.

### Out Of Scope

- T-007 execution and all Pi/backend/model calls.
- T-008 through T-013, automatic Pi promotion, generated guidance, repository
  docs, translations, or the external global guide.
- `graphify/cache.py` changes or any T-004 redesign.
- JSON-event/RPC fallback or reconstructed response metadata.
- Explicit Ollama runtime changes or automatic Pi-to-Ollama fallback.
- Windows runtime work.
- Global Pi settings/auth, packages, active CLI/global skills, installs,
  consumer repos, Graphify self-analysis, or hooks.
- Staging, commit, tag, push, PR, issue, publish, release, or remote-ref mutation.
- Reset, stash, revert, cleanup, formatting, or normalization of unrelated dirty
  work.
- Parallel writers or worktrees.

## 4. Current Baseline And Preflight

At draft time:

- repository: `/Users/mase/Codebase/Personal-Projects/graphify`;
- branch: `mase/local-fixes`;
- HEAD: `8cac3a75fb5d13b584dc2c31c673d22140158499`;
- index: clean;
- active Git operation: none; and
- worktree: intentionally large and dirty from the classified Graphify campaign.

Relevant source/test overlap already exists in the allowlist. The implementation
must preserve those current bytes and attribute only r12 changes. Do not use
r11's recovered whole-worktree baseline, reversible approval-byte
reconstruction, per-sidecar hash inventories, or repeated whole-worktree audits.

Immediately before activation, require:

```bash
test "$(pwd)" = "/Users/mase/Codebase/Personal-Projects/graphify"
test "$(git branch --show-current)" = "mase/local-fixes"
test "$(git rev-parse HEAD)" = \
  "8cac3a75fb5d13b584dc2c31c673d22140158499"
test -z "$(git diff --cached --name-only)"
```

Also require no merge, rebase, cherry-pick, revert, or sequencer operation;
valid approved r8/r12 hashes recorded in lifecycle state; the linked review
recorded for the exact reviewed draft hashes; explicit r12 implementation
activation; and no unexplained change to the exact writer-allowlist family after
approval.

Before the overlap snapshot or writer starts, run the same broader macOS offline
command used by CP-2:

```bash
uv run --frozen pytest tests/ -q -k 'not windows'
```

Record the exact command, exit status, and pass/skip/deselection summary in
lifecycle state as the pre-writer test baseline. A nonzero baseline stops for
Mase; it does not consume a repair pass. At CP-2, only newly failing tests may
enter the repair envelope. A failure already present in this baseline remains
outside r12 repair authority.

## 5. One Scoped Pre-r8 Overlap Snapshot

After activation preflight and the passing pre-writer test baseline, create one
private tar archive outside the repository. It contains the exact thirteen
implementation writer paths plus two text sentinels: (1) porcelain status for
paths outside the writer allowlist and the two mechanical status files, and (2)
the binary tracked diff for that same outside scope. Record one SHA-256 for the
single archive and its absolute path in lifecycle state. Do not create per-file
hash sidecars or a second digest.

Suggested bounded command shape, with `EXCLUDES` expanded to the thirteen writer
paths plus `tasks/todo.md` and `.agent-skills/lifecycle-state.json`:

```bash
SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/graphify-pi-r8-overlap.XXXXXX")"
EXCLUDES=(
  ':(exclude,top)graphify/llm.py'
  ':(exclude,top)graphify/__main__.py'
  ':(exclude,top)graphify/cli.py'
  ':(exclude,top)graphify/report.py'
  ':(exclude,top)graphify/pi_canary.py'
  ':(exclude,top)scripts/pi_backend_canary.py'
  ':(exclude,top)tests/test_pi_cli_backend.py'
  ':(exclude,top)tests/test_pi_canary.py'
  ':(exclude,top)tests/test_image_vision.py'
  ':(exclude,top)tests/test_labeling.py'
  ':(exclude,top)tests/test_cli_semantic_fail_closed.py'
  ':(exclude,top)tests/test_extract_cli.py'
  ':(exclude,top)tests/test_report.py'
  ':(exclude,top)tasks/todo.md'
  ':(exclude,top).agent-skills/lifecycle-state.json'
)
git status --porcelain=v1 --untracked-files=all -- . "${EXCLUDES[@]}" \
  > "$SNAPSHOT_DIR/outside-status.txt"
git diff --binary -- . "${EXCLUDES[@]}" \
  > "$SNAPSHOT_DIR/outside-tracked.diff"
tar -cf "$SNAPSHOT_DIR/pre-r8-overlap.tar" \
  -C "$SNAPSHOT_DIR" outside-status.txt outside-tracked.diff
tar -rf "$SNAPSHOT_DIR/pre-r8-overlap.tar" -C "$PWD" -- \
  graphify/llm.py \
  graphify/__main__.py \
  graphify/cli.py \
  graphify/report.py \
  graphify/pi_canary.py \
  scripts/pi_backend_canary.py \
  tests/test_pi_cli_backend.py \
  tests/test_pi_canary.py \
  tests/test_image_vision.py \
  tests/test_labeling.py \
  tests/test_cli_semantic_fail_closed.py \
  tests/test_extract_cli.py \
  tests/test_report.py
chmod 400 "$SNAPSHOT_DIR/pre-r8-overlap.tar"
shasum -a 256 "$SNAPSHOT_DIR/pre-r8-overlap.tar"
```

Each exclusion is a literal Git pathspec of the form
`:(exclude,top)<repo-relative-path>`. The controller prints and records the
expanded command before capture so an empty or malformed exclusion list cannot
silently widen or narrow the sentinel.

The controller records only:

- archive absolute path;
- one archive SHA-256;
- branch and HEAD;
- clean-index/no-active-operation result; and
- exact allowlist version `r12`.

At CP-1, CP-2, and closeout, compare current allowlist paths to the extracted
archive and inspect the new-only diff. Regenerate the two outside-scope sentinel
texts with the same printed exclusion list and require byte-for-byte equality to
the archived versions. Reuse the same archive/digest; do not create another
digest, rehash every worktree file, or recapture a baseline. Status-file changes
are reviewed separately as mechanical mirrors.

This sentinel detects new/removed outside status paths and tracked outside diff
changes. It does not claim byte-stability for an already-untracked outside file
whose path/status is unchanged; r12 makes no such closeout claim, and any
observed or tool-attributed touch to one remains a stop gate. A missing/changed
archive, sentinel mismatch, unseparable hunk, deletion, type/mode surprise, or
unlisted writer path stops the run. This is one scoped archive compared three
times, not r11's reversible approval reconstruction, per-file sidecars, or
repeated whole-worktree hash audit.

## 6. Authority Model

### Planning-Package Approval

Mase may approve the freshly reviewed r8/r12 pair. That approval allows only the
administrative approval transition described in Section 7. It does not launch a
writer or authorize implementation.

### Separate Offline Implementation Activation

After pair approval, Mase must separately instruct the agent to activate r12
offline implementation, for example by explicitly invoking `/build auto` for
this packet or saying to execute revision 12's offline scope. The activation
controller consumes this packet's exact five-task `approval_scope`, not the
plan's descriptive T-007 task or prose. Both plan and packet live-authority
fields remain empty. That activation allows:

- one serialized writer in the current checkout;
- tasks T-001, T-002, T-003, T-005, and T-006;
- T-004 preservation validation;
- CP-1 and CP-2 commands, targeted LSP/Pi Lens, and read-only review;
- at most five serial in-scope repair passes under Section 8;
- private local snapshot/validation evidence outside the repo; and
- mechanical todo/lifecycle updates supported by evidence.

It does not authorize T-007 or any other external/live/product provider call.
Fresh read-only implementation reviewers are workflow-validation substrate under
activation; they may inspect the exact diff and files but must not invoke Pi,
Graphify semantic backends, package managers, builds outside the named checks,
or mutate files.

### No Routine Reconfirmation Inside The Envelope

After explicit offline activation, the controller need not ask Mase again for:

- moving serially between T-001 through T-006 and CP-1/CP-2;
- running named offline tests, lint, LSP, Pi Lens, and read-only review;
- applying up to five accepted in-scope repair passes;
- rerunning affected offline checks after a repair;
- writing private local proof, safe review dispositions, checklist changes, or
  lifecycle status; or
- mechanical formatting/typing fixes confined to the exact writer allowlist and
  acceptance criteria.

Every stop gate remains binding.

### Authority Explicitly Not Requested

- Pi/provider/model calls or image upload.
- Automatic-default promotion or T-008 through T-013.
- Global edits, settings/auth, packages, installs, global skills, or consumers.
- Commit, push, PR, publish, release, or propagation.

## 7. Review, Approval, And Administrative Transition

### Linked Review Gate

Run one `workflow-plan-gate` review against this packet with the exact focus in
Section 2. The canonical sidecar is:

```text
docs/plans/_peer-reviews/graphify-pi-cli-backend-autonomous-build-packet-peer-review.json
```

Proceedability requires a sidecar for packet revision 12's exact draft hash, no
`BLOCK`, and no unresolved warning that makes offline activation unsafe. The
caller verifies and dispositions findings. Any substantive fix changes the
bound hashes and requires one fresh linked rerun. Historical r7/r11 review
claims remain unchanged but do not count.

### Approval Transition Without r11 Reconstruction

After Mase explicitly approves the reviewed r8/r12 pair, make only ordinary
administrative updates:

1. In `tasks/plan.md`, set `status: approved`, `approved_revision: 8`,
   `approved_by: Mase`, one UTC `approved_at`, and `approval_scope` to exactly
   `T-001`, `T-002`, `T-003`, `T-005`, and `T-006` in order. Preserve
   `live_scope_approved: []`. Replace the draft handoff with a concise approved
   handoff that preserves separate implementation and live authority.
2. In `tasks/todo.md`, change only derived approval/checklist status supported by
   the approval.
3. In this packet, set `status: approved`, `approved_revision: 12`,
   `approved_by: Mase`, the same `approved_at`, and `approval_scope` to exactly
   the offline requested scope `T-001`, `T-002`, `T-003`, `T-005`, `T-006`.
   Set `governing_plan_status: approved` and record the approved plan SHA-256 in
   `governing_plan_approved_sha256`. Keep
   `implementation_activation_status: pending`.
4. Record the reviewed spec/plan/todo/packet hashes, approved plan/packet hashes,
   sidecar path, reviewer provenance, approval time, and explicit statement
   `implementation not activated; T-007 not authorized` in lifecycle state.

Do not reverse/reconstruct draft bytes, create an approval receipt, duplicate
sidecar hashes across private files, or perform a whole-worktree hash audit. The
review sidecar remains evidence for the reviewed linked drafts; lifecycle state
records the bounded administrative transition and current approved hashes.

Any change beyond those fields/handoff/status mirrors is substantive and returns
to linked review before approval can stand.

### Peer-Review Call Budgets

Lifecycle state is the sole authoritative call-budget control; reviewer-local
historical round counters are not a gate. Every completed, failed, timed-out, or
started-then-aborted provider attempt consumes its named pool.

The four pools are independent and non-borrowable:

1. The original **five-attempt planning-review pool** is exhausted.
2. The separately authorized **one-attempt Claude budget-amendment pool** is
   exhausted. Its only attempt failed with `claude_session_limit` and produced
   no review findings.
3. Mase separately authorized up to **three explicit Codex budget-amendment
   recovery attempts**. Each completed, failed, timed-out, or
   started-then-aborted attempt counts. Stop after the first proceedable current
   sidecar; do not fall back to Claude or borrow from another pool. If all three
   fail to produce a proceedable current sidecar, stop for Mase.
4. Mase separately authorized up to **five read-only implementation-review
   attempts**. They remain reserved until explicit pair approval and separate
   offline activation. They may inspect the exact implementation diff and local
   files but must not mutate files or invoke Graphify/Pi semantic backends, live
   canaries, package managers, installs, commits, pushes, or propagation.

Unused calls in any pool grant no implementation, live, promotion, global,
install, commit, push, or propagation authority. Exhausting the implementation
review pool without the fresh proceedable review required by this packet stops
for Mase.

## 8. Bounded Repair Envelope

Offline activation includes at most **five serial repair passes total** across
the entire run.

A repair pass is permitted only when:

- a named offline test/diagnostic fails or the fresh reviewer reports a concrete
  issue that would make the approved acceptance criteria unsafe;
- the cause and fix remain within the current task, exact writer allowlist,
  r8 acceptance criteria, print-only transport, privacy boundary, T-004
  preservation, and Ollama behavior;
- no live/provider call, new fixture/corpus, global/install action, or product
  decision is needed; and
- the parent records the finding, accepted disposition, changed paths, and
  rerun checks before the writer proceeds.

Each pass may contain the smallest coherent set of related mechanical fixes.
After a pass, rerun the failed focused check, the owning task checks, and the
current checkpoint. A read-only re-review is required when the repair addressed
a review blocker or changed transport/privacy/cleanup behavior within the
already approved contract.

The following do not consume a repair pass:

- implementation work already required by an active task;
- rerunning a command unchanged to confirm a suspected flaky harness failure,
  at most once and only when no provider/live call is involved;
- status/checklist/lifecycle updates after evidence; or
- safe Markdown/typing/formatting cleanup in a touched allowlist file before a
  checkpoint reports a failure.

Stop for Mase when five passes are consumed, the same material failure remains,
a new path or acceptance criterion is needed, a reviewer blocker cannot be
closed within the envelope, or the fix would change scope, transport, privacy,
default behavior, Ollama, live budget, or authority.

## 9. Validation Contract

### Slice A And CP-1

Implement T-001 through T-003 with the governing plan's focused fake-process,
boundary, cleanup, metadata, and image tests. Run CP-1 exactly as specified in
r8. No Graphify/Pi backend call is permitted. Inspect the archive-relative
new-only diff and require both outside sentinels to match before continuing.

### Slice B And CP-2

Revalidate T-004 without a cache source edit, then implement/revalidate T-005 and
T-006. Run r8's focused and related commands, then exactly one broader offline
macOS gate:

```bash
uv run --frozen pytest tests/ -q -k 'not windows'
```

Also run targeted primary LSP diagnostics on every touched Python file,
`lens_diagnostics({ mode: "delta" })`, a fresh read-only combined review, the
archive-relative final allowlist diff, and both outside-sentinel comparisons.
Compare the broader suite to the pre-writer baseline; only new failures may
enter the repair envelope.

The combined reviewer must inspect:

- absence of JSON/RPC transport and fallback;
- final stdout/stderr exact limits, strict JSON, deadline, and cleanup;
- unavailable metadata across extraction, labels, doctor/report/marker/cost,
  ledger, and receipt;
- image consent, source identity, pixel provenance, and unchanged T-004 cache;
- attempt reservation, failure recording, receipt privacy, and sixth denial;
- automatic/explicit Ollama preservation; and
- test sufficiency and dirty-overlap separation.

### Final Offline Gate

Before closeout require:

- every requested task and CP-1/CP-2 check passed;
- no unresolved LSP/Pi Lens finding introduced or materially affected by r12;
- final reviewer has no blocker;
- the r12-attributable source/test delta is derived from and separable within
  the exact allowlist snapshot;
- both outside sentinels match their archived pre-writer text, while already-
  untracked outside file contents remain explicitly unverified unless their
  path/status changed or a tool touch was observed;
- todo/lifecycle changes are reviewed separately and are truthful mechanical
  status mirrors;
- `detect_backend()` still returns Ollama;
- no provider/live/global/install/commit/push/propagation side effect occurred;
  and
- no T-007 receipt or promotion claim was created.

If clean, status becomes `offline-ready-awaiting-separate-t007-authority`. Stop
and return control to Mase.

## 10. Separately Gated T-007 Envelope

This section defines a future decision; it grants no live authority.

A later explicit Mase authorization may allow one campaign only:

- maximum attempted Pi model calls: five;
- model request: `openai-codex/gpt-5.6-luna`;
- thinking request: `high`;
- API timeout per call: 540 seconds;
- Graphify output budget: 32,768;
- resulting final stdout cap: 1,048,576 bytes;
- retries: Pi and Graphify disabled;
- stages: doctor, text extraction, text label, image extraction, image label;
- image uploads: at most one, only the exact diagram below; and
- after five successful reservations, one reservation-only sixth denial before
  child creation.

A failed attempt consumes its reservation and stops the campaign. No automatic
retry, tuning, cap increase, fixture substitution, or second campaign is allowed.

Authorized fixture candidates and current draft-time SHA-256 values:

```text
e82b620b360cc91c8b1fd458a57b6f892a56e0940d1c0170f01b2e076f763221  tests/fixtures/semantic_eval/graphify_public_slice/architecture_excerpt.md
c7eb26d7f4736bbfe9b804df9a12306eb6a50922ff020629232d7eae380e9226  tests/fixtures/semantic_eval/graphify_public_slice/backend_excerpt.md
0be806da2552f56e53176d1cba7cb1829c6c591ad16d545ec15197822290a951  tests/fixtures/semantic_eval/graphify_public_slice/expected.json
91298a67d54dbe3cd9b2046c8b469dbfd06bb3d39cf2b2df5c80a0fad1074ca2  tests/fixtures/semantic_eval/graphify_public_slice/llm_backend_excerpt.py
26280cb35d39fa9597deef6f8c7629b6118cd7e3782d5e9b2ba485d41edc122c  tests/fixtures/semantic_eval/diagram_workflow/expected.json
0b6fb8f3736fd1f4a446d593409f7844d73a1680f9ec0680f61806f14d0c951e  tests/fixtures/semantic_eval/diagram_workflow/README.md
38180f8ddcf9234bfc8b928403654aadf7fee6aabde9d8241da430737d2395c2  tests/fixtures/semantic_eval/diagram_workflow/diagram.png
```

Every hash must be rechecked immediately before live dispatch. A mismatch stops
rather than refreshing authority. The sanitized receipt may include requested
configuration, fixture hashes, stage status, fixed failure codes, elapsed wall
time, scores, pixel provenance, outer-Pi detection/isolation, attempt count, and
sixth denial. It must carry `response_metadata_available: false` and omit actual
provider/model/usage/stop claims, prompt/response/stderr/byte payloads,
credentials, auth data, and session identifiers.

A passing receipt returns to Mase for a later CP-3 amendment. It does not activate
T-008 or promotion.

## 11. Orchestration Plan

The parent remains orchestrator, evidence owner, reviewer-triage owner, and final
decision-maker.

```text
approved linked r8/r12 package
  -> separate r12 offline activation
      -> parent preflight + broader test baseline + one scoped archive/digest
          -> one serialized writer for Slice A
              -> parent CP-1 focused validation
                  -> same writer for Slice B
                      -> parent CP-2 focused + broader offline validation
                          -> fresh read-only combined review
                              -> up to five total bounded serial repair passes
                                  -> final offline gate and scope review
                                      -> status mirrors
                                          -> stop before T-007
```

Writer/reviewer rules:

- exactly one writer in the current checkout; no worktrees;
- no child launches its own subagents;
- reviewers are fresh-context and read-only;
- the parent verifies reviewer findings before accepting a repair;
- no actor stages, commits, installs, or invokes a Graphify/Pi backend; and
- the parent, not a child, updates todo/lifecycle after evidence exists.

## 12. Stop Gates

Stop and ask Mase if:

1. branch, HEAD, clean index, Git-operation state, approved hash, linked review,
   or implementation activation is missing or differs;
2. the one overlap archive is missing/changed, either outside sentinel differs,
   or a new hunk cannot be separated from pre-r8 bytes;
3. a writer needs an unlisted or validation-only path, or any observed/tool-
   attributed write touches an already-untracked outside file;
4. print mode cannot satisfy strict final Graphify JSON/plain-text labels without
   JSON/RPC fallback;
5. unavailable metadata cannot be represented truthfully without broader
   cross-backend migration;
6. image consent, source identity, T-004 provenance, partial/cache/write gates,
   or outer-session isolation would weaken;
7. automatic/explicit Ollama behavior changes or fallback is proposed;
8. a test/reviewer issue requires more than five serial repair passes, remains
   after the fifth, or needs product/privacy/architecture judgment;
9. any live/provider call, image upload, fixture change, T-007 execution, cap
   tuning, retry, or promotion becomes relevant;
10. a global edit, setting/auth/package/install/skill/consumer mutation, commit,
    push, PR, publish, release, or propagation becomes relevant; or
11. r8/r12 requires a substantive post-review change.

## 13. Historical Completion And Authority Exhaustion

The packet's successful offline completion contract was:

- T-001, T-002, T-003, T-005, T-006, CP-1, and CP-2 are evidenced;
- T-004 preservation tests pass without a cache source edit;
- final review/scope checks pass;
- todo/lifecycle truthfully report
  `offline-ready-awaiting-separate-t007-authority`;
- all work remains uncommitted and unpushed;
- no live/global/install/promotion side effect occurred; and
- r12 offline implementation/repair authority is exhausted at closeout.

New authority is required for T-007, any further repair, T-008 through T-013,
global edits, install, active skill/CLI refresh, commit, push, or propagation.

On blocked/partial completion, preserve the safe worktree, mark only evidenced
items, report repair passes consumed, and identify the exact Mase decision
needed. Do not reset, hide, or normalize partial work.

## 14. Closed Approved Handoff

Revision 12 was approved by Mase at `2026-08-04T16:25:35Z` for T-001, T-002,
T-003, T-005, and T-006, with T-004 preservation-only. Mase separately activated
the exact offline implementation scope in the same instruction. The serialized
writer, five-pass repair envelope, and implementation-review pools are now
closed. T-007 later ran under separate consumed authority and stopped without
promotion. No implementation, live, install, push, propagation, or promotion
authority carries forward.
