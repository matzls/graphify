# Requirements: Graphify Codex Hook Rollout Hygiene

**Defined:** 2026-05-12
**Core Value:** Graphify activation must converge repos to a single, clean Codex hook representation while preserving unrelated project hooks and making stale semantic graph state visible to the main Codex agent.

## v1.1 Requirements

### Hook Source Hygiene

- [x] **HOOK-01**: `graphify codex install` writes Graphify Codex hooks to repo-local `.codex/config.toml` as the preferred active representation.
- [x] **HOOK-02**: `graphify codex install` does not recreate Graphify-managed `.codex/hooks.json` entries when equivalent TOML hooks exist.
- [x] **HOOK-03**: Graphify migration removes only Graphify-managed duplicate entries from `.codex/hooks.json`.
- [x] **HOOK-04**: Graphify migration preserves unrelated or ambiguous `.codex/hooks.json` entries and reports them for manual consolidation.
- [x] **HOOK-05**: Graphify install dedupes duplicate Graphify `SessionStart` entries inside `.codex/config.toml`.

### Startup Context

- [x] **START-01**: The Graphify `SessionStart` hook emits valid Codex JSON in all success, missing-tool, timeout, and error cases.
- [x] **START-02**: The startup context tells the main Codex agent when `graphify-out/needs_update` exists and recommends `/graphify . --update` before relying on semantic relationships.
- [x] **START-03**: Code-only refresh does not clear semantic refresh markers.

### Propagation Automation

- [ ] **PROP-01**: The OSS fork manager detects Graphify repo-local hook drift when both `.codex/config.toml` and `.codex/hooks.json` contain Graphify-owned hooks.
- [ ] **PROP-02**: The OSS fork manager reports per-target cleanup actions during dry-run propagation.
- [ ] **PROP-03**: The OSS fork manager delegates cleanup to Graphify-owned install/migration commands instead of hardcoding Graphify hook templates.
- [ ] **PROP-04**: Propagation blocks or reports dirty target repos before mutating hook/config files.

### Documentation And Skill Guidance

- [ ] **DOC-01**: `docs/mase-fork-operating-model.md` describes the TOML-first hook model and safe legacy JSON cleanup.
- [ ] **DOC-02**: `/Users/mase/.codex/docs/reference/graphify.md` describes the current `SessionStart` startup-context behavior.
- [ ] **DOC-03**: Packaged and installed Graphify Codex skill guidance describe the single-source hook expectation.

### Tests And Pilot

- [x] **TEST-01**: Tests cover config-only Graphify Codex hook installation.
- [x] **TEST-02**: Tests cover legacy hooks-json-only migration.
- [x] **TEST-03**: Tests cover both-present duplicate cleanup.
- [x] **TEST-04**: Tests cover both-present mixed user/project hooks preservation.
- [x] **TEST-05**: Tests cover duplicate Graphify `SessionStart` dedupe.
- [ ] **PILOT-01**: A pilot repo verifies no Codex duplicate-source warning after cleanup.
- [ ] **PILOT-02**: A pilot repo verifies `graphify codex-session-start <repo>` still returns valid startup JSON.

## Future Requirements

- **AUTO-01**: Broad rollout can update all Graphify-enabled repos after pilot verification.
- **AUTO-02**: A recurring read-only check can report stale semantic markers across selected repos.
- **AUTO-03**: A recurring refresh can run only when stale, only with lock/timeout/status sidecars, and only after manual refresh validation.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct post-commit semantic refresh | Too much runtime and generated-artifact risk before refresh stability is proven. |
| Broad rollout before pilot cleanup passes | The hook hygiene fix should prove itself in one repo first. |
| Automatic pushes or PRs | Fork and consumer repo sync should remain explicit. |
| Deleting non-Graphify hooks | Mixed or ambiguous hooks must be preserved and reported. |
| Mutating `$CODEX_HOME/config.toml` trust-state | Local evidence suggests repo-local duplicate hook files are the active issue. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HOOK-01 | Phase 5 | Complete |
| HOOK-02 | Phase 5 | Complete |
| HOOK-03 | Phase 5 | Complete |
| HOOK-04 | Phase 5 | Complete |
| HOOK-05 | Phase 5 | Complete |
| START-01 | Phase 5 | Complete |
| START-02 | Phase 5 | Complete |
| START-03 | Phase 5 | Complete |
| PROP-01 | Phase 6 | Pending |
| PROP-02 | Phase 6 | Pending |
| PROP-03 | Phase 6 | Pending |
| PROP-04 | Phase 6 | Pending |
| DOC-01 | Phase 7 | Pending |
| DOC-02 | Phase 7 | Pending |
| DOC-03 | Phase 7 | Pending |
| TEST-01 | Phase 5 | Complete |
| TEST-02 | Phase 5 | Complete |
| TEST-03 | Phase 5 | Complete |
| TEST-04 | Phase 5 | Complete |
| TEST-05 | Phase 5 | Complete |
| PILOT-01 | Phase 8 | Pending |
| PILOT-02 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-05-12*
*Last updated: 2026-05-12 after starting milestone v1.1*
