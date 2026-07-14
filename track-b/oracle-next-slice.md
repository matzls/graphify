Inherited decisions:
- Shared owner is `my-oss-fork-manager`; Graphify must remain a thin overlay.
- Track B requires durable read-only intake before any apply.
- Graphify forbids automatic `rebase --abort` and `reset --hard`.
- No real reconciliation is authorized while the checkout is dirty/stale.

Diagnosis:
- The current shared `GraphifyAdapter.update_apply()` inherits `_standard_update_apply()`, which fetches, rebases, auto-aborts conflicts, and hard-resets after validation failure.
- Current `update-fork --handoff` is read-only but is not a durable, validated intake artifact and lacks Track B’s decision matrix/exact-SHA contract.
- Registry mirror is `upstream-v8`; marker and primary AGENTS policy use `mirror/upstream-v8`. No local mirror branch currently exists.

Drift / contradiction check:
- The shared manager’s existing approved Graphify update path violates Graphify’s no-auto-abort/reset policy.
- Do not build a second Graphify reconciliation CLI or extend `graphify codex reconcile`.
- The legacy manual `git checkout upstream-v8` recovery instructions must eventually align with the chosen mirror convention.

Recommendation:
Implement one **shared-manager, read-only-first** slice:

1. Default Graphify’s registry mirror to `mirror/upstream-v8`—the marker and standing branch policy agree; do not create or update that branch in this slice.
2. Override Graphify `update_apply()` to fail closed with `blocked_pending_durable_intake`, even with `--approved`.
3. Add a new generic/shared `intake` command that:
   - accepts `--fork graphify`;
   - collects only local Git/registry/adapter evidence by default;
   - emits JSON plus Markdown to stdout;
   - writes only with explicit `--output`, atomically, and refuses overwrite;
   - returns `NO-GO` for dirty state, missing mirror, stale refs, missing decisions, or incomplete baseline evidence.
4. Keep release URLs/ranges as unverified local evidence by default; do not run `git ls-remote` or fetch in default intake.

This closes today’s unsafe apply route while producing the prerequisite artifact for a later explicit `--apply` handoff. The apply command itself should be a later slice and initially emit a reviewed manual/isolated-worktree command—not rebase.

Exact files:
- `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/oss_fork_manager.py`
- `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/adapters/base.py`
- `/Users/mase/.codex/oss-fork-manager/registry.json`
- `/Users/mase/.codex/skills/my-oss-fork-manager/tests/test_contracts.py`
- Graphify docs/marker only for mirror-policy alignment after the shared fixture contract passes.

Risks:
- Updating the global registry is a global control-plane mutation.
- The current Graphify checkout is dirty and must remain a live-intake `NO-GO`.
- Existing `update-fork --approved` must not retain a Graphify path around the new intake gate.

Need from main agent:
- No product decision is required if the default mirror becomes `mirror/upstream-v8`.
- If that convention is rejected, decide it before registry/marker/doc changes.

Suggested execution prompt:
- Warranted: use one writer in the shared manager. Implement only the read-only `intake` artifact contract plus Graphify’s fail-closed `update_apply` override and registry mirror correction. Add fixture tests for no mutation, atomic/non-overwriting output, dirty/missing-mirror NO-GO, missing decision NO-GO, and rejection of `--approved` Graphify apply. Do not fetch, rebase, reset, abort, install, propagate, or target the real Graphify checkout.