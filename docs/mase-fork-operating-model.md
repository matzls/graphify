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
updated: 2026-05-02
last_verified: 2026-05-02
source_of_truth: "./mase-fork-operating-model.md"
related:
  - "../AGENTS.md"
  - "../ARCHITECTURE.md"
  - "../README.md"
  - "/Users/mase/.codex/docs/reference/graphify.md"
tags:
  - "graphify"
  - "fork"
  - "codex"
  - "skills"
retrieval_hints:
  - "Graphify local fork"
  - "Mase fork versus upstream"
  - "Codex Graphify skill sync"
  - "graphify hook-check no-op"
---

# Mase Graphify Fork Operating Model

## Purpose

This repository is Mase's local fork of upstream Graphify. Treat it as both a
normal Python project and an operator-owned integration surface for Codex.

The main job of this document is to stop future agents from treating this repo
as a generic upstream checkout. Local changes may exist to support Mase's Codex
setup, and the installed CLI and installed Codex skill can drift from the source
files in this repo unless explicitly synchronized.

## When To Use

Read this document before:

- changing Graphify code, skills, hooks, install behavior, or watcher behavior
- explaining how Mase's Graphify install differs from upstream
- reinstalling the active `graphify` CLI
- changing `/Users/mase/.codex/skills/graphify/SKILL.md`
- changing `/Users/mase/.codex/docs/reference/graphify.md`
- running `graphify codex install` or advising that it creates an active Codex
  reminder

## Repository Roles

This checkout has three roles:

- Source fork: local code lives here and should be compared against
  `upstream/v6` before claims about local changes.
- Active install source: Mase's `graphify` CLI should be installed from this
  checkout, not from PyPI, while local fork fixes matter.
- Skill source: `graphify/skill-codex.md` is the source material for the global
  Codex skill at `/Users/mase/.codex/skills/graphify/SKILL.md`, plus local
  operating notes from `/Users/mase/.codex/docs/reference/graphify.md`.

## Branch And Remote Model

Remotes:

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Branch rules:

- Keep upstream mirror branches such as `v6` clean.
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
git diff --stat upstream/v6..HEAD
git diff --name-status upstream/v6..HEAD
git log --oneline --decorate --max-count=12
```

## Current Local Delta From Upstream

As last verified on 2026-05-02 against `upstream/v6`, the local fork carries
Mase-specific or recently upstream-oriented changes in these areas:

- `AGENTS.md`: fork operating notes for Mase's local setup.
- `graphify/__main__.py`: install-source diagnostics via
  `graphify doctor --require-source`, Codex/agent install guidance, and related
  platform install behavior.
- `graphify/skill-codex.md`: Mase/Codex-specific preflight, bounded root,
  `.graphifyignore`, active fork verification, and freshness guidance.
- `graphify/skill.md`: packaging or skill text alignment with the fork.
- `graphify/transcribe.py`: stable transcript paths that include media suffix
  and a stable hash so same-stem media files such as `sample.mp3` and
  `sample.mp4` do not collide.
- `graphify/watch.py`: code-only rebuilds preserve semantic community labels
  using `graphify-out/community_labels.json` or the previous
  `GRAPH_REPORT.md`.
- `tests/test_install.py`, `tests/test_transcribe.py`, and
  `tests/test_watch.py`: coverage for the local install, transcript, and watcher
  behavior above.

Refresh this section from `git diff upstream/v6..HEAD` before relying on it for
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
  refreshes.
- `transcribe.py`: local faster-whisper transcription for media inputs.
- `ingest.py` and `security.py`: URL ingestion and local security guards.

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

`graphify codex install` writes two repo-local surfaces:

- an `AGENTS.md` `## graphify` section
- `.codex/hooks.json` with a PreToolUse hook that runs `graphify hook-check`

Important current limitation:

- `graphify hook-check` currently exits silently in Codex Desktop.
- This is intentional because Codex Desktop rejected the old
  `hookSpecificOutput.additionalContext` payload.
- Therefore `.codex/hooks.json` is not currently an active reminder surface in
  Codex Desktop.

Practical compensation:

- Repo-local `AGENTS.md` is the reliable always-loaded guidance surface.
- The global skill at `/Users/mase/.codex/skills/graphify/SKILL.md` is the
  explicit invocation surface.
- Mase's global guide at `/Users/mase/.codex/docs/reference/graphify.md` is the
  operator policy surface.

Do not tell Mase that Codex is actively reminded by the hook unless
`graphify hook-check` has been changed and verified in the active Codex runtime.

## Skill And Guide Sync Rules

When Graphify skill behavior changes, compare and update these surfaces
intentionally:

- `graphify/skill-codex.md`
- `/Users/mase/.codex/skills/graphify/SKILL.md`
- `/Users/mase/.codex/docs/reference/graphify.md`

The global installed skill may include local Codex operating sections that are
not present in upstream `skill-codex.md`. Do not overwrite it blindly.

Mase may edit the installed Codex skill directly in `/Users/mase/.codex` during
workflow or skill-improvement sessions. Treat both copies as potentially
valuable until proven otherwise. Before syncing, replacing, or deleting either
copy, inspect:

- file diffs between the repo source and installed skill
- git history in this repo for `graphify/skill-codex.md`
- git history in `/Users/mase/.codex` for `skills/graphify/SKILL.md` and
  `docs/reference/graphify.md`
- current working-tree status in both repositories

Default rule: preserve both sides, then make an explicit sync decision. Do not
silently prefer the repo copy or the `.codex` copy based only on path or
packaging role.

Do not remove the packaged skill files from this repo as a drift workaround.
They are part of Graphify's distributable platform support. If Mase wants a
single source of truth, keep the repo skill as the package source and treat the
installed `.codex` skill as a local deployment/overlay that must be reconciled
back intentionally.

Useful checks:

```bash
diff -u graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md
git log --oneline -- graphify/skill-codex.md
git -C /Users/mase/.codex log --oneline -- skills/graphify/SKILL.md docs/reference/graphify.md
git -C /Users/mase/.codex status --short -- skills/graphify/SKILL.md docs/reference/graphify.md
rg -n "codex install|hook-check|GRAPH_REPORT|community_labels|doctor" \
  graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md \
  /Users/mase/.codex/docs/reference/graphify.md
```

## Upstream Skill Sync Procedure

Use this procedure after pulling or rebasing onto newer upstream Graphify when
`graphify/skill-codex.md` may have changed. This is a repo maintenance task,
not a separate skill: keep the procedure here and keep `AGENTS.md` pointing to
it.

Goal: decide what to carry from the packaged repo skill into the installed
Codex skill without breaking local `.codex` guidance.

1. Inspect both repositories before editing:

```bash
git status --short --branch
git -C /Users/mase/.codex status --short -- skills/graphify/SKILL.md docs/reference/graphify.md
git log --oneline --max-count=8 -- graphify/skill-codex.md
git -C /Users/mase/.codex log --oneline --max-count=8 -- skills/graphify/SKILL.md docs/reference/graphify.md
```

2. Compare the packaged skill to the installed skill:

```bash
diff -u graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md
rg -n "GRAPH_REPORT|graph.html|graph.json|community_labels|rationale|wiki|mcp|codex install|hook-check|doctor|graphify_semantic_new" \
  graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md \
  /Users/mase/.codex/docs/reference/graphify.md
```

3. Classify each delta before patching:

- Port: upstream behavior that matches current code/tests and improves the
  installed skill, such as new valid node types, output files, verification
  commands, or corrected install guidance.
- Adapt: upstream intent that is useful but path-, runtime-, or
  Codex-specific details need correction for Mase's setup.
- Preserve: local `.codex` operating guidance, especially bounded repo scans,
  strict `.graphifyignore`, no PyPI fallback, active fork verification,
  Second Brain separation, derived-output framing, and optional hook activation
  only after output review.
- Defer: output-surface expansion or product choices, such as advertising a new
  optional export, unless Mase explicitly wants that behavior in the global
  skill.

4. Patch surgically. Do not copy `graphify/skill-codex.md` over
   `/Users/mase/.codex/skills/graphify/SKILL.md`. Keep custom `.codex` sections
   unless there is an explicit replacement decision.

5. When importing an upstream procedure block, verify path contracts end to end.
   For example, a semantic extraction merge step must write the same
   `.graphify_semantic_new.json` path that later cache and graph-merge steps
   read. If useful for auditability, mirror the same payload into
   `graphify-out/.graphify_semantic_new.json`, but do not make the mirror the
   only copy unless all later reads are updated too.

6. Update the global operating guide only when the change affects operator
   policy, not merely internal prompt wording:

```bash
/Users/mase/.codex/docs/reference/graphify.md
```

7. Validate the documentation sync:

```bash
git -C /Users/mase/.codex diff --check -- skills/graphify/SKILL.md docs/reference/graphify.md
diff -u graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md
rg -n "rationale|community_labels|graphify_semantic_new|wiki|GRAPH_REPORT|graph.html|graph.json" \
  graphify/skill-codex.md /Users/mase/.codex/skills/graphify/SKILL.md \
  /Users/mase/.codex/docs/reference/graphify.md
```

Keep single-use carry-over decisions out of this operating model. If a specific
upstream-to-`.codex` skill upgrade has been accepted but not implemented yet,
track it as a plan under `docs/plans/` and link to that plan from the task or
PR instead of embedding the decision here.

Store future accepted Graphify skill-sync plans in the same folder, using one
plan file per upgrade decision. This keeps durable workflow rules in this
operating model and implementation-specific decisions in `docs/plans/`.

Current example plan:

- `docs/plans/safe-graphify-skill-upgrade.md`

## Active Install Verification

Verify the active CLI source before using Graphify as evidence for another repo:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

If it fails, reinstall from this checkout:

```bash
uv tool install --force --reinstall /Users/mase/Codebase/Personal-Projects/graphify \
  --with faster-whisper \
  --with yt-dlp \
  --with watchdog
```

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
- `git diff upstream/v6..HEAD` as of 2026-05-02
- `/Users/mase/.codex/docs/reference/graphify.md`
- local inspection of `graphify/__main__.py`, `skill-codex.md`, `watch.py`,
  `transcribe.py`, and related tests
