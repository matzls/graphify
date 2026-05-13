"""Tests for watch.py - file watcher helpers (no watchdog required)."""
import time
from pathlib import Path
import pytest

from graphify.watch import (
    _rebuild_lock,
    _rebuild_code,
    _load_community_labels,
    _notify_only,
    _parse_report_community_labels,
    _save_community_labels,
    _WATCHED_EXTENSIONS,
    mark_needs_update,
)


# --- _notify_only ---

def test_notify_only_creates_flag(tmp_path):
    _notify_only(tmp_path)
    flag = tmp_path / "graphify-out" / "needs_update"
    assert flag.exists()
    assert flag.read_text() == "1"

def test_notify_only_creates_flag_dir(tmp_path):
    # graphify-out dir does not exist yet
    assert not (tmp_path / "graphify-out").exists()
    _notify_only(tmp_path)
    assert (tmp_path / "graphify-out").is_dir()

def test_notify_only_idempotent(tmp_path):
    _notify_only(tmp_path)
    _notify_only(tmp_path)
    flag = tmp_path / "graphify-out" / "needs_update"
    assert flag.read_text() == "1"


def test_mark_needs_update_returns_flag_path(tmp_path):
    flag = mark_needs_update(tmp_path)

    assert flag == tmp_path / "graphify-out" / "needs_update"
    assert flag.read_text(encoding="utf-8") == "1"


# --- _WATCHED_EXTENSIONS ---

def test_watched_extensions_includes_code():
    assert ".py" in _WATCHED_EXTENSIONS
    assert ".ts" in _WATCHED_EXTENSIONS
    assert ".go" in _WATCHED_EXTENSIONS
    assert ".rs" in _WATCHED_EXTENSIONS

def test_watched_extensions_includes_docs():
    assert ".md" in _WATCHED_EXTENSIONS
    assert ".txt" in _WATCHED_EXTENSIONS
    assert ".pdf" in _WATCHED_EXTENSIONS

def test_watched_extensions_includes_images():
    assert ".png" in _WATCHED_EXTENSIONS
    assert ".jpg" in _WATCHED_EXTENSIONS
    assert ".mp4" in _WATCHED_EXTENSIONS
    assert ".mp3" in _WATCHED_EXTENSIONS

def test_watched_extensions_excludes_noise():
    assert ".json" not in _WATCHED_EXTENSIONS
    assert ".pyc" not in _WATCHED_EXTENSIONS
    assert ".log" not in _WATCHED_EXTENSIONS


# --- watch() import error without watchdog ---

def test_check_update_no_flag_returns_true(tmp_path):
    """check_update returns True and is silent when needs_update flag is absent."""
    from graphify.watch import check_update
    assert check_update(tmp_path) is True


def test_check_update_with_flag_returns_true_and_prints(tmp_path, capsys):
    """check_update returns True and prints notification when flag exists."""
    from graphify.watch import check_update
    flag = tmp_path / "graphify-out" / "needs_update"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1")
    result = check_update(tmp_path)
    assert result is True
    out = capsys.readouterr().out
    assert "graphify --update" in out


def test_codex_session_start_notice_with_flag(tmp_path):
    """Codex SessionStart notice is explicit and agent-facing when flag exists."""
    from graphify.watch import codex_session_start_notice
    flag = tmp_path / "graphify-out" / "needs_update"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1")

    notice = codex_session_start_notice(tmp_path)

    assert "Graphify graph refresh is pending" in notice
    assert "/graphify . --update" in notice
    assert "graphify update ." in notice


def test_codex_session_start_notice_without_flag_is_empty(tmp_path):
    """Codex SessionStart hook should not inject context when graph is fresh."""
    from graphify.watch import codex_session_start_notice
    assert codex_session_start_notice(tmp_path) == ""


def test_check_update_does_not_clear_flag(tmp_path):
    """check_update never removes the needs_update flag (clearing is LLM's job)."""
    from graphify.watch import check_update
    flag = tmp_path / "graphify-out" / "needs_update"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1")
    check_update(tmp_path)
    assert flag.exists()


def test_rebuild_lock_uses_external_lock_dir(tmp_path, monkeypatch):
    """Rebuild lock should not create Git-visible files under graphify-out."""
    lock_dir = tmp_path / "locks"
    graph_out = tmp_path / "repo" / "graphify-out"
    monkeypatch.setenv("GRAPHIFY_LOCK_DIR", str(lock_dir))

    with _rebuild_lock(graph_out) as acquired:
        assert acquired is True

    assert not (graph_out / ".rebuild.lock").exists()
    assert any(lock_dir.iterdir())


def test_rebuild_code_smoke_generates_outputs(tmp_path, monkeypatch):
    """Code-only rebuild must match the current extract() API."""
    monkeypatch.setenv("GRAPHIFY_LOCK_DIR", str(tmp_path / "locks"))
    (tmp_path / "app.py").write_text(
        "def hello(name):\n    return f'hello {name}'\n",
        encoding="utf-8",
    )

    assert _rebuild_code(tmp_path, block_on_lock=True) is True

    assert (tmp_path / "graphify-out" / "graph.json").exists()
    assert (tmp_path / "graphify-out" / "GRAPH_REPORT.md").exists()


def test_rebuild_code_writes_manifest_to_watched_graph_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GRAPHIFY_LOCK_DIR", str(tmp_path / "locks"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def hello():\n    return 'hello'\n", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)

    assert _rebuild_code(repo, block_on_lock=True) is True

    assert (repo / "graphify-out" / "manifest.json").exists()
    assert not (outside / "graphify-out" / "manifest.json").exists()


def test_rebuild_code_changed_paths_keep_project_relative_sources(tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GRAPHIFY_LOCK_DIR", str(tmp_path / "locks"))
    src = tmp_path / "src"
    src.mkdir()
    app = src / "app.py"
    helper = src / "helper.py"
    app.write_text("from helper import helper\n\ndef run():\n    return helper()\n", encoding="utf-8")
    helper.write_text("def helper():\n    return 1\n", encoding="utf-8")

    assert _rebuild_code(Path("."), block_on_lock=True) is True
    app.write_text("from helper import helper\n\ndef run():\n    return helper() + 1\n", encoding="utf-8")

    assert _rebuild_code(Path("."), changed_paths=[Path("src/app.py")], block_on_lock=True) is True

    graph = json.loads((tmp_path / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    app_nodes = [n for n in graph["nodes"] if n.get("label") == "app.py"]
    assert app_nodes
    assert {n.get("source_file") for n in app_nodes} == {"src/app.py"}
    assert "app.py" not in {n.get("source_file") for n in graph["nodes"]}


def test_watch_raises_without_watchdog(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "watchdog.observers" or name == "watchdog.events":
            raise ImportError("mocked missing watchdog")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    from graphify.watch import watch
    with pytest.raises(ImportError, match="watchdog not installed"):
        watch(tmp_path)


# --- community label preservation ---

def test_parse_report_community_labels(tmp_path):
    report = tmp_path / "GRAPH_REPORT.md"
    report.write_text(
        '### Community 0 - "Runtime Configuration"\n'
        '### Community 12 - "Auth And Query Scope"\n',
        encoding="utf-8",
    )

    assert _parse_report_community_labels(report) == {
        0: "Runtime Configuration",
        12: "Auth And Query Scope",
    }


def test_load_community_labels_prefers_durable_json(tmp_path):
    out = tmp_path / "graphify-out"
    _save_community_labels(out, {0: "Durable Label"})
    (out / "GRAPH_REPORT.md").write_text(
        '### Community 0 - "Report Label"\n',
        encoding="utf-8",
    )

    assert _load_community_labels(out) == {0: "Durable Label"}


def test_load_community_labels_falls_back_to_report(tmp_path):
    out = tmp_path / "graphify-out"
    out.mkdir()
    (out / "GRAPH_REPORT.md").write_text(
        '### Community 3 - "Media Chunking Pipeline"\n',
        encoding="utf-8",
    )

    assert _load_community_labels(out) == {3: "Media Chunking Pipeline"}
