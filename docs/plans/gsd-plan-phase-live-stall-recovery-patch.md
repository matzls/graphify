---
title: GSD Plan Phase Live-Stall Recovery Patch
status: draft
created: 2026-05-12
updated: 2026-05-12
---

# GSD Plan Phase Live-Stall Recovery Patch

## Problem

`gsd-plan-phase` documents fallback handling for spawned agents that return empty,
truncated, or unmarked output, but it does not document what the orchestrator
should do when a spawned researcher, planner, pattern mapper, or plan checker
remains live and stops producing a terminal result.

That leaves the operator to improvise. In the reported incident, the practical
recovery was to close stalled `phase_5_researcher` and `phase_5_plan_checker`
agents, then complete research/checking inline after local validation showed
`plan-artifacts-ok` and `state-ok`.

## Proposed Patch

Update `.codex/get-shit-done/workflows/plan-phase.md` with a runtime-neutral
recovery contract:

- Define a "live-stalled agent" as a spawned agent that remains running past the
  caller's wait budget without returning a recognized completion marker.
- Add a general recovery subsection near the agent-spawn contract, before the
  repeated spawn sites.
- Reuse it from all seven spawn sites: researcher, pattern mapper, planner,
  chunked outline planner, chunked single-plan planner, checker, and revision
  planner.
- Require artifact-first recovery:
  - inspect expected disk artifacts for the step
  - validate the artifact with the narrowest available check
  - close the stalled agent after deciding not to wait further
  - continue from validated disk state when safe
  - otherwise retry, stop, or complete a tightly bounded inline fallback
- Require an explicit deviation note in the final plan-phase closeout whenever
  recovery uses inline completion or accepts disk artifacts without a marker.

## Peer Review Disposition

Peer review returned `mixed` with five issues. Accepted changes:

- Define the wait-budget trigger instead of leaving it implicit.
- Address the partial-write race by requiring stable size / mtime checks before
  and after closing a stalled agent.
- Define inline fallback bounds: current artifact only, existing inputs only, no
  extra agents, no source edits, and same validation as recovered artifacts.
- Cross-check all seven `Agent(...)` sites in `plan-phase.md`: researcher,
  pattern mapper, planner, chunked outline, chunked single-plan, checker, and
  revision planner.
- Add scenario walkthroughs for researcher, planner, and checker recovery.

## Scope

In scope:

- Documentation-only patch to `plan-phase.md`.
- No behavior changes to Graphify source code.
- No changes to GSD agent implementations.

Out of scope:

- Building a new watcher or timeout runner.
- Changing Codex `spawn_agent` behavior.
- Creating new GSD state files.

## Validation

- Read the patched sections for consistency with existing marker fallback paths.
- Run a grep check for the new heading and spawn-site references.
- Cross-check all `Agent(...)` sites in `plan-phase.md` reference the recovery
  contract.
- Walk researcher, planner, and checker stall scenarios through the documented
  terminal states.
- Confirm `git diff --check` passes.

## Risks

- If the recovery contract is too broad, it could encourage accepting weak
  artifacts after a stalled agent. The patch should require narrow validation
  before continuing.
- If it is too specific to one incident, it will not help planner, checker, and
  pattern mapper stalls. The patch should be generic, with step-specific artifact
  examples.
