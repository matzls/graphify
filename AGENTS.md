<!-- markdownlint-disable MD013 -->

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

## Current Semantic Backend Status

As of 2026-08-05:

- `deepseek-v4-pro:cloud` remains the automatic Ollama text default.
- `deepseek-v4-flash:0731-cloud` was blind-tested and rejected as the default:
  it recovered broader architecture but regressed privacy-contract fidelity and
  was slower on the bounded comparison.
- This checkout contains a reviewed final-`pi --print` backend, but the active
  CLI has not been reinstalled from these source changes. Pi remains explicit,
  unpromoted, and must never replace Ollama automatically.
- Explicit Pi image runs require command-local upload consent and human review
  of semantic output.
- `graphify/semantic_eval.py` remains useful for deterministic diagnostics, but
  the current scorer and gates are not authoritative for prompt, model, image,
  or promotion decisions.
- The next project iteration is **plan-only evaluation-harness redesign**. Resume
  from `.agent-skills/lifecycle-state.json`, `tasks/todo.md`, and
  `docs/semantic-model-quality-harness.md`. Do not implement the redesign, tune
  prompts, spend provider calls, change defaults, install, or promote without a
  newly reviewed and approved plan.

## Remotes

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Keep local mirror branches such as `mirror/upstream-v8` clean; this mirrors
upstream's `v8` branch and is not a release-version branch. Put local
customizations on `mase/local-fixes` unless a task explicitly creates a narrower
PR branch.

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
graphify pi install
```

`graphify pi install` refreshes Mase's global Pi Graphify skill and version
stamp from this checkout. Verify the active tool still points to this checkout
before bootstrapping
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

The active Codex hook surface is `.codex/config.toml` SessionStart. By default,
`graphify codex install` writes a path-bound command containing the resolved
Graphify executable and project path. `--portable` instead writes exactly
`graphify codex-session-start`; use it only when the Codex hook process can
resolve `graphify` on `PATH`. The supported portable families are direct
`graphify codex install [--project] --portable` and generic
`graphify install --project` with positional `codex`, `--platform codex`, or
`--platform=codex`. Portability is opt-in, existing configs are not migrated
automatically, and reconciliation preserves either recognized mode.

The runtime command is `graphify codex-session-start [path]`. An explicit path
remains authoritative; without one, Graphify resolves the current Git worktree
root from root, nested, or linked-worktree directories and falls back to the
resolved current directory outside Git. Installation also cleans old
`.codex/hooks.json` Graphify `hook-check` entries. `graphify hook-check` is
retained only as a silent legacy/backcompat no-op for stale hook configs; do not
describe it as the active reminder path.

For Codex, keep three surfaces distinct: `graphify install --platform codex`
installs the reusable Codex `/graphify` skill, `graphify codex install` writes
repo-local activation guidance (`AGENTS.md` plus `.codex/config.toml`
SessionStart), and Mase's global guide at
`/Users/mase/.codex/docs/reference/graphify.md` defines operator policy. Semantic
refreshes use the backend CLI pipeline or Pi handoff, not old Codex worker-only
extraction assumptions.

Codex AppHarness `/goal` can run the repeatable multi-repo propagation workflow
by executing the CLI from this fork checkout:

```bash
cd /Users/mase/Codebase/Personal-Projects/graphify
python3 -m graphify adoption propagate \
  --root /Users/mase/Codebase \
  --adopted hushmail-agent-router,astral-sora-proto,gemini-embedding \
  --candidates activecollab-mcp,astral-signal-hub,obsidian-agent,remote-coding-agent \
  --exclude pm-agent-toolkit,maser-pm,workshops,workshops-origin-main,get-shit-done \
  --local \
  --semantic \
  --backend ollama \
  --safe-ollama \
  --verify-activation
```

This is a Codex App operator pattern, not a Pi slash-command contract. Pi should
run the same CLI command directly from this checkout, or receive a normal task
prompt that tells it to run the CLI; do not assume Pi supports Codex `/goal`.

For Pi, prefer one current global Graphify skill installed from this checkout's
`graphify/skill-pi.md` into `~/.pi/agent/skills/graphify/SKILL.md`. Per-repo
Graphify propagation should stay lightweight: `AGENTS.md`, `.codex/config.toml`,
Git hooks, `.graphifyignore`, and `graphify-out/` describe or activate that
repo's graph; they should not duplicate the whole Pi skill unless a repo
explicitly needs a pinned/custom workflow. Pi also discovers `~/.agents/skills/`,
so any stale `~/.agents/skills/graphify` copy must be reviewed before deletion
or replacement. Codex-specific skills should install under `.codex/skills/`, not
the shared `.agents/skills/` tree, to avoid colliding with Pi discovery.

If Codex blocks `graphify extract . --backend ollama` as private-data export,
do not treat Codex YOLO mode as the normal fix. Model selection follows
explicit `--model`, then `OLLAMA_MODEL`, then Graphify's built-in default. See
`docs/codex-pi-semantic-refresh.md` and hand Mase a copy-pasteable Pi or direct
terminal command for the semantic refresh. Future local-fork work should add a
minimal `graphify` handoff command that prints that Pi/terminal payload without
sending repo content itself.

## Upstream Sync

To take upstream changes while preserving local fixes, use the mandatory
sequence in `docs/mase-fork-operating-model.md` and the shared OSS fork-manager
owner once identified. The default is **read-only intake**, not a rebase.

1. Treat `git fetch upstream` as a separately authorized network/ref mutation;
   report old/new target SHAs and do not conflate it with intake.
2. Before any checkout or rebase, capture a readiness packet: branch/HEAD,
   worktree and active Git-operation state, immutable target SHA, baseline-test
   evidence, release-tag/URL evidence, local-patch inventory, and release-impact
   plus adoption decisions.
3. Missing evidence, dirty/unclassified state, unresolved baseline failures,
   stale refs, or missing patch decisions are `NO-GO` by default. The packet is
   not authority to mutate.
4. Only after explicit operator go/no-go and an immediate state recheck may an
   apply command checkout, merge, or rebase. It must never auto-stash, reset,
   abort a Git operation, push, reinstall, or propagate.

Review the upstream GitHub release pages for every incoming tag. Match
release-note bullets and linked issues against this repo's patch goals,
`docs/mase-fork-operating-model.md`, `docs/plans/`, and relevant Git history.
Classify local overlap as `keep`, `drop`, `adapt`, `defer`, or `reject`; classify
feature adoption as `automatic`, `adapt`, `opt-in`, `defer`, or `reject`.

After approved intake, the current manual recovery sequence is:

```bash
git checkout upstream-v8
git merge --ff-only upstream/v8
git checkout mase/local-fixes
git rebase upstream-v8
uv run --with pytest pytest tests/test_watch.py tests/test_transcribe.py tests/test_hooks.py
```

Do not run the active-CLI reinstall until the relevant reconciliation validation
is clean and Mase explicitly authorizes that environment mutation:

```bash
uv tool install --force --reinstall /Users/mase/Codebase/Personal-Projects/graphify \
  --with openai \
  --with tiktoken \
  --with faster-whisper \
  --with yt-dlp \
  --with watchdog \
  --with tree-sitter-sql
graphify pi install
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

After a reconciliation that changes graph IDs, cache/output formats, install
surfaces, activation behavior, or semantic-refresh behavior, do not broad
propagate immediately. Reinstall and verify the active CLI, run an adoption
audit, canary one or two representative repos, re-audit, then apply broader
propagation. Do not run `extract --force` everywhere by default; reserve it for
repos where release notes or canary results show generated state should be
rebuilt from scratch.

If upstream includes equivalent fixes, drop the matching local commits from
`mase/local-fixes`.

Every upstream reconciliation must end with a non-silent operator briefing for
Mase. Include:

- release tags reviewed, with GitHub release links
- functional changes and new commands/features Mase can use
- local patch decisions: kept, dropped, adapted, skipped
- settings or workflow recommendations, including when no change is advised and
  which features are automatic versus opt-in/adapted/deferred/rejected
- explicit opt-in commands for features such as CodeBuddy, HTTP MCP serving,
  PostgreSQL introspection, Azure backend use, or extra installs
- validation run plus remaining state: dirty/clean, committed/uncommitted,
  pushed/unpushed, and whether the active CLI was reinstalled

The briefing must distinguish upstream product changes from local-fork conflict
resolutions so reconciliation is never just a silent version bump.

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
- Normalize legacy or model-produced hyperedges missing `id` so `build_merge`,
  semantic-cache reuse, and exports cannot crash or preserve malformed graph
  metadata.

Prefer tests in `tests/test_watch.py`, `tests/test_transcribe.py`,
`tests/test_hooks.py`, `tests/test_cli_semantic_fail_closed.py`,
`tests/test_llm_backends.py`, `tests/test_cli_export.py`,
`tests/test_hypergraph.py`, `tests/test_build_merge_hyperedges_and_prune.py`,
and `tests/test_extract_cli.py` for these patches.

## Pi Runtime Note: GSD

The generated GSD routing block below is for Codex sessions only. Pi currently
does not load this repo's `.codex/skills/gsd-*`, and Mase is not using GSD in
Pi. In Pi, do not route work through GSD unless Mase explicitly asks to port or
enable it for Pi.

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

When the user types `/graphify`, use the installed Graphify Agent Skill or
instructions before doing anything else.

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
- For consumer repos managed by Mase, the default policy is now: keep
  `graphify-out/` generated locally, ignored, and untracked while preserving
  Graphify hooks for local refreshes.
