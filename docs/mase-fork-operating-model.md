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
updated: 2026-05-13
last_verified: 2026-05-13
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
retrieval_hints:
  - "Graphify local fork"
  - "Mase fork versus upstream"
  - "Codex Graphify backend guidance"
  - "graphify hook-check no-op"
---

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
- Codex guidance source: repo-local `AGENTS.md`, `.codex/config.toml`
  SessionStart reminders, and `/Users/mase/.codex/docs/reference/graphify.md`
  define Mase's Codex usage. Graphify no longer ships or installs a separate
  Codex Graphify skill file.

## Branch And Remote Model

Remotes:

- `origin`: `https://github.com/matzls/graphify.git`
- `upstream`: `https://github.com/safishamsi/graphify.git`

Branch rules:

- Keep upstream mirror branches such as `upstream-v8` clean.
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

## Upstream Release Review Gate

Before rebasing local fixes onto a newer upstream branch, inspect the GitHub
release pages for every incoming tag between the current local mirror and the
target upstream head:

```text
https://github.com/safishamsi/graphify/releases
```

Use the release notes and linked issues as an explicit reconciliation checklist.
For each relevant item, compare upstream's claim to:

- current local patch goals in this document and `AGENTS.md`
- accepted or pending plans in `docs/plans/`
- git history for the touched files, especially `graphify/__main__.py`,
  `graphify/watch.py`, `graphify/transcribe.py`, and their tests
- recent operator history or session notes when they are available in the
  active task context

Classify each overlap before rebasing or after the first conflict:

- Keep: local behavior is still Mase-specific or intentionally stricter.
- Drop: upstream now contains the same fix and the local commit is redundant.
- Adapt: upstream fixed the general product issue, but Mase's Codex runtime or
  installed-skill guidance still needs a local overlay.
- Defer: upstream added a feature that is not needed for Mase's active workflow.

Pay special attention to release bullets about Codex hooks, `AGENTS.md`,
skill files, output paths, cache roots, graph freshness, and install commands.
Those areas overlap with this fork's local operating model and are easy to
misreport if the release page is not checked.

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
- `graphify/watch.py`: code-only rebuilds preserve upstream v8's stable graph
  behavior while dropping stale edges from changed sources.
- `tests/test_install.py`, `tests/test_transcribe.py`, and
  `tests/test_watch.py`: coverage for the local install, transcript, and watcher
  behavior above.

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

Tracked graph outputs:

- Treat `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`,
  `graphify-out/manifest.json`, `graphify-out/community_labels.json`, and
  `graphify-out/.graphify_analysis.json` as durable Graphify outputs when a
  consumer repo tracks `graphify-out/`.
- Treat `graphify-out/cache/**`, lock files, and `graphify-out/needs_update` as
  local/runtime state unless a repo explicitly documents a different policy.
- `graphify-out/.graphify_analysis.json` is intentionally tracked: export/wiki
  flows use it as structured analysis, while `GRAPH_REPORT.md` is the
  human/agent-readable summary.

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
cheap code-only refreshes, then run `graphify extract . --backend <backend>
--model <model>`, `graphify cluster-only . --backend <backend> --model
<model>`, and `graphify export wiki --graph graphify-out/graph.json` when
docs/media/image relationships matter.

## Codex Guidance Rules

Codex no longer has a separate Graphify skill lane. Keep these surfaces aligned
instead:

- repo-local `AGENTS.md` graphify section
- `.codex/config.toml` SessionStart hook installed by `graphify codex install`
- `/Users/mase/.codex/docs/reference/graphify.md`

Use `graphify codex reconcile` as the safe one-repo primitive before or during
multi-repo propagation. It audits repo-local AGENTS.md, Codex SessionStart
config, legacy `.codex/hooks.json` entries, Git hooks, and graph artifacts in
dry-run mode by default. Use `--state active`, `--state staged`, or
`--state disabled` to declare the target state, and add `--apply` only after
reviewing the planned changes. Reconciliation removes active triggers for
staged/disabled repos but leaves `graphify-out/`, `.graphifyignore`,
`GRAPHIFY.md`, and historical review artifacts alone.

The SessionStart hook only reports pending semantic refresh work. It does not
extract semantic graph content. Semantic refreshes must run through the backend
CLI pipeline:

```bash
graphify extract . --backend <backend> --model <model>
graphify cluster-only . --backend <backend> --model <model>
graphify export wiki --graph graphify-out/graph.json
```

If upstream changes Codex skill packaging in the future, treat it as a product
decision: do not reintroduce `graphify/skill-codex.md` or
`/Users/mase/.codex/skills/graphify/SKILL.md` unless Mase explicitly asks for a
separate Codex skill again.

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
