---
title: "Mase Graphify Fork Operating Model"
kind: reference
status: active
audience: "agents-maintainers"
canonicality: canonical
doc_id: "mase-graphify-fork-operating-model"
owners:
  - "mase"
created: 2026-05-02
updated: 2026-07-19
last_verified: 2026-07-19
reconciliation_status: "v0.9.20 promoted locally; active CLI 0.9.20; canary passed; broad propagation gated"
source_of_truth: "./mase-fork-operating-model.md"
related:
  - "../AGENTS.md"
  - "../ARCHITECTURE.md"
  - "../README.md"
  - "./codex-pi-semantic-refresh.md"
  - "/Users/mase/.codex/docs/reference/graphify.md"
tags:
  - "graphify"
  - "fork"
  - "codex"
retrieval_hints:
  - "Graphify local fork"
  - "Mase fork versus upstream"
  - "Codex Graphify backend guidance"
  - "graphify hook-check no-op"
---

<!-- markdownlint-disable MD013 MD025 -->

# Mase Graphify Fork Operating Model

## Purpose

This repository is Mase's local fork of upstream Graphify. Treat it as both a
normal Python project and an operator-owned integration surface for Codex.

The main job of this document is to stop future agents from treating this repo
as a generic upstream checkout. Local changes may exist to support Mase's Codex
setup, and the installed CLI must stay pointed at this checkout while local
fork fixes matter.

## When To Use

Read this document before:

- changing Graphify code, skills, hooks, install behavior, or watcher behavior
- explaining how Mase's Graphify install differs from upstream
- reinstalling the active `graphify` CLI
- changing `/Users/mase/.codex/docs/reference/graphify.md`
- running `graphify codex install` or advising that it creates an active Codex
  reminder

## Repository Roles

This checkout has three roles:

- Source fork: local code lives here and should be compared against the current
  upstream release branch, now `upstream/v8`, before claims about local
  changes.
- Active install source: Mase's `graphify` CLI should be installed from this
  checkout, not from PyPI, while local fork fixes matter.
- Skill source: packaged assistant skills such as `graphify/skill-pi.md` live in
  this repo and are copied into harness-specific skill locations by install
  commands.
- Pi global skill source: the normal Pi setup should use one current global
  Graphify skill installed from this checkout into
  `~/.pi/agent/skills/graphify/SKILL.md`. Repo-local Graphify activation should
  remain lightweight and should not duplicate the full Pi skill unless a repo
  intentionally needs a pinned/custom workflow.
- Codex skill source: `graphify/skill-codex.md` and
  `graphify/skills/codex/references/` provide the reusable Codex `/graphify`
  skill. This fork installs that skill under `.codex/skills/graphify/`, not
  upstream's shared `.agents/skills/graphify/`, so it does not collide with Pi's
  shared-skill discovery.
- Codex activation source: repo-local `AGENTS.md`, `.codex/config.toml`
  SessionStart reminders, and `/Users/mase/.codex/docs/reference/graphify.md`
  define Mase's per-repo Codex usage. These activation surfaces complement the
  Codex skill; they do not replace upstream Git reconciliation.

## Branch And Remote Model

Remotes:

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Branch rules:

- Keep local mirror branches such as `mirror/upstream-v8` clean. The name means
  "local mirror of upstream's `v8` branch"; it is not tied to release tags such
  as `v0.9.9`.
- Keep Mase-local customizations on `mase/local-fixes` unless a narrower task
  branch is explicitly created.
- Before modifying anything, inspect `git status --short --branch`, current
  branch, and relevant diffs.
- Do not assume `origin`, `upstream`, and the local checkout are aligned. This
  fork can be ahead of Mase's remote and behind upstream at the same time.

Useful comparison commands:

```bash
git status --short --branch
git branch --show-current
git diff --stat upstream/v8..HEAD
git diff --name-status upstream/v8..HEAD
git log --oneline --decorate --max-count=12
```

## Upstream Release Review and Readiness Gate

Before rebasing local fixes onto a newer upstream branch, use the global OSS
fork-manager upstream-intake workflow. This document adds Graphify-specific
surfaces and validation expectations; it does not replace the shared process or
assume that a Graphify CLI command is its canonical implementation.

The required sequence is:

1. **Acquire deliberately.** `git fetch upstream` changes remote-tracking refs
   and uses the network, so it is a separately reported action—not part of
   default intake. Record the old/new target SHA and run `git remote set-head
   upstream -a` only when fetch is authorized.
2. **Run read-only intake.** Capture branch/HEAD, worktree and in-progress Git
   state, selected immutable target SHA, merge base/range, baseline-test result,
   release-tag range, local-patch inventory, and release-impact/adoption matrix.
   Default intake must not checkout, rebase, stash, reset, install the active
   CLI, run extraction, or propagate consumer repositories.
3. **Record an explicit decision.** Missing release evidence, a dirty or
   unclassified worktree, unresolved baseline failures, stale refs, or absent
   patch/adoption decisions are `NO-GO` by default. An intake report is evidence,
   not authorization to mutate.
4. **Apply only explicitly.** A mutation path must recheck branch, worktree,
   local HEAD, and target SHA immediately before acting, and require explicit
   operator approval plus an apply flag or equivalently deliberate command.
   It must never auto-stash, reset, push, reinstall, or propagate.
5. **Validate and stage.** After the approved reconciliation, run targeted
   regression checks, verify the active install only when authorized, audit,
   canary, re-audit, and give the operator briefing below before broad
   propagation.

The shared OSS fork-manager owner is identified, but its Graphify-specific
enforcement design remains refinement-required. The durable plan is
`docs/plans/graphify-upstream-reconciliation-readiness-plan.md`; follow the
manual gate above rather than inventing or claiming an unimplemented command.

Inspect the GitHub release pages for every incoming tag between the current
local mirror and the target upstream head:

```text
https://github.com/safishamsi/graphify/releases
```

Use the release notes and linked issues as an explicit reconciliation checklist.
For each relevant item, compare upstream's claim to:

- current local patch goals in this document and `AGENTS.md`
- accepted or pending plans in `docs/plans/`
- git history for the touched files, especially `graphify/cli.py`,
  `graphify/install.py`, `graphify/watch.py`, `graphify/transcribe.py`, and
  their tests
- recent operator history or session notes when they are available in the
  active task context

Classify local overlap as `keep`, `drop`, `adapt`, `defer`, or `reject`; classify
upstream feature adoption as `automatic`, `adapt`, `opt-in`, `defer`, or
`reject`. If an incoming release only improves correctness or performance and
requires no setting or workflow change, state that plainly.

For Graphify, the release impact memo should explicitly inspect these surfaces
when touched by the incoming release:

- CLI flags/help and command routing in `graphify/cli.py`, especially `extract`,
  `update`, `cluster-only`, `codex`, `hook`, `install`, and `doctor`.
- Backend and semantic extraction behavior in `graphify/llm.py`, including
  provider routing, retry/degraded-output handling, trace output, and cache use.
- Graph freshness behavior in `graphify/watch.py`, `graphify/hooks.py`, and
  generated repo-local guidance.
- Generated or installed skill surfaces, including Codex and Pi destination
  paths, progressive references, and always-on activation prose.
- Cache, manifest, graph output, wiki/report, and semantic-label behavior under
  `graphify-out/`.
- Optional dependency or install-extra changes that affect Mase's active
  `uv tool install --force --reinstall` command.

## Upstream Reconciliation Briefing

Upstream syncs must not be silent upgrades. After fetching release notes and
before calling the work complete, produce a short operator briefing for Mase.
The briefing must separate upstream product changes from local-fork conflict
resolutions and must include:

- Incoming release range and source links: list every upstream tag reviewed and
  link the GitHub release pages used as evidence.
- Functional changes: summarize new commands, backends, install surfaces,
  extraction behavior, graph quality changes, and breaking or behavior-changing
  fixes.
- Local patch decisions: call out any local commit or custom behavior that was
  kept, dropped, adapted, or skipped, with the reason. This is mandatory for
  Codex skill, `AGENTS.md`, hook, backend, semantic-refresh, and generated skill
  changes.
- Recommended leverage: say whether Mase should change any settings or habits
  to use the new functionality. If no settings should change, say that plainly
  and name which features are automatic, adapted, opt-in, deferred, or rejected.
- Graphify adoption audit: after reinstalling the reconciled fork, run or
  recommend `graphify adoption audit --root /Users/mase/Codebase` so the same
  Pi/Codex session can show which repos need propagation, semantic refresh,
  hooks, wiki output, or candidate bootstrap. Keep this report inline in chat;
  do not require Mase to open a separate plan artifact for the normal workflow.
- Suggested opt-ins: list concrete commands only for features that need
  deliberate adoption, such as CodeBuddy install, HTTP MCP serving, PostgreSQL
  introspection, Azure backend use, extra dependency installs, or explicit
  `graphify adoption apply ...` propagation.
- Validation and residual state: report targeted tests, generated-artifact
  checks, dirty or clean state, whether the active CLI was reinstalled, and
  whether anything remains uncommitted, unpushed, or operator-gated.

The briefing should be concise, but it should answer: "What changed?", "What
matters to this fork?", and "Should Mase do anything differently now?"

## Current Local Delta From Upstream

As last verified on 2026-05-16 against `upstream/v8`, the local fork carries
Mase-specific or recently upstream-oriented changes in these areas:

- `AGENTS.md`: fork operating notes for Mase's local setup.
- `graphify/__main__.py`: install-source diagnostics via
  `graphify doctor --require-source`, Codex/agent install guidance, and related
  platform install behavior.
- `graphify/skill.md`: packaging or skill text alignment with the fork.
- `graphify/transcribe.py`: stable transcript paths that include media suffix
  and a stable hash so same-stem media files such as `sample.mp3` and
  `sample.mp4` do not collide.
- `graphify/hooks.py`: repo-local hooks classify code versus semantic changes,
  rebuild code graphs without spending LLM tokens, and write
  `graphify-out/needs_update` for docs/media/image changes.
- `graphify/llm.py` and `graphify/__main__.py`: degraded semantic refreshes
  propagate failed/partial chunk state, fail closed unless `--allow-partial`,
  and mark partial outputs so wiki refreshes cannot look clean.
- `graphify/watch.py`: code-only rebuilds preserve upstream v8's stable graph
  behavior while dropping stale edges from changed sources.
- `graphify/build.py` and `graphify/export.py`: legacy or model-produced
  hyperedges missing `id` are normalized with deterministic stable IDs during
  build, merge, and export so semantic-cache reuse cannot re-poison graph
  output.
- `tests/test_install.py`, `tests/test_transcribe.py`, `tests/test_watch.py`,
  `tests/test_cli_semantic_fail_closed.py`, `tests/test_llm_backends.py`,
  `tests/test_cli_export.py`, `tests/test_hypergraph.py`,
  `tests/test_build_merge_hyperedges_and_prune.py`, and
  `tests/test_extract_cli.py`: coverage for the local install, transcript,
  watcher, hyperedge-normalization, and local semantic-refresh safety behavior
  above.

Refresh this section from `git diff upstream/v8..HEAD` before relying on it for
shipping decisions.

## Graphify Architecture Map

Graphify turns a bounded folder or corpus into derived graph artifacts under
`graphify-out/`. The high-level pipeline is:

```text
detect -> extract -> build -> cluster -> analyze -> report/export
```

Main modules:

- `detect.py`: classifies supported files, applies `.graphifyignore`, and
  produces detection metadata.
- `extract.py`: local deterministic AST/code extraction across supported
  languages.
- `llm.py` and skill files: semantic extraction for docs, papers, images, and
  rationale through the active assistant/model surface.
- `build.py`: builds NetworkX graph structures from extraction JSON.
- `cluster.py`: assigns graph communities and cohesion scores.
- `analyze.py`: finds god nodes, surprising connections, suggested questions,
  and graph diffs.
- `report.py`: renders `graphify-out/GRAPH_REPORT.md`.
- `export.py`: writes `graph.json`, HTML, SVG, GraphML, Obsidian, and other
  export formats.
- `serve.py`: exposes `graph.json` through MCP-style graph access.
- `watch.py`: live file watching and code-only rebuilds.
- `hooks.py`: repo-local Git hooks for post-commit and post-checkout code graph
  refreshes, plus post-commit stale flags for committed docs/media.
- `transcribe.py`: local faster-whisper transcription for media inputs.
- `ingest.py` and `security.py`: URL ingestion and local security guards.

Graph output git policy:

- Treat `graphify-out/` as derived local output for Mase's personal/local repos.
  Keep it on disk for agents to query, but keep it ignored and untracked so
  hook refreshes do not create commit churn.
- Keep Graphify hooks installed when a repo uses Graphify. Hooks should refresh
  local ignored graph files after commits/checkouts; they do not require graph
  files to be tracked.
- If a consumer repo already tracks root `graphify-out/`, migrate it with
  `git rm -r --cached --ignore-unmatch graphify-out` after adding `graphify-out/`
  to `.gitignore`; this removes files from the index without deleting local
  graph output.
- Treat `graphify-out/cache/**`, lock files, `graphify-out/cost.json`, and
  `graphify-out/needs_update` as local/runtime state. Committing Graphify output
  for a team/shared graph is an explicit repo policy, not Mase's default.

Graph outputs are derived evidence, not source of truth. For exact edits, read
the real source files even when graph context is available.

## Intended LLM Workflow

Do not paste all of `graphify-out/graph.json` into a prompt. The intended LLM
workflow is:

1. Read `graphify-out/GRAPH_REPORT.md` for god nodes, communities, surprising
   links, and suggested questions.
2. Use focused graph commands for the question at hand:
   - `graphify query "<question>" --graph graphify-out/graph.json`
   - `graphify path "<A>" "<B>" --graph graphify-out/graph.json`
   - `graphify explain "<node>" --graph graphify-out/graph.json`
3. Use graph output as context, then verify exact claims against source files.
4. For repeated tool access, consider MCP through `python -m graphify.serve
   graphify-out/graph.json` when the calling environment supports it.

## Codex Integration Reality

`graphify codex install` writes three repo-local surfaces:

- an `AGENTS.md` `## graphify` section
- `.codex/config.toml` with a SessionStart hook that reports pending semantic
  refresh work
- `.git/hooks/post-commit` and `.git/hooks/post-checkout` Graphify refresh
  hooks

Important current limitation:

- `graphify hook-check` is retained only as a silent legacy/backcompat no-op for
  stale `.codex/hooks.json` entries.
- New installs do not write Graphify `PreToolUse` entries to `.codex/hooks.json`.
- The SessionStart hook is the active startup freshness signal when Codex
  accepts `hookSpecificOutput.additionalContext` for that event.

Practical compensation:

- Repo-local `AGENTS.md` is the reliable always-loaded guidance surface.
- Mase's global guide at `/Users/mase/.codex/docs/reference/graphify.md` is the
  operator policy surface.
- There is no separate installed Codex Graphify skill; semantic refreshes use
  the backend CLI pipeline.

Do not tell Mase that Codex is actively reminded by `hook-check`; the active
Codex hook surface is `graphify codex-session-start` in `.codex/config.toml`.

The local Git hooks are active when installed. They refresh code graph outputs
after commits and branch switches. After commits, docs/media/image changes
write `graphify-out/needs_update`; they do not semantically refresh until
the backend semantic pipeline runs. Use native CLI `graphify update .` for
cheap code-only refreshes, then run `graphify extract . --backend ollama` and
`graphify cluster-only . --backend ollama` when docs/media/image relationships
matter. Model resolution is explicit `--model`, then `OLLAMA_MODEL`, then
Graphify's built-in DeepSeek V4 Pro default. `cluster-only` relabels
communities and refreshes `graphify-out/wiki/` by default.

## Adoption Audit And Propagation

Use the adoption scanner when Mase wants a one-session overview of where
Graphify is installed, stale, incomplete, or newly useful:

```bash
graphify adoption audit --root /Users/mase/Codebase
```

The default report is intentionally chat-native: summary counts, a compact repo
table, blockers, recommended propagation groups, and exact follow-up commands.
Use `--json` only for automation and `--verbose` only when the compact report is
not enough.

After upstream reconciliation, treat propagation as a staged rollout when the
incoming release changed graph IDs, cache/output formats, install surfaces,
activation behavior, or semantic-refresh behavior:

1. reinstall the active CLI from this fork, refresh the global Pi Graphify skill
   with `graphify pi install`, then verify source/version with
   `graphify doctor --require-source`
2. run `graphify adoption audit --root /Users/mase/Codebase`
3. canary one code/update-heavy repo and, when semantic/wiki output matters, one
   semantic repo
4. re-run the audit and only then apply broader propagation

Do not run `graphify extract --force` across every repo by default. Use it only
for repos where release notes, audit output, or canary results show generated
state should be rebuilt from scratch, such as prior same-name node-ID collision
risk.

The normal `/Users/mase/Codebase` audit has default retired/workspace exclusions
in `graphify/adoption.py` so they do not keep surfacing as partial or candidate
targets. As of 2026-06-30, `maser-pm`, `pm-agent-toolkit`, `workshops`, and
`workshops-origin-main` are excluded from routine Graphify propagation. Update
`DEFAULT_AUDIT_EXCLUSIONS` there when Mase changes the maintained repo set.

Apply remains explicit and re-runs the audit before mutating selected repos:

```bash
graphify adoption apply --root /Users/mase/Codebase --scope adopted --local
graphify adoption apply --root /Users/mase/Codebase --scope adopted --semantic --backend ollama
```

For repeatable bounded batches that include adopted repos and explicit
candidate bootstraps, prefer the workflow wrapper:

```bash
graphify adoption propagate \
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

In the Codex AppHarness, trigger this as a `/goal` whose instruction tells Codex
to work from this fork checkout and run the module form:

```text
/goal Run the standard Graphify propagation routine from the fork checkout.

Workdir:
/Users/mase/Codebase/Personal-Projects/graphify

Use:
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

Do not commit or push. Skip dirty repos. Report final audit status.
```

That `/goal` pattern is Codex App specific. It is not a PiHarness slash-command
contract. Pi can run the same CLI from this checkout, but Pi should receive a
normal task prompt or direct terminal command rather than Codex `/goal` syntax.

`--local` is for cheap repo-local fixes such as managed guidance, Codex
activation, hooks, code-only update, and wiki refresh from existing clean graph
state. `--semantic` is the explicit approval to run the standard Ollama Cloud
semantic refresh and then `cluster-only`/wiki refresh. The scanner skips the
Graphify fork itself by default and skips dirty source/config repos unless the
operator passes an explicit dirty override.

`--safe-ollama` uses bounded semantic extraction defaults for multi-repo batches:
single semantic concurrency, smaller per-chunk token budget, longer request
timeout, safe trace output, bounded model output tokens, and a conservative
`.graphifyignore` starter before semantic extraction.

Current model decision: use `deepseek-v4-pro:cloud` as Graphify's built-in
Ollama default. The 2026-07-07 prompt-v2 A/B showed DeepSeek V4 Pro as the
cleanest full-suite candidate under the calibrated semantic harness: it passed
the gate, improved edge coverage and relation quality, and had no forbidden or
source-grounding regression. Routine commands should omit `--model` so explicit
user flags and `OLLAMA_MODEL` can override the default. Treat `glm-5.2:cloud` as
a cost-conscious fallback candidate and `deepseek-v4-flash:cloud` as available
but lower-quality for this harness cycle.

## Codex Guidance Rules

Codex has both a reusable Graphify skill and repo-local activation surfaces.
Keep these aligned but separate:

- Codex skill installed by `graphify install --platform codex` into
  `.codex/skills/graphify/`
- repo-local `AGENTS.md` graphify section
- `.codex/config.toml` SessionStart hook installed by `graphify codex install`
- `/Users/mase/.codex/docs/reference/graphify.md`

Use `graphify codex reconcile` as the safe one-repo Codex activation-surface
primitive before or during multi-repo propagation. It audits repo-local
AGENTS.md, Codex SessionStart config, legacy `.codex/hooks.json` entries, Git
hooks, and graph artifacts in dry-run mode by default. It is not an upstream
fork reconciliation command; upstream reconciliation means Git fetch/release
review/rebase/merge work. Use `--state active`, `--state staged`, or
`--state disabled` to declare the target state, and add `--apply` only after
reviewing the planned changes. Reconciliation removes active triggers for
staged/disabled repos but leaves `graphify-out/`, `.graphifyignore`,
`GRAPHIFY.md`, and historical review artifacts alone.

The SessionStart hook only reports pending semantic refresh work. It does not
extract semantic graph content. Semantic refreshes must run through the backend
CLI pipeline:

```bash
graphify extract . --backend ollama
graphify cluster-only . --backend ollama
```

If Codex blocks that cloud semantic refresh as private-data export, use the
Codex-to-Pi handoff model in `docs/codex-pi-semantic-refresh.md`: Codex can run
or recommend `graphify update .`, then hand Mase a copy-pasteable Pi one-shot or
direct terminal command for the Ollama Cloud semantic extraction and
`cluster-only` label/wiki refresh. Do not treat Codex YOLO mode as the default
solution; it may bypass local approvals/sandboxing but is not a durable or
policy-clear answer to external corpus export.

Codex skill packaging is intentionally present. If upstream changes Codex skill
packaging in the future, preserve the local destination distinction unless Mase
explicitly decides otherwise: Codex-specific skills install under
`.codex/skills/graphify/`, while `.agents/skills/graphify/` is treated as a
shared/legacy location that can collide with Pi discovery.

## Active Install Verification

Verify the active CLI source before using Graphify as evidence for another repo:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

When validating local semantic extraction, first check backend dependencies,
then run a tiny explicit probe instead of starting with a full-repo semantic
refresh:

```bash
graphify doctor --backend ollama
GRAPHIFY_LLM_TRACE=1 graphify doctor --backend ollama --probe
```

`GRAPHIFY_LLM_TRACE=1` logs backend/model, URL host, timing, token counts,
finish reason, and parsed graph counts. It must not print prompt bodies, raw
model output, API keys, or document content.

If it fails, reinstall from this checkout:

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

The OpenAI-compatible Python SDK is installed by Mase's local fork reinstall
command because the direct semantic extraction path uses it for
OpenAI-compatible backends such as `ollama`, `gemini`, `kimi`, `openai`, and
`deepseek`. It remains an optional package dependency for upstream-friendly
packaging, so keep backend preflight checks and the local active-install
command aligned.

When changing backend dependencies, keep these aligned:

- `pyproject.toml` core dependencies and optional extras
- the documented `uv tool install` command for Mase's active fork install
- `graphify doctor` backend checks
- packaged and installed skill install guidance
- every backend routed through `graphify.llm._call_openai_compat`

Local Ollama semantic extraction is intentionally patient and conservative:
chunks run sequentially by default, each chunk prints a start line before model
generation, and trace mode can show whether a non-streaming request has been
sent and when the full response returns. Use `--token-budget <tokens>`,
`--api-timeout <seconds>`, `GRAPHIFY_OLLAMA_NUM_CTX=<tokens>`, or
`GRAPHIFY_LLM_TRACE=1` only when tuning a bounded smoke check or a specific
local model.

Do not use `pip install graphify`, `pip install graphifyy`, or
`uv tool upgrade graphifyy` as a substitute while Mase's local fork fixes are
required.

## Validation Expectations

Choose targeted tests based on the touched behavior:

- Install/source behavior: `uv run pytest tests/test_install.py`
- Codex hook behavior: `uv run pytest tests/test_hooks.py`
- Watch/code-only rebuild behavior: `uv run pytest tests/test_watch.py`
- Transcript/media behavior: `uv run pytest tests/test_transcribe.py`
- Broad CLI or extraction behavior: run the nearest module test first, then
  expand to `uv run pytest tests/ -q` if the change crosses module boundaries.

After changing install-source or skill behavior, also run:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

## Provenance

This document is derived from:

- repo-local `AGENTS.md`
- `ARCHITECTURE.md`
- `git diff upstream/v8..HEAD` as of 2026-05-16
- `/Users/mase/.codex/docs/reference/graphify.md`
- local inspection of `graphify/__main__.py`, `watch.py`, `transcribe.py`, and
  related tests
