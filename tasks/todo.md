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
- [ ] **T-002** — Add opt-in portable installation and strict CLI parsing.
- [ ] **CP-1** — Verify the runtime and installation contract.
- [ ] **T-003** — Preserve portable mode through reconcile and uninstall.
- [ ] **CP-2** — Verify lifecycle safety and unrelated-config preservation.
- [ ] **T-004** — Align documentation and prove the real portable path.
- [ ] **Final gate** — Complete full validation, fresh review, and scope audit.

## Deferred And Separately Authorized

- [ ] Active Graphify CLI reinstall and global skill refresh.
- [ ] Second Brain regeneration, RQ6/clean-clone validation, and commit.
- [ ] Any downstream propagation, push, PR, publish, or upstream Git mutation.

## Next Lane

After the canonical plan is approved and the baseline gates are clean, invoke
`/build auto` once for the exact pending task set. It may proceed between tasks
without routine confirmation but must stop on the canonical plan's blockers,
validation failures requiring judgment, scope changes, or protected actions.
