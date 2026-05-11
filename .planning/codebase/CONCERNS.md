# Codebase Concerns

**Analysis Date:** 2026-05-11

## Tech Debt

**Extractor monolith:**
- Issue: `graphify/extract.py` is a 4,987-line module that owns shared parser helpers, language-specific extractors, dispatch registration, cache orchestration, and parallel extraction.
- Files: `graphify/extract.py`, `tests/test_languages.py`, `tests/test_extract.py`, `tests/test_import_extension_resolution.py`, `tests/test_multilang.py`
- Impact: Adding or changing one language extractor requires editing a shared high-blast-radius file. Regression risk is broad because helper functions and dispatch tables are interleaved with many unrelated language implementations.
- Fix approach: Split new extractor work into language-focused modules or local sections with narrow tests. When touching `graphify/extract.py`, run the nearest language test plus `tests/test_import_extension_resolution.py` when import resolution changes.

**CLI command router monolith:**
- Issue: `graphify/__main__.py` is a 2,588-line command router that combines help text, installer behavior for many assistant platforms, graph commands, export commands, semantic extraction, and global graph commands.
- Files: `graphify/__main__.py`, `tests/test_install.py`, `tests/test_cli_export.py`, `tests/test_hooks.py`, `tests/test_ollama.py`
- Impact: Small CLI changes can accidentally affect unrelated installer, hook, export, or extraction flows. Argument parsing is hand-rolled across multiple command branches, so option interactions are fragile.
- Fix approach: Put new command behavior behind small helper functions before adding more inline branches. Validate with the command-specific test file and at least one smoke command through `python -m graphify`.

**Silent degradation patterns:**
- Issue: Several core paths catch broad exceptions and continue with reduced output, including AST extraction warnings, semantic chunk failures, cached graph recovery, global manifest reads, detection conversion failures, and watch rebuild fallback.
- Files: `graphify/extract.py`, `graphify/llm.py`, `graphify/watch.py`, `graphify/detect.py`, `graphify/global_graph.py`, `graphify/__main__.py`
- Impact: A run can complete with partial graph evidence while only printing warnings to stderr. Agents and users can treat `graphify-out/graph.json` as complete when semantic chunks, cached labels, or previous graph state were skipped.
- Fix approach: Preserve user-facing resilience, but add structured run status to `graphify-out/cost.json`, `graphify-out/manifest.json`, or a dedicated diagnostics sidecar. Treat warnings from `graphify extract` and `graphify watch` as validation evidence, not console noise.

**Duplicated generated skill guidance:**
- Issue: Platform skill files duplicate large guidance blocks and have a separate Codex installed copy outside the repo.
- Files: `graphify/skill-codex.md`, `graphify/skill.md`, `graphify/skill-opencode.md`, `graphify/skill-aider.md`, `docs/mase-fork-operating-model.md`, `/Users/mase/.codex/skills/graphify/SKILL.md`, `/Users/mase/.codex/docs/reference/graphify.md`
- Impact: Behavior guidance can drift between packaged Graphify, Mase's active Codex skill, and the global operator guide. This is especially risky for hook behavior, local fork install verification, semantic output paths, and `.graphifyignore` rules.
- Fix approach: Follow the sync procedure in `docs/mase-fork-operating-model.md` before changing skill behavior. Compare both repo and installed copies; never overwrite `/Users/mase/.codex/skills/graphify/SKILL.md` blindly.

## Known Bugs

**Partial semantic extraction can still produce a successful graph:**
- Symptoms: Semantic chunk failures are logged and skipped, then AST results and any successful semantic chunks are merged and written if the final graph has nodes.
- Files: `graphify/llm.py`, `graphify/__main__.py`, `graphify/cache.py`
- Trigger: Run `graphify extract <path>` on a mixed code/docs corpus where one or more LLM chunks fail, time out, or return invalid JSON while AST extraction still produces nodes.
- Workaround: Review stderr for `[graphify] chunk ... failed` and `[graphify extract] semantic extraction failed` messages. Re-run with smaller `GRAPHIFY_SEMANTIC_TOKEN_BUDGET`, lower `GRAPHIFY_FILE_CHAR_CAP`, or a more reliable backend before using semantic relationships as evidence.

**Concept-only semantic nodes are not cached:**
- Symptoms: `save_semantic_cache()` groups nodes, edges, and hyperedges by `source_file`; entries without `source_file` are not written to the semantic cache.
- Files: `graphify/cache.py`, `graphify/llm.py`, `graphify/__main__.py`
- Trigger: LLM extraction emits concept nodes or edges that do not carry `source_file`, then the same corpus is re-run incrementally.
- Workaround: Use a full semantic refresh when concept-level relationships matter. Prefer prompts and validation that ensure semantic nodes include a source file when they represent file-derived content.

**Markdown frontmatter changes do not invalidate cache entries:**
- Symptoms: Markdown cache hashing strips YAML frontmatter before hashing, so metadata-only edits do not invalidate AST or semantic cache entries.
- Files: `graphify/cache.py`, `graphify/ingest.py`, `graphify/detect.py`
- Trigger: Update `source_url`, `title`, `captured_at`, `author`, `contributor`, tags, or other frontmatter in a Markdown document without changing the body.
- Workaround: Clear the relevant cache or force a semantic refresh when frontmatter metadata is part of the graph evidence.

## Security Considerations

**Sensitive directories are not fully excluded by default:**
- Risk: `_is_sensitive()` checks only `path.name`, so a file such as `secrets/config.json` or `credentials/data.txt` can bypass the sensitive-file filter because the basename is generic.
- Files: `graphify/detect.py`, `SECURITY.md`
- Current mitigation: Specific sensitive basenames and extensions are skipped, `.env` is skipped as a directory, hidden directories are pruned, `.graphifyignore` can exclude additional paths, and this repo currently has no `.env*` or secret-looking files at max depth 2.
- Recommendations: Check all path parts for sensitive names and add explicit skip directories such as `secrets`, `.secrets`, `credentials`, and `config/secrets`. Add regression tests in `tests/test_detect.py`.

**Ollama remote endpoint is warning-only:**
- Risk: `OLLAMA_BASE_URL` can point to a non-loopback host; Graphify warns that the corpus will be sent there but still continues.
- Files: `graphify/llm.py`, `tests/test_ollama.py`, `docs/mase-fork-operating-model.md`
- Current mitigation: `_validate_ollama_base_url()` prints a warning for non-loopback or unencrypted endpoints, and backend detection prioritizes paid API keys over incidental `OLLAMA_BASE_URL`.
- Recommendations: Require an explicit opt-in environment variable or CLI flag for non-loopback Ollama endpoints before sending corpus contents.

**Generated HTML depends on third-party CDN JavaScript:**
- Risk: `graphify-out/graph.html` loads `vis-network` from `https://unpkg.com`, so opening a local graph visualization makes an external network request and depends on CDN availability.
- Files: `graphify/export.py`, `graphify/tree_html.py`
- Current mitigation: Node labels and embedded JSON are escaped before insertion into HTML, and large visualizations can be skipped with `GRAPHIFY_VIZ_NODE_LIMIT=0` or `--no-viz`.
- Recommendations: Offer an offline asset bundle or no-CDN export mode for private corpora and client-sensitive work.

**Global socket monkeypatch is not thread-safe:**
- Risk: `_ssrf_guarded_socket()` temporarily replaces `socket.getaddrinfo` process-wide. The comment says the CLI is single-threaded, but future threaded fetch/export flows could see surprising DNS behavior.
- Files: `graphify/security.py`, `graphify/ingest.py`, `graphify/transcribe.py`
- Current mitigation: URL ingestion is currently a direct CLI flow, and `safe_fetch()` uses the guard only during a single fetch.
- Recommendations: Keep `safe_fetch()` out of threaded code until the guard is redesigned around lower-level connection control or a library that supports per-request DNS validation.

## Performance Bottlenecks

**Full detection scans and word counting read many files:**
- Problem: `detect()` walks the scan root, classifies files, converts Office/Google sidecars, and counts words by reading supported files. PDF, DOCX, and XLSX counting can be expensive.
- Files: `graphify/detect.py`, `graphify/google_workspace.py`
- Cause: Detection doubles as corpus sizing, file conversion, sensitive-file filtering, and warning generation.
- Improvement path: Cache word counts and conversion metadata in `graphify-out/manifest.json`, and only recompute counts for changed files during incremental runs.

**Semantic extraction can be slow and lossy on large corpora:**
- Problem: LLM extraction reads capped file bodies into prompts, chunks by estimated tokens, retries truncated chunks recursively, and logs failed chunks without stopping the whole run.
- Files: `graphify/llm.py`, `graphify/__main__.py`, `tests/test_chunking.py`, `tests/test_ollama.py`
- Cause: Local model latency, JSON compliance, max-output limits, and backend rate limits are all handled at runtime by chunking and retry policy.
- Improvement path: Keep Ollama runs sequential unless proven otherwise, tune `GRAPHIFY_SEMANTIC_TOKEN_BUDGET` and `GRAPHIFY_FILE_CHAR_CAP`, and add a machine-readable failure summary so incomplete semantic output is visible after the process exits.

**HTML visualization has a hard node limit:**
- Problem: `to_html()` refuses large graphs above the configured node limit and CLI/watch flows skip or remove `graph.html`.
- Files: `graphify/export.py`, `graphify/watch.py`, `graphify/__main__.py`
- Cause: Browser rendering and pyvis/vis-network output are not suitable for very large graphs.
- Improvement path: Use `graphify-out/graph.json`, `GRAPH_REPORT.md`, `wiki`, `query`, and `path` commands for large graphs. Add filtered or community-scoped HTML export before raising the default limit.

## Fragile Areas

**Incremental graph merging:**
- Files: `graphify/detect.py`, `graphify/build.py`, `graphify/__main__.py`, `graphify/cache.py`, `tests/test_incremental.py`, `docs/superpowers/specs/2026-05-04-incremental-updates-dedup-design.md`
- Why fragile: `detect_incremental()` compares manifest entries by exact file path strings, then `build_merge()` preserves old graph nodes and prunes deleted source files by `source_file`. Path normalization, moved files, converted sidecars, and Markdown frontmatter hashing can leave stale or missing semantic evidence.
- Safe modification: Add tests that cover moved files, converted Office files, deleted docs, and frontmatter-only edits before changing manifest or cache semantics.
- Test coverage: Unit coverage exists for incremental behavior, cache behavior, and global graph behavior, but end-to-end semantic incremental runs with real LLM failures are not covered.

**Code-only watch rebuilds with semantic preservation:**
- Files: `graphify/watch.py`, `tests/test_watch.py`, `graphify/export.py`, `graphify/report.py`
- Why fragile: `_rebuild_code()` preserves prior semantic nodes/edges by node ID while replacing new AST nodes. Corrupt existing graphs, ID collisions, or changed node ID rules can silently fall back to AST-only output.
- Safe modification: Keep semantic label preservation tests when changing node IDs, extraction dispatch, or `to_json()` shrink protection. Use `GRAPHIFY_FORCE=1` only when a graph shrink is intentional.
- Test coverage: `tests/test_watch.py` covers flags and community label preservation, but full watch rebuild behavior is not covered through a live `watchdog` observer.

**Manual argument parsing:**
- Files: `graphify/__main__.py`
- Why fragile: Most commands parse `sys.argv` with hand-rolled loops, so adding one flag can shadow positional arguments or skip validation in a neighboring branch.
- Safe modification: Prefer helper parsers per subcommand or migrate touched commands to `argparse` incrementally. Add CLI tests in `tests/test_cli_export.py`, `tests/test_install.py`, or a new command-specific test file.
- Test coverage: Many command paths are covered by focused tests, but the whole CLI matrix is too wide for exhaustive option-combination coverage.

## Scaling Limits

**Corpus size:**
- Current capacity: Detection warns above 200 files or 500,000 words; it says corpora below 50,000 words may not need a graph.
- Limit: Large corpora increase scan time, LLM token cost, semantic chunk failures, and browser visualization size.
- Scaling path: Use `.graphifyignore`, bounded scan roots, `--no-semantic` for AST-only work, semantic cache, and subfolder runs for expensive document/media corpora.

**Visualization size:**
- Current capacity: HTML visualization default limit is 5,000 nodes.
- Limit: Graphs above this are not rendered to `graph.html` unless `GRAPHIFY_VIZ_NODE_LIMIT` is raised.
- Scaling path: Add filtered exports, community-level graph views, or server-side query workflows instead of raising the full-graph browser limit.

**Global graph persistence:**
- Current capacity: One global graph and one manifest under `~/.graphify`.
- Limit: `global_add()` and `global_remove()` read and write whole JSON files without locking, so concurrent writes can lose updates or corrupt the manifest.
- Scaling path: Add file locking and atomic temp-file writes around `~/.graphify/global-graph.json` and `~/.graphify/global-manifest.json` before using global graphs in automation.

## Dependencies at Risk

**Tree-sitter package matrix:**
- Risk: The project depends on many `tree-sitter-*` grammar packages with broad version ranges and no lockfile in this repo.
- Impact: Grammar node-name changes or API changes can break extractor behavior across languages.
- Migration plan: Keep the `tree-sitter>=0.23.0` guard in `graphify/extract.py`, pin problematic grammar ranges when regressions appear, and run `tests/test_languages.py`, `tests/test_import_extension_resolution.py`, and the specific language fixture test after dependency changes.

**Optional extras control runtime features:**
- Risk: Video, Office, PDF, Google Workspace, Neo4j, SVG, MCP, Bedrock, and hosted LLM functionality depend on optional packages that can be missing in the active install.
- Impact: Features fail at runtime with ImportError or skip conversion/extraction paths.
- Migration plan: Keep errors explicit and test optional import failure paths. For Mase's active fork install, include `faster-whisper`, `yt-dlp`, `watchdog`, and `tree-sitter-sql` as documented in `AGENTS.md` and `docs/mase-fork-operating-model.md`.

**Duplicate dependency declaration:**
- Risk: `tree-sitter-sql` appears twice in base dependencies, once as `tree-sitter-sql>=0.3.11` and once as `tree-sitter-sql`.
- Impact: Installers resolve this benignly today, but it makes dependency intent less clear and can confuse future audits.
- Migration plan: Keep one base dependency entry with the intended minimum version and retain the `sql` extra only for compatibility messaging if needed.

## Missing Critical Features

**Machine-readable run completeness status:**
- Problem: Graph outputs do not carry a clear success/partial/failure status for semantic chunks, cache writes, manifest writes, watch rebuild fallbacks, or skipped conversions.
- Blocks: Agents cannot reliably decide whether `graphify-out/graph.json` is complete without parsing stderr or re-running checks.

**First-class offline visualization mode:**
- Problem: Generated HTML visualizations depend on external CDN scripts.
- Blocks: Fully offline/private graph review for sensitive corpora.

**Hard policy gate for non-local Ollama:**
- Problem: Non-loopback `OLLAMA_BASE_URL` only triggers a warning.
- Blocks: Secure-by-default local semantic extraction in environments where warnings can be missed.

## Test Coverage Gaps

**Sensitive directory filtering:**
- What's not tested: Files under secret-looking directories with generic basenames, such as `secrets/config.json`.
- Files: `graphify/detect.py`, `tests/test_detect.py`
- Risk: Sensitive files can enter detection and semantic extraction unless `.graphifyignore` excludes them.
- Priority: High

**Partial semantic run status:**
- What's not tested: End-to-end CLI behavior when one semantic chunk fails and other extraction work succeeds.
- Files: `graphify/llm.py`, `graphify/__main__.py`, `tests/test_ollama.py`, `tests/test_chunking.py`
- Risk: Partial semantic graphs can be mistaken for complete graphs.
- Priority: High

**Cache invalidation for metadata-only Markdown edits:**
- What's not tested: Whether frontmatter changes that affect graph metadata should invalidate semantic or AST cache entries.
- Files: `graphify/cache.py`, `graphify/ingest.py`, `tests/test_cache.py`
- Risk: Updated source metadata can be absent from graph output after incremental runs.
- Priority: Medium

**Global graph concurrent writes:**
- What's not tested: Simultaneous `global_add()` or `global_remove()` calls against the same `~/.graphify` files.
- Files: `graphify/global_graph.py`, `tests/test_global_graph.py`
- Risk: Automation or parallel agents can lose global graph updates.
- Priority: Medium

**Offline HTML export:**
- What's not tested: Rendering `graph.html` without network access to `unpkg.com`.
- Files: `graphify/export.py`, `graphify/tree_html.py`, `tests/test_export.py`
- Risk: Visualization fails in offline or client-restricted environments.
- Priority: Low

---

*Concerns audit: 2026-05-11*
