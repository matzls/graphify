# Codebase Structure

**Analysis Date:** 2026-05-11

## Directory Layout

```text
graphify/
├── AGENTS.md                 # Repo instructions and Mase fork operating notes
├── ARCHITECTURE.md           # Upstream architecture summary
├── README.md                 # Product docs and command reference
├── SECURITY.md               # Security model and threat notes
├── pyproject.toml            # Python package metadata, deps, console script
├── graphify/                 # Runtime package and packaged assistant skills
├── tests/                    # Pytest suite and fixtures
├── docs/                     # Fork docs, how-it-works, plans, translations
├── worked/                   # Example corpora and generated reports
├── .codex/                   # Repo-local GSD skills, workflows, hooks, agents
├── .planning/                # GSD project state and codebase maps
├── .github/workflows/        # CI workflows
├── build/                    # Build output; generated
├── graphifyy.egg-info/       # Package metadata output; generated
└── .venv/                    # Local virtual environment; generated
```

## Directory Purposes

**`graphify/`:**
- Purpose: Python package implementing the Graphify CLI, extraction pipeline, graph processing, exports, query server, hooks, and packaged skill docs.
- Contains: `.py` runtime modules and `skill*.md` assistant skill templates.
- Key files: `graphify/__main__.py`, `graphify/detect.py`, `graphify/extract.py`, `graphify/llm.py`, `graphify/build.py`, `graphify/export.py`, `graphify/serve.py`, `graphify/watch.py`, `graphify/hooks.py`.

**`tests/`:**
- Purpose: Unit and integration-style tests for runtime modules.
- Contains: `test_*.py` files, language fixtures, example graph outputs.
- Key files: `tests/test_pipeline.py`, `tests/test_languages.py`, `tests/test_install.py`, `tests/test_watch.py`, `tests/test_hooks.py`, `tests/test_llm_backends.py`, `tests/test_security.py`.

**`tests/fixtures/`:**
- Purpose: Small source/document fixtures used by extractor and pipeline tests.
- Contains: `sample.py`, `sample.md`, `sample_calls.py`, `deploy_guide.md`, `graphify-out/`.
- Key files: `tests/fixtures/sample.py`, `tests/fixtures/sample.md`.

**`docs/`:**
- Purpose: Project docs beyond README, including fork operating model and planning notes.
- Contains: Architecture/how-it-works docs, translations, superpower docs, plan docs.
- Key files: `docs/mase-fork-operating-model.md`, `docs/how-it-works.md`, `docs/plans/safe-graphify-skill-upgrade.md`.

**`docs/translations/`:**
- Purpose: Localized README copies.
- Contains: `README.<locale>.md` files.
- Key files: `docs/translations/README.de-DE.md`, `docs/translations/README.zh-CN.md`.

**`docs/plans/`:**
- Purpose: Human/project planning docs for fork changes.
- Contains: Markdown plans.
- Key files: `docs/plans/safe-graphify-skill-upgrade.md`.

**`worked/`:**
- Purpose: Example corpora and generated graph reports that demonstrate Graphify output.
- Contains: Example `raw/` inputs, `GRAPH_REPORT.md`, README/review docs.
- Key files: `worked/example/raw/api.py`, `worked/httpx/GRAPH_REPORT.md`, `worked/mixed-corpus/GRAPH_REPORT.md`.

**`.codex/`:**
- Purpose: Repo-local Codex/GSD workflow installation.
- Contains: skill adapters, workflow engine files, agent definitions, hooks.
- Key files: `.codex/skills/gsd-map-codebase/SKILL.md`, `.codex/skills/gsd-graphify/SKILL.md`, `.codex/get-shit-done/bin/gsd-tools.cjs`.

**`.codex/skills/`:**
- Purpose: Project-local GSD command surfaces.
- Contains: One `SKILL.md` per `$gsd-*` command.
- Key files: `.codex/skills/gsd-execute-phase/SKILL.md`, `.codex/skills/gsd-plan-phase/SKILL.md`, `.codex/skills/gsd-code-review/SKILL.md`, `.codex/skills/gsd-map-codebase/SKILL.md`.

**`.codex/get-shit-done/`:**
- Purpose: GSD workflow implementation, templates, references, and CLI tools.
- Contains: `workflows/`, `templates/`, `references/`, `contexts/`, `bin/`.
- Key files: `.codex/get-shit-done/workflows/map-codebase.md`, `.codex/get-shit-done/references/project-skills-discovery.md`, `.codex/get-shit-done/templates/codebase/`, `.codex/get-shit-done/bin/gsd-tools.cjs`.

**`.planning/`:**
- Purpose: GSD state, generated codebase maps, and planning artifacts.
- Contains: `codebase/`; may contain `STATE.md`, `config.json`, phase/milestone docs, and graph context in active workflows.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

**`.github/workflows/`:**
- Purpose: GitHub Actions CI configuration.
- Contains: Workflow YAML files.
- Key files: `.github/workflows/ci.yml`.

**`build/`:**
- Purpose: Generated Python build output.
- Contains: Built package copy under `build/lib/graphify/`.
- Generated: Yes.
- Committed: Treat as generated output; do not edit source here.

**`graphifyy.egg-info/`:**
- Purpose: Generated package metadata for local builds.
- Contains: Metadata files from setuptools.
- Generated: Yes.
- Committed: Treat as generated metadata; do not edit for runtime changes.

**`.venv/`:**
- Purpose: Local Python virtual environment.
- Contains: installed dependencies and interpreter state.
- Generated: Yes.
- Committed: No.

## Key File Locations

**Entry Points:**
- `graphify/__main__.py`: Main CLI router and command implementation.
- `pyproject.toml`: Defines `graphify = "graphify.__main__:main"` console script.
- `graphify/serve.py`: MCP stdio server and graph query helpers.
- `.codex/skills/*/SKILL.md`: Repo-local GSD command entry points.

**Configuration:**
- `pyproject.toml`: Package metadata, dependencies, optional extras, package data.
- `AGENTS.md`: Repo-level operating notes, fork rules, and GSD routing.
- `.codex/get-shit-done/templates/config.json`: GSD config template.
- `.planning/config.json`: Optional active GSD config location; may not exist.
- `.graphifyignore`: Optional scan ignore file when present in scanned repos.
- `.graphifyinclude`: Optional include allowlist file when present in scanned repos.

**Core Logic:**
- `graphify/detect.py`: File classification, ignore/include rules, manifest helpers, Office/Google Workspace conversion.
- `graphify/extract.py`: Deterministic code/Markdown extraction, language dispatch, AST cache use, cross-file resolution.
- `graphify/llm.py`: Direct semantic extraction backends, chunking, retry, JSON parsing.
- `graphify/build.py`: NetworkX graph construction, merge, dedup integration.
- `graphify/cluster.py`: Community detection and cohesion scoring.
- `graphify/analyze.py`: God nodes, surprising connections, suggested questions, diffs.
- `graphify/report.py`: `GRAPH_REPORT.md` rendering.
- `graphify/export.py`: JSON, HTML, SVG, GraphML, Obsidian, Canvas, Cypher, Neo4j exports.
- `graphify/watch.py`: Code-only rebuilds and needs-update signaling.
- `graphify/hooks.py`: Git hook installation and hook script bodies.
- `graphify/global_graph.py`: `~/.graphify` global graph merge/list/remove.
- `graphify/security.py`: URL, path, and label safety helpers.

**Testing:**
- `tests/test_pipeline.py`: End-to-end local pipeline behavior.
- `tests/test_languages.py`: Multi-language extractor coverage.
- `tests/test_extract.py`: Extractor behavior.
- `tests/test_detect.py`: Detection and ignore behavior.
- `tests/test_llm_backends.py`, `tests/test_ollama.py`, `tests/test_chunking.py`: Semantic backend and chunking behavior.
- `tests/test_watch.py`, `tests/test_hooks.py`: Freshness and hook behavior.
- `tests/test_install.py`, `tests/test_claude_md.py`: Platform install/uninstall behavior.
- `tests/test_security.py`: Security helpers.
- `tests/fixtures/`: Shared input fixtures.

**Documentation:**
- `README.md`: Main product docs and command examples.
- `docs/how-it-works.md`: Pipeline explanation.
- `docs/mase-fork-operating-model.md`: Mase fork and skill-sync operating model.
- `ARCHITECTURE.md`: Existing concise upstream architecture summary.
- `.planning/codebase/`: Current generated codebase intelligence docs.

## Naming Conventions

**Files:**
- Runtime modules use lowercase snake_case: `graphify/global_graph.py`, `graphify/google_workspace.py`.
- Tests use `test_<module_or_feature>.py`: `tests/test_global_graph.py`, `tests/test_llm_backends.py`.
- Packaged skills use `skill-<platform>.md`: `graphify/skill-codex.md`, `graphify/skill-opencode.md`.
- GSD skill directories use `gsd-<command>/SKILL.md`: `.codex/skills/gsd-map-codebase/SKILL.md`.
- Generated codebase maps use uppercase names: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

**Directories:**
- Runtime package code belongs under `graphify/`.
- Tests belong under `tests/`; fixtures belong under `tests/fixtures/`.
- Durable human/project docs belong under `docs/`.
- Example corpora and output demonstrations belong under `worked/`.
- GSD workflow mechanics belong under `.codex/get-shit-done/`.
- GSD user-facing command adapters belong under `.codex/skills/`.
- GSD generated planning state belongs under `.planning/`.

## Where to Add New Code

**New CLI Command:**
- Primary code: `graphify/__main__.py`
- Supporting logic: Add a focused helper module under `graphify/` if command logic is more than routing.
- Tests: Add or extend `tests/test_<feature>.py`; use `tests/test_install.py` for install command behavior and `tests/test_query_cli.py` for query-oriented CLI behavior.

**New Language Extractor:**
- Primary code: `graphify/extract.py`
- Detection updates: `graphify/detect.py`
- Watch/update consistency: Confirm `graphify/watch.py` receives the extension through `CODE_EXTENSIONS`.
- Dependencies: `pyproject.toml`
- Tests: `tests/test_languages.py` plus fixtures under `tests/fixtures/` when a reusable file helps.

**New Semantic Backend:**
- Primary code: `graphify/llm.py`
- CLI backend validation: `graphify/__main__.py`
- Dependencies/extras: `pyproject.toml`
- Tests: `tests/test_llm_backends.py`, `tests/test_chunking.py`, backend-specific test file if behavior needs isolation.

**New Export Format:**
- Primary code: `graphify/export.py` for graph export logic.
- CLI routing: `graphify/__main__.py` under `export`.
- Tests: `tests/test_export.py` or a new focused `tests/test_<format>.py`.

**New Graph Analysis:**
- Primary code: `graphify/analyze.py`
- Report integration: `graphify/report.py`
- Tests: `tests/test_analyze.py`, `tests/test_report.py`.

**New Cache/Incremental Behavior:**
- Primary code: `graphify/cache.py`, `graphify/manifest.py`, `graphify/watch.py`
- CLI routing: `graphify/__main__.py` if user-facing.
- Tests: `tests/test_cache.py`, `tests/test_incremental.py`, `tests/test_watch.py`.

**New Security Guard:**
- Primary code: `graphify/security.py`
- Call sites: Use from `graphify/ingest.py`, `graphify/serve.py`, `graphify/export.py`, or the relevant command module.
- Tests: `tests/test_security.py`.

**New Assistant Platform Skill:**
- Packaged skill: `graphify/skill-<platform>.md`
- Install/uninstall logic: `graphify/__main__.py`
- Package data: `pyproject.toml`
- Tests: `tests/test_install.py`.

**New GSD Command/Workflow:**
- Skill adapter: `.codex/skills/gsd-<name>/SKILL.md`
- Workflow implementation: `.codex/get-shit-done/workflows/<name>.md`
- Supporting templates/references: `.codex/get-shit-done/templates/` or `.codex/get-shit-done/references/`
- Generated state/output: `.planning/`

**Utilities:**
- Shared runtime helpers: Put in the closest existing module, such as `graphify/security.py` for safety, `graphify/cache.py` for cache logic, or `graphify/build.py` for graph normalization.
- Avoid broad utility modules unless multiple existing modules need the same helper.

## Special Directories

**`graphify-out/`:**
- Purpose: Default output for Graphify runs in scanned projects.
- Generated: Yes.
- Committed: Generally no; example outputs exist under `worked/`.

**`.planning/codebase/`:**
- Purpose: Generated codebase intelligence for GSD planning/execution.
- Generated: Yes.
- Committed: Project-dependent; this repo uses it as workflow context.

**`.planning/graphs/`:**
- Purpose: GSD Graphify context output referenced by `$gsd-graphify`.
- Generated: Yes.
- Committed: Treat as derived evidence unless project workflow explicitly says otherwise.

**`.codex/skills/`:**
- Purpose: Repo-local GSD skill entry points.
- Generated: Installed workflow surface, then maintained as project tooling.
- Committed: Yes when repo-local GSD is part of the project.

**`.codex/get-shit-done/`:**
- Purpose: Repo-local GSD engine, workflows, references, and templates.
- Generated: Installed workflow framework, then maintained as project tooling.
- Committed: Yes when repo-local GSD is part of the project.

**`worked/`:**
- Purpose: Checked examples for documentation and behavioral demonstration.
- Generated: Mixed; contains source fixtures and generated reports.
- Committed: Yes.

**`build/`:**
- Purpose: setuptools build output.
- Generated: Yes.
- Committed: No source edits here.

**`graphifyy.egg-info/`:**
- Purpose: setuptools package metadata output.
- Generated: Yes.
- Committed: No source edits here.

**`.venv/`:**
- Purpose: local development virtualenv.
- Generated: Yes.
- Committed: No.

---

*Structure analysis: 2026-05-11*
