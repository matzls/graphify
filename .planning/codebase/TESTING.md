# Testing Patterns

**Analysis Date:** 2026-05-11

## Test Framework

**Runner:**
- `pytest`, version not pinned in project metadata.
- Config: Not detected. No `pytest.ini`, `tox.ini`, `setup.cfg`, or `[tool.pytest]` section is present.
- CI config: `.github/workflows/ci.yml`.

**Assertion Library:**
- Native `assert` statements with pytest assertion rewriting.
- `pytest.raises` for exception behavior: `tests/test_security.py`, `tests/test_hooks.py`, `tests/test_validate.py`.
- `pytest.approx` for approximate numeric checks: `tests/test_semantic_similarity.py`.

**Run Commands:**
```bash
python -m pytest tests/ -q --tb=short              # CI command
uv run pytest tests/test_install.py                # Install/source behavior
uv run pytest tests/test_hooks.py                  # Codex and git hook behavior
uv run pytest tests/test_watch.py                  # Watch/code-only rebuild behavior
uv run pytest tests/test_transcribe.py             # Transcript/media behavior
uv run pytest tests/ -q                            # Broad local suite
```

## Test File Organization

**Location:**
- Tests live in top-level `tests/`, not co-located with source modules.
- Test fixtures live under `tests/fixtures/`, including `tests/fixtures/sample.py`, `tests/fixtures/sample_calls.py`, and `tests/fixtures/graphify-out/`.
- Benchmark-style scripts also live in `tests/`, such as `tests/bench_extract.py`, but normal regression tests use `tests/test_*.py`.

**Naming:**
- Use `tests/test_<module-or-feature>.py`: `tests/test_build.py`, `tests/test_detect.py`, `tests/test_llm_backends.py`.
- Use `test_<specific behavior>` function names: `test_collect_files_handles_circular_symlinks`, `test_detect_backend_none_without_envvars`, `test_hook_check_no_additionalContext`.
- Use helper functions with a leading underscore inside test modules: `_make_git_repo` in `tests/test_hooks.py`, `_clear_backend_env` in `tests/test_llm_backends.py`, `_install` in `tests/test_install.py`.

**Structure:**
```text
tests/
├── test_<module>.py          # Unit/regression tests for one module or feature
├── test_pipeline.py          # AST-only end-to-end pipeline regression tests
├── fixtures/                 # Static source fixtures and graph outputs
└── bench_extract.py          # Manual benchmark helper
```

## Test Structure

**Suite Organization:**
```python
from pathlib import Path
import pytest

from graphify.extract import extract_python, extract, collect_files, _make_id

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_python_finds_class():
    result = extract_python(FIXTURES / "sample.py")
    labels = [n["label"] for n in result["nodes"]]
    assert "Transformer" in labels


def test_no_dangling_edges_on_extract():
    result = extract(list(FIXTURES.glob("*.py")))
    node_ids = {n["id"] for n in result["nodes"]}
    for edge in result["edges"]:
        if edge["relation"] in {"contains", "method", "inherits", "calls"}:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids
```

**Patterns:**
- Use Arrange-Act-Assert inline without formal section comments for small tests: `tests/test_extract.py`, `tests/test_build.py`.
- Use section comments for larger topic-based suites: `tests/test_security.py`, `tests/test_watch.py`.
- Test pure helpers directly when behavior is deterministic: `graphify.extract._make_id`, `graphify.llm._resolve_request_timeout`, `graphify.watch._parse_report_community_labels`.
- Test CLI behavior with `subprocess.run` only where process boundaries matter: `tests/test_hooks.py`, `tests/test_ollama.py`, `tests/test_install.py`.
- Prefer AST-only or mocked tests for semantic extraction behavior. Avoid live LLM or network calls in the default suite.

## Mocking

**Framework:** `unittest.mock` plus pytest `monkeypatch`.

**Patterns:**
```python
def test_extract_files_direct_routes_gemini_through_openai_compat(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    source = tmp_path / "note.md"
    source.write_text("# Architecture\n")
    result = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 1, "output_tokens": 1}

    with patch("graphify.llm._call_openai_compat", return_value=result) as call:
        assert llm.extract_files_direct([source], backend="gemini", root=tmp_path) is result

    assert call.call_args.args[2] == "gemini-3-flash-preview"
```

**What to Mock:**
- External SDK/client calls: `_call_openai_compat` in `tests/test_llm_backends.py` and `tests/test_ollama.py`.
- Network fetch helpers: `_build_opener` in `tests/test_security.py`.
- Home directory and current working directory effects for install tests: `Path.home`, `monkeypatch.chdir`, and `sys.argv` in `tests/test_install.py`.
- Environment variables for backend detection and feature flags: `monkeypatch.setenv` and `monkeypatch.delenv` in `tests/test_ollama.py`, `tests/test_llm_backends.py`, and `tests/test_google_workspace.py`.
- Global output paths when testing graph aggregation: patch `_GLOBAL_DIR`, `_GLOBAL_GRAPH`, and `_GLOBAL_MANIFEST` in `tests/test_global_graph.py`.

**What NOT to Mock:**
- Do not mock filesystem behavior when testing install, hook, cache, graph export, or detection behavior. Use `tmp_path` and real files instead: `tests/test_hooks.py`, `tests/test_cache.py`, `tests/test_detect.py`, `tests/test_export.py`.
- Do not mock the AST extraction path for normal extractor regressions. Use `tests/fixtures/sample.py` and `tests/fixtures/sample_calls.py`.
- Do not call real LLM providers, live Ollama, or external HTTP services in default tests. Mock these boundaries.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def tmp_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world")
    return f


def _make_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path
```

**Location:**
- Static fixtures: `tests/fixtures/`.
- Temporary files and repos: pytest `tmp_path` inside individual tests.
- Shared module constants for fixture paths: `FIXTURES = Path(__file__).parent / "fixtures"` in `tests/test_extract.py` and `tests/test_pipeline.py`.
- Local helper factories stay in the test module that uses them, not a shared conftest. No `tests/conftest.py` is present.

## Coverage

**Requirements:** None enforced. No coverage config or CI coverage threshold is detected.

**View Coverage:**
```bash
python -m pytest tests/ -q --tb=short              # Current enforced confidence gate
```

Coverage tooling is not configured. If coverage is needed, add an explicit tool and threshold rather than assuming one exists.

## Test Types

**Unit Tests:**
- Most tests are module-level unit/regression tests in `tests/test_*.py`.
- They exercise pure helpers, file classification, graph building, extraction, security guards, export functions, install routing, and backend selection.
- Examples: `tests/test_build.py`, `tests/test_detect.py`, `tests/test_cache.py`, `tests/test_security.py`, `tests/test_llm_backends.py`.

**Integration Tests:**
- `tests/test_pipeline.py` runs an end-to-end AST-only pipeline: detect, extract, build, cluster, analyze, report, and export.
- `tests/test_install.py` verifies install routing across supported assistant platforms and checks generated files.
- `tests/test_hooks.py` creates real temporary git repositories and verifies hook install/uninstall behavior.
- `tests/test_ollama.py` includes subprocess CLI coverage for `python -m graphify extract ... --backend ollama --no-cluster` without requiring a real API key for code-only corpora.

**E2E Tests:**
- No browser or full external-service E2E suite is detected.
- CI performs a package-level smoke test after pytest by running `graphify --help` and `graphify install` in `.github/workflows/ci.yml`.

## Common Patterns

**Async Testing:**
```python
def test_ollama_defaults_to_sequential_chunk_execution(tmp_path):
    files = []
    for i in range(3):
        source = tmp_path / f"note_{i}.md"
        source.write_text("# Note\n", encoding="utf-8")
        files.append(source)

    with patch("graphify.llm.extract_files_direct", side_effect=slow_extract):
        result = extract_corpus_parallel(files, backend="ollama", token_budget=None, chunk_size=1)

    assert len(result["nodes"]) == 3
```

The suite does not use async/await test helpers. Concurrency behavior is tested by controlling worker behavior and asserting elapsed time or call effects, as in `tests/test_ollama.py`.

**Error Testing:**
```python
def test_validate_url_rejects_file():
    with pytest.raises(ValueError, match="file"):
        validate_url("file:///etc/passwd")


def test_no_git_repo_raises(tmp_path):
    with pytest.raises(RuntimeError, match="No git repository"):
        install(tmp_path / "not_a_repo")
```

Use `pytest.raises(..., match=...)` when the message is part of the user-facing contract. This pattern appears in `tests/test_security.py`, `tests/test_hooks.py`, `tests/test_validate.py`, and `tests/test_llm_backends.py`.

**Output Testing:**
- Use `capsys` for stdout/stderr assertions: `tests/test_build.py`, `tests/test_claude_md.py`, `tests/test_global_graph.py`, `tests/test_install.py`.
- Use `subprocess.run(..., capture_output=True, text=True)` for process-level CLI checks: `tests/test_hooks.py`, `tests/test_ollama.py`.

**Filesystem Testing:**
- Use `tmp_path` for all write-heavy tests.
- Write files with explicit encoding when behavior depends on text contents: `tests/test_hooks.py`, `tests/test_ollama.py`, `tests/test_security.py`.
- For git hook tests, initialize a real git repo with `git init` and inspect `.git/hooks/` directly: `tests/test_hooks.py`, `tests/test_install.py`.

---

*Testing analysis: 2026-05-11*
