"""Multi-repo Graphify adoption audit and explicit propagation helpers.

This module is intentionally conservative: ``audit`` is read-only, and ``apply``
only mutates selected repositories after explicit ``--local`` and/or
``--semantic`` flags. It is primarily a chat-native operator surface for Mase's
local Graphify fork, but the scanner itself stays generic enough for upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter, defaultdict
import json
import os
import subprocess
import sys
import time
from typing import Iterable, Sequence

MANAGED_AGENTS_START = "<!-- graphify-guidance-start -->"
MANAGED_AGENTS_END = "<!-- graphify-guidance-end -->"
DEFAULT_MASE_ROOT = Path("/Users/mase/Codebase")
DEFAULT_SELF_PATH = Path("/Users/mase/Codebase/Personal-Projects/graphify")
DEFAULT_BACKEND = "ollama"
DEFAULT_MODEL: str | None = None

PRUNE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
}

CANDIDATE_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "Gemfile",
)

STATUS_ORDER = {
    "full": 0,
    "refresh-needed": 1,
    "activation-partial": 2,
    "artifacts-only": 3,
    "candidate": 4,
    "skip": 5,
}


@dataclass
class RepoAdoption:
    root: str
    name: str
    status: str
    reason: str = ""
    graph: bool = False
    report: bool = False
    wiki: bool = False
    stale_marker: bool = False
    semantic_partial: bool = False
    managed_agents: bool = False
    agents_graphify: bool = False
    codex_session: bool = False
    pi_project_skill: bool = False
    local_skill_paths: list[str] = field(default_factory=list)
    hooks: bool = False
    graphify_out_ignored: bool = False
    tracked_graphify_out_count: int = 0
    dirty_source: bool = False
    dirty_graphify_out: bool = False
    dirty_count: int = 0
    graph_mtime: str = ""
    graph_size_mb: float = 0.0
    candidate_score: int = 0
    actions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "graph": self.graph,
            "report": self.report,
            "wiki": self.wiki,
            "stale_marker": self.stale_marker,
            "semantic_partial": self.semantic_partial,
            "managed_agents": self.managed_agents,
            "agents_graphify": self.agents_graphify,
            "codex_session": self.codex_session,
            "pi_project_skill": self.pi_project_skill,
            "local_skill_paths": list(self.local_skill_paths),
            "hooks": self.hooks,
            "graphify_out_ignored": self.graphify_out_ignored,
            "tracked_graphify_out_count": self.tracked_graphify_out_count,
            "dirty_source": self.dirty_source,
            "dirty_graphify_out": self.dirty_graphify_out,
            "dirty_count": self.dirty_count,
            "graph_mtime": self.graph_mtime,
            "graph_size_mb": self.graph_size_mb,
            "candidate_score": self.candidate_score,
            "actions": list(self.actions),
            "blockers": list(self.blockers),
        }


@dataclass
class AdoptionAudit:
    roots: list[str]
    repos: list[RepoAdoption]

    def to_dict(self) -> dict:
        counts = Counter(r.status for r in self.repos)
        return {
            "roots": self.roots,
            "counts": dict(counts),
            "repos": [r.to_dict() for r in self.repos],
        }


@dataclass
class ApplyOptions:
    root: Path
    scope: str = "adopted"
    targets: list[str] = field(default_factory=list)
    local: bool = False
    semantic: bool = False
    backend: str = DEFAULT_BACKEND
    model: str | None = DEFAULT_MODEL
    include_dirty: bool = False
    allow_dirty_graphify_out: bool = False


@dataclass
class ApplyResult:
    repo: str
    status: str
    commands: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "status": self.status,
            "commands": list(self.commands),
            "message": self.message,
        }


def default_root() -> Path:
    return DEFAULT_MASE_ROOT if DEFAULT_MASE_ROOT.exists() else Path(".")


def _read_text(path: Path, limit: int | None = None) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return data[:limit] if limit is not None else data


def _run_git(root: Path, args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _is_git_repo_dir(path: Path) -> bool:
    return (path / ".git").exists()


def _git_root(path: Path) -> Path | None:
    result = _run_git(path, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return Path(text).resolve() if text else None


def _is_under_worktree_cache(path: Path) -> bool:
    parts = path.parts
    for i, part in enumerate(parts[:-1]):
        if part == ".claude" and i + 1 < len(parts) and parts[i + 1] == "worktrees":
            return True
    return False


def _is_self_graphify_repo(path: Path) -> bool:
    try:
        if path.resolve() == DEFAULT_SELF_PATH.resolve():
            return True
    except OSError:
        pass
    agents = _read_text(path / "AGENTS.md", limit=80_000)
    return (
        "Graphify should not be executed automatically against its own source repo" in agents
        or "unless Mase explicitly asks for a self-analysis run" in agents
    )


def _iter_dirs(root: Path) -> Iterable[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        yield current
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in reversed(entries):
            if not entry.is_dir():
                continue
            if entry.name in PRUNE_DIRS:
                continue
            if entry.name.startswith(".") and entry.name not in {".claude"}:
                continue
            stack.append(entry)


def discover_git_repos(root: Path, *, repo_filter: str | None = None) -> list[Path]:
    root = root.expanduser().resolve()
    repos: set[Path] = set()

    if _git_root(root):
        repos.add(_git_root(root) or root)

    for directory in _iter_dirs(root):
        if _is_git_repo_dir(directory):
            repo = _git_root(directory) or directory.resolve()
            repos.add(repo)
            # Do not traverse inside a discovered repo for nested dependency dirs;
            # nested first-party repos are still found when their own .git appears
            # before a pruned dir, but this keeps scans bounded.

    if repo_filter:
        needle = repo_filter.strip()
        resolved: Path | None = None
        try:
            p = Path(needle).expanduser()
            if p.exists():
                resolved = p.resolve()
        except OSError:
            resolved = None

        def matches(repo: Path) -> bool:
            if repo.name == needle:
                return True
            if needle in str(repo):
                return True
            if resolved is not None:
                try:
                    return repo.resolve() == resolved or resolved in repo.resolve().parents
                except OSError:
                    return False
            return False

        repos = {r for r in repos if matches(r)}

    return sorted(repos, key=lambda p: str(p))


def _graph_mtime(path: Path) -> str:
    try:
        return time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))
    except OSError:
        return ""


def _graph_size_mb(path: Path) -> float:
    try:
        return round(path.stat().st_size / 1_000_000, 1)
    except OSError:
        return 0.0


def _codex_has_graphify_session(repo: Path) -> bool:
    content = _read_text(repo / ".codex" / "config.toml", limit=80_000).lower()
    return "graphify" in content and ("sessionstart" in content or "session_start" in content)


def _semantic_marker_is_partial(out_dir: Path) -> bool:
    marker = out_dir / ".graphify_semantic_marker"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("status") == "partial"


def _hook_dir(repo: Path) -> Path | None:
    result = _run_git(repo, ["rev-parse", "--git-path", "hooks"])
    raw = result.stdout.strip()
    if result.returncode != 0 or not raw or any(c in raw for c in "\n\r\x00"):
        return None
    p = Path(raw)
    return p if p.is_absolute() else repo / p


def _has_graphify_hooks(repo: Path) -> bool:
    hooks = _hook_dir(repo)
    if hooks is None:
        return False
    found = []
    for name in ("post-commit", "post-checkout"):
        content = _read_text(hooks / name, limit=80_000).lower()
        found.append("graphify" in content)
    return all(found)


def _dirty_state(repo: Path) -> tuple[bool, bool, int]:
    result = _run_git(repo, ["status", "--porcelain"], timeout=10)
    if result.returncode != 0:
        return False, False, 0
    dirty_source = False
    dirty_graph = False
    count = 0
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        count += 1
        path_text = line[3:] if len(line) > 3 else line
        # Rename/copy porcelain lines contain "old -> new"; consider both sides.
        normalized = path_text.replace("\\", "/")
        if "graphify-out/" in normalized or normalized.rstrip("/") == "graphify-out":
            dirty_graph = True
        else:
            dirty_source = True
    return dirty_source, dirty_graph, count


def _graphify_out_ignored(repo: Path) -> bool:
    """Return whether the repo-local .gitignore ignores root graphify-out.

    Deliberately inspect the repository policy instead of `git check-ignore` so
    a user-global excludesfile does not hide repos that still need durable local
    propagation.
    """
    patterns = {
        "graphify-out",
        "graphify-out/",
        "/graphify-out",
        "/graphify-out/",
    }
    for line in _read_text(repo / ".gitignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        if stripped in patterns:
            return True
    return False


def _tracked_graphify_out_count(repo: Path) -> int:
    """Count root graphify-out files already tracked in the Git index."""
    result = _run_git(repo, ["ls-files", "-z", "graphify-out"], timeout=10)
    if result.returncode != 0 or not result.stdout:
        return 0
    return len([item for item in result.stdout.split("\0") if item])


def _ensure_graphify_out_ignored(repo: Path) -> None:
    """Append an idempotent .gitignore rule for local Graphify output."""
    if _graphify_out_ignored(repo):
        return
    ignore_path = repo / ".gitignore"
    existing = _read_text(ignore_path)
    addition = "# Graphify local derived output\ngraphify-out/\n"
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    separator = "" if not existing else "\n"
    ignore_path.write_text(existing + prefix + separator + addition, encoding="utf-8")


def _candidate_score(repo: Path) -> int:
    score = 0
    for name in CANDIDATE_FILES:
        if (repo / name).exists():
            score += 1
    try:
        first_party_files = [
            p for p in repo.iterdir() if p.name not in PRUNE_DIRS and not p.name.startswith(".")
        ]
    except OSError:
        first_party_files = []
    if len(first_party_files) >= 4:
        score += 1
    return score


def _local_graphify_skill_paths(repo: Path) -> list[str]:
    candidates = (
        repo / ".pi" / "skills" / "graphify" / "SKILL.md",
        repo / ".agents" / "skills" / "graphify" / "SKILL.md",
        repo / ".codex" / "skills" / "graphify" / "SKILL.md",
    )
    paths: list[str] = []
    for path in candidates:
        if path.exists():
            try:
                paths.append(str(path.relative_to(repo)))
            except ValueError:
                paths.append(str(path))
    return paths


def inspect_repo(repo: Path) -> RepoAdoption:
    repo = repo.resolve()
    name = repo.name

    if _is_under_worktree_cache(repo):
        return RepoAdoption(str(repo), name, "skip", reason="worktree-cache")
    if _is_self_graphify_repo(repo):
        return RepoAdoption(str(repo), name, "skip", reason="graphify-self")

    out = repo / "graphify-out"
    graph_path = out / "graph.json"
    graph = graph_path.exists()
    report = (out / "GRAPH_REPORT.md").exists()
    wiki = (out / "wiki" / "index.md").exists()
    semantic_partial = _semantic_marker_is_partial(out)
    stale = (out / "needs_update").exists() or (out / ".needs_update").exists() or semantic_partial
    agents = _read_text(repo / "AGENTS.md", limit=120_000)
    agents_lower = agents.lower()
    managed_agents = MANAGED_AGENTS_START in agents and MANAGED_AGENTS_END in agents
    agents_graphify = "graphify" in agents_lower
    codex_session = _codex_has_graphify_session(repo)
    local_skill_paths = _local_graphify_skill_paths(repo)
    pi_project_skill = any(p.startswith(".pi/") for p in local_skill_paths)
    hooks = _has_graphify_hooks(repo)
    graphify_out_ignored = _graphify_out_ignored(repo)
    tracked_graphify_out_count = _tracked_graphify_out_count(repo)
    dirty_source, dirty_graph, dirty_count = _dirty_state(repo)
    score = _candidate_score(repo)
    active = managed_agents or agents_graphify or codex_session or hooks

    actions: list[str] = []
    blockers: list[str] = []
    if (graph or active) and not graphify_out_ignored:
        actions.append("ignore graphify-out/ in git")
    if tracked_graphify_out_count:
        actions.append("untrack root graphify-out with git rm --cached")
    if dirty_source:
        blockers.append("dirty source/config files")
    if dirty_graph:
        blockers.append("dirty graphify-out")
    if semantic_partial:
        blockers.append("partial semantic output")
    if local_skill_paths:
        actions.append(
            "review local Graphify skill shadow before use; remove only if not intentionally pinned: "
            + ", ".join(local_skill_paths)
        )

    if graph:
        if not report:
            actions.append("regenerate GRAPH_REPORT.md")
        if not wiki:
            actions.append("refresh wiki")
        if not managed_agents or not codex_session:
            actions.append("update managed AGENTS/Codex guidance")
        if not hooks:
            actions.append("install Graphify git hooks")
        if stale:
            actions.append("semantic refresh")

        if report and wiki and managed_agents and codex_session and hooks and not stale:
            status = "full"
            reason = "adopted standard complete"
        elif not active:
            status = "artifacts-only"
            reason = "graph exists without activation surfaces"
        elif not managed_agents or not codex_session or not hooks:
            status = "activation-partial"
            reason = "activation surfaces missing or stale"
        else:
            status = "refresh-needed"
            reason = "graph/report/wiki refresh needed"
    elif active:
        status = "activation-partial"
        reason = "activation exists but graph output is missing"
        actions.append("build initial graph")
        if not managed_agents or not codex_session:
            actions.append("update managed AGENTS/Codex guidance")
        if not hooks:
            actions.append("install Graphify git hooks")
    elif score >= 2:
        status = "candidate"
        reason = "repo has project metadata but no graph"
        actions.append("consider Graphify bootstrap")
    else:
        status = "skip"
        reason = "no Graphify signals and weak candidate score"

    return RepoAdoption(
        root=str(repo),
        name=name,
        status=status,
        reason=reason,
        graph=graph,
        report=report,
        wiki=wiki,
        stale_marker=stale,
        semantic_partial=semantic_partial,
        managed_agents=managed_agents,
        agents_graphify=agents_graphify,
        codex_session=codex_session,
        pi_project_skill=pi_project_skill,
        local_skill_paths=local_skill_paths,
        hooks=hooks,
        graphify_out_ignored=graphify_out_ignored,
        tracked_graphify_out_count=tracked_graphify_out_count,
        dirty_source=dirty_source,
        dirty_graphify_out=dirty_graph,
        dirty_count=dirty_count,
        graph_mtime=_graph_mtime(graph_path),
        graph_size_mb=_graph_size_mb(graph_path),
        candidate_score=score,
        actions=_dedupe(actions),
        blockers=_dedupe(blockers),
    )


def _dedupe(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def audit(root: Path | None = None, *, repo_filter: str | None = None) -> AdoptionAudit:
    scan_root = root or default_root()
    repos = [inspect_repo(r) for r in discover_git_repos(scan_root, repo_filter=repo_filter)]
    repos.sort(key=lambda r: (STATUS_ORDER.get(r.status, 99), r.name.lower(), r.root))
    return AdoptionAudit(roots=[str(scan_root.expanduser().resolve())], repos=repos)


def _flag(value: bool, true: str = "yes", false: str = "no") -> str:
    return true if value else false


def format_report(result: AdoptionAudit, *, verbose: bool = False) -> str:
    counts = Counter(r.status for r in result.repos)
    adopted = [
        r
        for r in result.repos
        if r.status in {"full", "refresh-needed", "activation-partial", "artifacts-only"}
    ]
    candidates = [r for r in result.repos if r.status == "candidate"]
    skipped = [r for r in result.repos if r.status == "skip"]

    lines: list[str] = []
    lines.append("Graphify adoption audit")
    lines.append(f"Root: {', '.join(result.roots)}")
    lines.append(
        "Summary: "
        f"{len(result.repos)} repos · "
        f"full {counts.get('full', 0)} · refresh {counts.get('refresh-needed', 0)} · "
        f"partial {counts.get('activation-partial', 0)} · artifacts-only {counts.get('artifacts-only', 0)} · "
        f"candidates {counts.get('candidate', 0)} · skipped {counts.get('skip', 0)}"
    )
    lines.append("")

    if adopted:
        lines.append("Adopted / in-use repos:")
        lines.append(
            "status               repo                            graph wiki hooks ignore tracked stale dirty  actions"
        )
        display = adopted if verbose else adopted[:18]
        for r in display:
            dirty = "src" if r.dirty_source else ("graph" if r.dirty_graphify_out else "no")
            actions = ", ".join(r.actions[:3]) if r.actions else "ok"
            if len(r.actions) > 3 and not verbose:
                actions += f", +{len(r.actions) - 3}"
            lines.append(
                f"{r.status:<20} {r.name[:30]:<30} "
                f"{_flag(r.graph, 'yes', 'no ')}   {_flag(r.wiki, 'yes', 'no ')}  "
                f"{_flag(r.hooks, 'yes', 'no ')}   {_flag(r.graphify_out_ignored, 'yes', 'no ')}    "
                f"{r.tracked_graphify_out_count:<7} {_flag(r.stale_marker, 'yes', 'no ')}  "
                f"{dirty:<5}  {actions}"
            )
        if not verbose and len(adopted) > len(display):
            lines.append(
                f"  … {len(adopted) - len(display)} more adopted repos omitted; use --verbose"
            )
        lines.append("")

    if candidates:
        lines.append("Candidate repos (suggested, not auto-applied):")
        display = candidates if verbose else candidates[:10]
        for r in display:
            lines.append(f"  - {r.name} ({r.root}) — {r.reason}; score {r.candidate_score}")
        if not verbose and len(candidates) > len(display):
            lines.append(
                f"  … {len(candidates) - len(display)} more candidates omitted; use --verbose"
            )
        lines.append("")

    blocked = [r for r in result.repos if r.blockers and r.status != "skip"]
    if blocked:
        lines.append("Blocked or needs review before apply:")
        display = blocked if verbose else blocked[:10]
        for r in display:
            lines.append(f"  - {r.name}: {', '.join(r.blockers)}")
        if not verbose and len(blocked) > len(display):
            lines.append(
                f"  … {len(blocked) - len(display)} more blocked repos omitted; use --verbose"
            )
        lines.append("")

    if verbose and skipped:
        lines.append("Skipped repos:")
        for r in skipped:
            lines.append(f"  - {r.name}: {r.reason}")
        lines.append("")

    lines.append("Recommended next commands:")
    root_arg = result.roots[0] if result.roots else str(default_root())
    semantic_args = f"--semantic --backend {DEFAULT_BACKEND}"
    if DEFAULT_MODEL:
        semantic_args += f" --model {DEFAULT_MODEL}"
    if any(r.status in {"activation-partial", "artifacts-only", "refresh-needed"} for r in adopted):
        lines.append(
            f"  graphify adoption apply --root {json.dumps(root_arg)} --scope adopted --local"
        )
    if any(r.stale_marker or not r.wiki for r in adopted):
        lines.append(
            f"  graphify adoption apply --root {json.dumps(root_arg)} --scope adopted "
            f"{semantic_args}"
        )
    if candidates:
        lines.append(
            "  graphify adoption apply --root "
            f"{json.dumps(root_arg)} --scope candidates --targets <comma-separated-repos> "
            f"--local {semantic_args}"
        )
    if not adopted and not candidates:
        lines.append("  No Graphify adoption actions recommended from this scan.")

    return "\n".join(lines)


def _is_selected(repo: RepoAdoption, options: ApplyOptions) -> bool:
    if repo.status == "skip":
        return False
    if options.targets:
        needles = {t.strip() for t in options.targets if t.strip()}
        return repo.name in needles or repo.root in needles or any(t in repo.root for t in needles)
    # Candidate bootstraps are intentionally suggested by audit but not applied
    # unless the operator explicitly selects targets. This prevents a broad
    # --scope candidates/--scope all semantic run from graphing every plausible
    # repo under /Users/mase/Codebase.
    if repo.status == "candidate":
        return False
    if options.scope == "adopted":
        return repo.status in {"full", "refresh-needed", "activation-partial", "artifacts-only"}
    if options.scope == "candidates":
        return False
    if options.scope == "all":
        return repo.status in {"full", "refresh-needed", "activation-partial", "artifacts-only"}
    return False


def _dirty_allowed(repo: RepoAdoption, options: ApplyOptions) -> bool:
    if options.include_dirty:
        return True
    if repo.dirty_source:
        return False
    if repo.dirty_graphify_out and not options.allow_dirty_graphify_out:
        return False
    return True


def _module_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "graphify", *args]


def _run_command(args: list[str], *, cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode == 0, output[-2000:]


def _append_cmd(commands: list[str], args: Sequence[str]) -> None:
    commands.append(" ".join(args))


def apply(options: ApplyOptions) -> list[ApplyResult]:
    if options.scope not in {"adopted", "candidates", "all"}:
        raise ValueError("scope must be adopted, candidates, or all")
    if not options.local and not options.semantic:
        raise ValueError("apply requires --local and/or --semantic")

    result = audit(options.root)
    selected = [r for r in result.repos if _is_selected(r, options)]
    outputs: list[ApplyResult] = []

    for repo in selected:
        repo_path = Path(repo.root)
        commands: list[str] = []
        if not _dirty_allowed(repo, options):
            outputs.append(
                ApplyResult(
                    repo=repo.name,
                    status="skipped",
                    message="dirty source/config files or dirty graphify-out; use --include-dirty or --allow-dirty-graphify-out",
                )
            )
            continue

        needs_activation = not repo.managed_agents or not repo.codex_session or not repo.hooks
        needs_local_graph_refresh = bool(
            repo.graph
            and (
                repo.stale_marker
                or not repo.report
                or (not repo.wiki and not repo.semantic_partial)
            )
        )
        needs_local_wiki_refresh = bool(repo.graph and not repo.stale_marker and not repo.wiki)
        needs_semantic_refresh = bool(not repo.graph or repo.stale_marker or repo.semantic_partial)

        if options.local:
            if (
                repo.graph or repo.hooks or repo.managed_agents or repo.codex_session
            ) and not repo.graphify_out_ignored:
                try:
                    _ensure_graphify_out_ignored(repo_path)
                    commands.append("ensure .gitignore ignores graphify-out/")
                except OSError as exc:
                    outputs.append(
                        ApplyResult(
                            repo=repo.name, status="failed", commands=commands, message=str(exc)
                        )
                    )
                    continue
            if repo.status == "candidate" and not repo.graph and not options.semantic:
                outputs.append(
                    ApplyResult(
                        repo=repo.name,
                        status="skipped",
                        message="candidate bootstrap requires --semantic; no existing graph to update locally",
                    )
                )
                continue
            if needs_activation:
                cmd = _module_command(
                    "codex", "reconcile", "--state", "active", "--apply", repo.root
                )
                _append_cmd(commands, cmd)
                ok, out = _run_command(cmd, cwd=repo_path)
                if not ok:
                    outputs.append(
                        ApplyResult(repo=repo.name, status="failed", commands=commands, message=out)
                    )
                    continue
            if needs_local_graph_refresh and repo.graph:
                cmd = _module_command("update", ".")
                _append_cmd(commands, cmd)
                ok, out = _run_command(cmd, cwd=repo_path)
                if not ok:
                    outputs.append(
                        ApplyResult(repo=repo.name, status="failed", commands=commands, message=out)
                    )
                    continue
            if needs_local_wiki_refresh:
                cmd = _cluster_command(options, label=False)
                _append_cmd(commands, cmd)
                ok, out = _run_command(cmd, cwd=repo_path)
                if not ok:
                    outputs.append(
                        ApplyResult(repo=repo.name, status="failed", commands=commands, message=out)
                    )
                    continue

        if options.semantic and needs_semantic_refresh:
            cmd = _module_command("extract", ".", "--backend", options.backend)
            if options.model:
                cmd += ["--model", options.model]
            _append_cmd(commands, cmd)
            ok, out = _run_command(cmd, cwd=repo_path)
            if not ok:
                outputs.append(
                    ApplyResult(repo=repo.name, status="failed", commands=commands, message=out)
                )
                continue
            cmd = _cluster_command(options, label=True)
            _append_cmd(commands, cmd)
            ok, out = _run_command(cmd, cwd=repo_path)
            if not ok:
                outputs.append(
                    ApplyResult(repo=repo.name, status="failed", commands=commands, message=out)
                )
                continue

        if commands:
            outputs.append(
                ApplyResult(repo=repo.name, status="applied", commands=commands, message="ok")
            )
        else:
            outputs.append(
                ApplyResult(
                    repo=repo.name,
                    status="skipped",
                    commands=commands,
                    message="no selected actions needed",
                )
            )

    if not selected:
        outputs.append(
            ApplyResult(repo="(none)", status="skipped", message="no repos matched selection")
        )
    return outputs


def _cluster_command(options: ApplyOptions, *, label: bool) -> list[str]:
    cmd = _module_command("cluster-only", ".")
    if label:
        cmd += ["--backend", options.backend]
        if options.model:
            cmd += ["--model", options.model]
    else:
        # Local apply must remain local/cheap: --no-label refreshes report/wiki
        # without invoking a configured LLM backend for community names.
        cmd += ["--no-label"]
    return cmd


def format_apply_results(results: list[ApplyResult]) -> str:
    lines = ["Graphify adoption apply results"]
    for r in results:
        lines.append(f"- {r.repo}: {r.status} — {r.message or 'ok'}")
        for cmd in r.commands:
            lines.append(f"    {cmd}")
    return "\n".join(lines)


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _usage() -> str:
    return """Usage:
  graphify adoption audit [--root PATH] [--json] [--verbose] [--repo NAME_OR_PATH]
  graphify adoption apply [--root PATH] [--scope adopted|candidates|all] [--targets CSV] [--local] [--semantic] [--backend NAME] [--model NAME] [--include-dirty] [--allow-dirty-graphify-out]
""".rstrip()


def run_cli(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        print(_usage())
        return 0 if args else 1

    subcmd = args.pop(0)
    if subcmd == "audit":
        root = default_root()
        as_json = False
        verbose = False
        repo_filter: str | None = None
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--root" and i + 1 < len(args):
                root = Path(args[i + 1])
                i += 2
            elif arg.startswith("--root="):
                root = Path(arg.split("=", 1)[1])
                i += 1
            elif arg == "--json":
                as_json = True
                i += 1
            elif arg == "--verbose":
                verbose = True
                i += 1
            elif arg == "--repo" and i + 1 < len(args):
                repo_filter = args[i + 1]
                i += 2
            elif arg.startswith("--repo="):
                repo_filter = arg.split("=", 1)[1]
                i += 1
            elif arg in {"-h", "--help"}:
                print(_usage())
                return 0
            else:
                print(f"error: unknown adoption audit option: {arg}", file=sys.stderr)
                return 2
        result = audit(root, repo_filter=repo_filter)
        if as_json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_report(result, verbose=verbose))
        return 0

    if subcmd == "apply":
        root = default_root()
        scope = "adopted"
        targets: list[str] = []
        local = False
        semantic = False
        backend = DEFAULT_BACKEND
        model = DEFAULT_MODEL
        include_dirty = False
        allow_dirty_graph = False
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--root" and i + 1 < len(args):
                root = Path(args[i + 1])
                i += 2
            elif arg.startswith("--root="):
                root = Path(arg.split("=", 1)[1])
                i += 1
            elif arg == "--scope" and i + 1 < len(args):
                scope = args[i + 1]
                i += 2
            elif arg.startswith("--scope="):
                scope = arg.split("=", 1)[1]
                i += 1
            elif arg == "--targets" and i + 1 < len(args):
                targets = _parse_csv(args[i + 1])
                i += 2
            elif arg.startswith("--targets="):
                targets = _parse_csv(arg.split("=", 1)[1])
                i += 1
            elif arg == "--local":
                local = True
                i += 1
            elif arg == "--semantic":
                semantic = True
                i += 1
            elif arg == "--backend" and i + 1 < len(args):
                backend = args[i + 1]
                i += 2
            elif arg.startswith("--backend="):
                backend = arg.split("=", 1)[1]
                i += 1
            elif arg == "--model" and i + 1 < len(args):
                model = args[i + 1]
                i += 2
            elif arg.startswith("--model="):
                model = arg.split("=", 1)[1]
                i += 1
            elif arg == "--include-dirty":
                include_dirty = True
                i += 1
            elif arg == "--allow-dirty-graphify-out":
                allow_dirty_graph = True
                i += 1
            elif arg in {"-h", "--help"}:
                print(_usage())
                return 0
            else:
                print(f"error: unknown adoption apply option: {arg}", file=sys.stderr)
                return 2
        if scope not in {"adopted", "candidates", "all"}:
            print("error: --scope must be adopted, candidates, or all", file=sys.stderr)
            return 2
        if not local and not semantic:
            print("error: adoption apply requires --local and/or --semantic", file=sys.stderr)
            print(_usage(), file=sys.stderr)
            return 2
        options = ApplyOptions(
            root=root,
            scope=scope,
            targets=targets,
            local=local,
            semantic=semantic,
            backend=backend or DEFAULT_BACKEND,
            model=model,
            include_dirty=include_dirty,
            allow_dirty_graphify_out=allow_dirty_graph,
        )
        try:
            results = apply(options)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(format_apply_results(results))
        return 1 if any(r.status == "failed" for r in results) else 0

    print(f"error: unknown adoption subcommand: {subcmd}", file=sys.stderr)
    print(_usage(), file=sys.stderr)
    return 2


__all__ = [
    "AdoptionAudit",
    "ApplyOptions",
    "ApplyResult",
    "RepoAdoption",
    "audit",
    "apply",
    "default_root",
    "discover_git_repos",
    "format_apply_results",
    "format_report",
    "inspect_repo",
    "run_cli",
]
