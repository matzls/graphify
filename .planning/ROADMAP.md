# Roadmap: Graphify Local Fork Evaluation Harness

## Overview

The first milestone makes Graphify's local fork behavior measurable before changing consumer repos. Work starts with a read-only harness that captures the current state of the fork, installed CLI/skill, consumer activation, graph freshness, semantic cache, and local Ollama readiness. Only after the baseline is trustworthy do we patch the Second Brain target, add regression coverage, and evaluate controlled refresh automation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked as INSERTED

- [ ] **Phase 1: Read-Only Status Harness** - Build the baseline evaluator without mutating target repos.
- [ ] **Phase 2: Second Brain Baseline And Coverage Fix** - Use the harness to capture baseline, then repair target coverage configuration.
- [ ] **Phase 3: Regression Coverage For Exposed Failure Modes** - Lock the harness and fork behaviors into tests.
- [ ] **Phase 4: Controlled Local-Ollama Refresh Path** - Prove manual refresh safety before any recurring automation.

## Phase Details

### Phase 1: Read-Only Status Harness
**Goal**: A read-only harness can inspect Graphify fork health, installed CLI/skill health, target repo activation, target graph freshness, and Ollama readiness without changing the target repo.
**Depends on**: Nothing (first phase)
**Requirements**: [HARNESS-01, HARNESS-02, HARNESS-03, HARNESS-04, FORK-01, FORK-02, FORK-03, FORK-04, CONSUMER-01, CONSUMER-02, CONSUMER-03, CONSUMER-04, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, OLLAMA-01, OLLAMA-02, OLLAMA-03]
**Canonical refs**:
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `docs/mase-fork-operating-model.md`
- `/Users/mase/.codex/docs/reference/graphify.md`
**Success Criteria** (what must be TRUE):
  1. Running the harness against `/Users/mase/Codebase/Personal-Projects/my-second-brain-build` does not modify that repo.
  2. Harness JSON includes all four status layers: fork, installed CLI/skill, consumer activation, consumer graph.
  3. Harness Markdown summary clearly says whether the target is current, stale, misconfigured, or refresh-ready.
  4. Harness detects local Ollama availability and reports zero API cost separately from runtime risk.
  5. Harness identifies the current Second Brain root graph as stale or partial when run before any refresh.
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Design status schema and read-only probes.
- [ ] 01-02-PLAN.md — Implement private script harness and baseline Second Brain report.

### Phase 2: Second Brain Baseline And Coverage Fix
**Goal**: Use the harness output to safely configure Second Brain coverage, especially hidden `.claude/scripts/`, without running semantic refresh yet.
**Depends on**: Phase 1
**Requirements**: [CONSUMER-04, GRAPH-05]
**Canonical refs**:
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/codebase/STRUCTURE.md`
- `/Users/mase/Codebase/Personal-Projects/my-second-brain-build/AGENTS.md`
- `/Users/mase/Codebase/Personal-Projects/my-second-brain-build/.graphifyignore`
**Success Criteria** (what must be TRUE):
  1. A saved baseline report exists before any Second Brain config edits.
  2. Second Brain has a narrow `.graphifyinclude` for expected hidden source paths.
  3. Runtime/private/generated paths remain excluded by `.graphifyignore`.
  4. A post-config harness run changes diagnosis from coverage gap to configured-but-stale until refresh occurs.
  5. Existing graph query/explain smoke checks are either useful or explicitly reported as blocked by stale artifacts.
**Plans**: 2 plans

Plans:
- [ ] 02-01: Capture immutable baseline and decide target coverage expectations.
- [ ] 02-02: Patch Second Brain `.graphifyinclude` and rerun harness.

### Phase 3: Regression Coverage For Exposed Failure Modes
**Goal**: Add fork-level tests so the Second Brain findings become durable regression coverage rather than one-off observations.
**Depends on**: Phase 1
**Requirements**: [TEST-01, TEST-02, TEST-03, TEST-04, TEST-05]
**Canonical refs**:
- `.planning/codebase/TESTING.md`
- `.planning/codebase/CONCERNS.md`
- `tests/test_detect.py`
- `tests/test_watch.py`
- `tests/test_ollama.py`
- `tests/test_incremental.py`
**Success Criteria** (what must be TRUE):
  1. Tests prove `.graphifyinclude` can include `.claude/scripts/**/*.py` without including `.claude/data/`.
  2. Tests prove stale built-commit status is reported.
  3. Tests prove missing root semantic cache status is reported.
  4. Tests prove hooks-installed-but-stale-graph is not treated as healthy.
  5. Tests prove local Ollama readiness and zero-cost reporting can be determined without a live paid backend.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Add harness unit tests and fixtures.
- [ ] 03-02: Add integration-style status checks around existing Graphify artifacts.

### Phase 4: Controlled Local-Ollama Refresh Path
**Goal**: Prove a guarded local-Ollama semantic refresh can update Second Brain graph artifacts safely before considering recurring automation.
**Depends on**: Phase 2 and Phase 3
**Requirements**: [REFRESH-01, REFRESH-02]
**Canonical refs**:
- `.planning/codebase/CONCERNS.md`
- `graphify/llm.py`
- `graphify/__main__.py`
- `graphify/watch.py`
- `/Users/mase/Codebase/Personal-Projects/my-second-brain-build/graphify-out/GRAPH_REPORT.md`
**Success Criteria** (what must be TRUE):
  1. A refresh command/procedure can force backend `ollama`.
  2. Refresh uses a lock or equivalent duplicate-run guard.
  3. Refresh logs enough status to diagnose timeout, malformed JSON, partial semantic extraction, and cache behavior.
  4. After one approved refresh, harness confirms built commit matches target `HEAD`, `.claude/scripts/` is represented, and root semantic cache exists where expected.
  5. Recurring refresh remains disabled until the manual refresh evidence is reviewed.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Add controlled refresh procedure and runbook/status sidecar.
- [ ] 04-02: Run approved Second Brain refresh and decide recurring check vs recurring refresh.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Read-Only Status Harness | 0/2 | Not started | - |
| 2. Second Brain Baseline And Coverage Fix | 0/2 | Not started | - |
| 3. Regression Coverage For Exposed Failure Modes | 0/2 | Not started | - |
| 4. Controlled Local-Ollama Refresh Path | 0/2 | Not started | - |
