# Graphify Local Fork Evaluation Harness

## What This Is

This project is Mase's local Graphify fork and active CLI/skill source. The immediate project goal is to make Graphify activation and rollout behavior observable, idempotent, and safe across consumer repositories.

The current reference consumers are the Graphify fork itself, `/Users/mase/Codebase/Astral-Code/astral-sora-proto`, and `/Users/mase/Codebase/Personal-Projects/my-second-brain-build`, because they expose real Codex hook activation, worktree hook behavior, stale semantic graph markers, and rollout hygiene issues.

## Core Value

Graphify activation must converge repos to a single, clean Codex hook representation while preserving unrelated project hooks and making stale semantic graph state visible to the main Codex agent.

## Current Milestone: v1.1 Graphify Codex Hook Rollout Hygiene

**Goal:** Make `graphify codex install` idempotent, TOML-first, and safe to propagate across Graphify-enabled repos.

**Target features:**
- Prefer repo-local `.codex/config.toml` as the single active Graphify Codex hook source.
- Migrate or remove only Graphify-managed duplicate `.codex/hooks.json` entries when equivalent TOML hooks exist.
- Dedupe duplicate Graphify `SessionStart` entries inside `.codex/config.toml`.
- Preserve unrelated user/project hooks and report ambiguous hook ownership instead of deleting it.
- Teach the OSS fork manager to detect rollout hook hygiene drift and delegate cleanup through Graphify-owned installers.
- Update Graphify docs, global guidance, skill text, and tests to describe the expected single-source hook shape.

## Requirements

### Validated

- ✓ Graphify CLI exists as a local Python package and command surface — existing.
- ✓ Active CLI can be verified against this checkout with `graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify` — existing.
- ✓ Codebase supports deterministic code extraction, semantic LLM extraction, graph build, clustering, report/export, query/explain, watch, Git hooks, and global graph commands — existing.
- ✓ Local Ollama semantic extraction is implemented and detected when local Ollama is available — existing.
- ✓ Repo-local Graphify activation can install AGENTS guidance, Codex hook metadata, and Git refresh hooks — existing.
- ✓ `.graphifyignore` and `.graphifyinclude` support exists in the detection layer — existing.
- ✓ GSD codebase map exists under `.planning/codebase/` — mapped on 2026-05-11.

### Active

- [ ] Make Graphify Codex activation TOML-first and idempotent.
- [ ] Add safe migration/cleanup for Graphify-managed legacy `.codex/hooks.json` entries.
- [ ] Preserve and report unrelated or ambiguous hooks during cleanup.
- [ ] Add regression tests for config-only, hooks-json-only, duplicate both-present, mixed user hooks, and duplicate `SessionStart` cases.
- [ ] Update global Graphify guidance and packaged/installed skill text for the new hook model.
- [ ] Update OSS fork manager propagation checks so rollout reports hook hygiene drift and delegates cleanup to Graphify.
- [ ] Verify the cleaned install flow end-to-end in a pilot repo before broad rollout.

### Out of Scope

- Automatic semantic refresh inside Git hooks as the first implementation step — risk of long-running post-commit work and dirty generated artifacts.
- Treating `graphify-out/` as canonical project truth — graph outputs remain derived evidence.
- Broad scanning of `/Users/mase/Codebase` or other top-level workspaces — evaluation targets must be bounded repos.
- Replacing source-level tests with consumer-repo checks — Second Brain is acceptance evidence, not a substitute for fork tests.
- Building a hosted service or dashboard before the CLI/file harness proves useful.

## Context

This is a brownfield Python CLI/package with a large but well-mapped architecture:

- Runtime modules live in `graphify/`, with CLI routing in `graphify/__main__.py`.
- Detection and scan policy live in `graphify/detect.py`.
- Semantic extraction and backend detection live in `graphify/llm.py`.
- Incremental rebuild and hook behavior live in `graphify/watch.py` and `graphify/hooks.py`.
- Graph outputs are written under `graphify-out/`.
- Mase-specific fork rules are documented in `AGENTS.md`, `docs/mase-fork-operating-model.md`, and `/Users/mase/.codex/docs/reference/graphify.md`.
- Installed Codex skill state must be compared against `graphify/skill-codex.md` and `/Users/mase/.codex/skills/graphify/SKILL.md` before propagation claims.

Current Second Brain findings to preserve:

- The active environment detects local `ollama`, and local Ollama has `gemma4:31b` available.
- The Second Brain root graph was stale relative to repo `HEAD`.
- Root semantic cache was empty while a nested docs/reference graph had semantic cache entries.
- Second Brain has Graphify hooks installed, but no `.graphifyinclude` for `.claude/scripts/` yet.
- `needs_update` alone is insufficient as the only freshness signal.

## Constraints

- **Safety**: The first harness mode must be read-only and must not refresh or rewrite consumer graph artifacts.
- **Privacy**: Harness output must not expose secrets, tokens, or private data from target repos.
- **Fork provenance**: Active CLI checks must prove the installed `graphify` command comes from `/Users/mase/Codebase/Personal-Projects/graphify`.
- **Consumer isolation**: Second Brain changes must happen after a baseline report, not before.
- **Local LLM behavior**: Ollama removes API cost but not runtime risk; refresh automation needs locks, timeouts, and status reporting.
- **Planning tracking**: This `.planning/` setup is local-only for now because `commit_docs` is false.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Harness first, then consumer fixes | Preserves a clean baseline and avoids mixing measurement with mutation. | — Pending |
| Use My Second Brain build as first acceptance target | It is a real, active consumer repo that exposes propagation, coverage, and refresh behavior over time. | — Pending |
| Keep first harness mode read-only | We need status truth before graph refreshes or `.graphifyinclude` edits. | — Pending |
| Treat local Ollama as zero API cost but not zero risk | Runtime time, model quality, JSON failures, and generated-file churn still need guardrails. | — Pending |
| Do not put semantic refresh directly in Git hooks initially | Hooks should flag or queue semantic work until refresh reliability is proven. | — Pending |
| Keep Graphify fork tests and consumer acceptance checks separate | Fork regressions and consumer configuration drift need different diagnoses. | — Pending |
| Prefer `.codex/config.toml` for Graphify Codex hooks | Codex loads both TOML and JSON hook sources when both exist in a layer, causing duplicate hooks and startup warnings. | Accepted for v1.1 |
| Graphify owns hook cleanup behavior | `graphify codex install` creates activation state, so the fork should own idempotent install and safe migration logic. | Accepted for v1.1 |
| OSS fork manager should audit, not duplicate Graphify migration logic | Propagation should detect drift and delegate cleanup to the project-owned installer instead of hardcoding Graphify hook templates. | Accepted for v1.1 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-12 after starting milestone v1.1 for Graphify Codex hook rollout hygiene*
