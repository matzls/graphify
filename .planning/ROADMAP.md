# Roadmap: Graphify Codex Hook Rollout Hygiene

## Overview

Milestone v1.1 makes Graphify Codex activation idempotent and safe to propagate. The core target is a TOML-first repo-local hook model: `graphify codex install` should converge a repo to one active Graphify hook representation, remove only Graphify-managed legacy duplicates, preserve unrelated hooks, and provide enough propagation checks to roll the behavior out deliberately.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked as INSERTED

- [x] **Phase 5: TOML-First Graphify Hook Installer** - Make Graphify Codex install converge hook files safely and idempotently. (completed 2026-05-12)
- [ ] **Phase 6: Propagation Hygiene Audit** - Teach the OSS fork manager to detect Graphify hook drift and delegate cleanup.
- [ ] **Phase 7: Guidance And Skill Alignment** - Update fork docs, global guidance, and skill text to match the new hook model.
- [ ] **Phase 8: Pilot Verification And Rollout Readiness** - Prove the cleaned install flow in a pilot repo before broad rollout.

## Phase Details

### Phase 5: TOML-First Graphify Hook Installer
**Goal**: `graphify codex install` writes, migrates, dedupes, and uninstalls Graphify Codex hooks using `.codex/config.toml` as the preferred repo-local hook source.
**Depends on**: Nothing in this milestone
**Requirements**: [HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, START-01, START-02, START-03, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05]
**Canonical refs**:
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/research/SUMMARY.md`
- `docs/mase-fork-operating-model.md`
- `graphify/__main__.py`
- `graphify/watch.py`
- `tests/test_install.py`
- `tests/test_hooks.py`
**Success Criteria** (what must be TRUE):
  1. A fresh config-only install creates Graphify `SessionStart` and PreToolUse/Bash hooks in `.codex/config.toml`.
  2. A legacy hooks-json-only repo is migrated without losing Graphify behavior.
  3. A repo with both TOML and JSON Graphify hooks ends with only the preferred Graphify representation.
  4. Mixed user/project JSON hooks are preserved and reported, not deleted.
  5. Duplicate Graphify `SessionStart` entries are deduped.
  6. `graphify codex-session-start <repo>` still emits parseable Codex JSON.
**Plans**: 2 plans

Plans:
- [x] 05-01: Design TOML hook ownership, migration, and uninstall behavior.
- [x] 05-02: Implement installer migration and regression tests.

### Phase 6: Propagation Hygiene Audit
**Goal**: The OSS fork manager reports Graphify hook hygiene drift and delegates cleanup to the Graphify installer during propagation.
**Depends on**: Phase 5
**Requirements**: [PROP-01, PROP-02, PROP-03, PROP-04]
**Canonical refs**:
- `/Users/mase/.codex/skills/my-oss-fork-manager/SKILL.md`
- `/Users/mase/.codex/skills/my-oss-fork-manager/references/adapter-contract.md`
- `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/adapters/base.py`
- `/Users/mase/.codex/skills/my-oss-fork-manager/scripts/lib/hooks.py`
**Success Criteria** (what must be TRUE):
  1. Dry-run propagation reports per-target Graphify hook drift when both hook sources exist.
  2. The adapter distinguishes Graphify-owned duplicates from mixed or ambiguous user/project hooks.
  3. Approved propagation delegates cleanup through `graphify codex install`.
  4. Dirty target repos are blocked or reported before mutation.
**Plans**: 1 plan

Plans:
- [ ] 06-01: Update OSS fork manager Graphify hook hygiene checks.

### Phase 7: Guidance And Skill Alignment
**Goal**: All Graphify operating guidance describes the current TOML-first hook model and startup-context behavior.
**Depends on**: Phase 5
**Requirements**: [DOC-01, DOC-02, DOC-03]
**Canonical refs**:
- `docs/mase-fork-operating-model.md`
- `/Users/mase/.codex/docs/reference/graphify.md`
- `graphify/skill-codex.md`
- `/Users/mase/.codex/skills/graphify/SKILL.md`
**Success Criteria** (what must be TRUE):
  1. Fork operating docs no longer describe the Codex hook as passive/no-op.
  2. Global Graphify guidance names `.codex/config.toml` as the preferred active hook source.
  3. Packaged and installed skill text match the new installer behavior.
  4. Guidance says legacy JSON cleanup removes only Graphify-managed entries.
**Plans**: 1 plan

Plans:
- [ ] 07-01: Align fork docs, global guide, and Graphify skill text.

### Phase 8: Pilot Verification And Rollout Readiness
**Goal**: A pilot repo proves duplicate-source warnings are gone and startup context still works before broad rollout.
**Depends on**: Phase 5, Phase 6, Phase 7
**Requirements**: [PILOT-01, PILOT-02]
**Canonical refs**:
- `/Users/mase/Codebase/Astral-Code/astral-sora-proto`
- `/Users/mase/Codebase/Personal-Projects/my-second-brain-build`
- `.planning/research/SUMMARY.md`
**Success Criteria** (what must be TRUE):
  1. Pilot repo has one active Graphify Codex hook representation in `.codex/config.toml`.
  2. No Graphify-managed duplicate remains in `.codex/hooks.json`.
  3. Unrelated hooks, if present, are preserved.
  4. Startup JSON is valid with and without `graphify-out/needs_update`.
  5. Rollout report lists remaining Graphify-enabled repos and their hook hygiene status.
**Plans**: 1 plan

Plans:
- [ ] 08-01: Run pilot cleanup verification and prepare broad rollout decision.

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 5. TOML-First Graphify Hook Installer | 2/2 | Complete   | 2026-05-12 |
| 6. Propagation Hygiene Audit | 0/1 | Not started | - |
| 7. Guidance And Skill Alignment | 0/1 | Not started | - |
| 8. Pilot Verification And Rollout Readiness | 0/1 | Not started | - |
