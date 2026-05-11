# Requirements: Graphify Local Fork Evaluation Harness

**Defined:** 2026-05-11
**Core Value:** Graphify status must be observable before we mutate consumer repos.

## v1 Requirements

### Status Harness

- [ ] **HARNESS-01**: The harness can run against a target repo without modifying files.
- [ ] **HARNESS-02**: The harness emits machine-readable JSON status.
- [ ] **HARNESS-03**: The harness emits a compact Markdown summary for operator review.
- [ ] **HARNESS-04**: The harness reports a clear diagnosis category: fork bug, install/skill drift, consumer config gap, stale graph artifacts, or refresh/runtime issue.

### Fork And Install Health

- [ ] **FORK-01**: The harness reports Graphify fork branch state, dirty state, and local-vs-origin status.
- [ ] **FORK-02**: The harness verifies active CLI source with `graphify doctor --require-source`.
- [ ] **FORK-03**: The harness compares packaged Codex skill guidance with the installed global Graphify skill.
- [ ] **FORK-04**: The harness reports Graphify version and active module path.

### Consumer Activation Health

- [ ] **CONSUMER-01**: The harness reports target repo branch, dirty state, and `HEAD`.
- [ ] **CONSUMER-02**: The harness reports whether Graphify Git hooks are installed in the target repo.
- [ ] **CONSUMER-03**: The harness reports whether target `AGENTS.md` contains Graphify guidance.
- [ ] **CONSUMER-04**: The harness reports `.graphifyignore` and `.graphifyinclude` presence and highlights expected hidden-path coverage gaps.

### Consumer Graph Health

- [ ] **GRAPH-01**: The harness compares graph built commit against target repo `HEAD`.
- [ ] **GRAPH-02**: The harness reports `graphify-out/needs_update` presence.
- [ ] **GRAPH-03**: The harness reports manifest file count and whether expected paths are present.
- [ ] **GRAPH-04**: The harness reports root semantic cache count.
- [ ] **GRAPH-05**: The harness can run read-only `query` and `explain` smoke checks against an existing graph.

### Ollama And Refresh Readiness

- [ ] **OLLAMA-01**: The harness reports detected semantic backend.
- [ ] **OLLAMA-02**: The harness reports local Ollama availability and available model names without requiring API keys.
- [ ] **OLLAMA-03**: The harness distinguishes zero API cost from runtime risk.
- [ ] **REFRESH-01**: A controlled refresh command or procedure can force local Ollama, use a lock, capture logs, and avoid duplicate concurrent refreshes.
- [ ] **REFRESH-02**: Refresh automation remains opt-in until a manual refresh proves stable on Second Brain.

### Regression Coverage

- [ ] **TEST-01**: Tests cover `.graphifyinclude` including `.claude/scripts/**/*.py` without including `.claude/data/`.
- [ ] **TEST-02**: Tests cover stale built-commit detection.
- [ ] **TEST-03**: Tests cover missing root semantic cache detection.
- [ ] **TEST-04**: Tests cover hooks-installed-but-graph-stale diagnosis.
- [ ] **TEST-05**: Tests cover local Ollama zero-cost/readiness reporting with mocked backend availability.

## v2 Requirements

### Automation

- **AUTO-01**: A recurring read-only check can run against Second Brain and record status history.
- **AUTO-02**: A recurring refresh can run only when stale, only with lock/timeout/status sidecars, and only after manual refresh validation.
- **AUTO-03**: Git hooks can queue semantic refresh work without blocking commits or silently mutating generated artifacts post-commit.

### Reporting

- **REPORT-01**: Harness history can show trend lines for graph freshness, cache health, and recurring acceptance failures.
- **REPORT-02**: Harness output can support more than one consumer repo.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct post-commit semantic refresh in v1 | Too much runtime and generated-artifact risk before refresh stability is proven. |
| Hosted dashboard | CLI/file reports are enough to validate the workflow first. |
| Automatic pushes or PRs | Fork and consumer repo sync should remain explicit. |
| Broad workspace scanning | Evaluation should target bounded repos only. |
| Treating Second Brain as the only test suite | It is acceptance evidence; fork tests still carry source-level correctness. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARNESS-01 | Phase 1 | Pending |
| HARNESS-02 | Phase 1 | Pending |
| HARNESS-03 | Phase 1 | Pending |
| HARNESS-04 | Phase 1 | Pending |
| FORK-01 | Phase 1 | Pending |
| FORK-02 | Phase 1 | Pending |
| FORK-03 | Phase 1 | Pending |
| FORK-04 | Phase 1 | Pending |
| CONSUMER-01 | Phase 1 | Pending |
| CONSUMER-02 | Phase 1 | Pending |
| CONSUMER-03 | Phase 1 | Pending |
| CONSUMER-04 | Phase 1 baseline reporting; Phase 2 coverage fix | Pending |
| GRAPH-01 | Phase 1 | Pending |
| GRAPH-02 | Phase 1 | Pending |
| GRAPH-03 | Phase 1 | Pending |
| GRAPH-04 | Phase 1 | Pending |
| GRAPH-05 | Phase 2 | Pending |
| OLLAMA-01 | Phase 1 | Pending |
| OLLAMA-02 | Phase 1 | Pending |
| OLLAMA-03 | Phase 1 | Pending |
| REFRESH-01 | Phase 4 | Pending |
| REFRESH-02 | Phase 4 | Pending |
| TEST-01 | Phase 3 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 3 | Pending |
| TEST-04 | Phase 3 | Pending |
| TEST-05 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-05-11*
*Last updated: 2026-05-11 after GSD project initialization*
