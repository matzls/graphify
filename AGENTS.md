# Graphify Fork Operating Notes

This repository is Mase's fork of upstream Graphify.

This repo is both:

- a local source checkout for Mase's active `graphify` CLI install
- the source for the Codex Graphify skill copy installed under
  `/Users/mase/.codex/skills/graphify/SKILL.md`

For any non-trivial Graphify work, first read:

- `docs/mase-fork-operating-model.md` for the fork model, local delta from
  upstream, Graphify architecture map, Codex integration reality, and skill-sync
  rules. Use its "Upstream Skill Sync Procedure" section whenever upstream
  changes `graphify/skill-codex.md` and the installed `.codex` skill needs a
  carry-over review.
- `ARCHITECTURE.md` for the upstream project architecture summary.
- `/Users/mase/.codex/docs/reference/graphify.md` for Mase's global Graphify
  operating guide.

## Remotes

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Keep upstream mirror branches such as `v6` clean. Put local customizations on
`mase/local-fixes` unless a task explicitly creates a narrower PR branch.

Always inspect `git status --short --branch`, current branch, and relevant
diffs before making claims about local-vs-upstream state. This fork may be ahead
of or behind Mase's GitHub remote and upstream at the same time.

## Local Development

- Do not patch the uv tool site-packages copy directly.
- Make source changes in this repository.
- Run targeted tests before reinstalling the active CLI.
- Install the active CLI from this checkout when local fixes should be used:

```bash
uv tool install --force --reinstall /Users/mase/Codebase/Personal-Projects/graphify \
  --with faster-whisper \
  --with yt-dlp \
  --with watchdog \
  --with tree-sitter-sql
```

Verify the active tool still points to this checkout before bootstrapping
Graphify in another repo:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

If this check fails, do not continue by installing from PyPI. Reinstall from
this checkout with the command above, then verify again.

A repo-local Git hook cannot reliably prevent `uv tool upgrade graphifyy`,
because that command mutates the global uv tool installation outside this git
repo. Use the verifier above before repo bootstraps. If a hard block is ever
needed, add it as an explicit shell wrapper or Codex command hook rather than as
a Graphify repo Git hook.

## Codex And Skill Sync

The upstream Codex hook path is intentionally limited in Codex Desktop:
`graphify codex install` writes `.codex/hooks.json`, but `graphify hook-check`
currently exits silently because Codex Desktop rejects the old
`hookSpecificOutput.additionalContext` payload. Do not describe this as an
active per-tool reminder unless the hook implementation changes and is verified.

For Codex, the reliable guidance surface is repo-local `AGENTS.md`, the global
Graphify skill, and explicit `$graphify` invocation.

When editing Graphify skill behavior, keep these surfaces aligned:

- `graphify/skill-codex.md`
- `/Users/mase/.codex/skills/graphify/SKILL.md`
- `/Users/mase/.codex/docs/reference/graphify.md`

Do not assume they are already synchronized; compare them before changing or
reporting Graphify behavior.

Mase may sometimes improve the installed Codex skill directly inside
`/Users/mase/.codex`. Before overwriting either copy, compare both content and
git history to determine which side has the latest intentional work. Do not
discard `.codex` skill changes just because this repo packages
`graphify/skill-codex.md`, and do not remove packaged skill files from this repo
unless Mase explicitly decides to change Graphify's distribution model.

## Upstream Sync

To take upstream changes while preserving local fixes:

Before rebasing, review the upstream GitHub release pages for every tag being
pulled in. Match release-note bullets and linked issues against this repo's
local patch goals, `docs/mase-fork-operating-model.md`, `docs/plans/`, and the
relevant git history. Treat overlaps as explicit decisions:

- keep the local patch if it still adds Mase-specific behavior
- drop it if upstream now contains the same fix
- adapt it if upstream fixed the general case but Mase's Codex setup still
  needs local guidance

```bash
git fetch upstream
git checkout v6
git merge --ff-only upstream/v6
git checkout mase/local-fixes
git rebase v6
uv run pytest tests/test_watch.py tests/test_transcribe.py tests/test_hooks.py
uv tool install --force --reinstall /Users/mase/Codebase/Personal-Projects/graphify \
  --with faster-whisper \
  --with yt-dlp \
  --with watchdog \
  --with tree-sitter-sql
```

If upstream includes equivalent fixes, drop the matching local commits from
`mase/local-fixes`.

## Local Patch Goals

Current local fixes should stay small and upstream-friendly:

- Preserve semantic community labels during code-only rebuilds.
- Avoid transcript filename collisions for same-stem media files.
- Verify active install source with `graphify doctor --require-source`.
- Keep Codex skill guidance explicit about the safe no-op hook behavior.

Prefer tests in `tests/test_watch.py`, `tests/test_transcribe.py`, and
`tests/test_hooks.py` for these patches.

<!-- gsd-routing-start -->
<!-- template-version: 2026-05-11.1 -->
<!-- template-sha256: a268dee324e539b5e9c735b0eb34e95b479eaa6e531df938174b87d5d15a6022 -->

## GSD Routing

GSD is installed locally in this repo.

Use this repo's `.codex/skills/gsd-*` skills when the task is about managing,
planning, implementing, debugging, validating, documenting, or shipping work
inside this project.

Default routing:
- Use `gsd-progress` or `gsd-health` to inspect project/workflow state.
- Use `gsd-map-codebase` then `gsd-new-project` for first-time setup in an
  existing codebase.
- Use `gsd-discuss-phase`, `gsd-spec-phase`, or `gsd-plan-phase` when work
  needs clarification, specification, or planning.
- Use `gsd-execute-phase`, `gsd-quick`, or `gsd-fast` for implementation work,
  depending on scope.
- Use `gsd-debug` for bugs, regressions, failing checks, or unexplained runtime
  behavior.
- Use `gsd-code-review`, `gsd-validate-phase`, or `gsd-verify-work` for quality
  gates after implementation.
- Use `gsd-docs-update` for verified project documentation updates.
- Use `gsd-ship` only when preparing verified work for PR or release.

First-run onboarding for an existing codebase:
- Restart or open Codex in this repository after local GSD installation so
  repo-local `.codex/skills/gsd-*` and `.codex/agents/gsd-*` are loaded.
- For an existing project, use `gsd-map-codebase` before `gsd-new-project`.
  The map step builds repo-grounded context; the new-project step uses that
  context to create or refresh `.planning/`.
- Prefer invoking installed GSD skills directly, such as `gsd-map-codebase`
  and `gsd-new-project`. Inspect workflow files under
  `.codex/get-shit-done/workflows/` only as fallback/debug evidence, not as
  the normal entrypoint.

Do not use this repo's project workflow skills to update the GSD framework
itself.

For GSD framework updates, install inventory, stale install checks,
propagation dry-runs, or confirmed propagation, use Mase's local GSD fork:

the local fork propagation skill (`.codex/skills/gsd-fork-propagate/SKILL.md` in the fork checkout)

Do not use `/gsd-update`, `npx get-shit-done-cc@latest`, public npm update
flows, or upstream install flows unless Mase explicitly asks to replace the
fork-managed setup with upstream.

Safety rules:
- Always dry-run propagation before apply.
- Report selected targets, skipped targets, and exact commands before apply.
- Do not update dirty target repos unless Mase explicitly confirms.
- Do not update global installs unless Mase explicitly confirms.
- Do not update unknown-source installs unless Mase explicitly confirms.
<!-- gsd-routing-end -->
