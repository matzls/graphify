---
title: "First-Class Pi CLI Print Transport Task Checklist"
kind: plan
status: done
audience: "agents-operators"
canonicality: derived
created: 2026-07-31
updated: 2026-08-05
source_of_truth: "./plan.md"
related:
  - "./plan.md"
  - "../SPEC.md"
  - "../docs/plans/autonomous-build-packets/graphify-pi-cli-backend-autonomous-build-packet.md"
revision: 8
---

> Derived checklist only. Scope, dependencies, acceptance criteria,
> verification, approval, and authority are defined exclusively in
> `tasks/plan.md` revision 8 and the linked revision 12 packet. Both execution
> authorities are now completed historical contracts.

## Planning And Approval Gates

- [x] Branch `mase/local-fixes`, HEAD
      `8cac3a75fb5d13b584dc2c31c673d22140158499`, clean index, and no active
      Git operation reverified.
- [x] Installed Pi usage, JSON-mode, and RPC docs rechecked: print returns a
      response and exits; JSON/RPC are event-stream transports.
- [x] Synthetic print feasibility receipt content, `0600` mode, and SHA-256
      `02148cc1426367b20872ba9bbe691de9e0a09db51881aff3bc581a4667f4d64c`
      reverified.
- [x] `SPEC.md` amended for final print response, strict JSON, exact raw byte
      bounds, unavailable metadata, Ollama preservation, and separate promotion.
- [x] Revision 8 plan drafted with r7 approval metadata cleared.
- [x] Revision 12 packet drafted from final r8 hashes with r11 approval/authority
      cleared.
- [x] One fresh linked workflow-plan review covers the exact r8/r12 package and
      has no unresolved blocker.
- [x] Mase explicitly approves the reviewed r8/r12 pair. Machine-readable plan
      and packet approval scopes cover only T-001, T-002, T-003, T-005, and
      T-006; live scope remains empty.
- [x] Mase separately activates offline implementation under revision 12.

## Offline Execution Order

- [x] **Pre-writer baseline** — `3912 passed, 7 skipped, 62 deselected`; one
      scoped r12 overlap archive and outside sentinels were recorded before the
      implementation writer started.
- [x] **T-001** — Replaced JSON events with final print response.
- [x] **T-002** — Enforced final bounds, cleanup, and truthful unavailable
      metadata.
- [x] **T-003** — Revalidated print-mode images and consent.
- [x] **CP-1** — `177 passed, 5 deselected`; Ruff, LSP, archive-diff, and both
      outside-sentinel checks passed with no live provider call.
- [x] **T-004** — Preserve existing raster cache provenance; no implementation
      edit. CP-2 must revalidate it.
- [x] **T-005** — Revalidated serial print-mode labels, hub fallback, command
      isolation, Ollama preservation, and unavailable usage.
- [x] **T-006** — Amended the campaign ledger, driver, and receipt for
      metadata-free print success, five reservations, and sixth denial.
- [x] **CP-2** — Focused `323 passed, 6 deselected`; related/Ollama
      `184 passed, 5 deselected`; broader `3926 passed, 7 skipped,
      62 deselected`; Ruff and targeted primary LSP passed; current Pi Lens
      delta was clean; archive, outside sentinels, path set, and empty index
      were reverified; fresh implementation review attempt 4 reported no
      blockers.
- [x] **Stop** — Offline execution stopped at
      `offline-ready-awaiting-separate-t007-authority`; activation granted no
      live call or image-upload authority.

## Separately Authorized Live Gate

- [x] **T-007** — One separately authorized campaign ran with exactly five Pi
      calls: doctor, text extract, text label, authorized image extract, and
      image label. All calls completed, but the campaign failed the image
      quality gate; the one-campaign authority is consumed and no retry, tuning,
      fixture substitution, or second campaign is authorized.
- [x] **Sixth denial** — The reservation-only additional request was denied
      before child creation.
- [x] **CP-3** — The sanitized metadata-free receipt passed local privacy and
      envelope assertions. Because T-007 failed, Ollama remains automatic and
      Pi remains explicit; stop without promotion.
- [x] **Evaluation audit** — Local adversarial checks and an independent Codex
      review found material scorer, fixture, gate, provenance, hyperedge, and
      repeatability defects. Current scores are diagnostic only.
- [x] **Prompt comparison** — A blind current-versus-pinned-upstream image A/B
      found a path-structure versus local-predicate tradeoff. Neither prompt was
      adopted.
- [x] **Ollama candidate comparison** — A bounded blind comparison retained
      `deepseek-v4-pro:cloud` as automatic default and rejected
      `deepseek-v4-flash:0731-cloud` as default because broader architecture
      recall came with privacy regressions, noise, and slower runtime.

## Blocked Stable IDs

- [ ] **T-008** — Automatic Pi promotion; not authorized. Reconsider only after
      the evaluation foundation is redesigned and new evidence is reviewed.
- [ ] **T-009** — Canonical Pi/Codex guidance; blocked on T-008.
- [ ] **T-010** — Generated Pi/Codex mirrors; blocked on T-009.
- [ ] **T-011** — Repository operator docs; blocked on promoted behavior.
- [ ] **T-012** — Translations/global guide; blocked on T-008 and separate
      global-edit authority.
- [ ] **T-013** — Promoted-default final validation; blocked on T-008 through
      T-012.

## Authority Boundaries

- [x] Pair approval alone does not start implementation; Mase supplied the
      separate activation instruction.
- [x] Offline activation permits one writer, no worktrees, exact packet paths,
      and at most five serial in-scope repair passes.
- [x] Track four non-borrowable review pools in lifecycle state: the exhausted
      five-attempt planning pool, the exhausted one-attempt Claude amendment
      pool, the three-attempt Codex recovery pool, and the reserved five-attempt
      read-only implementation-review pool.
- [x] Routine offline proof, fresh read-only review, mechanical in-scope fixes,
      receipts, checkboxes, and lifecycle updates proceeded without repeated
      human feedback after activation.
- [x] No material scope, transport, privacy, default, Ollama, live-budget, or
      authority change was made without renewed review and Mase approval.
- [x] No global edit, install, active CLI/global skill refresh, push, PR,
      publish, release, provider retry, or propagation occurred. The later
      project closeout separately authorized one local Smart Commit; it grants
      no install, push, or propagation authority.

## Final Outcome Checks

- [x] Explicit Pi extraction and labels use final `--print` only.
- [x] Event JSONL/partial events and malformed/fenced/multiple final objects fail
      closed.
- [x] Raw stdout/stderr exact limits and cleanup pass.
- [x] Pi response metadata is visibly unavailable, never fabricated.
- [x] Authorized diagram path retains pixel-derived provenance; no-consent and
      ambiguous-cache paths remain fail/partial.
- [x] Bare/explicit Ollama behavior remains unchanged and no Pi failure falls
      back automatically.
- [x] The final offline diff is separable from the one scoped pre-r8 overlap
      snapshot and contains only revision 12 paths.

## Next Lane

The Pi print-backend task is complete, live-reviewed, explicit, uninstalled, and
unpromoted. Retain `deepseek-v4-pro:cloud` as the automatic Ollama text default.

The next project iteration is **plan-only evaluation-harness redesign** through
`planning-and-task-breakdown`. A fresh session should first read
`.agent-skills/lifecycle-state.json`, `docs/semantic-model-quality-harness.md`,
and `docs/mase-fork-operating-model.md`, then draft a reviewable plan that
separates operational safety, semantic fidelity, and promotion readiness.

The planning scope should cover representation-aware branch and hyperedge
semantics, relationship meaning, grounded labels, claim-level provenance,
general hallucination precision, held-out fixtures, paired repeats, blinded
qualitative review, and non-compensating privacy/safety gates. This handoff does
not authorize implementation, prompt edits, provider calls, model/default
changes, installation, or promotion.
