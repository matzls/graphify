<!-- refreshed: 2026-05-11 -->
# Architecture

**Analysis Date:** 2026-05-11

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                         CLI Surface                          │
├──────────────────┬──────────────────┬───────────────────────┤
│  graphify CLI    │ Assistant skills │       GSD skills       │
│ `graphify/__main__.py` │ `graphify/skill*.md` │ `.codex/skills/` |
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Extraction Pipeline                       │
│ `graphify/detect.py` → `graphify/extract.py` + `graphify/llm.py` │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Graph Build, Analysis, Output                │
│ `graphify/build.py` → `graphify/cluster.py` → `graphify/analyze.py` │
│ `graphify/report.py` + `graphify/export.py` + `graphify/serve.py` │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Derived Graph Artifacts                   │
│ `graphify-out/graph.json`, `GRAPH_REPORT.md`, `graph.html`  │
│ `.planning/graphs/`, `~/.graphify/global-graph.json`         │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI router | Parses `graphify` commands, runs installs, query/path/explain, update, extract, export, hook, and global graph commands. | `graphify/__main__.py` |
| Install surfaces | Writes assistant-specific skill or instruction files for Claude, Codex, OpenCode, Cursor, Gemini, VS Code, Kiro, Pi, and related platforms. | `graphify/__main__.py`, `graphify/skill-codex.md`, `graphify/skill.md` |
| File discovery | Classifies code/docs/papers/images/video, skips secrets and generated noise, applies `.graphifyignore` and `.graphifyinclude`, and writes manifests. | `graphify/detect.py`, `graphify/manifest.py` |
| Deterministic extraction | Uses tree-sitter and line parsers to extract code and Markdown structure without LLM calls. | `graphify/extract.py` |
| Semantic extraction | Calls direct LLM backends for docs, papers, images, and semantic relationships; chunks and retries prompt batches. | `graphify/llm.py` |
| Caching | Stores AST and semantic extraction fragments keyed by file content. | `graphify/cache.py` |
| Graph construction | Validates extraction schema, merges fragments, normalizes IDs, preserves edge direction metadata, and builds NetworkX graphs. | `graphify/build.py`, `graphify/validate.py` |
| Entity deduplication | Merges duplicate nodes and can use an LLM for ambiguous dedup pairs. | `graphify/dedup.py` |
| Community detection | Runs Leiden when available, falls back to NetworkX Louvain, splits large or low-cohesion communities, and scores cohesion. | `graphify/cluster.py` |
| Analysis | Finds god nodes, surprising connections, graph diffs, suggested questions, and graph gaps. | `graphify/analyze.py` |
| Report generation | Renders the Markdown audit report with corpus health, freshness, communities, ambiguous edges, and suggested questions. | `graphify/report.py` |
| Exports | Writes `graph.json`, HTML, SVG, GraphML, Obsidian vault, Canvas, wiki, Cypher, and Neo4j outputs. | `graphify/export.py`, `graphify/tree_html.py`, `graphify/wiki.py` |
| Query service | Loads `graph.json`, exposes BFS/DFS graph query text, and starts an MCP stdio server. | `graphify/serve.py` |
| Watch and hooks | Rebuilds code graphs for code-only changes, flags semantic refresh needs for docs/media, and installs Git hooks. | `graphify/watch.py`, `graphify/hooks.py` |
| Global graph | Merges project graphs into `~/.graphify/global-graph.json` using repo-tagged node prefixes. | `graphify/global_graph.py` |
| Ingestion and media | Fetches URL content, saves query feedback, and transcribes audio/video inputs. | `graphify/ingest.py`, `graphify/transcribe.py` |
| Project workflow layer | Provides repo-local GSD workflows and codebase-map outputs consumed by planning/execution agents. | `.codex/skills/`, `.codex/get-shit-done/`, `.planning/codebase/` |

## Pattern Overview

**Overall:** Staged pipeline with a thin CLI orchestrator and functional modules passing plain extraction dictionaries and NetworkX graphs.

**Key Characteristics:**
- Keep source graph work in `graphify/`; keep workflow planning intelligence in `.codex/` and `.planning/`.
- Pass data between stages as plain dictionaries with `nodes`, `edges`, optional `hyperedges`, `input_tokens`, and `output_tokens`.
- Treat `graphify-out/` and `.planning/graphs/` as derived artifacts; verify claims against source files before editing.
- Do deterministic local extraction first, then semantic LLM extraction, then graph build, clustering, analysis, and export.
- Use repo-local GSD command skills in `.codex/skills/` for project workflow operations; each skill delegates to `.codex/get-shit-done/workflows/`.

## Layers

**CLI and Command Layer:**
- Purpose: Parse command-line intent and invoke the correct library stage.
- Location: `graphify/__main__.py`
- Contains: `main()`, install/uninstall helpers, query/path/explain commands, `extract`, `update`, `cluster-only`, `export`, `global`, and hook commands.
- Depends on: Most `graphify/*` modules, `networkx`, JSON serialization, filesystem APIs.
- Used by: Installed `graphify` script configured in `pyproject.toml`.

**Assistant Integration Layer:**
- Purpose: Package Graphify as assistant guidance and hook/install surfaces.
- Location: `graphify/skill.md`, `graphify/skill-codex.md`, `graphify/skill-*.md`, `.codex/hooks/`, `.codex/skills/`
- Contains: Human/agent-facing skill docs, platform install logic, GSD command adapters, and repo-local Graphify guidance.
- Depends on: `graphify/__main__.py` install helpers and project instruction files.
- Used by: Codex, Claude Code, OpenCode, Cursor, Gemini, VS Code, Kiro, Pi, Aider, and GSD commands.

**Discovery Layer:**
- Purpose: Determine which files are relevant and what extraction path each file needs.
- Location: `graphify/detect.py`
- Contains: Extension sets, `FileType`, `.graphifyignore` and `.graphifyinclude` handling, Office and Google Workspace conversion helpers, manifest support.
- Depends on: `graphify/google_workspace.py` and optional libraries such as `pypdf`, `python-docx`, and `openpyxl`.
- Used by: `graphify extract`, `graphify update`, `graphify watch`, and Git hook classification.

**Deterministic Extraction Layer:**
- Purpose: Extract code and Markdown structure locally.
- Location: `graphify/extract.py`
- Contains: `LanguageConfig`, tree-sitter language configs, per-language extractors, Markdown heading/code-block parser, subprocess AST extraction, import/call resolution.
- Depends on: tree-sitter packages, `graphify/cache.py`.
- Used by: `graphify extract`, `graphify update`, `graphify.watch._rebuild_code()`.

**Semantic Extraction Layer:**
- Purpose: Extract semantic nodes, edges, and hyperedges from non-code corpus files.
- Location: `graphify/llm.py`
- Contains: backend registry, OpenAI-compatible calls, Claude direct calls, Bedrock calls, token-budget chunking, adaptive retry, JSON parsing and repair.
- Depends on: optional SDKs such as `openai`, `anthropic`, `boto3`, `tiktoken`.
- Used by: `graphify extract` and benchmarking/direct extraction paths.

**Graph Core Layer:**
- Purpose: Convert extraction fragments into a queryable NetworkX graph.
- Location: `graphify/build.py`, `graphify/validate.py`, `graphify/dedup.py`
- Contains: schema normalization, validation warnings, deduplication, `build()`, `build_from_json()`, `build_merge()`, global graph prefix/prune helpers.
- Depends on: `networkx`, `datasketch`, `rapidfuzz`, optional LLM dedup.
- Used by: extraction, cluster-only, update/watch, export/query/global graph commands.

**Analysis and Output Layer:**
- Purpose: Turn graphs into reports, visualizations, and query surfaces.
- Location: `graphify/cluster.py`, `graphify/analyze.py`, `graphify/report.py`, `graphify/export.py`, `graphify/tree_html.py`, `graphify/wiki.py`, `graphify/serve.py`, `graphify/benchmark.py`
- Contains: community detection, cohesion scoring, god nodes, surprising connections, reports, exports, MCP server, benchmark.
- Depends on: NetworkX, optional `graspologic`, optional `matplotlib`, optional Neo4j.
- Used by: `graphify extract`, `graphify cluster-only`, `graphify export`, `graphify query`, `graphify serve`.

**Freshness and Incremental Layer:**
- Purpose: Keep graph artifacts current without re-running expensive semantic extraction unnecessarily.
- Location: `graphify/watch.py`, `graphify/hooks.py`, `graphify/cache.py`, `graphify/manifest.py`
- Contains: file watchers, Git hook scripts, cache lookup/save, semantic refresh sentinel, manifest comparison.
- Depends on: `watchdog` when live watching, Git when hook/commit freshness is available.
- Used by: `graphify watch`, `graphify update`, `graphify hook install`, `graphify codex install`.

**Security Boundary Layer:**
- Purpose: Validate untrusted URLs, graph paths, and labels before fetching, loading, or emitting them.
- Location: `graphify/security.py`
- Contains: scheme and private-IP URL guards, redirect revalidation, streaming fetch caps, graph path containment, label sanitization.
- Depends on: stdlib networking and `ipaddress`.
- Used by: `graphify/ingest.py`, `graphify/serve.py`, `graphify/export.py`, query output paths.

## Data Flow

### Primary Headless Extraction Path

1. CLI parses `graphify extract <path>` and resolves backend/output flags (`graphify/__main__.py:2187`).
2. Detection runs full or incremental scan and separates code, docs, papers, and images (`graphify/__main__.py:2287`, `graphify/detect.py:116`).
3. Code files run deterministic AST extraction (`graphify/__main__.py:2341`, `graphify/extract.py:4687`).
4. Semantic files check cache and run LLM chunk extraction for uncached files (`graphify/__main__.py:2350`, `graphify/llm.py:667`).
5. AST and semantic fragments are merged with AST first so semantic attributes win on collision (`graphify/__main__.py:2434`).
6. Graph is built or incrementally merged, then clustered and analyzed (`graphify/__main__.py:2488`, `graphify/build.py:127`, `graphify/cluster.py:61`, `graphify/analyze.py:66`).
7. Outputs are written to `graphify-out/graph.json` and `.graphify_analysis.json`; optional global graph merge runs afterward (`graphify/__main__.py:2528`, `graphify/global_graph.py:56`).

### Code-Only Update Path

1. `graphify update <path>` resolves the watch path or previous `.graphify_root` (`graphify/__main__.py:1750`).
2. `graphify.watch._rebuild_code()` detects code and Markdown-extractable document files (`graphify/watch.py:102`).
3. Local AST extraction runs with the scan root preserved for stable relative source paths (`graphify/watch.py:137`).
4. Existing semantic nodes, edges, and hyperedges are preserved when the previous `graph.json` exists (`graphify/watch.py:140`).
5. The graph is rebuilt, clustered, analyzed, and written to `graphify-out/graph.json`, `GRAPH_REPORT.md`, and usually `graph.html` (`graphify/watch.py:175`, `graphify/watch.py:191`).

### Query Path

1. `graphify query`, `graphify path`, and `graphify explain` load `graphify-out/graph.json` or an explicit graph path (`graphify/__main__.py:1440`, `graphify/__main__.py:1528`, `graphify/__main__.py:1580`).
2. Node labels and source files are scored for query terms (`graphify/serve.py:53`).
3. Query mode traverses BFS or DFS, optionally filtering by edge context inferred from the question (`graphify/serve.py:206`).
4. Output is text rendered from the subgraph and sanitized before display (`graphify/serve.py:162`, `graphify/security.py:231`).

### Hook Freshness Path

1. `graphify hook install` writes post-commit and post-checkout hook blocks using markers (`graphify/hooks.py:242`).
2. Post-commit hook classifies changed files through `graphify.detect.classify_file()` (`graphify/hooks.py:87`).
3. Code changes launch background `_rebuild_code()`; docs/media write `graphify-out/needs_update` (`graphify/hooks.py:120`, `graphify/hooks.py:133`).
4. `graphify check-update <path>` reports pending semantic refresh without failing cron (`graphify/watch.py:234`).

### GSD Project Workflow Path

1. Repo-local GSD commands live as skill adapters in `.codex/skills/*/SKILL.md`.
2. Each skill points at a workflow under `.codex/get-shit-done/workflows/`.
3. `$gsd-map-codebase` writes `.planning/codebase/*.md`; `$gsd-graphify` reads `.planning/config.json` and operates on `.planning/graphs/`.
4. Planning and execution agents consume `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md` as durable project context.

**State Management:**
- Runtime state is file-based: `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/cache/`, semantic cache files, `graphify-out/needs_update`, `.graphify_analysis.json`, `.graphify_labels.json`, and `.graphify_root`.
- Global state is limited to `~/.graphify/global-graph.json` and `~/.graphify/global-manifest.json` in `graphify/global_graph.py`.
- Module-level caches exist for TypeScript aliases in `graphify/extract.py` and tokenizer/backend settings in `graphify/llm.py`.
- GSD state lives under `.planning/` and workflow implementation under `.codex/get-shit-done/`.

## Key Abstractions

**Extraction Fragment:**
- Purpose: Portable representation of graph nodes and edges before NetworkX construction.
- Examples: Returned by `graphify/extract.py:4687` and `graphify/llm.py:442`.
- Pattern: Dict with `nodes`, `edges`, optional `hyperedges`, `input_tokens`, `output_tokens`.

**Node and Edge Schema:**
- Purpose: Stable contract for all deterministic and semantic extractors.
- Examples: Validated in `graphify/validate.py`, normalized in `graphify/build.py:48`.
- Pattern: Node IDs are lowercase normalized strings; edges use `source`, `target`, `relation`, `confidence`, and source metadata.

**LanguageConfig:**
- Purpose: Configure generic tree-sitter extraction for language families without duplicating the full walker.
- Examples: `graphify/extract.py:146`, `_PYTHON_CONFIG`, `_JS_CONFIG`, `_TS_CONFIG`.
- Pattern: Dataclass containing node types, name fields, call fields, import handlers, and optional extra walk hooks.

**Backend Registry:**
- Purpose: Centralize semantic extraction provider configuration.
- Examples: `graphify/llm.py:51`.
- Pattern: `BACKENDS` maps provider names to base URL, model, env keys, pricing, temperature, and token limits.

**Community Map:**
- Purpose: Represent clustering output independent of NetworkX node attributes.
- Examples: `graphify/cluster.py:61`, `graphify/analyze.py:33`.
- Pattern: Dict of `community_id -> [node_id]`, then written into outputs by exporters.

**Graph Artifacts:**
- Purpose: Durable derived evidence for assistant navigation.
- Examples: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.html`, `.planning/graphs/`.
- Pattern: Generated files; do not use as source of truth for code edits.

**Skill Adapter:**
- Purpose: Bridge GSD workflow prompts into Codex-compatible tool behavior.
- Examples: `.codex/skills/gsd-map-codebase/SKILL.md`, `.codex/skills/gsd-graphify/SKILL.md`.
- Pattern: YAML metadata, `<codex_skill_adapter>`, objective/context, workflow references.

## Entry Points

**Installed CLI:**
- Location: `graphify/__main__.py`
- Triggers: `graphify` console script from `pyproject.toml`.
- Responsibilities: Route all user-facing commands.

**Headless Extraction:**
- Location: `graphify/__main__.py:2187`
- Triggers: `graphify extract <path>`.
- Responsibilities: Full detect/extract/build/cluster/write pipeline for CI/scripts.

**Code Update:**
- Location: `graphify/__main__.py:1750`, `graphify/watch.py:102`
- Triggers: `graphify update <path>`, Git hook background jobs, branch switch hook.
- Responsibilities: Rebuild deterministic code/Markdown graph while preserving semantic data.

**Interactive Query:**
- Location: `graphify/__main__.py:1440`, `graphify/serve.py:206`
- Triggers: `graphify query`, `graphify path`, `graphify explain`, MCP server tools.
- Responsibilities: Load graph and return focused graph context.

**MCP Server:**
- Location: `graphify/serve.py:272`
- Triggers: `python -m graphify.serve graphify-out/graph.json` or equivalent integration.
- Responsibilities: Expose graph query tools over stdio.

**Git Hooks:**
- Location: `graphify/hooks.py`
- Triggers: `graphify hook install`, `graphify codex install`, post-commit, post-checkout.
- Responsibilities: Refresh code graph or flag semantic refresh after repository changes.

**Repo-local GSD Commands:**
- Location: `.codex/skills/`
- Triggers: `$gsd-*` invocations.
- Responsibilities: Manage planning, execution, validation, codebase mapping, Graphify context, and project workflow artifacts.

## Architectural Constraints

- **Threading:** Semantic extraction uses `ThreadPoolExecutor` for backend chunks in `graphify/llm.py`; AST extraction uses `ProcessPoolExecutor` for uncached file batches in `graphify/extract.py`; watch mode uses `watchdog` observers in `graphify/watch.py`.
- **Global state:** `graphify/extract.py` uses `_TSCONFIG_ALIAS_CACHE`; `graphify/llm.py` caches tokenizer state; `graphify/global_graph.py` writes under `~/.graphify`; `graphify/watch.py` reads `GRAPHIFY_OUT`.
- **Circular imports:** No explicit circular import chain was detected in the sampled architecture; modules generally import downward or locally inside functions to avoid heavy startup dependencies.
- **Derived-output discipline:** Never treat `graphify-out/`, `.planning/graphs/`, or `worked/*/GRAPH_REPORT.md` as authoritative source for code changes.
- **Secret handling:** Detection skips sensitive file names in `graphify/detect.py`; external fetches and path reads must use `graphify/security.py` guards where applicable.
- **Fork discipline:** This repo is Mase's fork; local Graphify skill surfaces include `graphify/skill-codex.md`, `/Users/mase/.codex/skills/graphify/SKILL.md`, and `/Users/mase/.codex/docs/reference/graphify.md`.

## Anti-Patterns

### Bypassing Detection

**What happens:** New extraction flows manually recurse the filesystem instead of using `graphify.detect.detect()` or `graphify.extract.collect_files()`.
**Why it's wrong:** It can include secrets, generated output, hidden directories, or ignored paths that existing guards exclude.
**Do this instead:** Use `graphify/detect.py` for corpus classification and `graphify/extract.py:4937` for AST-supported file collection.

### Replacing Full Graphs During Incremental Work

**What happens:** A code-only rebuild overwrites `graphify-out/graph.json` with only AST output.
**Why it's wrong:** It drops expensive semantic nodes, community labels, hyperedges, and report context.
**Do this instead:** Use `graphify.watch._rebuild_code()` or `graphify.build.build_merge()` as shown in `graphify/watch.py:140` and `graphify/build.py:214`.

### Reading Raw Graph JSON Into Prompts

**What happens:** Agents paste all of `graphify-out/graph.json` into context.
**Why it's wrong:** It wastes context and bypasses the intended graph query/report surfaces.
**Do this instead:** Read `graphify-out/GRAPH_REPORT.md`, then use `graphify query`, `graphify path`, or `graphify explain` through `graphify/__main__.py`.

### Adding New Languages In One Place Only

**What happens:** A new extractor is added without updating detection, dispatch, watch extensions, dependencies, and tests.
**Why it's wrong:** CLI extraction, watch/update, and file classification drift apart.
**Do this instead:** Update `CODE_EXTENSIONS` in `graphify/detect.py`, `_DISPATCH` in `graphify/extract.py`, `_WATCHED_EXTENSIONS` via `graphify/watch.py`, `pyproject.toml`, and tests such as `tests/test_languages.py`.

### Treating Codex Hook Check As Active Guidance

**What happens:** Documentation claims `graphify hook-check` currently injects Codex reminders.
**Why it's wrong:** `graphify/__main__.py:1784` intentionally exits as a no-op because Codex Desktop rejects the old hook payload.
**Do this instead:** Use repo `AGENTS.md`, the installed Graphify skill, and explicit `$graphify` invocation as Codex guidance surfaces.

## Error Handling

**Strategy:** Keep extraction resilient, fail user-facing CLI commands with clear stderr, and skip failed chunks/files where partial graph output remains useful.

**Patterns:**
- Use `_safe_extract()` to warn and return empty fragments for extractor failures (`graphify/extract.py:21`).
- Validate backend prerequisites before long extraction work when possible (`graphify/__main__.py:2244`).
- Parse and repair common malformed LLM JSON, otherwise skip the chunk (`graphify/llm.py:201`).
- Log semantic chunk failures and continue (`graphify/llm.py:741`).
- For corrupt graph loads, print actionable errors and exit (`graphify/serve.py:11`).
- For Git merge-driver graph corruption or size abuse, exit non-zero so Git surfaces the conflict (`graphify/__main__.py:1852`).

## Cross-Cutting Concerns

**Logging:** Mostly direct `print()`/`stderr` CLI messages in `graphify/__main__.py`, `graphify/extract.py`, `graphify/llm.py`, `graphify/watch.py`, and `graphify/hooks.py`.
**Validation:** Extraction schema validation in `graphify/validate.py`; graph path and URL validation in `graphify/security.py`; backend/env checks in `graphify/llm.py` and `graphify/__main__.py`.
**Authentication:** API keys and provider configuration come from environment variables only; do not hardcode keys. Neo4j password should prefer `NEO4J_PASSWORD` over `--password` per `graphify/__main__.py:1994`.
**Caching:** AST and semantic caches live under `graphify-out/cache/` and related semantic cache helpers in `graphify/cache.py`.
**Security:** URL fetches must go through `safe_fetch()` or `safe_fetch_text()` in `graphify/security.py`; labels emitted to HTML/text must be sanitized or escaped.
**Workflow:** Use `.codex/skills/` and `.planning/` for GSD state; do not mix GSD workflow implementation into `graphify/` runtime modules.

---

*Architecture analysis: 2026-05-11*
