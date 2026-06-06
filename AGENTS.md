# Graphify Fork Operating Notes

This repository is Mase's fork of upstream Graphify.

This repo is both:

- a local source checkout for Mase's active `graphify` CLI install
- the source for repo-local Codex guidance written to `AGENTS.md` plus
  `.codex/config.toml` SessionStart reminders

For any non-trivial Graphify work, first read:

- `docs/mase-fork-operating-model.md` for the fork model, local delta from
  upstream, Graphify architecture map, and Codex integration reality.
- `ARCHITECTURE.md` for the upstream project architecture summary.
- `/Users/mase/.codex/docs/reference/graphify.md` for Mase's global Graphify
  operating guide.

## Remotes

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Keep upstream mirror branches such as `upstream-v8` clean. Put local customizations on
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
  --with openai \
  --with tiktoken \
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

## Codex Integration

The active Codex hook surface is `.codex/config.toml` SessionStart:
`graphify codex install` writes `graphify codex-session-start <repo>` there and
cleans old `.codex/hooks.json` Graphify `hook-check` entries. `graphify
hook-check` is retained only as a silent legacy/backcompat no-op for stale
hook configs. Do not describe it as the active reminder path.

For Codex, keep three surfaces distinct: `graphify install --platform codex`
installs the reusable Codex `/graphify` skill, `graphify codex install` writes
repo-local activation guidance (`AGENTS.md` plus `.codex/config.toml`
SessionStart), and Mase's global guide at
`/Users/mase/.codex/docs/reference/graphify.md` defines operator policy. Semantic
refreshes use the backend CLI pipeline or Pi handoff, not old Codex worker-only
extraction assumptions.

For Pi, prefer one current global Graphify skill installed from this checkout's
`graphify/skill-pi.md` into `~/.pi/agent/skills/graphify/SKILL.md`. Per-repo
Graphify propagation should stay lightweight: `AGENTS.md`, `.codex/config.toml`,
Git hooks, `.graphifyignore`, and `graphify-out/` describe or activate that
repo's graph; they should not duplicate the whole Pi skill unless a repo
explicitly needs a pinned/custom workflow. Pi also discovers `~/.agents/skills/`,
so any stale `~/.agents/skills/graphify` copy must be reviewed before deletion
or replacement. Codex-specific skills should install under `.codex/skills/`, not
the shared `.agents/skills/` tree, to avoid colliding with Pi discovery.

If Codex blocks `graphify extract . --backend ollama --model minimax-m3:cloud`
as private-data export, do not treat Codex YOLO mode as the normal fix. See
`docs/codex-pi-semantic-refresh.md` and hand Mase a copy-pasteable Pi or direct
terminal command for the semantic refresh. Future local-fork work should add a
minimal `graphify` handoff command that prints that Pi/terminal payload without
sending repo content itself.

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
git remote set-head upstream -a
git checkout upstream-v8
git merge --ff-only upstream/v8
git checkout mase/local-fixes
git rebase upstream-v8
uv run --with pytest pytest tests/test_watch.py tests/test_transcribe.py tests/test_hooks.py
uv tool install --force --reinstall /Users/mase/Codebase/Personal-Projects/graphify \
  --with openai \
  --with tiktoken \
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
- Keep Codex guidance explicit about the safe no-op hook behavior.
- Preserve the Codex-to-Pi semantic refresh handoff for Ollama Cloud blocks;
  see `docs/codex-pi-semantic-refresh.md`.
- Fail closed on degraded semantic refreshes unless `--allow-partial` is
  explicit; partial markers must prevent wiki refreshes from looking clean.

Prefer tests in `tests/test_watch.py`, `tests/test_transcribe.py`,
`tests/test_hooks.py`, `tests/test_cli_semantic_fail_closed.py`,
`tests/test_llm_backends.py`, and `tests/test_cli_export.py` for these patches.

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

## graphify

This project has historical knowledge graph artifacts at `graphify-out/`, but
Graphify should not be executed automatically against its own source repo.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions in this repo, prefer source inspection, tests, and
  docs over Graphify output.
- Dirty `graphify-out/` files may exist from older hooks or manual runs; do not
  treat them as a required refresh signal in this repo.
- Do not run `graphify update .`, `graphify extract .`, Graphify semantic
  refreshes, or `graphify hook install` in this repo unless Mase explicitly
  asks for a self-analysis run.
- Existing `graphify-out/` files are retained as historical derived artifacts,
  not as an always-fresh map.
