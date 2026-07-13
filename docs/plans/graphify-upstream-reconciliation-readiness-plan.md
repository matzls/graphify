---
title: "Graphify Upstream Reconciliation Readiness Plan"
kind: plan
status: ready-for-approval
audience: "agents-operators"
canonicality: canonical
created: 2026-07-13
updated: 2026-07-13
source_of_truth: "./graphify-upstream-reconciliation-readiness-plan.md"
related:
  - "../../AGENTS.md"
  - "../mase-fork-operating-model.md"
  - "../../ARCHITECTURE.md"
  - "./graphify-semantic-cli-reconciliation-recovery-plan.md"
tags:
  - graphify
  - upstream-reconciliation
  - readiness
  - fork-management
---

## Objective

Make upstream reconciliation a deliberate, evidence-backed process with a
mandatory **read-only intake/readiness phase** before any checkout, rebase, or
other worktree mutation. The process must expose a clear go/no-go decision,
separate upstream product adoption from fork-conflict resolution, and preserve
Mase's existing Codex/Pi/active-install safeguards.

## Decision Boundary

This is an execution-ready design plan, not approval to implement or reconcile
upstream. It must not be combined with Track A's semantic CLI recovery. Graphify
policy/documentation alignment may proceed as a separately approved low-risk
slice; any new enforcement code or mutation-path validation begins only after
Track A is validation-clean and via `/build auto` or an approved
autonomous-build packet. Local commits need separate authorization; pushes
remain out of scope.

The process target is **Git upstream reconciliation of this fork**, not the
existing one-repository command `graphify codex reconcile`. Do not overload or
rename the latter: it reconciles Codex activation surfaces and already follows a
separate dry-run/`--apply` contract. Also do not presume Graphify is the owner
of the reusable enforcement: identify Mase's canonical shared OSS fork-manager
surface before selecting a code home. Graphify should retain only its
project-specific overlay and, if needed, a thin adapter to that shared process.

## Verified Starting State

- The fork already documents release review, adoption categories, staged canary,
  and an operator briefing in `AGENTS.md` and
  `docs/mase-fork-operating-model.md`.
- Those requirements are policy-only today; a future agent can still start with
  fetch/rebase without proving a baseline, review range, local-patch decision,
  or explicit go/no-go.
- `graphify/adoption.py` and `graphify/install.py` demonstrate useful local
  patterns: audit/dry-run first, explicit mutation flags, bounded reports, and
  tests. They must be reused as patterns, not conflated with Git reconciliation.
- A previously completed rebase has unresolved semantic CLI validation. This is
  a hard prerequisite: do not implement or exercise a new reconciliation
  mutation path until Track A finishes cleanly.

## Target Operating Model

### Phase 0: explicit acquisition, separate from intake

Fetching changes remote-tracking refs and may use the network. It is not part of
read-only intake. The operator must explicitly request and report a fetch:

```bash
git fetch upstream
git remote set-head upstream -a
```

Record the old/new `upstream/v8` SHA, fetch time, and source remote. Do not
checkout, pull, rebase, or alter the worktree in this phase.

### Phase 1: default read-only intake/readiness

The default command/workflow must inspect the current worktree and supplied
upstream ref without changing files, refs, index, branch, stash, installed CLI,
or consumer repositories. It should emit human-readable Markdown and
machine-readable JSON to stdout; writing a durable intake artifact must require
an explicit output path.

Required evidence:

- branch, HEAD, remotes, dirty/staged/untracked state, `git stash list`,
  ahead/behind state, and existing rebase/merge/cherry-pick state;
- selected base and target refs/SHA, merge-base, commit range, changed files,
  and whether the target is a fast-forward/rebase candidate;
- baseline test command(s), result status, and a rule that unresolved failures
  are a no-go unless explicitly classified and accepted by Mase;
- release-tag range plus GitHub release URLs for operator review; offline intake
  may emit the range/URLs but must label release-note content unverified;
- local-patch inventory from `git diff <base>..HEAD`, historical local commits,
  and relevant plans/operator docs;
- a release-impact/adoption matrix for CLI, install/Codex/Pi skills, semantic
  refresh, cache/output IDs, watcher/hooks, optional extras, and generated
  artifacts;
- explicit decisions for every overlap: `keep`, `drop`, `adapt`, `defer`, or
  `reject`, with evidence/owner; and upstream feature leverage classification:
  `automatic`, `adapt`, `opt-in`, `defer`, or `reject`;
- a final `GO`, `NO-GO`, or `NEEDS-OPERATOR-DECISION` result with reasons.

A dirty worktree, unresolved baseline failure, absent release impact memo,
missing patch decision, stale target SHA, or incomplete approval is a no-go by
default. Intake must never treat its own report as approval to mutate.

### Phase 2: explicit mutation/apply

Only an explicit apply invocation may mutate the worktree. It must require a
fresh, complete intake artifact; exact expected HEAD and target SHA; an explicit
`--apply`; and an operator-confirmed decision. It must fail closed when any
precondition changed. It may then create a dedicated recovery branch/worktree or
perform the authorized rebase according to the artifact; the exact mutation
mechanism is a design decision to settle before implementation.

No command may silently fetch, stash, reset, discard changes, install a tool,
run a semantic refresh, or propagate to consumer repos.

### Phase 3: post-mutation validation and staged rollout

Require targeted regression validation, comparison of retained/adapted/dropped
patches, active-install verification only when authorized, adoption audit,
representative canaries, re-audit, and a non-silent operator briefing. Broad
propagation remains separately opt-in and must not use `extract --force` by
default.

## Autonomous Execution Slices

### 1. Identify the actual reusable owner before designing code

1. Inventory the global OSS fork-manager instructions, scripts, configuration,
   and tests named by the existing process. Determine whether a shared owner
   already has an intake/artifact format or mutation wrapper.
2. Record the ownership-discovery result before any Slice 2 work: `found shared
   owner`, `no shared owner—Graphify-only overlay approved`, or `new shared
   component explicitly approved`. Record its exact path and test command when
   found. Do not create a Graphify command merely because it is convenient.
3. Inspect `graphify/cli.py`, `graphify/adoption.py`, `graphify/install.py`,
   their CLI routing, and related tests only to identify Graphify-specific
   inputs/outputs. Keep Git mechanics and report serialization out of generic
   install/adoption modules. Do not add network scraping or LLM use.
4. Define how the operator records release-note review and patch decisions
   without pretending a local command verified GitHub content, and decide
   whether apply must only emit a guarded command or may ever invoke rebase.

### 2. Build deterministic read-only intake in the chosen owner

1. Implement pure data collection and rendering for git state, ref comparison,
   patch inventory, and preflight blockers in the canonical shared owner. A
   Graphify adapter is permitted only when it is needed to supply this fork's
   patch inventory or validation checklist. Use subprocess argument lists, not
   shell strings; redact remote credentials in rendered output.
2. Define an intake schema that records command versions, captured SHAs,
   timestamp, outcomes, report completeness, decision fields, and known
   limitations. Treat missing/invalid required fields as blockers.
3. Add a default dry-run command or script that cannot mutate. If an explicit
   `--output` writes an artifact, make it atomic and refuse to overwrite by
   default.
4. Add deterministic fixture-repository tests for clean/no-go states, dirty
   worktrees, stale/missing refs, in-progress Git operations, release-range
   rendering, missing decisions, and credential redaction. Tests must not fetch
   or contact GitHub.

### 3. Add a guarded application handoff

1. Implement only after the read-only contract and tests are accepted. Require
   a validated intake artifact, exact expected source/target SHAs, explicit
   `--apply`, and a current-state recheck immediately before mutation.
2. Make the default apply behavior emit a reviewed command or create an
   isolated worktree/branch only if the owner decision selects it. Do not
   automate a rebase in the first release merely because it is possible.
3. Block on dirty state, active Git operation, changed refs, failed baseline,
   incomplete decision matrix, or missing Mase approval. Surface one actionable
   reason per blocker.
4. Add synthetic Git fixture tests proving that dry-run never mutates and apply
   refuses every stale/unsafe condition. Test the approved happy path only in an
   isolated temporary repository.

### 4. Complete validation and operator workflow

1. Add/update `AGENTS.md` and `docs/mase-fork-operating-model.md` so the
   mandatory phases, no-go rules, shared-owner location, and distinction from
   `codex reconcile` agree with the selected command/script help text.
2. Add tests for command help, JSON contract, output-path safety, report
   completeness, and apply guards in the module that owns enforcement. Run the
   full affected owner/Graphify CLI suite plus the project regression suite
   named in Track A.
3. Run one inert canary against a throwaway Git fixture only. Do not fetch,
   rebase, reinstall the active tool, or propagate consumer repos as validation.
4. Require the final operator briefing to list release links, local-patch
   decisions, feature adoption status, validation, worktree/commit/push state,
   active-install state, and explicit opt-in commands where applicable.

## Acceptance Criteria

- A default reconciliation intake in the confirmed shared owner is read-only
  and reports a machine-checkable `GO`/`NO-GO`/`NEEDS-OPERATOR-DECISION` outcome.
- It cannot silently fetch, rebase, stash, reset, install, extract, or propagate.
- Incomplete evidence, dirty state, active Git operations, stale SHAs, and
  unclassified baseline failures block apply by default.
- Release-note review and patch/adoption decisions are explicit artifacts, not
  inferred from Git history or LLM output.
- Apply is opt-in, state-checked immediately before mutation, and safe-tested in
  fixture repositories before any real reconciliation uses it.
- Documentation consistently distinguishes upstream Git reconciliation from
  Codex activation reconciliation and staged consumer propagation.
- The existing Graphify CLI regression suite remains green, including Track A's
  semantic CLI coverage.

## Risks and Stop Gates

- **False assurance:** local Git evidence cannot verify release-note claims;
  require URLs and operator-reviewed memo fields rather than scraping or
  fabricating claims.
- **Over-automation:** a rebase is high impact. Start with guarded handoff or
  isolated-worktree capability, not an opaque one-command rebase.
- **Secret leakage:** redact credentials from remotes and do not embed private
  repository paths/content in reports beyond the local operator's chosen output.
- **Scope confusion:** never route this through `graphify codex reconcile`,
  adoption apply, or Graphify self-extraction.
- **Current validation debt:** Track A must be clean before this implementation
  begins; otherwise process work could falsely bless a broken baseline.

## Definition of Done

This track is complete only when the canonical shared owner is identified, the
mandatory intake contract and explicit mutation gate are implemented there (with
only necessary Graphify overlay), deterministic fixture coverage passes,
operator docs align, and the staged post-mutation workflow is reviewed. A
Graphify-only command or documentation-only reminder without enforceable
defaults does not meet the objective.
