# Phase 1: Read-Only Status Harness - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/status_harness.py` | service / utility | request-response, file-I/O, diagnostic transform | `graphify/hooks.py`, `graphify/detect.py`, `graphify/llm.py`, `graphify/__main__.py` | composite exact |
| `graphify/status_profiles.py` | config | request-response, file-I/O expectations | `graphify/__main__.py` platform config and `graphify/detect.py` include rules | role-match |
| `scripts/graphify_status_harness.py` | route / script | request-response CLI wrapper | `graphify/__main__.py` | role-match |
| `tests/test_status_harness.py` | test | file-I/O, request-response, subprocess boundaries | `tests/test_hooks.py`, `tests/test_detect.py`, `tests/test_ollama.py`, `tests/test_install.py`, `tests/test_watch.py` | exact |
| `.planning/phases/01-read-only-status-harness/reports/*.json` and `*.md` | local report output | file-I/O, transform | `graphify/export.py`, `graphify/report.py`, `graphify/watch.py` | role-match |

## Pattern Assignments

### `graphify/status_harness.py` (service / utility, request-response + file-I/O)

**Analog:** `graphify/hooks.py`, `graphify/detect.py`, `graphify/llm.py`, `graphify/__main__.py`

**Imports pattern** (`graphify/hooks.py` lines 1-7, `graphify/detect.py` lines 1-14, `graphify/llm.py` lines 8-15):

```python
from __future__ import annotations
import configparser
import re
import sys
from pathlib import Path

import fnmatch
import json
import os
from enum import Enum
```

Use stdlib-first imports: `dataclasses`, `json`, `subprocess`, `difflib`, `os`, `urllib.request`, and `pathlib.Path`. Import existing Graphify helpers only where they are already source of truth: `graphify.hooks.status`, `graphify.detect` include/ignore helpers, `graphify.llm.BACKENDS`, `graphify.llm.detect_backend`, and `graphify.__main__._doctor` or `_install_source`.

**Active install source pattern** (`graphify/__main__.py` lines 25-66):

```python
def _install_source() -> Path | str | None:
    """Return the direct install source for graphifyy when package metadata records it."""
    if _pkg_distribution is None:
        return None
    try:
        dist = _pkg_distribution("graphifyy")
        text = dist.read_text("direct_url.json") or "{}"
        data = json.loads(text)
    except Exception:
        return None
    url = data.get("url")
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        return Path(urllib.parse.unquote(parsed.path)).resolve()
    return url
```

```python
def _doctor(require_source: str | None = None) -> int:
    """Print install diagnostics and return a process exit code."""
    source = _install_source()
    module_path = Path(__file__).resolve()
    print(f"graphify version: {__version__}")
    print(f"graphify module: {module_path}")
    print(f"graphify install source: {source or '<unknown>'}")
```

Planner should reuse this semantics for FORK-02/FORK-04. If calling `_doctor()` directly, capture stdout in tests; if using subprocess, run `graphify doctor --require-source <fork>`.

**Consumer activation pattern** (`graphify/hooks.py` lines 333-348):

```python
def status(path: Path = Path(".")) -> str:
    """Check if graphify hooks are installed."""
    root = _git_root(path)
    if root is None:
        return "Not in a git repository."
    hooks_dir = _hooks_dir(root)

    def _check(name: str, marker: str) -> str:
        p = hooks_dir / name
        if not p.exists():
            return "not installed"
        return "installed" if marker in p.read_text(encoding="utf-8") else "not installed (hook exists but graphify not found)"

    commit = _check("post-commit", _HOOK_MARKER)
    checkout = _check("post-checkout", _CHECKOUT_MARKER)
    return f"post-commit: {commit}\npost-checkout: {checkout}"
```

Use this helper for the hook layer rather than re-reading marker constants in the new harness. The harness can parse the returned two-line string into structured evidence.

**Graph coverage and include/ignore pattern** (`graphify/detect.py` lines 525-552, 634-769):

```python
def _load_graphifyinclude(root: Path) -> list[tuple[Path, str]]:
    """Read .graphifyinclude allowlist patterns from root and ancestors.

    Include patterns opt matching hidden files/dirs into traversal. Sensitive
    files and hard-skipped noise directories are still excluded later.
    Uses the same VCS-root ceiling logic as _load_graphifyignore.
    """
```

```python
ignore_patterns = _load_graphifyignore(root)
include_patterns = _load_graphifyinclude(root)
...
dirnames[:] = [
    d for d in dirnames
    if (not d.startswith(".") or _could_contain_included_path(dp / d, root, include_patterns))
    and not _is_noise_dir(d)
    and (has_negation or not _is_ignored(dp / d, root, ignore_patterns))
]
...
if p.name.startswith(".") and not _is_included(p, root, include_patterns):
    continue
```

For Second Brain hidden-path coverage, do not hand-roll broad hidden-directory traversal. Compare the target manifest and profile expectations against the same include semantics used by `detect()`.

**Graph freshness pattern** (`graphify/export.py` lines 400-448; `graphify/watch.py` lines 234-258):

```python
commit = built_at_commit if built_at_commit is not None else _git_head()
if commit:
    data["built_at_commit"] = commit
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
```

```python
def check_update(watch_path: Path) -> bool:
    flag = Path(watch_path) / _GRAPHIFY_OUT / "needs_update"
    if flag.exists():
        print(f"[graphify check-update] Pending non-code changes in {watch_path}.")
        print("[graphify check-update] Run `/graphify --update` to apply semantic re-extraction.")
    return True
```

Read `graphify-out/graph.json` and compare `built_at_commit` to target `git rev-parse HEAD`. Read the `needs_update` sentinel directly. Do not call rebuild/update/extract paths.

**Ollama readiness and cost pattern** (`graphify/llm.py` lines 51-76, 869-955):

```python
"ollama": {
    "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    "default_model": os.environ.get("GRAPHIFY_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL", "gemma4:31b"),
    "env_key": "OLLAMA_API_KEY",
    "pricing": {"input": 0.0, "output": 0.0},
    "temperature": 0,
    "max_tokens": 8192,
    "timeout": 1800.0,
},
```

```python
def estimate_cost(backend: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a given token count using published pricing."""
    if backend not in BACKENDS:
        return 0.0
    p = BACKENDS[backend]["pricing"]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
```

```python
def detect_backend() -> str | None:
    """Return the name of whichever backend has an API key set, or None.

    Priority: gemini -> kimi -> claude -> openai -> bedrock -> ollama (last).
    """
```

Use `BACKENDS["ollama"]["pricing"]` for zero priced backend cost and `detect_backend()` for active semantic backend. Probe local Ollama model availability separately with a bounded `/api/tags` or `ollama list` call so readiness is distinct from backend selection.

**Error handling pattern** (`graphify/hooks.py` lines 227-239; `graphify/watch.py` lines 229-231):

```python
except (configparser.Error, OSError) as exc:
    print(
        f"[graphify hooks] could not read core.hooksPath from "
        f"{root / '.git' / 'config'}: {exc}",
        file=sys.stderr,
    )
```

```python
except Exception as exc:
    print(f"[graphify watch] Rebuild failed: {exc}")
    return False
```

For the harness, prefer structured `CheckResult(severity="fail"|"warn", evidence={"error": str(exc)})` over printing. Use narrow exceptions where the failure mode is known; keep broad boundary catches only around external process/filesystem probes so one bad check does not abort the whole status report.

---

### `graphify/status_profiles.py` (config, profile-driven file-I/O expectations)

**Analog:** `graphify/__main__.py` platform config and `graphify/detect.py` include rules

**Config object pattern** (`graphify/__main__.py` lines 126-202):

```python
_PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "skill_file": "skill.md",
        "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
        "claude_md": True,
    },
    "codex": {
        "skill_file": "skill-codex.md",
        "skill_dst": Path(".agents") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
}
```

Use a small immutable profile map or dataclass registry, not scattered constants in `status_harness.py`. The Second Brain profile should hold target root, expected hidden include globs, forbidden/private globs, expected graph output paths, semantic cache expectations, and expected Ollama model names.

**Include semantics to reflect in profile checks** (`graphify/detect.py` lines 525-552):

```python
for d in dirs:
    include_file = d / ".graphifyinclude"
    if include_file.exists():
        for raw in include_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = _parse_gitignore_line(raw)
            if line:
                patterns.append((d, line))
```

Profile expectations should be data, but the harness check should use existing parse behavior when validating `.graphifyinclude`.

---

### `scripts/graphify_status_harness.py` (internal route / script, request-response)

**Analog:** `graphify/__main__.py`

**CLI routing pattern** (`graphify/__main__.py` lines 1163+ located by `main()`; install tests exercise `sys.argv` at `tests/test_install.py` lines 48-68):

```python
def test_install_positional_platform_opencode(tmp_path, monkeypatch):
    from graphify.__main__ import main
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "install", "opencode"])
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        main()
```

Keep the script thin: parse target/profile/output flags, call `graphify.status_harness.run_status_harness(...)`, print or write paths, and return a process exit code based on `overall_status`. Do not register a public `graphify` subcommand in Phase 1.

**Subprocess boundary pattern** (`tests/test_hooks.py` lines 190-205):

```python
result = subprocess.run(
    [sys.executable, "-m", "graphify", "hook-check"],
    cwd=tmp_path,
    capture_output=True,
    text=True,
)

assert result.returncode == 0
assert result.stdout == ""
assert result.stderr == ""
```

Use script-level subprocess tests only for argument parsing and process exit behavior. Keep probe logic directly unit-tested in `tests/test_status_harness.py`.

---

### `tests/test_status_harness.py` (test, file-I/O + subprocess + mocked boundaries)

**Analog:** `tests/test_hooks.py`, `tests/test_detect.py`, `tests/test_ollama.py`, `tests/test_install.py`, `tests/test_watch.py`

**Temporary git repo pattern** (`tests/test_hooks.py` lines 17-24):

```python
def _make_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path

def test_install_creates_hook(tmp_path):
    repo = _make_git_repo(tmp_path)
    result = install(repo)
```

Use real `tmp_path` repos for fork/consumer git status probes. Configure commits only where `HEAD` is needed. Avoid mutating the real Second Brain repo in tests.

**Detection fixture pattern** (`tests/test_detect.py` lines 83-104):

```python
(tmp_path / ".graphifyignore").write_text("vendor/\n*.generated.py\n")
vendor = tmp_path / "vendor"
vendor.mkdir()
(vendor / "lib.py").write_text("x = 1")
(tmp_path / "main.py").write_text("print('hi')")

result = detect(tmp_path)
file_list = result["files"]["code"]
assert any("main.py" in f for f in file_list)
assert not any("vendor" in f for f in file_list)
```

Mirror this pattern for `.graphifyinclude`, manifest contents, `graphify-out/needs_update`, and missing hidden-path coverage.

**Ollama and backend mocking pattern** (`tests/test_ollama.py` lines 24-31, 97-145):

```python
def test_ollama_in_backends():
    assert "ollama" in BACKENDS
    assert BACKENDS["ollama"]["pricing"]["input"] == 0.0
    assert BACKENDS["ollama"]["pricing"]["output"] == 0.0
    assert BACKENDS["ollama"]["timeout"] == 1800.0
```

```python
monkeypatch.delenv("OPENAI_API_KEY", raising=False)
monkeypatch.setattr("graphify.llm._local_ollama_available", lambda: True)
assert detect_backend() == "ollama"
```

Default tests must not require live Ollama. Mock any local service availability or model-list helper and assert severity mapping: unavailable is `warn` in read-only mode and `fail` for generation/stress mode.

**Doctor/source verification pattern** (`tests/test_install.py` lines 132-149):

```python
monkeypatch.setattr(main_mod, "_install_source", lambda: tmp_path.resolve())
assert main_mod._doctor(require_source=str(tmp_path)) == 0
assert f"graphify install source: {tmp_path.resolve()}" in capsys.readouterr().out
```

Test source mismatch as a `fail` check with captured evidence rather than shelling out for every unit test.

**Sentinel pattern** (`tests/test_watch.py` lines 37-41, 77-96):

```python
flag = mark_needs_update(tmp_path)

assert flag == tmp_path / "graphify-out" / "needs_update"
assert flag.read_text(encoding="utf-8") == "1"
```

For harness tests, create the sentinel directly and assert it appears in JSON evidence without being removed.

---

### `.planning/phases/01-read-only-status-harness/reports/*.json` and `*.md` (local report output, file-I/O transform)

**Analog:** `graphify/export.py`, `graphify/report.py`, `graphify/watch.py`

**JSON write pattern** (`graphify/export.py` lines 421-448):

```python
try:
    data = json_graph.node_link_data(G, edges="links")
except TypeError:
    data = json_graph.node_link_data(G)
...
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
return True
```

Use `json.dumps(..., indent=2, sort_keys=True)` or `json.dump(..., indent=2)` for stable machine-readable reports. JSON is authoritative; Markdown should be rendered from the final JSON payload only.

**Report metadata pattern** (`graphify/report.py` lines 73-83):

```python
if built_at_commit:
    lines.extend([
        "",
        "## Build Metadata",
        "",
        f"- Built from commit: `{built_at_commit[:8]}`",
        "",
    ])
```

The Markdown summary should be compact: overall status, primary diagnosis, failed/warned checks, evidence snippets, and recommended next action.

**Output directory pattern** (`graphify/watch.py` lines 187-204):

```python
out.mkdir(exist_ok=True)
(out / ".graphify_root").write_text(str(watch_root), encoding="utf-8")
...
(out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
```

Apply only to the fork-controlled report directory, e.g. `.planning/phases/01-read-only-status-harness/reports/`. Never write inside the target consumer repo.

## Shared Patterns

### Severity Model

**Source:** Phase decisions in `01-CONTEXT.md`
**Apply to:** `graphify/status_harness.py`, tests, JSON report schema

Use exactly `pass`, `warn`, `fail`, and `info`. Broken fork/install/source checks fail. Stale or partial generated artifacts usually warn in Phase 1. Second Brain hidden-path coverage failure is a profile-level fail.

### Read-Only Boundaries

**Source:** `graphify/hooks.py` status helper and `graphify/watch.py` check-update helper
**Apply to:** all probes

Allowed: file reads, JSON parsing, `git status`, `git rev-parse`, bounded model-list/readiness probes, `hooks.status(path)`, `detect_backend()`.

Forbidden in Phase 1 harness: `graphify update`, `graphify extract`, `_rebuild_code`, `mark_needs_update`, hook install/uninstall, target repo writes, semantic refresh.

### Git Probe Shape

**Source:** Research recommendation plus existing subprocess usage in `tests/test_hooks.py`
**Apply to:** fork git status and consumer git status

Use a small helper equivalent to:

```python
result = subprocess.run(
    ["git", "-C", str(repo), *args],
    capture_output=True,
    text=True,
    timeout=5,
)
```

Return code, stdout, stderr, and command in evidence. Do not raise on nonzero git status probes; convert them to structured checks.

### Skill Drift

**Source:** `AGENTS.md` and `docs/mase-fork-operating-model.md`
**Apply to:** fork/install layer

Compare `graphify/skill-codex.md` with `/Users/mase/.codex/skills/graphify/SKILL.md`. Default drift is `warn`; drift touching source verification, hooks, refresh guidance, or Graphify operating instructions is `fail`. Use `difflib` and keyword classification; do not overwrite either file.

### Test Defaults

**Source:** `.planning/codebase/TESTING.md`
**Apply to:** `tests/test_status_harness.py`

Use `pytest`, `tmp_path`, `monkeypatch`, `capsys`, and `unittest.mock.patch`. Default suite must not call live LLMs, real external HTTP services, or mutate Second Brain. Use subprocess only where process boundaries matter.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| None | - | - | All planned files have usable analogs. `status_harness.py` is composite rather than single-file because no existing module currently aggregates fork, install, consumer, graph, skill, and Ollama checks into one report. |

## Metadata

**Analog search scope:** `graphify/`, `tests/`, `.planning/phases/01-read-only-status-harness/`, `.planning/codebase/`, repo-local `.codex/skills/`
**Files scanned:** source/test maps plus focused analog files: `graphify/hooks.py`, `graphify/watch.py`, `graphify/detect.py`, `graphify/llm.py`, `graphify/__main__.py`, `graphify/export.py`, `graphify/report.py`, `tests/test_hooks.py`, `tests/test_detect.py`, `tests/test_ollama.py`, `tests/test_install.py`, `tests/test_watch.py`
**Pattern extraction date:** 2026-05-11
