# Phase 1: Read-Only Status Harness - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a repeatable, read-only evaluation harness for checking whether Mase's local Graphify fork, active install, Codex skill copy, target repo activation, target graph artifacts, and local Ollama readiness are in a trustworthy state before any consumer repo refresh or fix work happens.

The first acceptance target is `/Users/mase/Codebase/Personal-Projects/my-second-brain-build`, but the harness should be designed so the same core checks can later be reused for other consumer repos.

</domain>

<decisions>
## Implementation Decisions

### Harness Shape
- **D-01:** Do not make this a public Graphify CLI command in Phase 1. The checks are still being learned from a real consumer repo, so they should start as an internal/dev evaluation harness in this fork.
- **D-02:** Keep the implementation structured enough that it can later be promoted into a Graphify CLI command if the report shape proves stable.
- **D-03:** The harness must be callable repeatably against Second Brain without mutating that target repo.

### Output Contract
- **D-04:** Emit both machine-readable JSON and a short Markdown summary.
- **D-05:** Treat JSON as the source of truth for agents, recurring checks, and trend tracking.
- **D-06:** Keep Markdown concise: overall status, diagnosis, evidence, and recommended next action. It should be agent-readable first and human-readable second.
- **D-07:** Save local reports for tracking. Reports should live in a controlled local evaluation/output location, not as accidental generated churn inside the consumer repo.

### Diagnosis Model
- **D-08:** Use diagnostic-by-default behavior for Phase 1. Stale or partial generated artifacts should usually be warnings, while broken fork/install/source verification should fail.
- **D-09:** Reserve strict acceptance behavior for a later explicit mode. Strict mode can turn selected warnings, such as stale target graphs, into failures for recurring acceptance checks.
- **D-10:** Use four severity levels: `pass`, `warn`, `fail`, and `info`.
- **D-11:** Active CLI not installed from `/Users/mase/Codebase/Personal-Projects/graphify` is `fail`.
- **D-12:** Installed Codex skill drift from packaged `graphify/skill-codex.md` is `warn` by default; if the drift affects Graphify operating instructions, source verification, hooks, or refresh guidance, classify it as `fail`.
- **D-13:** Target graph built commit differing from target HEAD is `warn` by default.
- **D-14:** Missing expected hidden-path coverage for the Second Brain profile, such as `.claude/scripts/**/*.py`, is `fail` for that profile.
- **D-15:** Missing semantic cache is `warn` before any approved refresh expectation exists, and `fail` only when a refresh was expected to have produced cache artifacts.
- **D-16:** Ollama unavailable is `warn` in read-only status mode and `fail` in generation/stress mode.
- **D-17:** Small generation passing while the larger stress check times out is `warn` by default, unless strict mode later decides otherwise.

### Second Brain Targeting
- **D-18:** Support Second Brain-specific expectations in Phase 1.
- **D-19:** Express those expectations through a target profile or profile-like configuration rather than hardcoding one-off Second Brain logic throughout the harness.
- **D-20:** The Second Brain profile should cover expected Graphify activation, hidden path inclusion needs, relevant ignore/include behavior, root graph freshness, semantic cache status, and smoke-query concepts.

### Ollama And Local Generation
- **D-21:** Include local generation checks, because the implementation uses local Ollama and therefore does not create paid API cost exposure.
- **D-22:** Separate readiness checks from generation/stress checks.
- **D-23:** Readiness checks should detect the active backend, verify local Ollama is reachable, report available/expected models, and report zero priced backend cost separately from runtime risk.
- **D-24:** Generation checks should include one small local smoke test and one larger stress-style local test in a temporary harness-controlled area.
- **D-25:** Generation/stress checks must not perform an implicit semantic refresh of Second Brain in Phase 1.

### the agent's Discretion
The agent may choose the internal module/file layout, exact report directory under `.planning` or another local harness output path, fixture shape for the generation stress test, and the exact JSON schema details, as long as the decisions above are preserved and tests can validate the contract.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Defines the project goal, core value, and harness-first operating context.
- `.planning/REQUIREMENTS.md` — Defines Phase 1 status, fork/install, consumer activation, graph health, and Ollama requirements.
- `.planning/ROADMAP.md` — Defines the Phase 1 boundary, success criteria, and later phases.
- `.planning/STATE.md` — Current GSD project state and local-only planning note.

### Codebase Maps
- `.planning/codebase/ARCHITECTURE.md` — Current architecture map for Graphify's runtime modules and data flow.
- `.planning/codebase/STRUCTURE.md` — Existing source/test layout and likely homes for new internal harness code.
- `.planning/codebase/TESTING.md` — Existing pytest patterns and external-boundary mocking guidance.
- `.planning/codebase/CONCERNS.md` — Current fork risks, generated artifact concerns, and semantic/cache fragility.

### Fork And Graphify Operating Guides
- `docs/mase-fork-operating-model.md` — Local fork model, active CLI source rules, upstream/local delta, and Codex skill sync expectations.
- `ARCHITECTURE.md` — Upstream Graphify architecture summary.
- `/Users/mase/.codex/docs/reference/graphify.md` — Mase's global Graphify operating guide for repo activation and scan safety.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/__main__.py`: Existing public CLI router. Phase 1 should avoid adding a public command here unless planning proves a small private hook is unavoidable.
- `graphify/llm.py`: Backend detection, Ollama defaults, model selection, pricing, timeout, chunking, and extraction helpers are the likely source of truth for Ollama readiness and generation behavior.
- `graphify/detect.py`: File collection, `.graphifyignore`, and `.graphifyinclude` behavior should be reused for target coverage checks rather than reimplemented with ad hoc path rules.
- `graphify/watch.py`: Existing freshness and `needs_update` semantics should inform graph freshness diagnosis.
- `graphify/hooks.py`: Existing hook installation and hook-check behavior should inform consumer repo activation checks.

### Established Patterns
- Tests live under `tests/test_*.py` and should use `tmp_path`, real files, and subprocess only where process boundaries matter.
- Default tests should avoid live LLM/network calls. Any live Ollama generation/stress behavior should be explicitly gated or separated from the default unit suite.
- Existing suite uses direct helper tests plus focused subprocess CLI tests where appropriate.
- Generated outputs should be treated as evidence, not source. Avoid creating noisy target repo artifacts in default checks.

### Integration Points
- The harness should inspect the Graphify fork repo, active installed CLI, installed Codex skill, and one target consumer repo.
- The first target profile should point to `/Users/mase/Codebase/Personal-Projects/my-second-brain-build`.
- The report writer should save local baseline reports for tracking without modifying the target repo.

</code_context>

<specifics>
## Specific Ideas

- Start with an internal/dev harness rather than a public CLI command.
- JSON plus short Markdown is the desired output shape.
- Default diagnosis should be informative and conservative, not overly strict.
- Second Brain checks should be profile-driven but specific enough to catch the current hidden `.claude/scripts/**/*.py` coverage issue.
- Local Ollama generation checks are in scope, including a larger stress-style test, because API cost is not the constraint.
- The harness should make clear that local Ollama has zero priced backend cost while still carrying runtime and reliability risk.

</specifics>

<deferred>
## Deferred Ideas

- Promote the harness into a public Graphify CLI command after report shape and diagnosis semantics stabilize.
- Add strict recurring acceptance mode that can fail on stale consumer graph state or generation stress instability.
- Run an approved semantic refresh of Second Brain and then use post-refresh expectations as stricter assertions in later phases.

</deferred>

---

*Phase: 1-Read-Only Status Harness*
*Context gathered: 2026-05-11*
