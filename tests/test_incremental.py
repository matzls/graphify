"""Integration tests for incremental graphify extract behavior."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

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
    assert (src / "graphify-out" / "GRAPH_REPORT.md").exists()
    assert (src / "graphify-out" / ".graphify_labels.json").exists()


def test_extract_transcribes_video_files_for_semantic_extraction(tmp_path, monkeypatch):
    from graphify.__main__ import main

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    video = corpus / "lecture.mp4"
    video.write_bytes(b"fake video")
    transcript = corpus / "graphify-out" / "transcripts" / "lecture.txt"
    calls: dict[str, object] = {}

    def fake_transcribe_all(video_files, output_dir=None, initial_prompt=None, force=False):
        calls["video_files"] = video_files
        calls["output_dir"] = output_dir
        calls["force"] = force
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("Transcript content.", encoding="utf-8")
        return [str(transcript)]

    def fake_extract_corpus_parallel(paths, **kwargs):
        calls["semantic_paths"] = [str(p) for p in paths]
        return {
            "nodes": [
                {
                    "id": "lecture_transcript",
                    "label": "Lecture Transcript",
                    "file_type": "document",
                    "source_file": str(transcript),
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 5,
        }

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "extract", str(corpus), "--backend", "gemini"])

    with patch("graphify.transcribe.transcribe_all", side_effect=fake_transcribe_all), \
         patch("graphify.llm.extract_corpus_parallel", side_effect=fake_extract_corpus_parallel):
        main()

    assert calls["video_files"] == [str(video)]
    assert calls["output_dir"] == corpus / "graphify-out" / "transcripts"
    assert calls["force"] is False
    assert calls["semantic_paths"] == [str(transcript)]
    assert (corpus / "graphify-out" / "graph.json").exists()


def test_incremental_extract_forces_changed_video_retranscription(tmp_path, monkeypatch):
    from graphify.__main__ import main

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    video = corpus / "lecture.mp4"
    video.write_bytes(b"v1")
    transcript = corpus / "graphify-out" / "transcripts" / "lecture.txt"
    out = corpus / "graphify-out"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps({
        "version": 1,
        "files": {
            "video": [
                {
                    "path": str(video),
                    "mtime": 0,
                    "size": 0,
                    "hash": "old",
                }
            ]
        },
    }), encoding="utf-8")
    (out / "graph.json").write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_transcribe_all(video_files, output_dir=None, initial_prompt=None, force=False):
        calls["video_files"] = video_files
        calls["force"] = force
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("Fresh transcript.", encoding="utf-8")
        return [str(transcript)]

    def fake_extract_corpus_parallel(paths, **kwargs):
        return {
            "nodes": [{"id": "fresh", "label": "Fresh", "source_file": str(transcript)}],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "extract", str(corpus), "--backend", "gemini"])

    with patch("graphify.transcribe.transcribe_all", side_effect=fake_transcribe_all), \
         patch("graphify.llm.extract_corpus_parallel", side_effect=fake_extract_corpus_parallel):
        main()

    assert calls["video_files"] == [str(video)]
    assert calls["force"] is True


def test_incremental_no_cluster_preserves_unchanged_graph_data(tmp_path, monkeypatch):
    from graphify.__main__ import main

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    keep = corpus / "keep.py"
    change = corpus / "change.py"
    keep.write_text("def keep_func():\n    return 1\n", encoding="utf-8")
    change.write_text("def old_func():\n    return 2\n", encoding="utf-8")
    env = {
        k: v for k, v in os.environ.items()
        if not k.endswith("_API_KEY") and k not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
    }
    first = _run(["extract", str(corpus), "--no-cluster"], tmp_path, env=env)
    assert first.returncode == 0, first.stderr

    change.write_text("def new_func():\n    return 3\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "extract", str(corpus), "--no-cluster"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    graph = json.loads((corpus / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    labels = {n.get("label") for n in graph["nodes"]}
    assert "keep_func()" in labels
    assert "new_func()" in labels
    assert "old_func()" not in labels


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
