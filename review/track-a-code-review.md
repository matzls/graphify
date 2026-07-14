---
title: "Track A Code Review"
kind: review
status: complete
reviewed_at: 2026-07-13
scope: "Uncommitted post-upstream-rebase semantic CLI compatibility repair"
---

## Review Summary

**Verdict:** REQUEST CHANGES

**Overview:** The repair restores the intended CLI ownership split and the main
fail-closed, marker, report, wiki, and doctor paths. One cache-path interaction
still lets retry-exhausted partial semantic output bypass the fail-closed
contract on a subsequent run.

### Critical Issues

- **[graphify/cli.py:932-1031; graphify/llm.py:2259-2294] Partial semantic
  results are checkpointed before the CLI can reject them.** `_dispatch_extract`
  calls `extract_corpus_parallel` with checkpointing enabled. The extractor
  calls `save_semantic_cache(..., merge_existing=True)` for every returned
  chunk before `_dispatch_extract` evaluates `partial_chunks` and skips its
  final cache save. Thus a default fail-closed run can still persist a
  retry-exhausted partial chunk; the next run treats that file as a cache hit,
  performs no fresh semantic work, writes a clean marker (`cli.py:1327-1335`),
  and can write graph/report/wiki artifacts from degraded data. `--allow-partial`
  has the same cache-poisoning path. This also writes checkpoints under
  `target` rather than `--out`'s `out_root`.

  Verified locally without a provider call: a temporary document with
  `extract_files_direct` stubbed to return `finish_reason="length"` produced
  `partial_chunks == 1`, then `check_semantic_cache(..., root=target)` returned
  no uncached files. The current test at
  `tests/test_cli_semantic_fail_closed.py:287-323` replaces the whole corpus
  extractor, so it cannot exercise this checkpoint.

  **Smallest safe repair:** add an explicit `checkpoint_cache: bool = True`
  parameter to `extract_corpus_parallel`, skip `_checkpoint_chunk` when false,
  and call it as false from the strict CLI path. Retain the CLI's existing final
  `save_semantic_cache(..., root=out_root)` only after clean fresh output. Add a
  regression test that uses the real corpus wrapper with its provider call
  stubbed and proves a partial result remains a cache miss on the next CLI run
  (including `--out`).

### Important Issues

- None beyond the blocker above.

### Suggestions

- **[`graphify/__main__.py:659-673; graphify/__main__.py:583-584`] Doctor help
  does not expose the newly restored backend/probe surface.** The universal
  help guard runs before the doctor branch, so `graphify doctor --help` prints
  only `Run 'graphify --help' for full usage.` The global help then lists only
  `--require-source`, not `--backend` or `--probe`. Valid doctor routing itself
  works. **Smallest repair:** exempt `doctor` from the generic guard (or handle
  it first), list the two flags in global help, and add a `doctor --help`
  regression test.

### What's Done Well

- `cli.py` owns extraction, markers, cache gating, and report/wiki behavior;
  `__main__.py` retains entry/doctor routing; `install.py` remains untouched.
  The imports remain one-way, with no new `cli.py` to `__main__.py` eager cycle.
- The visible fail-closed checks cover failed, empty, and `partial_chunks`
  output, and marker lifecycle tests cover clean code-only/cache-only runs.
  Wiki protection and explicit `--allow-partial` behavior are also covered.
- The large CLI diff is predominantly a deliberate extraction of the
  `extract` branch into `_dispatch_extract` plus restored historical behavior;
  `git diff --check` and Python compilation are clean. I found no separate
  formatting-churn or install-boundary blocker.

### Verification Story

- Tests reviewed: **yes**. Independently ran the plan's combined selection:
  **551 passed, 2 skipped**. Also ran the focused/boundary selection
  (`test_cli_semantic_fail_closed`, `test_extract_cli`, `test_cli_export`, and
  `test_merge_graphs_cli`): **71 passed**. The passing tests are not adequate
  to detect the checkpoint issue because their degraded-output cases stub
  `extract_corpus_parallel`.
- Build verified: **no full package build run**. `python -m py_compile` passed,
  and targeted `uv run pyright graphify/__main__.py graphify/cli.py
  graphify/build.py` reported **0 errors, 0 warnings**.
- Security checked: **yes**. No new dependency, install, or network path was
  introduced by this diff; `doctor --probe` remains explicitly opt-in. The
  critical finding is semantic-output integrity rather than a credential or
  authorization issue.

No Graphify self-extraction, network operation, install command, source edit,
or commit was performed during this review.
