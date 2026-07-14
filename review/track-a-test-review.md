---
title: "Track A Regression-Test Review"
kind: review
status: complete
created: 2026-07-13
scope: "Uncommitted semantic CLI recovery diff"
---

## Verdict

**Test coverage is not fully sufficient for every repaired migration contract.**
The core extraction, cache, output-root, wiki-gate, monkeypatch, and doctor
success paths are well covered. Two material marker/report lifecycle behaviors
and one doctor failure path remain unproven.

## Findings

### High — A clean fresh semantic run is not proven to replace a stale partial marker

`graphify/cli.py` writes a clean marker after both no-cluster and clustered fresh
semantic runs at lines 1212-1223 and 1326-1337. The only clean-marker lifecycle
test is cache-only: `tests/test_cli_semantic_fail_closed.py:447-508`. The fresh
happy-path tests provide `failed_chunks: 0` (`tests/test_cli_semantic_fail_closed.py:76-122`,
`511-544`) but never seed a partial marker or assert that it becomes
`status: clean` with zero failure/partial counts.

A regression that leaves a prior partial marker in place after a successful fresh
refresh would still pass. That stale marker blocks later wiki generation at
`graphify/cli.py:2590-2606` and `3268-3285`.

**Needed test:** start with a partial marker, return successful fresh semantic
output, then assert the rewritten marker is clean and a subsequent wiki path is
not blocked.

### High — Partial-marker report behavior is untested and currently not gated

The recovery plan requires an explicit report/wiki policy for partial markers.
Existing subprocess tests verify only wiki behavior:
`tests/test_cli_export.py:533-584`. In particular,
`test_cluster_only_skips_wiki_when_semantic_marker_is_partial` asserts exit 0 and
no wiki at lines 540-544, but makes no assertion about `GRAPH_REPORT.md`.

`cluster-only` writes `GRAPH_REPORT.md` before checking the partial marker; the
check at `graphify/cli.py:2590-2606` suppresses only wiki output. Thus the current
test suite would remain green if a partial run overwrote a report that the intended
contract meant to preserve. The direct export-wiki guard is covered at
`graphify/cli.py:3268-3285` and `tests/test_cli_export.py:560-584`.

**Needed test/decision:** seed a sentinel report and partial marker, run
`cluster-only` with and without `--allow-partial`, and assert the intended report
policy explicitly (preserved, or intentionally rewritten with a partial warning).

### Medium — Doctor probe failure mapping is not exercised

The new entrypoint catches backend-validation failures at
`graphify/__main__.py:205-212` and probe failures at lines 214-219, returning 1
without printing a false success summary. Existing tests cover only missing
`--backend` (`tests/test_cli_semantic_fail_closed.py:640-645`) and the successful
summary (`648-670`). No test makes either dependency validation or
`probe_backend()` fail.

**Needed test:** patch each dependency/probe seam to raise and assert exit 1,
error output, and absence of `backend probe (...): ok`.

## Demonstrably covered contracts

- **Single-file output root:** `graphify/cli.py:628-633`; asserted by
  `tests/test_cli_semantic_fail_closed.py:76-122`. External `--out` isolation is
  also covered by `tests/test_extract_cli.py:316-351`.
- **Fail-closed fresh semantic output:** all-failed, empty, some-failed, and
  retry-exhausted partial outputs preserve the prior graph at
  `tests/test_cli_semantic_fail_closed.py:125-250`; the production guard is
  `graphify/cli.py:984-1013`. The public-entrypoint test independently verifies
  non-zero exit/no graph write for all failed chunks at
  `tests/test_extract_cli.py:34-89`.
- **Explicit `--allow-partial`:** AST-only output and partial marker fields are
  asserted at `tests/test_cli_semantic_fail_closed.py:253-284` and `326-364`.
- **No degraded fresh cache writes:** the cache saver is a fail-on-call seam in
  the shared helper and the partial-output test at
  `tests/test_cli_semantic_fail_closed.py:287-323`; production skips cache writes
  at `graphify/cli.py:1014-1026`.
- **Code-only/cache-only marker lifecycle:** code-only clears stale partial state
  at `tests/test_cli_semantic_fail_closed.py:408-444`; cache-only rewrites it
  clean at `447-508`.
- **Wiki gates and override:** `cluster-only` and direct `export wiki` default
  refusal plus `--allow-partial` are covered in
  `tests/test_cli_export.py:533-584` against the two current gate locations.
- **Moved CLI import/monkeypatch seams:** both focused suites invoke
  `graphify.__main__.main` while patching leaf dependencies
  (`tests/test_cli_semantic_fail_closed.py:10-73`,
  `tests/test_extract_cli.py:65-75`), exercising the current lazy imports in
  `graphify/cli.py:887-892` and public dispatch through
  `graphify/__main__.py:708-711`.
- **Doctor probe invocation and summary:** covered at
  `tests/test_cli_semantic_fail_closed.py:640-670` for the required-backend and
  successful-probe paths.

## Verification

- `uv run pytest tests/test_cli_semantic_fail_closed.py`
  `tests/test_extract_cli.py tests/test_cli_export.py -q`
  - **68 passed**; one existing Hypothesis collection warning.
- LSP diagnostics for the reviewed tests and changed production files: **0 errors**.

No project source or test files were modified by this review.
