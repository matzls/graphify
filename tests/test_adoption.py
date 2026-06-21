from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest  # type: ignore[reportMissingImports]

from graphify import adoption


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-q", "-m", "init")
    return path


def _commit_all(repo: Path, message: str = "state") -> None:
    _git(repo, "add", ".")
    result = _git(repo, "commit", "-q", "-m", message)
    if result.returncode != 0 and "nothing to commit" not in result.stderr.lower():
        raise AssertionError(result.stderr)


def _write_graph(
    repo: Path, *, report: bool = True, wiki: bool = False, stale: bool = False
) -> None:
    out = repo / "graphify-out"
    out.mkdir(exist_ok=True)
    (out / "graph.json").write_text('{"nodes": [], "links": []}\n', encoding="utf-8")
    if report:
        (out / "GRAPH_REPORT.md").write_text("# Graph report\n", encoding="utf-8")
    if wiki:
        (out / "wiki").mkdir(exist_ok=True)
        (out / "wiki" / "index.md").write_text("# Wiki\n", encoding="utf-8")
    if stale:
        (out / "needs_update").write_text("semantic refresh needed\n", encoding="utf-8")


def _write_managed_guidance(repo: Path) -> None:
    (repo / "AGENTS.md").write_text(
        "<!-- graphify-guidance-start -->\n"
        "## graphify\n"
        "Graphify managed guidance.\n"
        "<!-- graphify-guidance-end -->\n",
        encoding="utf-8",
    )
    codex = repo / ".codex"
    codex.mkdir(exist_ok=True)
    (codex / "config.toml").write_text(
        "[[hooks.SessionStart]]\ncommand = 'graphify codex-session-start .'\n",
        encoding="utf-8",
    )


def _write_hooks(repo: Path) -> None:
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "post-commit").write_text("#!/bin/sh\n# graphify hook\n", encoding="utf-8")
    (hooks / "post-checkout").write_text("#!/bin/sh\n# graphify hook\n", encoding="utf-8")


def _ignore_graphify(repo: Path) -> None:
    (repo / ".gitignore").write_text("graphify-out/\n", encoding="utf-8")


def test_audit_classifies_full_repo(tmp_path: Path):
    repo = _init_repo(tmp_path / "full")
    _write_graph(repo, wiki=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _ignore_graphify(repo)
    _commit_all(repo)

    result = adoption.audit(tmp_path)
    rows = {r.name: r for r in result.repos}

    assert rows["full"].status == "full"
    assert rows["full"].wiki is True
    assert rows["full"].hooks is True
    assert rows["full"].graphify_out_ignored is True
    assert rows["full"].tracked_graphify_out_count == 0


def test_audit_reports_missing_hooks_and_wiki(tmp_path: Path):
    repo = _init_repo(tmp_path / "partial")
    _write_graph(repo, wiki=False)
    _write_managed_guidance(repo)
    _git(repo, "add", "-f", "graphify-out")
    _commit_all(repo)

    row = adoption.audit(tmp_path).repos[0]

    assert row.status == "activation-partial"
    assert "install Graphify git hooks" in row.actions
    assert "refresh wiki" in row.actions
    assert "ignore graphify-out/ in git" in row.actions
    assert "untrack root graphify-out with git rm --cached" in row.actions
    assert row.graphify_out_ignored is False
    assert row.tracked_graphify_out_count >= 1


def test_audit_reports_local_graphify_skill_shadow_paths(tmp_path: Path):
    repo = _init_repo(tmp_path / "local-skills")
    for rel in (
        ".pi/skills/graphify/SKILL.md",
        ".agents/skills/graphify/SKILL.md",
        ".codex/skills/graphify/SKILL.md",
    ):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# local graphify skill\n", encoding="utf-8")
    _write_graph(repo, wiki=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _ignore_graphify(repo)
    _commit_all(repo)

    row = adoption.audit(tmp_path).repos[0]

    assert row.local_skill_paths == [
        ".pi/skills/graphify/SKILL.md",
        ".agents/skills/graphify/SKILL.md",
        ".codex/skills/graphify/SKILL.md",
    ]
    assert row.pi_project_skill is True
    assert any("local Graphify skill" in action for action in row.actions)
    assert "local_skill_paths" in row.to_dict()


def test_audit_skips_graphify_self_marker_and_worktree_cache(tmp_path: Path):
    self_repo = _init_repo(tmp_path / "graphify")
    (self_repo / "AGENTS.md").write_text(
        "Graphify should not be executed automatically against its own source repo\n",
        encoding="utf-8",
    )
    _commit_all(self_repo)

    worktree = _init_repo(tmp_path / ".claude" / "worktrees" / "child")

    rows = {r.name: r for r in adoption.audit(tmp_path).repos}

    assert rows["graphify"].status == "skip"
    assert rows["graphify"].reason == "graphify-self"
    assert rows["child"].status == "skip"
    assert rows["child"].reason == "worktree-cache"


def test_dirty_source_blocks_but_dirty_graph_can_be_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _init_repo(tmp_path / "dirty")
    _write_graph(repo, wiki=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _commit_all(repo)
    (repo / "src.py").write_text("print('dirty')\n", encoding="utf-8")

    blocked = adoption.apply(adoption.ApplyOptions(root=tmp_path, local=True))
    assert blocked[0].status == "skipped"
    assert "dirty" in blocked[0].message

    _git(repo, "add", "src.py")
    _git(repo, "commit", "-q", "-m", "source")
    (repo / "graphify-out" / "GRAPH_REPORT.md").write_text("dirty graph\n", encoding="utf-8")
    (repo / "graphify-out" / "wiki" / "index.md").unlink()

    calls: list[tuple[tuple[str, ...], Path]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append((tuple(args), cwd))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    allowed = adoption.apply(
        adoption.ApplyOptions(root=tmp_path, local=True, allow_dirty_graphify_out=True)
    )

    assert allowed[0].status == "applied"
    assert calls


def test_local_apply_adds_graphify_gitignore_without_deleting_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _init_repo(tmp_path / "needs-ignore")
    _write_graph(repo, wiki=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _git(repo, "add", "-f", "graphify-out")
    _commit_all(repo)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    results = adoption.apply(adoption.ApplyOptions(root=tmp_path, local=True))

    assert results[0].status == "applied"
    assert (repo / "graphify-out" / "graph.json").exists()
    assert "graphify-out/" in (repo / ".gitignore").read_text(encoding="utf-8")
    row = adoption.audit(tmp_path).repos[0]
    assert row.graphify_out_ignored is True
    assert "untrack root graphify-out with git rm --cached" in row.actions


def test_json_shape_and_chat_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    repo = _init_repo(tmp_path / "candidate")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    _commit_all(repo)

    result = adoption.run_cli(["audit", "--root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert payload["repos"][0]["status"] == "candidate"

    result = adoption.run_cli(["audit", "--root", str(tmp_path)])
    captured = capsys.readouterr()
    assert result == 0
    assert "Graphify adoption audit" in captured.out
    assert "Recommended next commands" in captured.out


def test_apply_requires_local_or_semantic(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    result = adoption.run_cli(["apply", "--root", str(tmp_path)])
    captured = capsys.readouterr()

    assert result == 2
    assert "requires --local and/or --semantic" in captured.err


def test_partial_semantic_marker_is_refresh_needed_and_blocking(tmp_path: Path):
    repo = _init_repo(tmp_path / "partial-semantic")
    _write_graph(repo, wiki=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    marker = repo / "graphify-out" / ".graphify_semantic_marker"
    marker.write_text(json.dumps({"status": "partial", "failed_chunks": 1}), encoding="utf-8")
    _commit_all(repo)

    row = adoption.audit(tmp_path).repos[0]

    assert row.status == "refresh-needed"
    assert row.semantic_partial is True
    assert row.stale_marker is True
    assert "partial semantic output" in row.blockers
    assert "semantic refresh" in row.actions


def test_local_apply_does_not_touch_full_repo_or_use_backend_for_wiki_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    full = _init_repo(tmp_path / "full")
    _write_graph(full, wiki=True)
    _write_managed_guidance(full)
    _write_hooks(full)
    _ignore_graphify(full)
    _commit_all(full)

    missing_wiki = _init_repo(tmp_path / "missing-wiki")
    _write_graph(missing_wiki, wiki=False)
    _write_managed_guidance(missing_wiki)
    _write_hooks(missing_wiki)
    _ignore_graphify(missing_wiki)
    _commit_all(missing_wiki)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    results = adoption.apply(adoption.ApplyOptions(root=tmp_path, local=True))

    by_repo = {r.repo: r for r in results}
    assert by_repo["full"].status == "skipped"
    assert by_repo["full"].message == "no selected actions needed"
    assert by_repo["missing-wiki"].status == "applied"
    rendered = [" ".join(c) for c in calls]
    assert any("cluster-only . --no-label" in c for c in rendered)
    assert not any("cluster-only . --backend" in c for c in rendered)


def test_subcommand_help(capsys: pytest.CaptureFixture[str]):
    assert adoption.run_cli(["audit", "--help"]) == 0
    assert "graphify adoption audit" in capsys.readouterr().out
    assert adoption.run_cli(["apply", "--help"]) == 0
    assert "graphify adoption apply" in capsys.readouterr().out


def test_semantic_apply_uses_default_ollama_backend_without_pinning_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _init_repo(tmp_path / "adopted")
    _write_graph(repo, wiki=True, stale=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _commit_all(repo)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    results = adoption.apply(adoption.ApplyOptions(root=tmp_path, semantic=True))

    assert results[0].status == "applied"
    rendered = [" ".join(c) for c in calls]
    assert any("extract . --backend ollama" in c for c in rendered)
    assert any("cluster-only . --backend ollama" in c for c in rendered)
    assert not any("--model" in c for c in rendered)


def test_semantic_apply_propagates_explicit_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _init_repo(tmp_path / "adopted-explicit-model")
    _write_graph(repo, wiki=True, stale=True)
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _commit_all(repo)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    results = adoption.apply(
        adoption.ApplyOptions(root=tmp_path, semantic=True, model="custom-model")
    )

    assert results[0].status == "applied"
    rendered = [" ".join(c) for c in calls]
    assert any("extract . --backend ollama --model custom-model" in c for c in rendered)
    assert any("cluster-only . --backend ollama --model custom-model" in c for c in rendered)


def test_semantic_apply_builds_active_repo_without_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _init_repo(tmp_path / "active-no-graph")
    _write_managed_guidance(repo)
    _write_hooks(repo)
    _commit_all(repo)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)
    results = adoption.apply(adoption.ApplyOptions(root=tmp_path, semantic=True))

    assert results[0].status == "applied"
    rendered = [" ".join(c) for c in calls]
    assert any("extract . --backend ollama" in c for c in rendered)
    assert any("cluster-only . --backend ollama" in c for c in rendered)
    assert not any("--model" in c for c in rendered)


def test_candidate_apply_requires_explicit_target_for_semantic_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _init_repo(tmp_path / "candidate")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    _commit_all(repo)

    calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], *, cwd: Path):
        calls.append(tuple(args))
        return True, "ok"

    monkeypatch.setattr(adoption, "_run_command", fake_run)

    broad = adoption.apply(adoption.ApplyOptions(root=tmp_path, scope="candidates", semantic=True))
    assert broad[0].repo == "(none)"
    assert broad[0].status == "skipped"
    assert calls == []

    targeted = adoption.apply(
        adoption.ApplyOptions(
            root=tmp_path,
            scope="candidates",
            targets=["candidate"],
            local=True,
            semantic=True,
        )
    )
    assert targeted[0].status == "applied"
    rendered = [" ".join(c) for c in calls]
    assert any("extract . --backend ollama" in c for c in rendered)
    assert not any("--model" in c for c in rendered)
