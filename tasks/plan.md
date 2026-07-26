---
title: "Portable Codex SessionStart Installation Plan"
kind: plan
status: approved
audience: "agents-operators"
canonicality: canonical
created: 2026-07-26
updated: 2026-07-26
source_of_truth: "./plan.md"
related:
  - "../AGENTS.md"
  - "../ARCHITECTURE.md"
  - "../docs/mase-fork-operating-model.md"
  - "./todo.md"
tags:
  - graphify
  - codex
  - session-start
  - portability
  - local-fork
revision: 4
approved_revision: 4
approved_by: "Mase"
approved_at: "2026-07-26T11:22:38Z"
approval_scope:
  - T-001
  - T-002
  - T-003
  - T-004
spec_status: not-required
spec_rationale: >-
  This is a bounded maintenance fix to an existing local-fork installation and
  runtime contract. This plan carries the complete behavior, acceptance,
  boundary, and verification contract without introducing a new product
  capability or public data schema.
next_lane: "/build auto"
review_policy: "operator-selected-gpt-5.6-sol-xhigh-substitute"
opposite_review_status: "failed-to-run-session-limit"
---

> Canonical execution plan. The checklist view is `tasks/todo.md`; it does not
> define scope or authority independently.

## Goal

Make Graphify's repo-local Codex `SessionStart` activation optionally portable
across clone and worktree paths while preserving the current absolute-executable
installation as the unchanged default.

## Observable Success State

A maintainer can opt into a shareable Codex hook with any supported Codex
project-install entry point. The generated managed command is exactly
`graphify codex-session-start`, and that no-path runtime command resolves the
current Git worktree root from a repository subdirectory or linked worktree.
Default installs retain their existing absolute executable and explicit project
path, reconciliation does not silently downgrade an existing portable block,
and uninstall/idempotent reinstall continue to preserve unrelated Codex config.

## Mental Model

- The installer owns what command is persisted in `.codex/config.toml`: the
  default remains machine-specific and reliable, while `--portable` deliberately
  trades that reliability for a PATH-resolved, shareable command.
- The runtime command owns where the startup check runs: an explicit path remains
  authoritative, while no path means the current Git worktree root, falling back
  to the current directory outside Git.
- Reconciliation preserves the mode already chosen for an installed managed
  block; it does not invent portability for a missing installation.
- Revision 4 and task IDs `T-001` through `T-004` are approved and hash-reviewed;
  the next gate is the clean preparatory commit and status check before an
  explicit `/build auto` invocation.

## Requirements Basis

The defect and behavior contract were established through source inspection,
local subprocess probes, current Codex configuration documentation, and a live
upstream comparison. A separate feature specification is not required because
this plan fully defines the bounded maintenance behavior.

Current evidence:

- `graphify/install.py::_codex_session_start_block` always embeds the resolved
  Graphify executable and absolute project path.
- `graphify/cli.py` resolves a missing `codex-session-start` path as the process
  current directory, so invocation from a repository subdirectory checks the
  wrong location.
- The generic `install` parser rejects unknown options, but the platform-specific
  `graphify codex install` branch currently accepts arbitrary trailing options
  without validation.
- Upstream `v8` at `v0.9.26` has no equivalent SessionStart portability feature;
  this remains a local SessionStart defect with an upstream absolute-executable
  analogue.
- At planning intake, the only pre-existing worktree modification was an
  AST-identical formatting change in `tests/test_hooks.py`; it was preserved
  separately in local commit `0e210b2` before the planning/governance commit.

## Behavior Contract

### AC-001 — Absolute Default Is Unchanged

A fresh install without `--portable` must produce the same managed SessionStart
block as before this change: the resolved absolute Graphify executable followed
by `codex-session-start` and the resolved absolute project path. This is the
safe default for GUI and extension processes whose PATH may omit Graphify.

### AC-002 — Portable Command Is Exact And Opt-In

A supported install with `--portable` must write a managed TOML command whose
value is exactly:

```text
graphify codex-session-start
```

It must contain no executable path, project path, dot argument, shell wrapper,
or environment-specific prefix. Documentation must state that the Codex hook
process must be able to resolve `graphify` on PATH.

### AC-003 — Equivalent Codex Entry Points Agree

Portable mode must work for the direct Codex activation forms and every generic
project-install spelling already supported by the parser:

```text
graphify codex install --portable
graphify codex install --project --portable
graphify install --project codex --portable
graphify install codex --project --portable
graphify install --project --platform codex --portable
graphify install --project --platform=codex --portable
```

`--portable` may appear before or after the other valid options wherever the
existing order-independent generic parser permits. Parameterized tests must
cover positional platform selection before and after `--project`, separate
`--platform codex`, and `--platform=codex`. The corresponding generic
user-skill-only spellings without `--project` must reject `--portable` before
writing anything.

### AC-004 — Codex Parsing Fails Closed Without Broad Parser Reform

The direct `graphify codex install` parser must whitelist only `--project`,
`--portable`, and `-h`/`--help`; help prints Codex-specific usage and performs no
writes. Direct Codex uninstall must whitelist only `--project` and help, so
`--portable`, `--strict`, arbitrary trailing values, and unknown options fail
non-zero before mutation.

The shared generic `install` parser keeps its existing option and platform
behavior, adding only `--portable` collection plus post-parse validation that
the selected canonical platform is Codex and `--project` is present. Existing
unknown-option rejection and valid Claude `--strict` behavior remain unchanged;
this task does not reform other platform-specific parsers. Tests must explicitly
cover direct help, direct `--strict`, unknown options, uninstall, positional
Codex selection, `--platform codex`, `--platform=codex`, every non-project
Codex spelling, and a representative non-Codex rejection before writes.

### AC-005 — No-Path Runtime Is Git-Root-Aware

`graphify codex-session-start <path>` must retain explicit-path behavior.
Without a path, the command must resolve the current Git worktree root when run
from the root, a nested directory, or a linked worktree. Outside Git, it must
fall back to the resolved current directory. The command must keep returning
valid SessionStart JSON and exit zero when the notice calculation raises.

### AC-006 — Managed Config Remains Safe To Reapply And Remove

Reinstalling the same selected mode is idempotent. Explicitly running a portable
install may replace the managed path-bound block, and explicitly running the
default install may replace the managed portable block; unrelated TOML sections
and legacy-cleanup behavior remain untouched. Uninstall removes either managed
mode without deleting unrelated `.codex/config.toml` content or unrelated
`.codex/hooks.json` entries.

### AC-007 — Reconciliation Preserves Only Recognized Modes

Managed-block inspection must classify SessionStart as exactly one of:

- `missing`: neither Graphify managed marker appears anywhere in the config;
- `portable`: exactly one well-ordered marker pair encloses one decoded command
  equal to `graphify codex-session-start` with no extra command arguments;
- `path-bound`: exactly one well-ordered marker pair encloses a command that
  tokenizes to a Graphify executable, `codex-session-start`, and the current
  resolved project path, with no extra arguments; or
- `unrecognized`: any other marker topology or command shape, including only one
  marker, reversed or nested markers, duplicate marker pairs, any marker count
  other than one start plus one later end, an undecodable or untokenizable
  command, extra arguments, a stale checkout path, or a custom command.

`graphify codex reconcile --state active --apply` must preserve recognized
portable and path-bound modes even when another Codex surface forces
reinstallation. Missing SessionStart uses the unchanged path-bound default. An
unrecognized managed block is a manual-review state: dry-run reports it, and
apply exits non-zero before changing any Codex activation surface. Reconciliation
does not gain a portable flag or treat every non-portable marker block as the
default mode.

### AC-008 — Documentation And Help Match Shipped Behavior

Top-level help, install-specific help, direct Codex help, the README, this
fork's operating model, and repo-local operating notes must distinguish the
reliable path-bound default from opt-in portable mode and name the PATH
requirement. Help must present `codex-session-start [path]`, document portable
applicability, and remain mutation-free. No surface may describe portability as
automatic.

### AC-009 — Real Portability Path Passes End To End

A temporary repository installed in portable mode must keep working after its
managed config is used from a different checkout path. From nested directories
and a linked worktree, the no-path command must read the marker belonging to that
worktree root rather than the original install path or nested directory.

## Scope And Responsibility Boundaries

### In Scope

- `graphify/cli.py` owns no-path SessionStart target resolution and JSON output.
- `graphify/install.py` owns portable/default block generation, option plumbing,
  strict install parsing, managed-block replacement, uninstall, and reconcile
  mode preservation.
- `graphify/__main__.py` owns top-level CLI summaries;
  `graphify/install.py::_print_install_usage` and direct Codex dispatch own
  install-specific and mutation-free direct help.
- `tests/test_hooks.py` owns subprocess-level SessionStart, managed config,
  reconcile, uninstall, nested-directory, and linked-worktree regressions.
- `tests/test_install.py` owns equivalent install-entry-point and parser routing
  regressions.
- `README.md`, `docs/mase-fork-operating-model.md`, and `AGENTS.md` own the
  shipped and local-fork operator contract.

### Non-Goals

- Do not change the default to portable.
- Do not bootstrap, modify, or diagnose the Codex hook process PATH.
- Do not redesign other assistant hook installers or `_resolve_graphify_exe`.
- Do not change the SessionStart notice text, semantic refresh policy, or JSON
  schema.
- Do not add a portable option to `codex reconcile` or uninstall.
- Do not update translated READMEs in this local maintenance slice.
- Defer `/Users/mase/.codex/docs/reference/graphify.md`; its current policy makes
  no false portability claim, and synchronizing that external global guide
  requires separately approved global-governance scope.
- Do not fetch, merge, rebase, or otherwise reconcile upstream Git refs.
- Do not reinstall the active Graphify CLI or refresh global Pi/Codex skills.
- Do not regenerate or commit Second Brain configuration or graph artifacts.
- Do not push, create a PR, publish, or modify any downstream repository.

### Constraints

- Keep changes small and upstream-friendly on `mase/local-fixes`.
- Preserve unrelated `.codex/config.toml`, `.codex/hooks.json`, and `AGENTS.md`
  content through install and uninstall.
- Avoid reusable Git-root machinery beyond the existing owner unless tests prove
  that owner cannot satisfy nested and linked-worktree behavior.
- Keep one writer path during implementation; fresh reviewers may inspect but
  must not edit the same worktree.
- `/build auto` is commit-capable and should create one coherent local commit per
  task after its task-level validation passes. It never authorizes a push.

## Dependency Graph

```text
Pre-build baseline gate
  -> T-001 Git-root-aware runtime
      -> T-002 portable install and strict parsing
          -> T-003 reconciliation and lifecycle preservation
              -> T-004 docs, E2E, and final validation
```

T-001 establishes the runtime contract required by the command emitted in
portable mode. T-002 exposes that command through every supported installation
path. T-003 depends on the installed-mode representation introduced by T-002.
T-004 documents and validates the complete behavior only after code contracts
are stable.

## Pre-Build Readiness Gate

The plan may be approved before this gate is cleared, but `/build auto` must not
start until every item below is true:

- [x] The operator-selected GPT-5.6-Sol X-HIGH review artifact is fresh for the
      approved plan revision, records the plan SHA-256, and has no blocking
      issue. The failed opposite-model sidecar remains historical evidence of
      the unavailable preferred gate; it is not represented as passing.
- [x] Approval metadata names exactly `T-001`, `T-002`, `T-003`, and `T-004`.
- [x] The AST-identical pre-existing formatting diff in `tests/test_hooks.py` was
      preserved in separate local commit `0e210b2`.
- [x] Planning artifacts, lifecycle state, the failed opposite-model sidecar,
      and the operator-selected GPT review artifact are assigned to this clean,
      attributable planning/governance commit.
- [x] No implementation or ambiguous changes remain, and no merge, rebase,
      cherry-pick, or revert is active before the planning/governance commit.
- [x] No active-CLI reinstall, downstream rollout, push, or PR authority was
      inferred from plan approval or preparatory commit authority.

Disposition used: preserve the formatting-only test diff in local commit
`0e210b2`, then commit the approved planning/governance artifacts separately.
Mase explicitly authorized both preparatory local commits; neither commit grants
implementation or external-action authority.

## T-001 — Resolve No-Path SessionStart At The Current Worktree Root

**Scope and responsibility boundary:** Change the `codex-session-start` branch
in `graphify/cli.py` and its subprocess regressions in `tests/test_hooks.py`.
Reuse the existing Git-root owner in `graphify/hooks.py` through a lazy import;
do not change explicit-path behavior or other hook installation behavior.

**Done when:** A no-path SessionStart command reports freshness for the current
primary or linked worktree root from any nested working directory, with a cwd
fallback outside Git.

**Traceability:** AC-005, AC-009.

**Acceptance criteria:**

- [ ] Explicit-path output remains unchanged and valid JSON.
- [ ] No-path execution selects the primary or linked worktree root from a nested
      directory, and outside Git selects the resolved cwd.
- [ ] Notice exceptions remain fail-open as valid SessionStart JSON with exit
      code zero.

**Verification:**

- [ ] `uv run --frozen pytest tests/test_hooks.py -q -k 'codex_session_start'`
      — explicit, root, nested, linked-worktree, outside-Git, and exception paths
      pass.
- [ ] Bounded manual probe: create a temporary Git repo and linked worktree with
      distinct `graphify-out/needs_update` state, run the no-path module command
      from nested directories in each, and observe context from the correct root.

**Dependencies:** None.

**Dependency rationale:** This is the runtime prerequisite for any installed
portable command.

**Outcome/E2E:** An operator opens Codex from a nested directory in a linked
worktree; SessionStart checks that worktree's pending marker rather than the
primary checkout or nested directory.

**Near-miss checks:** An explicit path must override cwd/Git discovery, and a
non-Git directory must not fail or search a parent unrelated to cwd.

**Blockers/decisions:** None after the pre-build baseline gate.

**Estimated scope:** S — two files and one existing command branch.

## T-002 — Add Opt-In Portable Installation And Strict CLI Parsing

**Scope and responsibility boundary:** Add the selected portable/default mode to
managed block generation and install routing in `graphify/install.py`; update
routing regressions in `tests/test_install.py`, config assertions in
`tests/test_hooks.py`, top-level help in `graphify/__main__.py`, and
install-specific help in `graphify/install.py`. Fully parse direct Codex
install/uninstall arguments, but do not reform other platform parsers or change
executable resolution.

**Done when:** Every direct and generic Codex project activation spelling emits
the same exact portable command when requested, default output remains
byte-for-byte compatible, direct Codex help is mutation-free, and the bounded
invalid-option envelope fails before filesystem writes.

**Traceability:** AC-001, AC-002, AC-003, AC-004, AC-006, AC-008.

**Acceptance criteria:**

- [ ] Default and portable managed blocks match AC-001 and AC-002 exactly, and
      same-mode reinstall is idempotent while preserving unrelated TOML.
- [ ] Direct Codex activation and all positional, `--platform`, and
      `--platform=` generic project forms accept `--portable` in valid option
      orders and produce equivalent managed config.
- [ ] Direct Codex parsing and generic portable validation match AC-004, including
      mutation-free help and negative cases, while unrelated platform parsing
      behavior stays unchanged.

**Verification:**

- [ ] `uv run --frozen pytest tests/test_install.py tests/test_hooks.py -q -k 'codex and (install or uninstall or session_start or help)'`
      — install modes, the full alias matrix, idempotency, help, preservation,
      uninstall, and parser negatives pass.
- [ ] Bounded manual probe: install each valid portable form in a separate
      temporary repo, inspect the managed TOML command, and observe exactly
      `graphify codex-session-start` with no checkout path.

**Dependencies:** T-001.

**Dependency rationale:** The portable block deliberately omits a target path,
so its emitted command is only usable after no-path runtime resolution works.

**Outcome/E2E:** A committed `.codex/config.toml` contains no source checkout or
executable path and behaves identically regardless of which supported install
entry point generated it.

**Near-miss checks:** Reject every positional/`--platform`/`--platform=` generic
non-project Codex portable form, representative non-Codex portable forms,
direct Codex `--strict`, Codex uninstall `--portable`, trailing positional
values, and arbitrary unknown direct Codex options without leaving partial
files.

**Blockers/decisions:** None after T-001.

**Estimated scope:** M — four files across block generation, CLI routing, help,
and focused tests.

## Checkpoint CP-1 — Runtime And Installation Contract

After T-002, stop the auto run if either focused suite fails, if default managed
output changed beyond the new option plumbing, or if any invalid-option case
writes a partial activation surface. Record the exact test commands and results
in the T-002 commit.

## T-003 — Preserve Portable Mode Through Reconcile And Uninstall

**Scope and responsibility boundary:** Add the four-state managed-mode classifier
from AC-007 and use it during reconciliation in `graphify/install.py`; add
lifecycle and malformed-block regressions in `tests/test_hooks.py`.
Reconciliation may inspect the Graphify marker-owned block but must not infer a
mode from markers alone or parse/rewrite unrelated TOML ownership.

**Done when:** Active reconciliation repairs adjacent Codex drift without
changing a recognized portable or path-bound mode, missing SessionStart still
receives the path-bound default, unrecognized blocks stop before mutation, and
uninstall removes either recognized mode safely.

**Traceability:** AC-006, AC-007.

**Acceptance criteria:**

- [ ] Forced active reconciliation preserves a portable block and separately
      preserves a path-bound block; missing SessionStart installs the unchanged
      path-bound default.
- [ ] Start-only, end-only, reversed, nested, and duplicate marker layouts, plus
      malformed commands, stale checkout paths, extra arguments, and custom
      marked commands, classify as unrecognized. Dry-run reports manual review,
      and apply exits non-zero before any activation write.
- [ ] Portable and path-bound uninstall remove only the managed block and legacy
      Graphify hook-check entries while retaining unrelated config; repeated
      recognized operations remain idempotent.

**Verification:**

- [ ] `uv run --frozen pytest tests/test_hooks.py -q -k 'codex_reconcile or codex_install or codex_uninstall'`
      — lifecycle mode preservation, four-state classification, unrecognized
      fail-closed behavior, and unrelated-content assertions pass.
- [ ] Bounded manual probe: create a portable block plus missing `AGENTS.md` to
      force active reconcile, apply it, and confirm the command stays exact and
      portable.

**Dependencies:** T-002.

**Dependency rationale:** Reconciliation can preserve a portable mode only after
the installer has a defined representation and mode-aware write path.

**Outcome/E2E:** An adoption or reconciliation repair may restore missing
activation surfaces without reintroducing the original checkout path into a
shareable config.

**Near-miss checks:** Missing must not become portable implicitly; unrecognized
must not be coerced to path-bound or rewritten; a recognized portable block must
not cause unrelated SessionStart hooks to be removed or rewritten.

**Blockers/decisions:** None after T-002.

**Estimated scope:** S — two files within the existing reconciliation owner.

## Checkpoint CP-2 — Lifecycle Safety

After T-003, require focused lifecycle tests to pass and inspect the generated
TOML from portable, absolute, reconciled, and uninstalled scenarios. Stop if an
unrelated hook or TOML section changes.

## T-004 — Align Documentation And Prove The Real Portable Path

**Scope and responsibility boundary:** Update `README.md`,
`docs/mase-fork-operating-model.md`, and `AGENTS.md`; run final source, docs,
regression, and end-to-end validation. Do not reinstall the active CLI or touch a
downstream repo.

**Done when:** Operators can choose the correct install mode from current docs,
and the complete clean-clone/nested-directory/linked-worktree contract passes
without environment or downstream mutation.

**Traceability:** AC-008, AC-009 and final coverage of AC-001 through AC-007.

**Acceptance criteria:**

- [ ] Help and docs state `codex-session-start [path]`, the exact portable
      command, every direct/generic project entry-point family, the unchanged
      path-bound default, and the PATH tradeoff without implying an automatic
      migration.
- [ ] Focused, full-suite, lint, language-server, and current-turn diagnostics
      are clean or any pre-existing limitation is explicitly reported.
- [ ] A temporary clean-checkout scenario proves portable config contains no old
      path and resolves root-specific pending state from nested and linked
      worktree directories.

**Verification:**

- [ ] `uv run --frozen pytest tests/test_hooks.py tests/test_install.py -q`
      — all directly affected tests pass.
- [ ] `uv run --frozen pytest tests/ -q --tb=short` — the repository test suite
      passes.
- [ ] `uv run --frozen ruff check graphify/install.py graphify/cli.py graphify/__main__.py tests/test_hooks.py tests/test_install.py`
      — touched Python files satisfy the configured lint floor.
- [ ] `uv run --frozen pyright graphify/install.py graphify/cli.py graphify/__main__.py tests/test_hooks.py tests/test_install.py`
      — either exits zero or exits non-zero with exactly the four pre-existing
      `reportOperatorIssue` diagnostics at the existing `out2` membership
      assertions in `tests/test_install.py` (line-number drift is allowed). Any
      additional diagnostic, changed rule, or diagnostic outside those
      assertions blocks completion; repairing that baseline is not authorized
      implicitly.
- [ ] `lsp_diagnostics` on touched Python files and `lens_diagnostics` in current-
      turn mode report no unresolved current-change errors or practical warnings.
- [ ] Bounded E2E probe: first verify
      `.venv/bin/graphify doctor --require-source "$(pwd)"`, then prefix the
      source checkout's `.venv/bin` on PATH explicitly. Commit portable config in
      a temporary consumer repo, clone it to a different path, create a linked
      worktree, set root-distinct pending markers, and execute the bare installed
      command from nested directories. Observe valid JSON from the correct root
      and record the resolved Graphify source identity.

**Dependencies:** T-003.

**Dependency rationale:** Documentation and final E2E proof must describe and
exercise the stable complete lifecycle, not an intermediate implementation.

**Outcome/E2E:** A clean clone at a path unrelated to the installer machine can
run the committed portable SessionStart command and receive the correct
repository-specific freshness context.

**Near-miss checks:** The E2E probe must also prove the default config still
contains its absolute path, outside-Git no-path fallback works, and unrelated
Codex config survives install/uninstall.

**Blockers/decisions:** Active CLI reinstall and Second Brain rollout are
explicitly deferred and must not be used as validation in this task.

**Estimated scope:** M — three documentation files plus bounded whole-change
validation.

## Final Validation And Outcome Gate

The implementation is complete only when:

- all task and checkpoint commands meet their stated expected result, including
  the explicitly bounded Pyright baseline outcome;
- the temporary clean-clone and linked-worktree scenario satisfies AC-009;
- exact generated commands have been inspected for both default and portable
  modes;
- the final diff contains only approved task files and task-status updates;
- a fresh-context code review reports no blocker;
- task commits are local and unpushed; and
- the active CLI, global skills, Second Brain, and every other downstream repo
  remain unchanged.

Outcome evaluation scenario: a maintainer opts into portable config in one
checkout, commits it, and another checkout starts Codex from a nested linked
worktree. Success means the bare PATH-resolved Graphify command returns valid
SessionStart JSON for that worktree's pending semantic state, with no original
absolute path in the committed config.

## Risks And Stop Conditions

- **PATH absence:** Portable mode can fail if Codex cannot resolve `graphify`.
  Keep it opt-in, document the tradeoff, and do not add fallback shell wrappers.
- **Parser regression:** Shared install dispatch serves many platforms. Stop if
  a non-Codex route changes or accepts `--portable`, or if direct Codex help
  writes activation files.
- **Silent mode downgrade:** Reconciliation currently rewrites the managed block
  when other drift exists. Stop if a recognized portable command becomes
  absolute without an explicit default install.
- **Config ownership damage:** Stop on any change to unrelated TOML hooks,
  comments, or hooks JSON content.
- **Dirty baseline absorption:** Stop before staging if the pre-existing
  formatting diff or planning artifacts are not separately attributable.
- **Scope expansion:** Stop for any requirement to change hook payload semantics,
  other platform installers, active installs, downstream repos, or upstream Git
  state.
- **Validation failure requiring judgment:** Use the debugging lane and return to
  Mase rather than broadening the fix or weakening tests.

## Approval And Execution Authority

Mase approved revision 4 and exact task scope `T-001` through `T-004` at
`2026-07-26T11:22:38Z`. Plan approval authorizes the planning handoff only; it
does not authorize implementation, commits, reinstall, rollout, push, or PR.
The preferred opposite-model review failed to run because Claude was
session-limited. Mase explicitly selected a fresh-context GPT-5.6-Sol X-HIGH
review as the substitute gate; its artifact must identify the same-model
limitation, record the exact approved-plan hash, and close every material
finding without claiming opposite-model provenance.

Because approval metadata changed the file hash, the approved revision requires
a fresh GPT review/hash check before the pre-build readiness gate can clear.

After this planning/governance commit lands and final status confirms the clean
baseline, a single explicit `/build auto` invocation may implement `T-001`
through `T-004` without routine confirmation between tasks. Auto execution must
still honor every stop condition above and cannot infer authority for deferred
external or downstream actions.
