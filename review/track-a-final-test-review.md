---
title: "Track A Final Test and Diff Review"
kind: review
status: approved
reviewed_at: 2026-07-13
scope: "Current uncommitted Track A changes"
---

## Verdict

**APPROVE.** No critical, high, medium, or low severity regression was found in
this review.

## Evidence reviewed

- Current uncommitted diff: `graphify/llm.py`, `graphify/cli.py`,
  `graphify/__main__.py`, `graphify/build.py`, and the three changed test files.
- Focused local validation completed without network or CLI-install activity:

  ```text
  uv run --offline --group dev pytest -q \
    tests/test_chunking.py tests/test_cli_semantic_fail_closed.py \
    tests/test_cli_export.py tests/test_extract_cli.py
  94 passed, 1 skipped
  ```

- Touched-file static checks:

  ```text
  pyright: 0 errors, 0 warnings, 0 information diagnostics
  ruff: All checks passed
  ```

- `git diff --check` completed with no whitespace errors.

## Scenario evidence

### [None] Checkpoint, cache-root, and fail-closed regression

`test_retry_exhausted_semantic_output_is_not_checkpointed_across_output_roots`
in `tests/test_cli_semantic_fail_closed.py` exercises the real CLI call to
`extract_corpus_parallel`; it stubs only `extract_files_direct` as the provider
boundary. The stub returns `finish_reason: "length"` for one short Markdown
file, which follows the real adaptive-retry single-file exhaustion path and
returns `partial_chunks == 1`.

The test proves the CLI passes `checkpoint_cache=False`: after an
`--allow-partial --out <external>` run, neither the corpus root nor external
output root contains a semantic cache entry. Its second default-root extraction
calls the provider again (`calls == 2`) and fails closed (`rc == 1`), rather
than accepting poisoned checkpoint data as a cache hit.

`test_corpus_checkpoint_cache_remains_enabled_by_default` separately verifies
the library default remains enabled: a successful provider-stubbed call to the
real parallel extractor produces a semantic cache hit under its supplied root.

### [None] Marker replacement and partial-output presentation policy

- `test_fresh_semantic_extract_rewrites_stale_partial_marker_as_clean` seeds a
  partial marker, runs a fresh successful semantic CLI extraction, and verifies
  `status: clean` plus zero failed and partial chunks.
- `test_cache_only_semantic_extract_rewrites_stale_partial_marker_as_clean`
  verifies the same replacement behavior when all semantic data is a cache hit.
- `test_cluster_only_refreshes_report_but_skips_wiki_when_semantic_marker_is_partial`
  runs the subprocess command with a seeded partial marker and stale report. It
  verifies the report is refreshed, the partial warning is emitted, and no wiki
  is written.
- The adjacent existing subprocess tests verify both wiki refusal by default
  and the explicit `--allow-partial` override for `cluster-only` and
  `export wiki`.

### [None] Doctor help and failure paths

The doctor tests invoke the real `main()` argument-routing and `_doctor()` flow
with only LLM dependency/probe calls stubbed:

- `doctor --help` lists `--backend BACKEND` and `--probe`.
- Dependency validation failure returns 1 and prints no success status.
- Probe failure returns 1 after dependency success, prints the probe error, and
  prints no probe-success status.
- Existing adjacent coverage verifies `--probe` requires `--backend` and a
  successful probe prints its summary.

## `tests/test_chunking.py` change classification

### Necessary for behavioral correctness or passing checks

1. The new `test_corpus_checkpoint_cache_remains_enabled_by_default` is the
   Track A regression test. It is necessary to protect the public default after
   adding `checkpoint_cache=False` for the CLI's fail-closed path.
2. `from graphify.file_slice import unit_path`, the conversion to
   `sorted(map(str, chunks[0]))`, and both `unit_path(p).parent` expressions
   are necessary compatibility/type-correctness edits. `_pack_chunks_by_tokens`
   returns `Path | FileSlice`; the previous assertions assumed every item was a
   `Path`. Re-running Pyright against the pre-change file produced exactly three
   errors: one unsupported `sorted(Path | FileSlice)` call and two missing
   `FileSlice.parent` accesses. The current touched-file Pyright run is clean.

### Removable churn

All other `tests/test_chunking.py` diff hunks are formatter-only:

- inserted blank separator lines; and
- splitting same-line fixture setup statements such as
  `f = ...; f.write_text(...)` into two statements.

These edits do not change a test assertion, fixture value, control flow, or
runtime behavior. They may be kept if a formatter pass is intentionally part of
the change, but are removable to minimize the Track A diff.

## Residual note

The reviewed semantic `--out` regression specifically proves that degraded
output cannot checkpoint into either the scan root or external output root. The
positive default-checkpoint behavior is independently covered at the library
root level. This is sufficient evidence for the Track A cache-poisoning fix.
