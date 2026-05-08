"""Tests for the Ollama backend additions in graphify/llm.py."""
from __future__ import annotations

import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

from graphify.llm import (
    _call_openai_compat,
    _default_model_for_backend,
    _openai_client_kwargs,
    _parse_llm_json,
    _resolve_file_char_cap,
    _resolve_request_timeout,
    _resolve_token_budget,
    detect_backend,
    extract_corpus_parallel,
    BACKENDS,
)


def test_ollama_in_backends():
    assert "ollama" in BACKENDS
    assert BACKENDS["ollama"]["pricing"]["input"] == 0.0
    assert BACKENDS["ollama"]["pricing"]["output"] == 0.0
    assert BACKENDS["ollama"]["max_tokens"] == 8192
    assert BACKENDS["ollama"]["timeout"] == 1800.0
    assert _default_model_for_backend("ollama") == "gemma4:31b"


def test_ollama_timeout_can_be_overridden(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_LLM_TIMEOUT_SECONDS", "12.5")

    assert _resolve_request_timeout("ollama") == 12.5


def test_ollama_openai_client_disables_sdk_retries(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_LLM_TIMEOUT_SECONDS", "12.5")

    assert _openai_client_kwargs("ollama") == {"timeout": 12.5, "max_retries": 0}


def test_ollama_auto_token_budget_is_smaller_than_hosted_default(monkeypatch):
    monkeypatch.delenv("GRAPHIFY_SEMANTIC_TOKEN_BUDGET", raising=False)

    assert _resolve_token_budget("ollama", "auto") == 8000
    assert _resolve_token_budget("kimi", "auto") == 60000
    assert _resolve_token_budget("ollama", None) is None


def test_ollama_uses_smaller_default_file_char_cap(monkeypatch):
    monkeypatch.delenv("GRAPHIFY_FILE_CHAR_CAP", raising=False)

    assert _resolve_file_char_cap("ollama") == 8000
    assert _resolve_file_char_cap("kimi") == 20000


def test_file_char_cap_can_be_overridden(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_FILE_CHAR_CAP", "12000")

    assert _resolve_file_char_cap("ollama") == 12000


def test_ollama_defaults_to_sequential_chunk_execution(tmp_path):
    files = []
    for i in range(3):
        source = tmp_path / f"note_{i}.md"
        source.write_text("# Note\n", encoding="utf-8")
        files.append(source)

    def slow_extract(chunk, **kwargs):
        time.sleep(0.05)
        return {
            "nodes": [{"id": chunk[0].stem}],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }

    with patch("graphify.llm.extract_files_direct", side_effect=slow_extract):
        started = time.time()
        result = extract_corpus_parallel(
            files,
            backend="ollama",
            token_budget=None,
            chunk_size=1,
        )
        elapsed = time.time() - started

    assert len(result["nodes"]) == 3
    assert elapsed >= 0.15


def test_detect_backend_ollama(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    assert detect_backend() == "ollama"


def test_detect_backend_auto_detects_local_ollama(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr("graphify.llm._local_ollama_available", lambda: True)

    assert detect_backend() == "ollama"


def test_detect_backend_kimi_beats_ollama(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert detect_backend() == "kimi"


def test_detect_backend_claude_beats_ollama(monkeypatch):
    # ANTHROPIC_API_KEY (paid, intentional) should win over OLLAMA_BASE_URL
    # (env-driven, easy to set accidentally) -- security fix F-002/F-029.
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert detect_backend() == "claude"


def test_detect_backend_none_without_envvars(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.setattr("graphify.llm._local_ollama_available", lambda: False)
    assert detect_backend() is None


def test_ollama_api_key_sentinel(monkeypatch):
    """extract_files_direct with backend=ollama and no OLLAMA_API_KEY should use sentinel 'ollama' not raise."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    from unittest.mock import patch
    from pathlib import Path
    import tempfile

    fake_result = {
        "nodes": [],
        "edges": [],
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 10,
        "finish_reason": "stop",
    }
    with patch("graphify.llm._call_openai_compat", return_value=fake_result) as mock_call:
        from graphify.llm import extract_files_direct
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("x = 1\n")
            tmp = Path(f.name)
        try:
            extract_files_direct([tmp], backend="ollama", root=tmp.parent)
            # Should have called _call_openai_compat with api_key="ollama"
            assert mock_call.called
            call_kwargs = mock_call.call_args
            api_key_used = call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs.get("api_key", "")
            assert api_key_used == "ollama"
        finally:
            tmp.unlink(missing_ok=True)


def test_ollama_requests_json_object_response_format(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"nodes":[],"edges":[],"hyperedges":[]}'
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=FakeCompletions()
            )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    _call_openai_compat(
        "http://localhost:11434/v1",
        "ollama",
        "gemma4:latest",
        "extract this",
        backend="ollama",
    )

    assert captured["response_format"] == {"type": "json_object"}
    assert captured["extra_body"] == {"options": {"num_predict": 8192}}


def test_parse_llm_json_repairs_missing_final_object_delimiter():
    result = _parse_llm_json(
        '{"nodes":[],"edges":[{"source":"a","target":"b"}],"hyperedges":[]'
    )

    assert result == {
        "nodes": [],
        "edges": [{"source": "a", "target": "b"}],
        "hyperedges": [],
    }


def test_cli_ollama_backend_does_not_require_api_key_for_code_only_corpus(tmp_path, monkeypatch):
    """The CLI should allow Ollama's no-auth sentinel instead of rejecting early."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    source = tmp_path / "sample.py"
    source.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "graphify",
            "extract",
            str(tmp_path),
            "--backend",
            "ollama",
            "--no-cluster",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "requires OLLAMA_API_KEY" not in result.stderr
