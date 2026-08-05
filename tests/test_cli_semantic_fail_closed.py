from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]


def _run_main(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> int:
    from graphify.__main__ import main

    monkeypatch.setattr(sys, "argv", ["graphify", *args])
    try:
        main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def _patch_extract_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    fresh: dict,
    ast_nodes: list[dict] | None = None,
    patch_llm: bool = True,
) -> tuple[Path, Path]:
    import graphify.cache
    import graphify.detect
    import graphify.extract
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("# Doc\n\nSemantic input.\n", encoding="utf-8")
    code = root / "app.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")

    files = {"document": [str(doc)], "code": [str(code)] if ast_nodes is not None else []}
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": files,
            "total_files": sum(len(v) for v in files.values()),
            "total_words": 3,
        },
    )
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: ([], [], [], list(paths)),
    )
    monkeypatch.setattr(
        graphify.cache,
        "save_semantic_cache",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("cache should not be written")),
    )
    if patch_llm:
        monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
        monkeypatch.setattr(graphify.llm, "extract_corpus_parallel", lambda *_, **__: fresh)
    if ast_nodes is not None:
        monkeypatch.setattr(
            graphify.extract,
            "extract",
            lambda *_, **__: {
                "nodes": ast_nodes,
                "edges": [],
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
    return root, doc


def test_extract_single_file_target_writes_output_next_to_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.llm

    doc = tmp_path / "decision.md"
    doc.write_text("# Decision\n\nUse a bounded semantic scan.\n", encoding="utf-8")
    node_id = "decision"
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: ([], [], [], list(paths)),
    )
    monkeypatch.setattr(graphify.cache, "save_semantic_cache", lambda *_, **__: None)
    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "extract_corpus_parallel",
        lambda *_, **__: {
            "nodes": [
                {
                    "id": node_id,
                    "label": "Decision",
                    "type": "document",
                    "source_file": str(doc.resolve()),
                    "confidence": 1.0,
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "total_chunks": 1,
        },
    )

    rc = _run_main(monkeypatch, ["extract", str(doc), "--backend", "ollama", "--no-cluster"])

    graph_path = tmp_path / "graphify-out" / "graph.json"
    assert rc == 0
    assert graph_path.exists()
    assert not (doc / "graphify-out").exists()
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["nodes"][0]["id"] == node_id


def test_pending_marker_widens_no_change_incremental_semantic_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("# unchanged\n", encoding="utf-8")
    out = root / "graphify-out"
    out.mkdir()
    (out / "graph.json").write_text(
        json.dumps({"nodes": [{"id": "old", "source_file": "doc.md"}], "links": []}),
        encoding="utf-8",
    )
    (out / "manifest.json").write_text("{}", encoding="utf-8")
    pending = out / "needs_update"
    legacy_pending = out / ".needs_update"
    pending.write_text("1", encoding="utf-8")
    legacy_pending.write_text("1", encoding="utf-8")
    monkeypatch.setattr(
        graphify.detect,
        "detect_incremental",
        lambda *_, **__: {
            "files": {"document": [str(doc)], "code": [], "paper": [], "image": [], "video": []},
            "new_files": {"document": [], "code": [], "paper": [], "image": [], "video": []},
            "unchanged_files": {"document": [str(doc)]},
            "deleted_files": [],
            "excluded_files": [],
        },
    )
    monkeypatch.setattr(graphify.detect, "save_manifest", lambda *_, **__: None)
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: (
            [
                {
                    "id": "cached_doc",
                    "label": "Cached Doc",
                    "file_type": "document",
                    "source_file": str(doc),
                }
            ],
            [],
            [],
            [],
        ),
    )
    monkeypatch.setattr(
        graphify.llm,
        "validate_backend_dependencies",
        lambda backend: (_ for _ in ()).throw(AssertionError("semantic preflight called")),
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 0
    assert not pending.exists()
    assert not legacy_pending.exists()
    graph = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    assert [node["id"] for node in graph["nodes"]] == ["cached_doc"]


def test_extract_preserves_pending_marker_when_manifest_save_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect

    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "fresh_doc",
                    "label": "Fresh Doc",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "partial_chunks": 0,
            "total_chunks": 1,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    pending = out / "needs_update"
    pending.write_text("1", encoding="utf-8")
    monkeypatch.setattr(graphify.cache, "save_semantic_cache", lambda *_, **__: None)
    monkeypatch.setattr(
        graphify.detect,
        "save_manifest",
        lambda *_, **__: (_ for _ in ()).throw(OSError("manifest unavailable")),
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 0
    assert pending.exists(), "manifest failure must keep semantic work pending"


def test_video_transcription_failure_preserves_pending_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect
    import graphify.llm
    import graphify.transcribe

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("# semantic input\n", encoding="utf-8")
    video = root / "demo.mp4"
    video.write_bytes(b"video fixture")
    out = root / "graphify-out"
    out.mkdir()
    pending = out / "needs_update"
    pending.write_text("1", encoding="utf-8")
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": {
                "document": [str(doc)],
                "video": [str(video)],
                "code": [],
                "paper": [],
                "image": [],
            },
            "total_files": 2,
            "total_words": 3,
        },
    )
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: ([], [], [], list(paths)),
    )
    monkeypatch.setattr(graphify.cache, "save_semantic_cache", lambda *_, **__: None)
    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "extract_corpus_parallel",
        lambda *_, **__: {
            "nodes": [
                {
                    "id": "doc",
                    "label": "Doc",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "partial_chunks": 0,
            "total_chunks": 1,
        },
    )
    monkeypatch.setattr(
        graphify.transcribe,
        "transcribe",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("transcription failed")),
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 0
    assert pending.exists(), "a skipped video must keep semantic work pending"


def test_extract_preserves_existing_graph_when_all_fresh_semantic_chunks_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "failed_chunks": 2,
            "total_chunks": 2,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    graph = out / "graph.json"
    graph.write_text('{"sentinel": true}', encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 1
    assert graph.read_text(encoding="utf-8") == '{"sentinel": true}'


def test_extract_preserves_existing_graph_when_fresh_semantic_output_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "failed_chunks": 0,
            "total_chunks": 1,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    graph = out / "graph.json"
    graph.write_text('{"sentinel": true}', encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 1
    assert graph.read_text(encoding="utf-8") == '{"sentinel": true}'


def test_extract_preserves_existing_graph_when_some_fresh_semantic_chunks_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "failed_chunks": 1,
            "partial_chunks": 0,
            "total_chunks": 2,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    graph = out / "graph.json"
    graph.write_text('{"sentinel": true}', encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 1
    assert graph.read_text(encoding="utf-8") == '{"sentinel": true}'


def test_extract_preserves_existing_graph_when_fresh_semantic_chunks_are_partial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "failed_chunks": 0,
            "partial_chunks": 1,
            "total_chunks": 1,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    graph = out / "graph.json"
    graph.write_text('{"sentinel": true}', encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 1
    assert graph.read_text(encoding="utf-8") == '{"sentinel": true}'


def test_allow_partial_writes_ast_output_when_fresh_semantic_chunks_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "failed_chunks": 1,
            "total_chunks": 1,
        },
        ast_nodes=[{"id": "app_value", "label": "VALUE", "source_file": "app.py"}],
    )
    out = root / "graphify-out"
    out.mkdir()
    pending = out / "needs_update"
    pending.write_text("1", encoding="utf-8")

    rc = _run_main(
        monkeypatch,
        ["extract", str(root), "--backend", "ollama", "--no-cluster", "--allow-partial"],
    )

    assert rc == 0
    assert pending.exists(), "partial semantic output must remain pending"
    data = json.loads((root / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    assert data["nodes"] == [{"id": "app_value", "label": "VALUE", "source_file": "app.py"}]
    marker = json.loads(
        (root / "graphify-out" / ".graphify_semantic_marker").read_text(encoding="utf-8")
    )
    assert marker["status"] == "partial"
    assert marker["failed_chunks"] == 1
    assert marker["total_chunks"] == 1


def test_allow_partial_degraded_semantic_output_is_not_cached(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "failed_chunks": 0,
            "partial_chunks": 1,
            "total_chunks": 1,
        },
    )

    rc = _run_main(
        monkeypatch,
        ["extract", str(root), "--backend", "ollama", "--no-cluster", "--allow-partial"],
    )

    assert rc == 0
    marker = json.loads(
        (root / "graphify-out" / ".graphify_semantic_marker").read_text(encoding="utf-8")
    )
    assert marker["status"] == "partial"
    assert marker["partial_chunks"] == 1


def test_retry_exhausted_semantic_output_is_not_checkpointed_across_output_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("Partial semantic input.\n", encoding="utf-8")
    external_out = tmp_path / "external-output"
    calls = 0

    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": {"document": [str(doc)]},
            "total_files": 1,
            "total_words": 3,
        },
    )
    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)

    def partial_provider(*_, **__):
        nonlocal calls
        calls += 1
        return {
            "nodes": [
                {
                    "id": "partial_doc",
                    "label": "Partial Doc",
                    "file_type": "document",
                    "source_file": str(doc),
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "finish_reason": "length",
        }

    monkeypatch.setattr(graphify.llm, "extract_files_direct", partial_provider)

    rc = _run_main(
        monkeypatch,
        [
            "extract",
            str(root),
            "--backend",
            "ollama",
            "--no-cluster",
            "--allow-partial",
            "--out",
            str(external_out),
        ],
    )

    assert rc == 0
    assert calls == 1
    assert not list((root / "graphify-out" / "cache" / "semantic").glob("*.json"))
    assert not list((external_out / "graphify-out" / "cache" / "semantic").glob("*.json"))

    # A later default-root run must invoke the provider again and fail closed,
    # rather than treating the degraded first result as a semantic cache hit.
    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 1
    assert calls == 2
    *_, uncached = graphify.cache.check_semantic_cache([str(doc)], root=root)
    assert uncached == [str(doc)]


def test_allow_partial_marks_degraded_semantic_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "failed_chunks": 1,
            "partial_chunks": 1,
            "total_chunks": 3,
        },
    )

    rc = _run_main(
        monkeypatch,
        ["extract", str(root), "--backend", "ollama", "--no-cluster", "--allow-partial"],
    )

    marker = json.loads(
        (root / "graphify-out" / ".graphify_semantic_marker").read_text(encoding="utf-8")
    )
    assert rc == 0
    assert marker["status"] == "partial"
    assert marker["failed_chunks"] == 1
    assert marker["partial_chunks"] == 1
    assert marker["total_chunks"] == 3


def test_code_only_extract_does_not_preflight_semantic_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.detect
    import graphify.extract
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    code = root / "app.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {"files": {"code": [str(code)], "document": []}},
    )
    monkeypatch.setattr(
        graphify.extract,
        "extract",
        lambda *_, **__: {
            "nodes": [{"id": "app_value", "label": "VALUE", "source_file": "app.py"}],
            "edges": [],
            "input_tokens": 0,
            "output_tokens": 0,
        },
    )
    monkeypatch.setattr(
        graphify.llm,
        "validate_backend_dependencies",
        lambda backend: (_ for _ in ()).throw(AssertionError("semantic preflight called")),
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    data = json.loads((root / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert data["nodes"] == [{"id": "app_value", "label": "VALUE", "source_file": "app.py"}]
    assert not (root / "graphify-out" / ".graphify_semantic_marker").exists()


def test_code_only_extract_clears_stale_partial_semantic_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.detect
    import graphify.extract

    root = tmp_path / "corpus"
    root.mkdir()
    code = root / "app.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")
    out = root / "graphify-out"
    out.mkdir()
    (out / ".graphify_semantic_marker").write_text(
        json.dumps({"status": "partial", "failed_chunks": 1}),
        encoding="utf-8",
    )
    pending = out / "needs_update"
    pending.write_text("1", encoding="utf-8")
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {"files": {"code": [str(code)], "document": []}},
    )
    monkeypatch.setattr(
        graphify.extract,
        "extract",
        lambda *_, **__: {
            "nodes": [{"id": "app_value", "label": "VALUE", "source_file": "app.py"}],
            "edges": [],
            "input_tokens": 0,
            "output_tokens": 0,
        },
    )

    rc = _run_main(
        monkeypatch,
        ["extract", str(root), "--backend", "ollama", "--no-cluster", "--code-only"],
    )

    assert rc == 0
    assert not (out / ".graphify_semantic_marker").exists()
    assert pending.exists(), "code-only extraction must preserve pending semantic work"


def test_fresh_semantic_extract_rewrites_stale_partial_marker_as_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "fresh_doc",
                    "label": "Fresh Doc",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "partial_chunks": 0,
            "total_chunks": 1,
        },
    )
    out = root / "graphify-out"
    out.mkdir()
    (out / ".graphify_semantic_marker").write_text(
        json.dumps({"status": "partial", "failed_chunks": 1}),
        encoding="utf-8",
    )
    pending = out / "needs_update"
    legacy_pending = out / ".needs_update"
    pending.write_text("1", encoding="utf-8")
    legacy_pending.write_text("1", encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 0
    assert not pending.exists()
    assert not legacy_pending.exists()
    marker = json.loads((out / ".graphify_semantic_marker").read_text(encoding="utf-8"))
    assert marker["status"] == "clean"
    assert marker["failed_chunks"] == 0
    assert marker["partial_chunks"] == 0


def test_cache_only_semantic_extract_rewrites_stale_partial_marker_as_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("# Doc\n\nCached semantic input.\n", encoding="utf-8")
    out = root / "graphify-out"
    out.mkdir()
    (out / ".graphify_semantic_marker").write_text(
        json.dumps({"status": "partial", "failed_chunks": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": {"document": [str(doc)]},
            "total_files": 1,
            "total_words": 3,
        },
    )
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: (
            [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": str(doc),
                }
            ],
            [],
            [],
            [],
        ),
    )
    monkeypatch.setattr(
        graphify.cache,
        "save_semantic_cache",
        lambda *_, **__: (_ for _ in ()).throw(AssertionError("cache should not be saved")),
    )
    monkeypatch.setattr(
        graphify.llm,
        "validate_backend_dependencies",
        lambda backend: (_ for _ in ()).throw(AssertionError("semantic preflight called")),
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    assert rc == 0
    marker = json.loads((out / ".graphify_semantic_marker").read_text(encoding="utf-8"))
    assert marker["status"] == "clean"
    assert marker["failed_chunks"] == 0
    assert marker["partial_chunks"] == 0


def test_extract_writes_graph_report_from_current_graph(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root, doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [
                {
                    "id": "doc_concept",
                    "label": "Doc Concept",
                    "file_type": "document",
                    "source_file": "doc.md",
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "failed_chunks": 0,
            "total_chunks": 1,
        },
    )
    monkeypatch.setattr("graphify.cache.save_semantic_cache", lambda *_, **__: None)
    out = root / "graphify-out"
    out.mkdir()
    pending = out / "needs_update"
    legacy_pending = out / ".needs_update"
    pending.write_text("1", encoding="utf-8")
    legacy_pending.write_text("1", encoding="utf-8")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama"])

    assert not pending.exists()
    assert not legacy_pending.exists()
    report = (root / "graphify-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    graph = json.loads((root / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert f"{len(graph['nodes'])} nodes" in report
    assert "10 input" in report
    assert "20 output" in report


def test_incremental_extract_prunes_existing_graphify_temp_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import graphify.cache
    import graphify.detect
    import graphify.extract
    import graphify.llm

    root = tmp_path / "corpus"
    root.mkdir()
    doc = root / "doc.md"
    doc.write_text("# Doc\n\nSemantic input.\n", encoding="utf-8")
    kept = root / "kept.md"
    kept.write_text("# Kept\n", encoding="utf-8")
    out = root / "graphify-out"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps({"document": []}), encoding="utf-8")
    (out / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "stale_diag",
                        "label": "stale diag",
                        "file_type": "document",
                        "source_file": ".graphify_detect.json",
                    },
                    {
                        "id": "kept",
                        "label": "Kept",
                        "file_type": "document",
                        "source_file": "kept.md",
                    },
                ],
                "links": [
                    {
                        "source": "stale_diag",
                        "target": "kept",
                        "relation": "references",
                        "confidence": "EXTRACTED",
                        "source_file": ".graphify_detect.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    detection = {
        "files": {"document": [str(doc), str(kept)]},
        "new_files": {"document": [str(doc)]},
        "unchanged_files": {"document": [str(kept)]},
        "deleted_files": [],
        "total_files": 2,
        "total_words": 3,
    }
    monkeypatch.setattr(graphify.detect, "detect_incremental", lambda *_, **__: detection)
    monkeypatch.setattr(
        graphify.cache,
        "check_semantic_cache",
        lambda paths, root, **_: ([], [], [], list(paths)),
    )
    monkeypatch.setattr(graphify.cache, "save_semantic_cache", lambda *_, **__: None)
    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "extract_corpus_parallel",
        lambda *_, **__: {
            "nodes": [
                {
                    "id": "fresh_doc",
                    "label": "Fresh Doc",
                    "file_type": "document",
                    "source_file": str(doc),
                }
            ],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "total_chunks": 1,
        },
    )
    monkeypatch.setattr(
        graphify.extract,
        "extract",
        lambda *_, **__: {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0},
    )

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama"])

    graph = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    sources = {node.get("source_file") for node in graph["nodes"]}
    assert rc == 0
    assert ".graphify_detect.json" not in sources
    assert "kept.md" in sources


def test_doctor_help_lists_backend_and_probe(monkeypatch: pytest.MonkeyPatch, capsys):
    rc = _run_main(monkeypatch, ["doctor", "--help"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "--backend BACKEND" in out
    assert "--probe" in out


def test_doctor_backend_validation_failure_does_not_report_success(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    import graphify.llm

    monkeypatch.setattr(
        graphify.llm,
        "validate_backend_dependencies",
        lambda backend: (_ for _ in ()).throw(ImportError("missing backend dependency")),
    )

    rc = _run_main(monkeypatch, ["doctor", "--backend", "ollama", "--probe"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "missing backend dependency" in captured.err
    assert "backend dependencies (ollama): ok" not in captured.out
    assert "backend probe (ollama): ok" not in captured.out


def test_doctor_pi_capability_runtime_error_returns_status_one(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    import graphify.llm

    monkeypatch.setattr(
        graphify.llm,
        "validate_backend_dependencies",
        lambda backend: (_ for _ in ()).throw(RuntimeError("Pi capability unavailable")),
    )

    rc = _run_main(monkeypatch, ["doctor", "--backend", "pi"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Pi capability unavailable" in captured.err
    assert "backend dependencies (pi): ok" not in captured.out


def test_doctor_probe_failure_does_not_report_success(monkeypatch: pytest.MonkeyPatch, capsys):
    import graphify.llm

    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "probe_backend",
        lambda backend: (_ for _ in ()).throw(RuntimeError("probe unavailable")),
    )

    rc = _run_main(monkeypatch, ["doctor", "--backend", "ollama", "--probe"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "probe unavailable" in captured.err
    assert "backend dependencies (ollama): ok" in captured.out
    assert "backend probe (ollama): ok" not in captured.out


def test_doctor_probe_requires_backend(monkeypatch: pytest.MonkeyPatch, capsys):
    rc = _run_main(monkeypatch, ["doctor", "--probe"])

    err = capsys.readouterr().err
    assert rc == 2
    assert "--probe requires --backend" in err


def test_doctor_backend_probe_reports_summary(monkeypatch: pytest.MonkeyPatch, capsys):
    import graphify.llm

    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "probe_backend",
        lambda backend: {
            "nodes": 1,
            "edges": 2,
            "hyperedges": 3,
            "input_tokens": 4,
            "output_tokens": 5,
        },
    )

    rc = _run_main(monkeypatch, ["doctor", "--backend", "ollama", "--probe"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "backend dependencies (ollama): ok" in out
    assert "backend probe (ollama): ok" in out
    assert "1 nodes, 2 edges, 3 hyperedges" in out


def test_doctor_pi_probe_reports_usage_unavailable(monkeypatch: pytest.MonkeyPatch, capsys):
    import graphify.llm

    monkeypatch.setattr(graphify.llm, "validate_backend_dependencies", lambda backend: None)
    monkeypatch.setattr(
        graphify.llm,
        "probe_backend",
        lambda backend: {
            "nodes": 1,
            "edges": 0,
            "hyperedges": 0,
            "usage_available": False,
            "requested_model": "openai-codex/gpt-5.6-luna",
            "usage": "unavailable",
        },
    )

    rc = _run_main(monkeypatch, ["doctor", "--backend", "pi", "--probe"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "response usage metadata unavailable" in out
    assert "input tokens" not in out


def test_extract_late_pixel_cache_identity_mismatch_is_partial_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """A final cache race must not stamp B with A semantics."""
    import graphify.cache
    import graphify.detect
    import graphify.llm

    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "failed_chunks": 0,
            "partial_chunks": 0,
            "total_chunks": 1,
        },
        ast_nodes=[
            {
                "id": "code",
                "label": "Code",
                "file_type": "code",
                "source_file": "app.py",
            }
        ],
    )
    image = root / "diagram.png"
    image.write_bytes(b"raster-A")
    source = image.resolve()
    identity = graphify.llm._ImageSourceIdentity(
        source,
        graphify.llm._image_stat_identity(image.stat()),
        source,
        root.resolve(),
    )
    fresh = {
        "nodes": [
            {"id": "A-semantics", "label": "A", "file_type": "image", "source_file": image.name}
        ],
        "edges": [],
        "hyperedges": [],
        "input_tokens": 1,
        "output_tokens": 1,
        "failed_chunks": 0,
        "partial_chunks": 0,
        "total_chunks": 1,
        "_image_provenance": {str(source): "pixel-derived"},
        "_image_identity": {str(source): identity},
    }
    monkeypatch.setattr(graphify.llm, "extract_corpus_parallel", lambda *_, **__: fresh)
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": {
                "document": [],
                "paper": [],
                "image": [str(image)],
                "video": [],
                "code": [str(root / "app.py")],
            },
            "total_files": 2,
            "total_words": 1,
        },
    )
    original_mtime = image.stat().st_mtime_ns

    def late_save(*_, **__):
        image.unlink()
        image.write_bytes(b"raster-B")
        os.utime(image, ns=(original_mtime, original_mtime))
        return 0

    monkeypatch.setattr(graphify.cache, "save_semantic_cache", late_save)

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "ollama", "--no-cluster"])

    out = root / "graphify-out"
    graph = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    marker = json.loads((out / ".graphify_semantic_marker").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert all(node.get("id") != "A-semantics" for node in graph["nodes"])
    assert marker["status"] == "partial"
    assert not manifest.get("diagram.png", {}).get("semantic_hash")


@pytest.mark.parametrize(
    "no_cluster",
    [pytest.param(True, id="no-cluster"), pytest.param(False, id="clustered")],
)
def test_extract_graph_publication_identity_race_is_partial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_cluster: bool
):
    """A replacement during either graph writer cannot publish A semantics as clean."""
    import graphify.cache
    import graphify.detect
    import graphify.export
    import graphify.llm
    import graphify.paths

    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={},
        ast_nodes=[
            {
                "id": "code",
                "label": "Code",
                "file_type": "code",
                "source_file": "app.py",
            }
        ],
    )
    image = root / "diagram.png"
    image.write_bytes(b"raster-A")
    source = image.resolve()
    identity = graphify.llm._ImageSourceIdentity(
        source,
        graphify.llm._image_stat_identity(image.stat()),
        source,
        root.resolve(),
    )
    fresh = {
        "nodes": [
            {"id": "A-semantics", "label": "A", "file_type": "image", "source_file": image.name}
        ],
        "edges": [],
        "hyperedges": [],
        "input_tokens": 1,
        "output_tokens": 1,
        "failed_chunks": 0,
        "partial_chunks": 0,
        "total_chunks": 1,
        "_image_provenance": {str(source): "pixel-derived"},
        "_image_identity": {str(source): identity},
    }
    monkeypatch.setattr(graphify.llm, "extract_corpus_parallel", lambda *_, **__: fresh)
    monkeypatch.setattr(graphify.cache, "save_semantic_cache", lambda *_, **__: None)
    monkeypatch.setattr(
        graphify.detect,
        "detect",
        lambda *_, **__: {
            "files": {
                "document": [],
                "paper": [],
                "image": [str(image)],
                "video": [],
                "code": [str(root / "app.py")],
            },
            "total_files": 2,
            "total_words": 1,
        },
    )

    swapped = False

    def replace_source() -> None:
        nonlocal swapped
        if swapped:
            return
        swapped = True
        image.unlink()
        image.write_bytes(b"raster-B")

    if no_cluster:
        original_writer = graphify.paths.write_json_atomic

        def late_raw_writer(path, obj, **kwargs):
            if Path(path).name == "graph.json":
                replace_source()
            return original_writer(path, obj, **kwargs)

        monkeypatch.setattr(graphify.paths, "write_json_atomic", late_raw_writer)
    else:
        original_writer = graphify.export.to_json

        def late_cluster_writer(G, communities, output_path, **kwargs):
            replace_source()
            return original_writer(G, communities, output_path, **kwargs)

        monkeypatch.setattr(graphify.export, "to_json", late_cluster_writer)

    args = ["extract", str(root), "--backend", "ollama"]
    if no_cluster:
        args.append("--no-cluster")
    rc = _run_main(monkeypatch, args)

    out = root / "graphify-out"
    graph = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    marker = json.loads((out / ".graphify_semantic_marker").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert swapped
    assert all(node.get("id") != "A-semantics" for node in graph["nodes"])
    assert marker["status"] == "partial"
    assert not manifest.get("diagram.png", {}).get("semantic_hash")


def test_pi_cli_fail_closed_on_actual_adapter_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    root, _doc = _patch_extract_dependencies(
        monkeypatch,
        tmp_path,
        fresh={},
        ast_nodes=[],
        patch_llm=False,
    )
    attempt = tmp_path / "model-attempt.txt"
    script = tmp_path / "pi"
    script.write_text(
        f"""#!{sys.executable}
import json, sys
if '--help' in sys.argv:
    print('--mode --print --no-session --no-tools --no-extensions --no-skills --no-prompt-templates --no-themes --no-context-files --offline --approve --model --thinking --list-models')
    raise SystemExit(0)
sys.stdin.read()
open({str(attempt)!r}, 'w', encoding='utf-8').write('1')
message = {{
    'role': 'assistant',
    'content': [{{'type': 'text', 'text': 'PRIVATE_SOURCE_LINE'}}],
    'provider': 'openai-codex',
    'model': 'gpt-5.6-luna',
    'usage': {{'input': 1, 'output': 1, 'cacheRead': 0, 'cacheWrite': 0}},
    'stopReason': 'error',
}}
print(json.dumps({{'type': 'message_end', 'message': message}}))
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | 0o100)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    rc = _run_main(monkeypatch, ["extract", str(root), "--backend", "pi", "--no-cluster"])

    captured = capsys.readouterr()
    assert rc == 1
    assert attempt.read_text(encoding="utf-8") == "1"
    assert "PRIVATE_SOURCE_LINE" not in captured.out + captured.err
    assert not (root / "graphify-out" / "graph.json").exists()
