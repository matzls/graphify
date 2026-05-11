# Coding Conventions

**Analysis Date:** 2026-05-11

## Naming Patterns

**Files:**
- Use lowercase module filenames under `graphify/`, with words separated by underscores when needed: `graphify/global_graph.py`, `graphify/google_workspace.py`, `graphify/tree_html.py`.
- Place tests in `tests/test_<module-or-feature>.py`, matching the module or behavior under test: `tests/test_watch.py`, `tests/test_transcribe.py`, `tests/test_llm_backends.py`.
- Keep reusable test fixtures under `tests/fixtures/`: `tests/fixtures/sample.py`, `tests/fixtures/sample_calls.py`.
- Packaged assistant skill files live beside package code as Markdown assets: `graphify/skill-codex.md`, `graphify/skill-opencode.md`, `graphify/skill-droid.md`.

**Functions:**
- Use `snake_case` for public functions, private helpers, and tests: `graphify.extract.collect_files`, `graphify.llm.detect_backend`, `tests/test_extract.py::test_collect_files_follows_symlinked_directory`.
- Prefix internal helpers with a single underscore: `graphify.__main__._doctor`, `graphify.extract._make_id`, `graphify.llm._parse_llm_json`.
- Use imperative names for operations that perform work: `graphify.hooks.install`, `graphify.hooks.uninstall`, `graphify.watch.mark_needs_update`.
- Use `test_<expected behavior>` names for tests, with explicit behavior in the function name: `tests/test_ollama.py::test_detect_backend_claude_beats_ollama`, `tests/test_security.py::test_validate_graph_path_blocks_traversal`.

**Variables:**
- Use lowercase `snake_case` for local variables and parameters: `graphify.build.build_from_json`, `graphify.detect.classify_file`, `tests/test_pipeline.py::run_pipeline`.
- Use uppercase constants for module-level configuration: `graphify.detect.CODE_EXTENSIONS`, `graphify.detect.CORPUS_WARN_THRESHOLD`, `graphify.llm.BACKENDS`.
- Use leading-underscore uppercase constants for private module constants: `graphify.llm._DEFAULT_TOKEN_BUDGET`, `graphify.detect._SENSITIVE_PATTERNS`, `graphify.__main__._PLATFORM_CONFIG`.
- Use short graph variables only in graph-specific code where NetworkX idioms are clear: `G` in `graphify.build.build_from_json` and `tests/test_pipeline.py`.

**Types:**
- Prefer built-in generic types from Python 3.10+: `list[dict]`, `dict[str, str]`, `Path | str | None` in `graphify.build.py`, `graphify.llm.py`, and `graphify.__main__.py`.
- Use `dataclass` for structured extractor configuration: `graphify.extract.LanguageConfig`.
- Use `Enum` for closed value sets that cross module boundaries: `graphify.detect.FileType`.
- Keep graph payloads as plain dictionaries and lists instead of custom classes: extraction fragments in `graphify.extract.py`, `graphify.build.py`, and `graphify.llm.py`.

## Code Style

**Formatting:**
- Tool used: Not detected. No Black, Ruff, Prettier, or formatter config is present in `pyproject.toml` or repo root config files.
- Use 4-space indentation for Python code throughout `graphify/*.py` and `tests/*.py`.
- Keep imports at the top, with `from __future__ import annotations` before standard-library imports in newer modules such as `graphify/__main__.py`, `graphify/extract.py`, `graphify/llm.py`, and `tests/test_ollama.py`.
- Keep lines readable, but the repo does not enforce a strict line length. Some user-facing strings and assertions exceed 88 characters in `graphify/__main__.py` and `tests/test_pipeline.py`.
- Prefer explicit `encoding="utf-8"` for durable file reads and writes, especially package/install and hook behavior: `graphify/__main__.py`, `graphify/hooks.py`, `tests/test_hooks.py`.
- Avoid broad formatting churn. The current codebase has compact import blocks and some adjacent test functions without separating blank lines, as seen in `tests/test_security.py` and `tests/test_watch.py`.

**Linting:**
- Tool used: Bandit configuration only.
- Config: `[tool.bandit] skips = ["B404"]` in `pyproject.toml`.
- No Ruff, Flake8, Pylint, or mypy config is detected.
- CI does not run linting. `.github/workflows/ci.yml` installs editable package extras and runs `python -m pytest tests/ -q --tb=short`.

## Import Organization

**Order:**
1. Module docstring, then `from __future__ import annotations` when present: `graphify/llm.py`, `tests/test_ollama.py`.
2. Standard library imports: `json`, `os`, `sys`, `subprocess`, `Path`, `unittest.mock`.
3. Third-party imports: `networkx`, `pytest`, optional SDK imports inside functions.
4. Local package imports: `from graphify...` in tests, relative imports inside package modules such as `from .validate import validate_extraction`.

**Path Aliases:**
- Not detected. The Python package uses regular imports from `graphify` and relative package imports.
- Tests import installed package modules directly: `from graphify.extract import extract_python`, `from graphify import llm`, `from graphify.hooks import install`.

## Error Handling

**Patterns:**
- CLI-facing functions print concise errors to `stderr` and return or raise `SystemExit`: `graphify.__main__._doctor`, `graphify.__main__.install`, `graphify.__main__.main`.
- Corpus and extraction helpers degrade gracefully for optional dependencies or malformed inputs by returning empty values and warnings: `graphify.detect.extract_pdf_text`, `graphify.detect.docx_to_markdown`, `graphify.llm._parse_llm_json`.
- Recoverable extraction failures return empty graph fragments plus an error field rather than crashing the whole run: `graphify.extract._safe_extract`.
- User input validation raises specific exceptions that tests assert against: `graphify.security.validate_url`, `graphify.security.validate_graph_path`, `graphify.hooks.install`.
- Optional dependency imports belong inside the function that needs them and should catch `ImportError` when absence is expected: `graphify.detect.extract_pdf_text`, `graphify.detect.xlsx_to_markdown`, `graphify.watch.watch`.

## Logging

**Framework:** `print`

**Patterns:**
- Use `print(..., file=sys.stderr)` for warnings and user-facing errors: `graphify.build.build_from_json`, `graphify.extract._safe_extract`, `graphify.llm._parse_llm_json`.
- Use stdout for CLI status and install diagnostics: `graphify.__main__.install`, `graphify.__main__._doctor`, `graphify.__main__.gemini_install`.
- Keep messages operational and specific enough for tests to assert snippets: `tests/test_hooks.py`, `tests/test_install.py`, `tests/test_build.py`.
- Do not introduce Python `logging` unless adding a coherent project-wide logging layer. The current code and tests expect direct stdout/stderr output.

## Comments

**When to Comment:**
- Use comments to explain non-obvious compatibility or safety behavior: tree-sitter resolver order in `graphify/extract.py`, LLM timeout/retry choices in `graphify/llm.py`, node deduplication rules in `graphify/build.py`.
- Use short section comments in tests when they make a larger file scannable: `tests/test_security.py`, `tests/test_watch.py`.
- Avoid comments that restate simple code. Prefer tests with explicit names for straightforward behavior.

**JSDoc/TSDoc:**
- Not applicable. This is a Python codebase.
- Use Python docstrings for public functions and important private helpers: `graphify.build.build_from_json`, `graphify.extract._read_tsconfig_aliases`, `graphify.llm._resolve_request_timeout`.
- Test docstrings are used selectively to document regression intent: `tests/test_hooks.py::test_hook_check_no_additionalContext`, `tests/test_ollama.py::test_cli_ollama_backend_does_not_require_api_key_for_code_only_corpus`.

## Function Design

**Size:** Keep small helpers focused where possible, but accept larger functions in CLI routing and language extraction code. `graphify/__main__.py` and `graphify/extract.py` contain large dispatch/configuration surfaces, so new logic should prefer extracting small helpers near the relevant section.

**Parameters:** Prefer `Path` objects for filesystem-facing helpers and convert at boundaries. Examples: `graphify.hooks.install(repo: Path)`, `graphify.detect.classify_file(path: Path)`, `graphify.llm._read_files(paths: list[Path], root: Path, ...)`.

**Return Values:** Use plain dictionaries for graph extraction and detection results, `Path` for filesystem artifacts, and process-style integer return codes for CLI diagnostics. Examples: `graphify.detect.detect`, `graphify.extract.extract`, `graphify.watch.mark_needs_update`, `graphify.__main__._doctor`.

## Module Design

**Exports:** Modules expose functions directly rather than class-based services. New feature code should live in the module that owns the behavior and be imported explicitly by tests.

**Barrel Files:** Minimal. `graphify/__init__.py` exposes package-level metadata only; do not add broad re-export barrels unless a public API contract needs them.

**Project-Specific Constraints:**
- Preserve local fork behavior documented in `AGENTS.md` and `docs/mase-fork-operating-model.md`.
- For install-source, Codex hook, watcher, and transcript behavior, prefer targeted tests in `tests/test_install.py`, `tests/test_hooks.py`, `tests/test_watch.py`, and `tests/test_transcribe.py`.
- Do not patch the active uv tool install directly. Source changes belong in this repository under `graphify/`.

---

*Convention analysis: 2026-05-11*
