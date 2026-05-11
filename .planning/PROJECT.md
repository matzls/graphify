# Graphify Local Fork Evaluation Harness

## What This Is

This project is Mase's local Graphify fork and active CLI/skill source. The immediate project goal is to add a reliable evaluation harness that tells us whether Graphify fork updates, installed CLI/skill propagation, repo activation, and real consumer graphs are working as expected.

The main reference consumer is `/Users/mase/Codebase/Personal-Projects/my-second-brain-build`, because it is actively used and exposes real Graphify behavior over time: hooks, `.graphifyignore`, hidden `.claude/scripts/` coverage, local Ollama semantic extraction, stale graph output, semantic cache, and query/explain usefulness.

## Core Value

Graphify status must be observable before we mutate consumer repos: the harness should separate fork bugs, install/skill propagation drift, consumer configuration gaps, and stale generated graph artifacts.

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

- [ ] Build a read-only Graphify status/evaluation harness in this fork.
- [ ] Use My Second Brain build as the first recurring consumer acceptance target.
- [ ] Report status across four layers: fork health, installed CLI/skill health, consumer activation health, and consumer graph health.
- [ ] Detect local Ollama availability and whether semantic refresh can run with zero API cost.
- [ ] Detect stale or partial graph output, including built commit vs `HEAD`, semantic cache presence, `needs_update`, and hidden-path coverage.
- [ ] Add regression tests for the status checks and Graphify behaviors exposed by Second Brain.
- [ ] Iterate Second Brain activation/configuration only after a baseline harness report exists.

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
*Last updated: 2026-05-11 after GSD codebase mapping and project initialization*
