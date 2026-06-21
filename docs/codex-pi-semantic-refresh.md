---
title: "Codex and Pi Semantic Refresh Handoff"
kind: reference
status: active
audience: "agents-maintainers-operators"
canonicality: canonical
doc_id: "graphify-codex-pi-semantic-refresh"
owners:
  - "mase"
created: 2026-06-04
updated: 2026-06-04
last_verified: 2026-06-04
source_of_truth: "./codex-pi-semantic-refresh.md"
related:
  - "./mase-fork-operating-model.md"
  - "../AGENTS.md"
  - "../ARCHITECTURE.md"
  - "/Users/mase/.codex/docs/reference/graphify.md"
tags:
  - "graphify"
  - "codex"
  - "pi"
  - "semantic-refresh"
  - "ollama-cloud"
retrieval_hints:
  - "Codex blocks Graphify semantic refresh"
  - "Pi handoff for Ollama Cloud"
  - "Graphify cloud semantic refresh copy paste"
  - "YOLO mode Graphify"
---

# Codex and Pi Semantic Refresh Handoff

## Purpose

Record the working model for Graphify semantic refreshes when Codex blocks an
Ollama Cloud extraction as private-data export, and define the preferred Pi or
terminal handoff path.

This is a local-fork operational note. It is not a claim that upstream Graphify
or Codex should relax data-export policy.

## Summary

Graphify itself can run the backend semantic pipeline from this fork:

```bash
graphify extract . --backend ollama
graphify cluster-only . --backend ollama
```

The problem is that Codex may reject the cloud-backed extraction before or
during command execution because the command sends repository content to an
external model endpoint. Repo-local `AGENTS.md` authorization helps future
agents understand Mase's intent, but it does not necessarily override Codex's
runtime guardian/export policy.

Preferred policy:

- Codex may run `graphify update .` because it is code-only and no-LLM.
- Codex should report pending semantic refresh work when
  `graphify-out/needs_update` exists or a backend semantic refresh is required.
- Cloud semantic refreshes should run from Pi or a direct terminal command
  unless Mase explicitly chooses a different trusted runner.
- Use smaller Ollama Cloud chunks for reliability; large chunks can produce
  invalid/truncated JSON, which Graphify then bisects and retries.

## Architecture Notes

Relevant code paths:

- `graphify/__main__.py`: CLI routing for `extract`, `cluster-only`, `update`,
  `doctor`, `codex-session-start`, and install commands.
- `graphify/llm.py`: direct backend semantic extraction, OpenAI-compatible
  Ollama calls, trace logging, chunk packing, and adaptive retry on truncation,
  hollow responses, or context overflow.
- `graphify/watch.py`: code-only rebuilds, semantic-stale marker handling, and
  Codex SessionStart notice text.
- `graphify/hooks.py`: Git hook behavior; code changes trigger deterministic
  rebuilds, while docs/media/image changes write `graphify-out/needs_update`.
- `graphify/skill-pi.md`: Pi skill source. The normal Pi setup is one current
  global skill copied from this file to `~/.pi/agent/skills/graphify/SKILL.md`;
  repo-local Graphify activation should stay lightweight and should not duplicate
  the full skill unless a repo intentionally needs a pinned/custom workflow. This
  skill should be kept aligned with the backend CLI pipeline rather than old
  Codex worker/subagent extraction.

Graphify's backend pipeline is:

```text
detect -> AST extraction for code -> LLM semantic extraction for docs/images/papers -> merge -> build -> cluster -> report/export
```

`graphify update .` runs only the deterministic code-graph rebuild. It should
not spend LLM tokens or export corpus content.

`graphify extract . --backend ollama` sends uncached semantic files to the
configured Ollama OpenAI-compatible endpoint. Model resolution is explicit
`--model`, then `OLLAMA_MODEL`, then Graphify's built-in Kimi default. With the
local fork default, `OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`,
and the model can still be an Ollama Cloud model routed through the local
Ollama service.

## YOLO Mode Finding

Codex CLI documents `--yolo` / `--dangerously-bypass-approvals-and-sandbox` as a
mode that bypasses approvals and sandboxing. That may solve failures caused by
local sandbox or approval prompts, but it should not be treated as the Graphify
solution for cloud semantic refreshes.

Reasons:

- A sandbox/approval bypass is not the same as a policy guarantee that Codex
  will allow private-data export to a third-party model endpoint.
- If YOLO does bypass the guardian in practice, it does so by removing the
  safety layer around the exact action we are trying to handle deliberately.
- It is appropriate only for isolated, non-private smoke tests or a hardened
  runner Mase intentionally controls.

Operational conclusion: do not make Codex YOLO the normal Graphify cloud-refresh
path. Prefer Pi or direct terminal execution for the cloud semantic step.

## Recommended Operator Flow

From a target repository that has a Graphify graph and pending semantic work:

```bash
cd /path/to/repo
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
graphify doctor --backend ollama
graphify update .
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify extract . \
  --backend ollama \
  --token-budget 2000 \
  --max-concurrency 1 \
  --api-timeout 180
OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify cluster-only . \
  --backend ollama
```

Use `--token-budget 1200` for a smaller smoke or a model that frequently returns
truncated JSON. Increase only after a representative slice is reliable.

Validate outputs:

```bash
test -s graphify-out/graph.json
test -s graphify-out/GRAPH_REPORT.md
test -s graphify-out/wiki/index.md
graphify query "what are the core abstractions" --graph graphify-out/graph.json
```

## Pi One-Shot Handoff

Pi can run as a terminal one-shot with `pi -p`. If Codex cannot run the cloud
semantic refresh, it should print a copy-pasteable command like this for Mase:

```bash
cd /path/to/repo && pi --name "graphify semantic refresh: $(basename "$PWD")" -p '
You are running an operator-authorized Graphify semantic refresh from Pi, not Codex.
Do not edit source files. Do not send email, publish, commit, or push.

Goal:
- Refresh this repo’s Graphify semantic graph through the backend CLI pipeline.
- Use Mase’s local Graphify fork as the active CLI source.

Run these commands in order and report exact results:
1. graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
2. graphify doctor --backend ollama
3. graphify update .
4. OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify extract . --backend ollama --token-budget 2000 --max-concurrency 1 --api-timeout 180
5. OLLAMA_API_KEY=ollama GRAPHIFY_LLM_TRACE=1 graphify cluster-only . --backend ollama
6. test -s graphify-out/graph.json && test -s graphify-out/GRAPH_REPORT.md
7. test -s graphify-out/wiki/index.md

If any command fails, stop and report the failure. Do not retry with another hosted provider unless Mase explicitly approves.
'
```

For a direct no-agent terminal path, Codex can print only the raw shell commands
from `Recommended Operator Flow`.

## Proposed Minimal Fork Change

A useful local-fork improvement would be a small command that prints the Pi or
terminal handoff text without trying to run the cloud refresh inside Codex.

Candidate command names:

- `graphify semantic-handoff <path> --runner pi`
- `graphify refresh-command <path> --runner pi`
- `graphify codex semantic-handoff <path>`

Suggested behavior:

1. Resolve the target repo path.
2. Verify or warn about the active install source using the same source path
   expected by `graphify doctor --require-source`.
3. Print a copy-pasteable Pi one-shot command and a direct terminal command.
4. Include backend, model, token budget, concurrency, timeout, and trace flags.
5. Never send repo content itself; this command only prints instructions.
6. Optionally include `--smoke` to print a synthetic temp-corpus probe first.

This is better than trying to catch the guardian block inside `graphify extract`
because a Codex guardian rejection can happen outside the Graphify process. If
Graphify never starts, it cannot catch the failure inline. The reliable place to
surface the handoff is Codex guidance, SessionStart notice text, or a separate
command that an agent can run before attempting a blocked refresh.

## Scheduled Runner Option

A separate scheduled script is viable if Mase wants refreshes independent of
active Codex/Pi sessions.

Recommended constraints:

- Use an explicit allowlist of repo roots.
- Check for `graphify-out/needs_update` or stale semantic markers.
- Run `graphify doctor --require-source ...` before any refresh.
- Run `graphify update .` first.
- Run the same bounded Ollama Cloud extraction settings used above.
- Log commands and outputs under `~/.cache/graphify-refresh.log` or a per-repo
  cache directory.
- Do not auto-run on dirty repos unless Mase explicitly approves that policy.
- Do not switch hosted providers automatically.

## Failure Modes

- Codex blocks the cloud command before Graphify starts. Use Pi or direct
  terminal handoff.
- `openai` Python package is missing. Reinstall the fork with the documented
  `uv tool install --force --reinstall ... --with openai ...` command.
- Ollama Cloud returns invalid/truncated JSON for a large chunk. Lower
  `--token-budget` and keep `--max-concurrency 1`.
- The model is not available on the current Ollama account. Run a synthetic
  smoke first or choose an approved accessible cloud/local model.
- `cluster-only` rewrites the report with zero token accounting even after a
  token-spending extraction. Check extraction trace/cost output when token
  evidence matters.

## Verify Commands

Read-only checks used while creating this note:

```bash
graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify
graphify doctor --backend ollama
```

No real repo cloud semantic refresh was run while creating this note.

## Provenance

Derived from local inspection of Graphify docs and source on 2026-06-04:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/mase-fork-operating-model.md`
- `/Users/mase/.codex/docs/reference/graphify.md`
- `graphify/__main__.py`
- `graphify/llm.py`
- `graphify/watch.py`
- `graphify/hooks.py`
- Pi docs for print mode and SDK/extension capabilities under the installed Pi
  package docs.
