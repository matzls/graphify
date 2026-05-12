"""Tests for hooks.py - git hook install/uninstall."""
import os
import subprocess
from pathlib import Path
import pytest
from graphify.hooks import (
    install,
    uninstall,
    status,
    _HOOK_MARKER,
    _HOOK_MARKER_END,
    _CHECKOUT_MARKER,
    _HOOK_SCRIPT,
)


def _make_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


def test_install_creates_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = install(repo)
    hook = repo / ".git" / "hooks" / "post-commit"
    assert hook.exists()
    assert _HOOK_MARKER in hook.read_text()
    assert "installed" in result


def test_install_supports_git_worktree(tmp_path):
    repo = tmp_path / "repo"
    worktree = tmp_path / "repo-wt"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Graphify Test",
            "-c",
            "user.email=graphify@example.test",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", str(worktree)],
        check=True,
        capture_output=True,
    )

    result = install(worktree)

    assert (worktree / ".git").is_file()
    hook = repo / ".git" / "hooks" / "post-commit"
    assert hook.exists()
    assert _HOOK_MARKER in hook.read_text()
    assert "post-commit" in result


def test_install_is_executable(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    hook = repo / ".git" / "hooks" / "post-commit"
    if os.name == "nt":
        assert hook.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
    else:
        assert hook.stat().st_mode & 0o111  # executable bit set


def test_install_idempotent(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = install(repo)
    assert "updated existing" in result
    # marker appears only once
    hook = repo / ".git" / "hooks" / "post-commit"
    assert hook.read_text().count(_HOOK_MARKER) == 1


def test_install_appends_to_existing_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/bash\necho existing\n")
    hook.chmod(0o755)
    install(repo)
    content = hook.read_text()
    assert "existing" in content
    assert _HOOK_MARKER in content


def test_install_updates_existing_graphify_block(tmp_path):
    repo = _make_git_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text(
        "#!/bin/bash\n"
        "echo before\n"
        f"{_HOOK_MARKER}\n"
        "echo old graphify hook\n"
        f"{_HOOK_MARKER_END}\n"
        "echo after\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    result = install(repo)
    content = hook.read_text(encoding="utf-8")

    assert "updated existing post-commit" in result
    assert "echo before" in content
    assert "echo after" in content
    assert "echo old graphify hook" not in content
    assert content.count(_HOOK_MARKER) == 1
    assert "docs/media changes write graphify-out/needs_update" in content


def test_install_backs_up_partial_graphify_block(tmp_path):
    repo = _make_git_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text(
        "#!/bin/bash\n"
        f"{_HOOK_MARKER}\n"
        "echo truncated graphify hook\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    result = install(repo)

    backup = repo / ".git" / "hooks" / "post-commit.graphify-backup"
    assert "backed up partial graphify block" in result
    assert backup.exists()
    assert "echo truncated graphify hook" in backup.read_text(encoding="utf-8")
    assert _HOOK_MARKER_END in hook.read_text(encoding="utf-8")


def test_post_commit_hook_marks_docs_and_media_stale():
    assert "classify_file" in _HOOK_SCRIPT
    assert "_load_graphifyignore" in _HOOK_SCRIPT
    assert "FileType.DOCUMENT" in _HOOK_SCRIPT
    assert "FileType.IMAGE" in _HOOK_SCRIPT
    assert "mark_needs_update" in _HOOK_SCRIPT
    assert _HOOK_SCRIPT.index("_rebuild_code") < _HOOK_SCRIPT.index("mark_needs_update")


def test_uninstall_removes_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = uninstall(repo)
    hook = repo / ".git" / "hooks" / "post-commit"
    assert not hook.exists()
    assert "removed" in result.lower()


def test_uninstall_no_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = uninstall(repo)
    assert "nothing to remove" in result


def test_status_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = status(repo)
    assert "installed" in result


def test_status_not_installed(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = status(repo)
    assert "not installed" in result


def test_no_git_repo_raises(tmp_path):
    with pytest.raises(RuntimeError, match="No git repository"):
        install(tmp_path / "not_a_repo")


def test_install_creates_post_checkout_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    hook = repo / ".git" / "hooks" / "post-checkout"
    assert hook.exists()
    assert _CHECKOUT_MARKER in hook.read_text()


def test_install_post_checkout_is_executable(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    hook = repo / ".git" / "hooks" / "post-checkout"
    if os.name == "nt":
        assert hook.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
    else:
        assert hook.stat().st_mode & 0o111


def test_uninstall_removes_post_checkout_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    uninstall(repo)
    hook = repo / ".git" / "hooks" / "post-checkout"
    assert not hook.exists()


def test_status_shows_both_hooks(tmp_path):
    repo = _make_git_repo(tmp_path)
    install(repo)
    result = status(repo)
    assert "post-commit" in result
    assert "post-checkout" in result
    assert result.count("installed") >= 2


def test_hook_skips_head_on_exe():
    """Hook script must skip shebang extraction for .exe binaries (Windows)."""
    from graphify.hooks import _PYTHON_DETECT
    assert "*.exe) _SHEBANG=" in _PYTHON_DETECT or '*.exe)' in _PYTHON_DETECT


def test_hook_check_no_additionalContext(tmp_path):
    """graphify hook-check must not emit additionalContext — Codex Desktop rejects it."""
    import sys
    out = tmp_path / "graphify-out"
    out.mkdir()
    (out / "graph.json").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "hook-check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_codex_session_start_outputs_json(tmp_path):
    """Codex SessionStart command must emit valid JSON even when graph is fresh."""
    import json
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "codex-session-start", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert payload["hookSpecificOutput"]["additionalContext"] == ""


def test_codex_session_start_outputs_pending_context(tmp_path):
    """Codex SessionStart command injects refresh context when needs_update exists."""
    import json
    import sys

    flag = tmp_path / "graphify-out" / "needs_update"
    flag.parent.mkdir(parents=True)
    flag.write_text("1", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "codex-session-start", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "Graphify graph refresh is pending" in context
    assert "/graphify . --update" in context
    assert "graphify update ." in context
    assert "will not clear semantic refresh needs" in context
