---
title: "Graphify Semantic CLI Reconciliation Recovery Plan"
kind: plan
status: ready-for-approval
audience: "agents-operators"
canonicality: canonical
created: 2026-07-13
updated: 2026-07-13
source_of_truth: "./graphify-semantic-cli-reconciliation-recovery-plan.md"
related:
  - "../../AGENTS.md"
  - "../mase-fork-operating-model.md"
  - "../../ARCHITECTURE.md"
  - "./graphify-upstream-reconciliation-readiness-plan.md"
tags:
  - graphify
  - upstream-reconciliation
  - semantic-extraction
  - cli
---

## Objective

Restore the fork-local fail-closed semantic-extraction contract after the
completed upstream rebase, without undoing upstream's `__main__.py` split into
`cli.py` and `install.py`.

The intended result is that the migrated CLI preserves `--allow-partial`,
semantic-marker, cache, graph/report/wiki, and monkeypatchable test-seam
behavior covered by the fork-local tests.

## Authority and Scope

This is an execution-ready plan, not approval to implement. Use `/build auto`
or an approved autonomous-build packet before mutating code. Local commits need
separate authorization; pushes are out of scope.

In scope:

- `graphify/cli.py`, `graphify/__main__.py`, and only the directly implicated
  support modules after evidence requires them.
- `tests/test_cli_semantic_fail_closed.py` and `tests/test_extract_cli.py`, plus
  focused test updates that express preserved behavior.
- Documentation/status updates caused by the repair.

Out of scope:

- Another upstream rebase, reset, rebase abort, pull, push, or broad formatting.
- Changes to Graphify's upstream CLI/install module split.
- Semantic model/prompt tuning, release intake, or consumer-repo propagation.
- Running Graphify extraction/update/hooks against this source repository.

## Verified Starting State

- Branch at planning time: `mase/local-fixes`, HEAD
  `5be2648cd743220dba8059600ef3ff08a3904338`.
- The completed rebase must be treated as a fixed baseline. Its compatibility
  repair is incomplete; a prior targeted run reported 15 failures concentrated
  in the two in-scope semantic/extract CLI suites. That result has **not** been
  revalidated at the formatting-only HEAD above.
- Historical pre-split behavior is available at `bbf7738` in
  `graphify/__main__.py`. The live implementation now belongs in
  `graphify/cli.py`; `graphify/install.py` owns installation/Codex activation.
- Preserve any worktree or stash state observed at execution start. In
  particular, do not apply/drop/replace existing stashes merely to simplify the
  repair.

## Module Boundary

`graphify/cli.py` owns argument parsing, extraction orchestration, marker
lifecycle, and report/wiki gating. `graphify/install.py` owns install and Codex
activation surfaces. `graphify/llm.py` owns extraction results and chunk
metadata. The repair may adapt calls across these boundaries, but must not copy
install behavior back into the CLI or re-consolidate the upstream split.

## Autonomous Execution Slices

### 1. Re-establish a trustworthy baseline

1. Run `git status --short --branch`, `git rev-parse HEAD`, `git diff --stat`,
   and `git stash list` before editing. If the branch, HEAD, dirty state, or
   target-test failures differ materially from the starting state, stop and
   reassess rather than applying this plan mechanically.
2. Run the two focused suites independently and save their exact failure names:

   ```bash
   uv run pytest tests/test_cli_semantic_fail_closed.py -q
   uv run pytest tests/test_extract_cli.py -q
   ```

3. Classify each failure as a missing migrated behavior, a stale test seam, an
   upstream intentional behavior change, or an unrelated regression. Do not
   weaken assertions to turn a behavior regression into a pass.
4. If a failure is outside the semantic CLI boundary or exposes an upstream
   behavior decision that cannot be inferred from tests/history, pause for an
   operator decision.

### 2. Map behavior, not files

1. Compare the relevant functions and parser branches in
   `git show bbf7738:graphify/__main__.py` with their current homes in
   `graphify/cli.py` and `graphify/install.py`.
2. Build a small failure-to-contract table before editing. It must cover:
   - fail-closed handling of failed, empty, or retry-exhausted fresh semantic
     chunks, including `partial_chunks` as a distinct degraded-output trigger
     even when `failed_chunks` is zero;
   - explicit `--allow-partial` override;
   - cache-write rules for degraded fresh output;
   - semantic-marker write, clear, and cache-only-clean lifecycle;
   - graph/report/wiki behavior when a marker is partial;
   - imports and monkeypatch seams used by the two focused test modules.
3. Use `git blame`, focused source reads, and test fixtures as evidence. Do not
   port entire historical blocks blindly: upstream may have moved or changed
   surrounding responsibilities.

### 3. Repair the smallest missing contract slices

Implement one logically independent failing contract at a time:

1. Restore parser/routing and dependency seams needed for the tests to exercise
   the migrated CLI.
2. Restore fail-closed extraction and cache behavior; retain the explicit
   `--allow-partial` escape hatch only where historical tests require it.
3. Restore marker lifecycle for fresh semantic, code-only, and cache-only runs.
4. Restore report/wiki suppression or override behavior for partial markers.
5. Add or adapt regression tests only when they document a verified contract
   missing from the migrated suite. Keep fixtures local and inert; no live LLM
   calls.

After each slice, run the smallest affected test selection before proceeding.

### 4. Validate the fork boundary end to end

Run, in order:

```bash
uv run pytest tests/test_cli_semantic_fail_closed.py -q
uv run pytest tests/test_extract_cli.py -q
uv run pytest tests/test_detect.py tests/test_hooks.py tests/test_install.py tests/test_cli_export.py tests/test_llm_backends.py tests/test_watch.py tests/test_cli_semantic_fail_closed.py tests/test_extract_cli.py tests/test_semantic_eval.py -q
```

Then run the repository's configured type check:

```bash
uv run pyright
```

Treat existing repo-wide pyright findings as diagnostic baseline noise; investigate
only new or changed findings attributable to this repair in touched files.

Review the diff to confirm that no install/Codex activation behavior moved back
into `cli.py` and no unrelated formatting or generated artifact entered the
changeset.

Only after the focused combined suite is clean and an operator authorizes it,
reinstall and verify the active CLI using the repository's required source
install command and:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

The reinstall is intentionally not automatic in this plan because it mutates
Mase's active tool environment.

### 5. Close the recovery before starting a fresh intake

- Update this plan's status and `.agent-skills/lifecycle-state.json` with the
  exact test evidence and residual risks.
- Record a concise operator briefing: repaired contracts, files changed,
  validation, active-install state, and whether the worktree is clean,
  committed/uncommitted, or pushed/unpushed.
- Do **not** begin the next upstream fetch/rebase as a continuation by default.
  The next move is Track B readiness/intake design or an explicit fresh intake
  only after this recovery is validation-clean.

## Acceptance Criteria

- The two focused semantic CLI suites pass without live provider access.
- The combined targeted regression command passes.
- Fail-closed behavior remains default; `--allow-partial` is explicit and does
  not allow degraded fresh output into semantic cache unintentionally.
- Partial markers protect wiki/report paths, while clean code-only and
  cache-only paths clear/rewrite stale partial state as the tests specify.
- The upstream `cli.py` / `install.py` responsibility split remains intact.
- No rebase/pull/push/reset or source-repo Graphify self-analysis occurs.
- Documentation, lifecycle status, and the operator briefing accurately state
  validation and active-install status.

## Risks and Stop Gates

- **Dirty/stale state:** stop if execution-start status differs from the recorded
  state; preserve rather than normalize it.
- **Historical drift:** historical `bbf7738` is behavioral evidence, not a
  patch source. Stop if its assumptions conflict with current upstream tests or
  architecture.
- **Test-seam mismatch:** do not make production dependencies globally mutable
  merely for tests; preserve existing injection/import patterns.
- **Validation failure:** do not proceed to active CLI reinstall, broad
  propagation, or a new rebase while the targeted suite fails.
- **Scope expansion:** defer general reconciliation-process changes to the
  companion plan; do not mix them into this compatibility repair.

## Definition of Done

This track is complete only with passing focused and combined regression
commands, reviewed boundary-preserving code, accurate lifecycle/doc status, and
an explicit decision on whether to reinstall the active CLI. A passing edit
without the combined suite is not complete.
