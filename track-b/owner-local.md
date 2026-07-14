# Code Context

## Files Retrieved

1. `docs/mase-fork-operating-model.md` (lines 113-147) - Graphify policy explicitly delegates upstream intake to the global OSS fork manager and prohibits claiming an unimplemented Graphify command.
2. `docs/plans/graphify-upstream-reconciliation-readiness-plan.md` (lines 40-61, 132-180, 197-234) - Track B requires discovering the shared owner first, then keeping Graphify as a thin project-specific overlay; it also defines the stricter target intake/apply contract.
3. `.codex/oss-fork-manager.json` (lines 1-27) - Graphify's repo-local marker identifies `my-oss-fork-manager`'s central registry and Graphify adapter.
4. `/Users/mase/.codex/oss-fork-manager/registry.json` (lines 7-133) - Canonical registration for Graphify: checkout, remotes, branches, manager-owned source-fork update surface, and validation commands.
5. `/Users/mase/.codex/skills/my-oss-fork-manager/SKILL.md` (lines 16-29, 66-99) - Declares this skill the sole standard-fork maintenance control plane and defines the read-only `update-fork --handoff` contract.
6. `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py` (lines 231-489, 1128-1192) - Actual CLI interface, pinned handoff rendering, and approved-update routing.
7. `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/adapters/base.py` (lines 170-230, 1030-1143, 1722-1734, 1947-1986) - Git guardrails, current mutating update implementation, Graphify adapter capabilities, and Graphify dry-run plan.
8. `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/lib/git_state.py` (lines 10-44, 330-428) - Read-only Git runner rejects fetch/pull/merge/rebase/checkout/push and collects state/drift guardrails.
9. `/Users/mase/.codex/skills/my-oss-fork-manager/tests/test_contracts.py` (lines 473-480, 689-754, 1497-1532) - CLI dry-run, Graphify guardrail/live-upstream, and pinned-handoff contract coverage.
10. `/Users/mase/.codex/skills/my-oss-fork-manager/references/update-workflow.md` (lines 15-88, 168-216) - Shared upstream intake and apply policy.

## Key Code

**Candidate-owner verdict: found shared canonical owner.**

- **Logic/CLI:** `/Users/mase/.codex/skills/my-oss-fork-manager/`
  - entry point: `scripts/oss_fork_manager.py`
  - Graphify adapter: `scripts/adapters/base.py:GraphifyAdapter`
  - tests: `tests/test_contracts.py`
- **Canonical mutable configuration:**
  `/Users/mase/.codex/oss-fork-manager/registry.json`
- **Graphify registration/guardrail marker:**
  `./.codex/oss-fork-manager.json`

The owner skill calls itself the *only* standard-managed OSS-fork control plane; it owns coordination, normalized inventory, safety gates, dry-run/apply reporting, and rollback wrappers. It says managed forks retain their own repo-local installation/propagation templates (`SKILL.md` lines 16-19, 66-80).

Graphify is already registered there with adapter `graphify`, upstream push disabled, `v8`/`upstream-v8`/`mase/local-fixes` branch policy, a manager-owned `graphify.source.fork` `update-fork` surface, and Graphify-specific validation commands (`registry.json` lines 7-66, 128-132). The registry currently labels Graphify `pending_verification` (line 10), so ownership is confirmed but its manager registration is not marked fully verified.

**Existing owner interface**

```text
python3 /Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py \
  update-fork --fork graphify [--handoff | --approved]
```

- Without `--approved`, `update-fork` calls `GraphifyAdapter.update_plan()`; `--handoff` adds a pinned Markdown brief to the JSON response (`oss_fork_manager.py` lines 442-489).
- `--handoff` is explicitly incompatible with `--approved`; it is documented and tested as read-only (`SKILL.md` lines 95-98; `test_contracts.py` lines 1497-1532).
- The plan/handoff use local Git diagnostics that reject mutation-capable Git verbs (`git_state.py` lines 10-44). The Graphify adapter's plan also performs `git ls-remote` checks for live upstream state, so it is non-mutating but not strictly offline (`adapters/base.py` lines 450-512).

**Track B gap: extend this owner; do not implement Git reconciliation in Graphify.**

The current shared owner is not yet the Track B target contract:

- No parser option accepts a durable intake `--output`, an intake artifact, exact expected source/target SHAs, or an explicit `--apply`; the relevant interface only exposes `--fork`, `--approved`, and `--handoff` (`oss_fork_manager.py` lines 1187-1192).
- `--handoff` returns a report in JSON (`data.handoff_brief`), not a persisted, validated intake artifact (`oss_fork_manager.py` lines 326-439).
- `update-fork --approved` currently executes `git fetch`, `git update-ref`, and `git rebase` after guardrail checks (`adapters/base.py` lines 1030-1143). It does not require the fresh complete artifact, decision matrix, exact artifact SHA expectations, and `--apply` gate required by Track B (`graphify-upstream-reconciliation-readiness-plan.md` lines 149-180).

Therefore **Graphify should only overlay the shared manager**: provide protected-surface/release-impact input, Graphify validation/provenance, and active-install/propagation policy. Keep Git topology collection, intake schema/rendering, artifact validation, and guarded-apply behavior in `my-oss-fork-manager`. Do not add or overload `graphify codex reconcile`, adoption, or a new Graphify Git-reconciliation command.

Existing tests cover dry-run routing, dirty Graphify rejection, live-upstream drift detection, and generic pinned handoff output. They do **not** demonstrate Track B's required durable-artifact, `GO`/`NO-GO`/`NEEDS-OPERATOR-DECISION`, or stale-artifact apply-refusal contract.

## Architecture

`Graphify marker -> shared registry -> GraphifyAdapter -> shared CLI/update workflow`

The marker points this checkout to the global registry. The registry supplies shared fork identity, branch/remotes policy, source/global surfaces, and validation commands. `GraphifyAdapter` adds Graphify-specific provenance, release-intel, protected areas, and propagation behavior, while inherited shared logic handles Git state and current update flow. The Track B plan assigns any reusable intake/artifact/apply enforcement to this shared owner and permits only a thin Graphify adapter/overlay.

## Start Here

Open:

`/Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py`

Start with lines 442-489 and 1128-1192 to preserve the current public CLI contract, then `scripts/adapters/base.py` lines 1030-1143 to replace or further guard the existing direct approved-rebase path.

## Next Safe Commands

Do not run an approved update, fetch, rebase, install, or propagation command.

1. Read-only handoff (non-mutating by contract; it may perform outbound `git ls-remote` checks):

```bash
python3 /Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py \
  update-fork --fork graphify --handoff
```

1. After implementation approval, fixture-only owner regression suite (uses temporary Git repositories; it must not target the Graphify checkout):

```bash
cd /Users/mase/.codex
python3 -m unittest discover -s skills/my-oss-fork-manager/tests -p test_contracts.py
```

No fetch, Git mutation, test execution, or source edit was performed during this discovery pass.
