---
title: "Graphify Hyperedge ID Normalization Patch Plan"
kind: plan
status: complete
audience: "agents-operators"
canonicality: canonical
created: 2026-07-01
updated: 2026-07-26
source_of_truth: "./graphify-hyperedge-id-normalization-plan.md"
related:
  - "../../AGENTS.md"
  - "../mase-fork-operating-model.md"
  - "../../ARCHITECTURE.md"
tags:
  - graphify
  - semantic-refresh
  - hyperedges
  - local-fork
---

## Summary

Status as of 2026-07-26: complete with the operational deviation recorded
below. The shipped patch prevents the reproducible `KeyError: 'id'` failure when
an existing graph or semantic cache contains otherwise-valid hyperedges missing
an `id` field.

The local target that exposed this is:

```text
/Users/mase/Codebase/Personal-Projects/my-second-brain-build/graphify-out/graph.json
```

Observed evidence from that artifact:

- `41` hyperedges in the existing graph
- `23` hyperedges missing `id`
- semantic cache also has malformed hyperedges: `15` cached hyperedges, `5`
  missing `id`
- minimal temp repro and real-artifact repro both fail in `build_merge()` with
  `KeyError: 'id'` before any Ollama dependency is required

Current upstream `safishamsi/graphify` `v8` still contains the same unsafe
`attach_hyperedges()` implementation as of a 2026-07-01 raw-source check, so
this should be maintained as a small local fork delta until upstream lands an
equivalent fix.

## Completion Record (2026-07-26)

The task and checkpoint checkboxes below are retained as the original execution
contract rather than retroactively checked without contemporaneous evidence.
This completion record is the authoritative disposition.

### Accepted Evidence

- Commit `651c807` centralizes hyperedge normalization in `graphify/build.py`
  and applies it at build, merge, attach, and export boundaries. It preserves
  existing non-empty IDs, synthesizes deterministic IDs for meaningful
  missing-ID hyperedges, normalizes member aliases and source paths, and drops
  unusable entries safely.
- The same commit adds focused regressions in `tests/test_hypergraph.py`,
  `tests/test_build_merge_hyperedges_and_prune.py`, and
  `tests/test_extract_cli.py` for existing graph metadata, incremental merge,
  fresh semantic output, semantic-cache reuse, export normalization, and
  absolute-source carry-forward. Its recorded validation was 40 passing tests
  plus a passing Ruff check.
- Fresh closeout validation included those three files in the prescribed
  five-file selection and passed with `197 passed` and one existing Hypothesis
  collection warning.
- The active Graphify 0.9.26 CLI now passes
  `graphify doctor --require-source` for this checkout. Installed `build.py` and
  `export.py` directly match source at SHA-256
  `5734dd1639b4707fbc7d559d7946b9e911a02855b21835a4579c0b83e3651ecc` and
  `28dde0d477254875222b83980583cd7e668054249a0fdcc1c3e0547d6be72456`;
  the installed entry and activation modules also match source. The prior
  closeout records that installation followed focused validation; the original
  installer transcript is not retained in this plan.
- No cache-schema or extraction-prompt change was required for the patch, and
  no broad consumer refresh was performed as part of its implementation.

### Operational Deviation And Residual Evidence Limits

- Task 5's real-incident `build_merge()` and
  `cluster-only . --no-label --no-viz` commands are not preserved as durable
  completion evidence and were not rerun here. The current closeout explicitly
  forbids touching the dirty `my-second-brain-build` repository. This plan closes
  the shipped normalization patch; any future Second Brain recovery or semantic
  refresh remains a separately authorized operational action.
- The original incident counts and upstream snapshot are historical observations
  from 2026-07-01 and were not reverified during this closeout.
- Current source treats missing, blank, and whitespace-only IDs as unusable and
  synthesizes replacements when at least two valid members remain. The focused
  suite does not name a separate whitespace-only-ID regression; further schema
  tightening belongs to a new task if real evidence requires it.

## Goal

Graphify should tolerate legacy or model-produced hyperedges that omit `id`
without crashing during `extract`, `update`, `build_merge`, `cluster-only`, or
semantic-cache reuse.

## Success State

- Existing malformed hyperedges do not raise `KeyError: 'id'` during merge.
- Valid missing-ID hyperedges are assigned deterministic stable IDs.
- Unusable hyperedges are dropped safely with no crash.
- Semantic cache entries with missing-ID hyperedges cannot re-poison future
  semantic refreshes.
- Regression tests prove the reproduced failure no longer occurs.
- Active `graphify` CLI is reinstalled from this checkout only after tests pass.

## Non-Goals

- Do not redesign the hyperedge schema beyond missing-ID normalization.
- Do not change the LLM extraction prompt unless tests show prompt guidance is
  the only durable prevention path.
- Do not manually patch installed `uv tool` site-packages.
- Do not broad-refresh all Graphify consumer repos.
- Do not block the Pi session backward-ingestion rollout on this tooling fix.

## Responsibility Boundaries

- `graphify/build.py` owns graph-ingestion normalization: graph JSON, semantic
  fragments, and merge-time carried hyperedges should be canonical before they
  become graph metadata.
- `graphify/export.py` owns output/export safety: `attach_hyperedges()` should
  remain defensive even if an upstream caller passes malformed metadata.
- `graphify/cache.py` may preserve cache portability, but cache read/write
  should not need to understand merge semantics if build/export normalization is
  robust.
- Tests own the reproducible contract: the failure must be caught without
  calling Ollama or depending on model output.

## Architecture Decisions

1. Prefer deterministic ID synthesis for otherwise-valid missing-ID hyperedges.
   Dropping them avoids the crash but loses semantic group relationships and
   leaves old artifacts less useful. A synthesized ID can be based on stable
   hyperedge content such as `source_file`, `relation`, `label`, and normalized
   member IDs.
2. Keep `attach_hyperedges()` defensive. It should not use `h["id"]` on
   untrusted existing graph metadata; it should ignore or normalize non-dict and
   missing-ID entries safely.
3. Centralize normalization enough to avoid divergent behavior. If a helper is
   introduced in `build.py`, it should be usable by both `build_from_json()` and
   `export.attach_hyperedges()` without creating a new import cycle.
4. Preserve valid existing IDs exactly. Only synthesize when `id` is missing or
   blank.

## Task List

### Task 1: Add focused regression coverage

**Description:** Capture the exact failure class before changing behavior.

**Acceptance criteria:**

- [ ] A unit test proves `build_merge()` does not crash when the existing
      `graph.json` contains a hyperedge missing `id`.
- [ ] A unit test proves `attach_hyperedges()` does not crash when existing graph
      metadata already contains a hyperedge missing `id`.
- [ ] A unit or integration-style test covers semantic-cache/fresh semantic
      input with a missing-ID hyperedge so the cache cannot reintroduce the bug.

**Likely files touched:**

```text
tests/test_build_merge_hyperedges_and_prune.py
tests/test_hypergraph.py
```

**Verify commands:**

```bash
uv run pytest \
  tests/test_build_merge_hyperedges_and_prune.py \
  tests/test_hypergraph.py \
  -q
```

**Dependencies:** None.

### Task 2: Implement hyperedge ID normalization

**Description:** Add a small canonicalization path for hyperedge dictionaries so
missing IDs are handled before merge/export deduplication.

**Acceptance criteria:**

- [ ] Hyperedges with existing non-empty `id` keep that ID unchanged.
- [ ] Hyperedges with missing/blank `id` and at least two valid member nodes get
      a deterministic stable ID.
- [ ] Hyperedges that are not dictionaries or cannot be made meaningful are
      skipped safely.
- [ ] Member alias normalization (`members`, `node_ids`) continues to work.
- [ ] Absolute `source_file` relativization behavior remains unchanged.

**Likely files touched:**

```text
graphify/build.py
graphify/export.py
```

**Verify commands:**

```bash
uv run pytest \
  tests/test_hypergraph.py \
  tests/test_build_merge_hyperedges_and_prune.py \
  -q
```

**Dependencies:** Task 1.

### Task 3: Guard semantic cache reuse and writeback behavior

**Description:** Ensure cached semantic fragments with missing-ID hyperedges are
normalized on the build path and do not keep writing malformed graph metadata.

**Acceptance criteria:**

- [ ] Cached semantic hyperedges missing `id` no longer crash incremental
      `extract` / `build_merge`.
- [ ] Exported `graph.json` does not retain missing-ID hyperedges after a
      normalization pass.
- [ ] Existing semantic cache files do not need destructive manual deletion for
      the CLI to recover.

**Likely files touched:**

```text
graphify/build.py
graphify/cache.py  # only if build/export normalization is insufficient
tests/test_extract_cli.py or tests/test_build_merge_hyperedges_and_prune.py
```

**Verify commands:**

```bash
uv run pytest \
  tests/test_extract_cli.py \
  tests/test_build_merge_hyperedges_and_prune.py \
  -q
```

**Dependencies:** Task 2.

### Task 4: Run targeted validation and reinstall the active CLI

**Description:** Prove the patch and update the active `graphify` tool only from
this checkout.

**Acceptance criteria:**

- [ ] Targeted tests pass.
- [ ] Ruff passes for touched Python files.
- [ ] Active CLI source verifier passes after reinstall.
- [ ] No unrelated dirty files are staged or committed by this task.

**Verify commands:**

```bash
uv run pytest \
  tests/test_hypergraph.py \
  tests/test_build_merge_hyperedges_and_prune.py \
  tests/test_extract_cli.py \
  -q
uv run ruff check graphify tests
uv tool install --force --reinstall \
  /Users/mase/Codebase/Personal-Projects/graphify \
  --with openai \
  --with tiktoken \
  --with faster-whisper \
  --with yt-dlp \
  --with watchdog \
  --with tree-sitter-sql
graphify doctor \
  --require-source /Users/mase/Codebase/Personal-Projects/graphify
```

**Dependencies:** Tasks 1-3.

### Task 5: Validate against the real incident artifact

**Description:** Confirm the repaired CLI can load and rewrite the affected
Second Brain graph without invoking Ollama.

**Acceptance criteria:**

- [ ] The previously reproduced `build_merge()` real-artifact probe no longer
      raises `KeyError: 'id'`.
- [ ] `cluster-only` can refresh core graph/report output without LLM labeling
      when run with `--no-label`.
- [ ] Current CLI source or help confirms the `cluster-only` recovery flags
      before the incident-repo command is run.
- [ ] Remaining Ollama semantic refresh, if desired, is reported as a separate
      operator action rather than a blocker for backward ingestion.

**Verify commands:**

```bash
uv run python - <<'PY'
from pathlib import Path
from graphify.build import build_merge
root = Path('/Users/mase/Codebase/Personal-Projects/my-second-brain-build')
G = build_merge([
    {
        'nodes': [
            {
                'id': '__graphify_repro_dummy__',
                'label': 'dummy',
                'file_type': 'document',
                'source_file': '__graphify_repro_dummy__.md',
            }
        ],
        'edges': [],
        'hyperedges': [],
    }
], graph_path=root / 'graphify-out/graph.json', root=root)
print(G.number_of_nodes(), len(G.graph.get('hyperedges', [])))
PY

rg -n "no_label|no_viz|--no-label|--no-viz" graphify/__main__.py

cd /Users/mase/Codebase/Personal-Projects/my-second-brain-build && \
  graphify cluster-only . --no-label --no-viz
```

**Dependencies:** Task 4.

## Checkpoints

### Checkpoint A: Regression locked

- [ ] Task 1 tests fail on the current implementation or otherwise directly
      demonstrate the old failure path.
- [ ] The intended normalization behavior is clear before production code is
      edited.

### Checkpoint B: Local fork patch validated

- [ ] Tasks 1-3 pass targeted tests.
- [ ] `ruff` is clean for touched files.
- [ ] No site-packages patching occurred.

### Checkpoint C: Operator recovery path validated

- [ ] Active CLI source points to this checkout.
- [ ] The real incident artifact no longer reproduces the `KeyError`.
- [ ] Any remaining semantic-refresh timeout is isolated to Ollama labeling or
      model runtime, not the hyperedge merge crash.

Closure disposition: active CLI provenance is now verified. The two
incident-repository checks remain the explicit operational deviation above and
must not be inferred from unit-test success or the adoption audit.

## Risks And Mitigations

- **Synthesized IDs churn across runs**
  - Impact: Medium.
  - Mitigation: base IDs on stable content and member order after alias
    normalization.
- **Dropping malformed hyperedges loses useful graph context**
  - Impact: Medium.
  - Mitigation: prefer synthesis for meaningful entries; only drop unusable
    entries.
- **Import cycle between build/export helpers**
  - Impact: Medium.
  - Mitigation: keep normalization helper in `build.py` and import it from
    `export.py`, which already imports `edge_data` from `build.py`; avoid
    importing `export.py` at `build.py` module top level.
- **Existing semantic cache keeps malformed entries**
  - Impact: High.
  - Mitigation: normalize on read/build/export path so old cache can be
    tolerated without deletion.
- **`cluster-only --backend ollama` remains slow**
  - Impact: Low for this bug.
  - Mitigation: use `--no-label` or `--missing-only` for recovery; treat Ollama
    labeling as separate performance work.
- **Upstream later lands a different fix**
  - Impact: Low.
  - Mitigation: keep the patch small and upstream-friendly; drop or adapt during
    the next upstream reconciliation.

## Open Questions

- Should normalization print a warning when it synthesizes a missing hyperedge
  ID, or stay quiet to avoid noisy refreshes on legacy graphs?
- Should Graphify eventually validate hyperedge schema in `validate_extraction()`
  the same way it validates node and edge schema?

## Recommended Next Action

No implementation action remains for this patch plan. Preserve commit
`651c807` through future upstream reconciliations unless upstream ships an
equivalent fix. Do not run the deferred Second Brain recovery or semantic
refresh without separate authority and a clean, reviewed target state.
