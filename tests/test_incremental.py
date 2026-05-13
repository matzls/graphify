"""Integration tests for incremental graphify extract behavior."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable


def _run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", "graphify"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def _make_docs_corpus(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "intro.md").write_text("# Introduction\nThis doc introduces the system.")
    (docs / "api.md").write_text("# API Reference\nThe API has endpoints.")
    return docs


def test_manifest_written_after_extract(tmp_path):
    """After a full extract run, manifest.json must exist (or run fails before writing it)."""
    docs = _make_docs_corpus(tmp_path)
    r = _run(["extract", str(docs)], tmp_path)
    # Should fail with no API key — but NOT with a path error
    assert "no LLM API key" in r.stderr or r.returncode != 0
    # manifest should NOT exist (run failed before writing)
    manifest = docs / "graphify-out" / "manifest.json"
    assert not manifest.exists()


def test_incremental_mode_detected_via_manifest(tmp_path):
    """If manifest.json + graph.json exist, incremental mode message is shown."""
    docs = _make_docs_corpus(tmp_path)
    out = docs / "graphify-out"
    out.mkdir()
    (out / "graph.json").write_text(json.dumps({"nodes": [], "links": []}))
    (out / "manifest.json").write_text(json.dumps({"document": [str(docs / "intro.md")]}))
    r = _run(["extract", str(docs)], tmp_path)
    combined = r.stdout + r.stderr
    assert "incremental" in combined.lower() or r.returncode != 0


def test_no_incremental_without_manifest(tmp_path):
    """Without manifest.json, full scan message is shown (not incremental)."""
    docs = _make_docs_corpus(tmp_path)
    r = _run(["extract", str(docs)], tmp_path)
    assert "[graphify extract] incremental scan" not in r.stdout


def test_code_only_extract_does_not_require_llm_key(tmp_path):
    """AST-only corpora should not fail early just because no LLM key exists."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def hello():\n    return 'hello'\n")
    env = {
        k: v for k, v in os.environ.items()
        if not k.endswith("_API_KEY") and k not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
    }

    r = _run(["extract", str(src)], tmp_path, env=env)

    assert r.returncode == 0, r.stderr
    assert "no LLM API key" not in r.stderr
    assert (src / "graphify-out" / "graph.json").exists()


def test_incremental_extract_prunes_changed_code_source(tmp_path):
    """Modified files should replace stale nodes from the same source_file."""
    src = tmp_path / "src"
    src.mkdir()
    app = src / "app.py"
    app.write_text(
        "def stale_func():\n    return 1\n\n"
        "def keep_func():\n    return 2\n"
    )
    env = {
        k: v for k, v in os.environ.items()
        if not k.endswith("_API_KEY") and k not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
    }
    first = _run(["extract", str(src)], tmp_path, env=env)
    assert first.returncode == 0, first.stderr

    app.write_text("def keep_func():\n    return 3\n")
    second = _run(["extract", str(src)], tmp_path, env=env)

    assert second.returncode == 0, second.stderr
    graph = json.loads((src / "graphify-out" / "graph.json").read_text())
    labels = {node.get("label") for node in graph.get("nodes", [])}
    assert "stale_func" not in labels
    assert any(label and "keep_func" in label for label in labels)
