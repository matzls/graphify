"""Packaging contract tests."""

import tomllib
from pathlib import Path


def test_openai_sdk_is_installed_by_default_for_semantic_backends():
    """Auto-detected Ollama/Gemini/OpenAI-compatible extraction must not fail
    after a normal graphify install.
    """
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "openai" in pyproject["project"]["dependencies"]
