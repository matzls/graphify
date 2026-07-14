# Code Context

## Files Retrieved

1. `/Users/mase/.codex/skills/my-oss-fork-manager/SKILL.md` (lines 1-109) - declares the central fork-management control plane, registry, command surface, and read-only handoff rule.
2. `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py` (lines 442-490, 993-1205) - implements single-fork approval gating, dry-run/handoff dispatch, and CLI commands.
3. `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/adapters/base.py` (lines 170-225, 1030-1218, 1722-2208) - supplies git guardrails and the Graphify-specific inventory, intake-plan, provenance, and propagation adapter.
4. `/Users/mase/.codex/skills/my-oss-fork-manager/tests/test_contracts.py` (lines 1-230, 599-755, 1337-1532, 2198-2600) - contract coverage for schema/safety, Graphify dirty/live-upstream planning, generic approved update/recovery, Graphify activation, and skill sync.
5. `/Users/mase/.codex/oss-fork-manager/registry.json` (lines 1-133) - live global Graphify record, its adapter, remotes, branches, declared surfaces, and validation commands.
6. `.codex/oss-fork-manager.json` (lines 1-26) - Graphify checkout marker pointing at the global registry.
7. `AGENTS.md` (lines 126-149) and `docs/mase-fork-operating-model.md` (lines 119-147) - Graphify's required read-only-first intake and its no-auto-reset/abort/install/propagate constraint.
8. `/Users/mase/Codebase/Personal-Projects/mase-pi-subagents/scripts/reconcile-upstream.mjs` (lines 1-144) and `reconcile-manifest.json` (lines 1-182) - a separate, fork-local dry-run reconcile guard.
9. `/Users/mase/Codebase/Personal-Projects/pi-agent-skills/scripts/reconcile-upstream.mjs` (lines 1-180), `reconcile-manifest.json` (lines 1-178), and `package.json` (lines 1-24) - another fork-local reconcile guard and its package command.

## Key Code

### Primary candidate: shared OSS Fork Manager

**Path:** `/Users/mase/.codex/skills/my-oss-fork-manager/`

This is an actual reusable implementation, not a prose-only workflow:

- The skill calls itself the only maintenance control plane for standard-managed OSS forks and assigns it inventory, upstream intake, provenance, installs, overlays, and marker bootstrap (`SKILL.md` lines 16-29).
- Its Python CLI has inventory, candidate discovery, `update-fork(s)`, `plan-update`, `apply-update`, provenance, propagation, and hook-audit commands (`scripts/oss_fork_manager.py` lines 442-490, 993-1205).
- The central registry contains a real `graphify` entry wired to the `graphify` adapter, read-only upstream push URL, source/CLI/Codex-skill surfaces, provenance, and validation commands (`registry.json` lines 7-133).
- `GraphifyAdapter` implements read-only inventory/provenance and an update plan with upstream-policy, live-upstream, guardrail, convergence, and release-intel evidence (`scripts/adapters/base.py` lines 1722-1986).

Relevant declared capability:

```python
class GraphifyAdapter(ForkAdapter):
    capabilities = {
        "inventory": True,
        "provenance": True,
        "update-plan": True,
        "update-apply": True,
        "propagate-plan": True,
        "propagate-apply": True,
    }
```

The safe reusable path is specifically the unapproved, read-only handoff mode:

```text
update-fork --fork <id> --handoff
```

The skill states that this mode must not fetch, branch, merge, rebase, commit, push, or update installs (`SKILL.md` lines 95-98).

### Supporting candidates, not global owners

1. `/Users/mase/Codebase/Personal-Projects/mase-pi-subagents/scripts/reconcile-upstream.mjs`
   - Actual code plus `reconcile-manifest.json`; checks one fixed checkout's branch, refs, upstream push URL, reviewed release, mirror, dirty state, and protected local paths.
   - It derives `repoRoot` from its own script location and always reads its sibling manifest, so it is a **per-fork guard**, not a reusable owner for Graphify or other forks.
   - `package.json` exposes it as `npm run reconcile`.

2. `/Users/mase/Codebase/Personal-Projects/pi-agent-skills/scripts/reconcile-upstream.mjs`
   - Actual code plus manifest; checks the Agent Skills fork's fixed branch/upstream/mirror state, local delta allowlist, and range-diff baseline.
   - It is also **per-fork only**, not a central registry/adapter owner.
   - `package.json` exposes it as `npm run reconcile:upstream`.

No additional reusable upstream-intake owner was found in the searched Pi notes/skills or shared Codex documentation. `~/.codex/notes` is not a directory. The Pi notes contain policy and historical fork-plan references, but no separate manager implementation.

### Tests

- The OSS Fork Manager has one local contract suite:
  `/Users/mase/.codex/skills/my-oss-fork-manager/tests/test_contracts.py`
  Static count: **115** `test_*` methods (3,566 lines); not executed for this read-only inventory.
- Direct Graphify coverage includes dirty-worktree blocking and live-upstream drift detection (`test_contracts.py` lines 689-755), repository activation/propagation behavior (lines 2198-2468), and global skill provenance/sync rollback behavior (lines 2469-2600).
- Generic approved-update coverage verifies fetch, fast-forward, rebase, validation, conflict abort/recovery, and non-fast-forward refusal (lines 1337-1455). This exercises the inherited implementation but is **not** a Graphify-specific successful upstream-apply test.
- The two per-fork reconcile scripts are exposed through package scripts, but this inventory did not find a dedicated test suite for either script.

## Architecture

```text
Codex skill/procedure
  -> oss_fork_manager.py CLI
    -> global registry.json
      -> GraphifyAdapter
        -> Graphify checkout marker, git state, provenance, and declared surfaces
```

The registry is the authoritative cross-fork inventory; the repo-local Graphify marker is guardrail-only (`SKILL.md` lines 21-29). The manager is therefore the only found candidate that can own shared upstream-intake coordination while letting Graphify retain its product-specific install/activation commands.

The maintained-project metadata check found only three roots with an `upstream` remote: `graphify`, `mase-pi-subagents`, and `pi-agent-skills`. All have upstream push URL `DISABLED`. The latter two contain only their own reconcile guards; Graphify is already in the global manager registry.

## Owner Recommendation

Adopt **`my-oss-fork-manager`** as the external/shared owner for **Graphify read-only intake, normalized inventory, and handoff generation only**. It is the sole verified reusable implementation and already has a Graphify adapter plus a registry record.

Do **not** authorize its `--approved` update or propagation paths for Graphify yet. Use the Graphify-specific manual gate after the blockers below are resolved and an enforcement design is explicitly approved.

## Blockers

1. **Mirror-name mismatch blocks current manager planning.** The registry declares `upstream-v8` (`registry.json` line 25), but both the checkout marker and the only local mirror ref are `mirror/upstream-v8` (`.codex/oss-fork-manager.json` lines 19-22; read-only branch inspection). The adapter guardrail requires the registry mirror branch, so Graphify intake will fail until this divergence is reconciled.
2. **Graphify's apply policy conflicts with the shared adapter's recovery behavior.** Graphify prohibits auto-reset and auto-abort during apply (`AGENTS.md` lines 141-143). The inherited adapter executes `git rebase`, then calls `git rebase --abort` after conflict and `git reset --hard` after failed validation (`scripts/adapters/base.py` lines 1101-1124, 1178-1194). This makes the existing manager safe to nominate only for read-only work until the Graphify apply path is disabled or made policy-compliant.
3. **Graphify remains `pending_verification` in the global registry** (`registry.json` line 10), despite having a marker. Treat the entry as not fully active.
4. **Pi installation is absent from the manager's declared Graphify surfaces.** The registry declares only source, global CLI, and global Codex skill surfaces (lines 41-119); Graphify's active Pi skill is a separate required surface (`AGENTS.md` lines 108-116). The manager cannot currently prove or refresh that Pi surface.
5. **Apply coverage is incomplete for Graphify.** The contract suite has Graphify planning and propagation tests, but no explicit successful Graphify upstream-apply test; shared apply coverage is indirect through `GsdAdapter`.
6. **No runtime validation was performed.** No manager command, test, fetch, install, or mutation ran in this slice. The source repository was already dirty before this report was created; no existing work was changed.

## Start Here

Open this first:

`/Users/mase/.codex/skills/my-oss-fork-manager/SKILL.md`

It identifies the actual global control plane and directs the reader to the registry and deterministic CLI. Then inspect the Graphify entry in:

`/Users/mase/.codex/oss-fork-manager/registry.json`

before deciding whether to resolve the mirror/configuration and policy-compatibility blockers.

## Bounded Search Scope

Searched only the requested operator roots: shared Codex docs and skills (plus the registry referenced by the discovered skill), Pi agent notes and skills, and metadata/targeted script-schema-test artifacts in maintained personal-project roots. Derived/vendor artifacts such as `node_modules`, `graphify-out`, virtual environments, and caches were excluded from candidate assessment. No unrelated personal-data roots were traversed; no fetch, install, or external action occurred.
