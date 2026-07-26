---
title: "Portable Codex SessionStart Task Checklist"
kind: plan
status: approved
audience: "agents-operators"
canonicality: derived
created: 2026-07-26
updated: 2026-07-26
source_of_truth: "./plan.md"
related:
  - "./plan.md"
revision: 4
---

> Derived checklist only. Scope, acceptance criteria, dependencies, verification,
> approval, and execution authority are defined exclusively in
> `tasks/plan.md` revision 4.

## Planning And Baseline Gates

- [x] Operator-selected GPT-5.6-Sol X-HIGH review artifact is hash-fresh,
      blocker-free, and records the same-model substitution accurately.
- [x] Mase approved plan revision 4 with exact scope `T-001` through `T-004`
      at `2026-07-26T11:22:38Z`.
- [x] Preserved the pre-existing AST-identical `tests/test_hooks.py` formatting
      diff in separate local commit `0e210b2`.
- [x] Commit approved planning/governance artifacts separately so `/build auto`
      starts from a clean, attributable baseline.
- [x] Confirmed no active Git operation and no unrelated dirty files before the
      planning/governance commit.

## Approved Execution Order

- [x] **T-001** — Resolve no-path SessionStart at the current worktree root.
- [x] **T-002** — Add opt-in portable installation and strict CLI parsing.
- [x] **CP-1** — Verify the runtime and installation contract.
- [x] **T-003** — Preserve portable mode through reconcile and uninstall.
- [x] **CP-2** — Verify lifecycle safety and unrelated-config preservation.
- [x] **T-004** — Align documentation and prove the real portable path.
- [x] **Final gate** — Complete full validation, fresh review, and scope audit.

## Deferred And Separately Authorized

- [x] Active Graphify CLI reinstall and global Pi skill refresh; Graphify 0.9.26
      is source-verified and the installed core files and skill hash match this
      checkout.
- [ ] Second Brain regeneration, RQ6/clean-clone validation, and commit.
- [ ] Any additional downstream propagation, push, PR, publish, or upstream Git
      mutation.

## Next Lane

Portability implementation, active CLI/global Pi skill refresh, and the bounded
`pi-agent-skills` semantic propagation are complete. The reviewed seven-path
closeout packet is committed locally. Remain in `shipping-and-launch` for the
operator briefing. Second Brain regeneration/RQ6
work, any other propagation, additional commit, push, or PR remains separately
gated.
