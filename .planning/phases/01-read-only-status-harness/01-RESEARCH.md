# Phase 1: Read-Only Status Harness - Research

**Researched:** 2026-05-11
**Domain:** Python CLI status harness, Graphify fork/install diagnostics, consumer graph freshness, Ollama readiness
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Harness Shape
- **D-01:** Do not make this a public Graphify CLI command in Phase 1. The checks are still being learned from a real consumer repo, so they should start as an internal/dev evaluation harness in this fork.
- **D-02:** Keep the implementation structured enough that it can later be promoted into a Graphify CLI command if the report shape proves stable.
- **D-03:** The harness must be callable repeatably against Second Brain without mutating that target repo.

### Output Contract
- **D-04:** Emit both machine-readable JSON and a short Markdown summary.
- **D-05:** Treat JSON as the source of truth for agents, recurring checks, and trend tracking.
- **D-06:** Keep Markdown concise: overall status, diagnosis, evidence, and recommended next action. It should be agent-readable first and human-readable second.
- **D-07:** Save local reports for tracking. Reports should live in a controlled local evaluation/output location, not as accidental generated churn inside the consumer repo.

### Diagnosis Model
- **D-08:** Use diagnostic-by-default behavior for Phase 1. Stale or partial generated artifacts should usually be warnings, while broken fork/install/source verification should fail.
- **D-09:** Reserve strict acceptance behavior for a later explicit mode. Strict mode can turn selected warnings, such as stale target graphs, into failures for recurring acceptance checks.
- **D-10:** Use four severity levels: `pass`, `warn`, `fail`, and `info`.
- **D-11:** Active CLI not installed from `/Users/mase/Codebase/Personal-Projects/graphify` is `fail`.
- **D-12:** Installed Codex skill drift from packaged `graphify/skill-codex.md` is `warn` by default; if the drift affects Graphify operating instructions, source verification, hooks, or refresh guidance, classify it as `fail`.
- **D-13:** Target graph built commit differing from target HEAD is `warn` by default.
- **D-14:** Missing expected hidden-path coverage for the Second Brain profile, such as `.claude/scripts/**/*.py`, is `fail` for that profile.
- **D-15:** Missing semantic cache is `warn` before any approved refresh expectation exists, and `fail` only when a refresh was expected to have produced cache artifacts.
- **D-16:** Ollama unavailable is `warn` in read-only status mode and `fail` in generation/stress mode.
- **D-17:** Small generation passing while the larger stress check times out is `warn` by default, unless strict mode later decides otherwise.

### Second Brain Targeting
- **D-18:** Support Second Brain-specific expectations in Phase 1.
- **D-19:** Express those expectations through a target profile or profile-like configuration rather than hardcoding one-off Second Brain logic throughout the harness.
- **D-20:** The Second Brain profile should cover expected Graphify activation, hidden path inclusion needs, relevant ignore/include behavior, root graph freshness, semantic cache status, and smoke-query concepts.

### Ollama And Local Generation
- **D-21:** Include local generation checks, because the implementation uses local Ollama and therefore does not create paid API cost exposure.
- **D-22:** Separate readiness checks from generation/stress checks.
- **D-23:** Readiness checks should detect the active backend, verify local Ollama is reachable, report available/expected models, and report zero priced backend cost separately from runtime risk.
- **D-24:** Generation checks should include one small local smoke test and one larger stress-style local test in a temporary harness-controlled area.
- **D-25:** Generation/stress checks must not perform an implicit semantic refresh of Second Brain in Phase 1.

### the agent's Discretion
The agent may choose the internal module/file layout, exact report directory under `.planning` or another local harness output path, fixture shape for the generation stress test, and the exact JSON schema details, as long as the decisions above are preserved and tests can validate the contract.

### Deferred Ideas (OUT OF SCOPE)
- Promote the harness into a public Graphify CLI command after report shape and diagnosis semantics stabilize.
- Add strict recurring acceptance mode that can fail on stale consumer graph state or generation stress instability.
- Run an approved semantic refresh of Second Brain and then use post-refresh expectations as stricter assertions in later phases.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARNESS-01 | The harness can run against a target repo without modifying files. | Use subprocess/git/filesystem reads only; save reports under `.planning/phases/01-read-only-status-harness/reports/`, not inside the target repo. [CITED: .planning/REQUIREMENTS.md] [VERIFIED: codebase grep] |
| HARNESS-02 | The harness emits machine-readable JSON status. | Make JSON the source of truth with stable layers and per-check severity. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] |
| HARNESS-03 | The harness emits a compact Markdown summary for operator review. | Render Markdown from the JSON payload after all probes complete. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] |
| HARNESS-04 | The harness reports diagnosis categories. | Derive `primary_diagnosis` from failed/warned check categories: fork bug, install/skill drift, consumer config gap, stale graph artifacts, refresh/runtime issue. [CITED: .planning/REQUIREMENTS.md] |
| FORK-01 | Reports fork branch, dirty state, local-vs-origin status. | Use `git status --short --branch` and `git rev-list --left-right --count @{u}...HEAD` when upstream exists. [ASSUMED] |
| FORK-02 | Verifies active CLI source with `graphify doctor --require-source`. | `_doctor()` already prints version, module path, and direct install source, and returns nonzero when source mismatches. [VERIFIED: graphify/__main__.py] |
| FORK-03 | Compares packaged Codex skill guidance with installed global Graphify skill. | Compare `graphify/skill-codex.md` with `/Users/mase/.codex/skills/graphify/SKILL.md`; classify drift keywords from fork docs. [CITED: docs/mase-fork-operating-model.md] |
| FORK-04 | Reports Graphify version and active module path. | `_doctor()` already reports both values. [VERIFIED: graphify/__main__.py] |
| CONSUMER-01 | Reports target repo branch, dirty state, and `HEAD`. | Use git read-only probes against the target path. [VERIFIED: terminal probe] |
| CONSUMER-02 | Reports whether Graphify Git hooks are installed. | Reuse `graphify.hooks.status(path)`; it checks post-commit and post-checkout hook markers. [VERIFIED: graphify/hooks.py] |
| CONSUMER-03 | Reports whether target `AGENTS.md` contains Graphify guidance. | Read `AGENTS.md` and check for `## graphify` and core guidance strings. [VERIFIED: terminal probe] |
| GRAPH-01 | Compares graph built commit against target `HEAD`. | `graphify/export.py` writes `built_at_commit` into `graph.json`; compare it to `git rev-parse HEAD`. [VERIFIED: graphify/export.py] |
| GRAPH-02 | Reports `graphify-out/needs_update` presence. | `graphify.watch.mark_needs_update()` writes this sentinel and `check_update()` reports it without clearing it. [VERIFIED: graphify/watch.py] |
| GRAPH-03 | Reports manifest file count and expected paths. | `graphify/detect.py` writes `graphify-out/manifest.json`; current Second Brain root manifest has 103 entries and no `.claude/scripts/` paths. [VERIFIED: terminal probe] |
| GRAPH-04 | Reports root semantic cache count. | Inspect `graphify-out/cache/semantic` or current semantic cache convention after confirming cache layout; current root has AST cache files but no semantic cache directory under checked candidate paths. [VERIFIED: terminal probe] [ASSUMED] |
| OLLAMA-01 | Reports detected semantic backend. | Reuse `graphify.llm.detect_backend()`; priority is Gemini, Kimi, Claude, OpenAI, Bedrock, then Ollama. [VERIFIED: graphify/llm.py] |
| OLLAMA-02 | Reports local Ollama availability and model names without API keys. | Use native Ollama tags/list probe separately from `detect_backend()`; current machine reports `gemma4:31b`, `gemma4:26b`, and `gemma4:latest`. [VERIFIED: terminal probe] |
| OLLAMA-03 | Distinguishes zero API cost from runtime risk. | `BACKENDS["ollama"]["pricing"]` is zero for input and output, while timeout and sequential chunk behavior are explicitly tested. [VERIFIED: graphify/llm.py] [VERIFIED: tests/test_ollama.py] |
</phase_requirements>

## Summary

Build Phase 1 as a private Python harness module plus a small script entry point, not a public `graphify` CLI command. The harness should collect read-only evidence from the local fork checkout, the active installed CLI, the installed Codex skill copy, the target consumer repo, target `graphify-out/` artifacts, and local Ollama readiness. This matches the locked phase boundary and avoids adding more behavior to the already large `graphify/__main__.py` router. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [VERIFIED: .planning/codebase/CONCERNS.md]

The report model should be JSON-first: `overall_status`, `primary_diagnosis`, four status layers, per-check severities, evidence snippets, and recommended next action. Markdown should be rendered from JSON and stay short. The saved report location should be inside this fork's controlled planning output, e.g. `.planning/phases/01-read-only-status-harness/reports/`, so repeated runs against Second Brain do not modify the target repo. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

Current read-only probes confirm the acceptance target is a useful failing baseline: active CLI source verification passes for this checkout; Second Brain is on `main...origin/main [ahead 4]` with dirty/untracked files; root `graphify-out/graph.json` was built from `fe6f639...` while target `HEAD` is `c49aa592...`; root manifest has 103 entries and no `.claude/scripts/` entries; `.graphifyinclude` is absent; local Ollama lists `gemma4:31b`. [VERIFIED: terminal probe]

**Primary recommendation:** Implement `graphify/status_harness.py` with pure read-only probe functions, `scripts/graphify_status_harness.py` as the internal callable, `tests/test_status_harness.py` for mocked/unit coverage, and saved reports under `.planning/phases/01-read-only-status-harness/reports/`. [VERIFIED: .planning/codebase/STRUCTURE.md] [ASSUMED]

## Project Constraints (from AGENTS.md)

- Make source changes in this repository, not in the uv tool site-packages copy. [CITED: AGENTS.md]
- Verify active CLI source with `graphify doctor --require-source /Users/mase/Codebase/Personal-Projects/graphify` before using Graphify as evidence in another repo. [CITED: AGENTS.md]
- Do not continue by installing from PyPI if source verification fails. [CITED: AGENTS.md]
- Keep upstream mirror branches such as `v6` clean; local customizations belong on `mase/local-fixes` unless a narrower branch is explicitly created. [CITED: AGENTS.md]
- Always inspect `git status --short --branch`, current branch, and relevant diffs before making local-vs-upstream claims. [CITED: AGENTS.md]
- Treat `graphify-out/`, `.planning/graphs/`, and other graph outputs as derived evidence, not source of truth. [CITED: AGENTS.md] [CITED: /Users/mase/.codex/docs/reference/graphify.md]
- For Codex behavior, reliable guidance surfaces are repo-local `AGENTS.md`, the global Graphify skill, and explicit `$graphify`; `graphify hook-check` is intentionally silent in the current Codex Desktop runtime. [CITED: AGENTS.md] [CITED: docs/mase-fork-operating-model.md]
- When skill behavior changes, compare `graphify/skill-codex.md`, `/Users/mase/.codex/skills/graphify/SKILL.md`, and `/Users/mase/.codex/docs/reference/graphify.md`; do not overwrite the installed skill blindly. [CITED: AGENTS.md] [CITED: docs/mase-fork-operating-model.md]
- Prefer targeted tests in `tests/test_watch.py`, `tests/test_transcribe.py`, and `tests/test_hooks.py` for current local patch goals, plus nearest module tests for touched behavior. [CITED: AGENTS.md] [CITED: docs/mase-fork-operating-model.md]
- This `.planning/` setup is local-only for now because `commit_docs` is false. [CITED: .planning/STATE.md] [VERIFIED: .planning/config.json]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Fork git/source health | Local CLI / Filesystem | Git subprocess | The harness runs inside the fork checkout and reads git/package metadata. [VERIFIED: graphify/__main__.py] |
| Active installed CLI health | Local CLI / Python package metadata | Subprocess | `graphify doctor --require-source` already encodes source verification and module path evidence. [VERIFIED: graphify/__main__.py] |
| Installed Codex skill drift | Filesystem | Diff classifier | Drift is a file-content comparison between repo packaged skill and installed `.codex` skill. [CITED: docs/mase-fork-operating-model.md] |
| Consumer activation health | Filesystem / Git | Existing hook helper | Hooks and AGENTS guidance live in the target repo; reads must not write. [VERIFIED: graphify/hooks.py] |
| Consumer graph freshness | Filesystem / JSON parser | Git subprocess | `built_at_commit`, manifest, cache, and `needs_update` are artifact reads compared with target `HEAD`. [VERIFIED: graphify/export.py] [VERIFIED: graphify/detect.py] |
| Ollama readiness | Local service probe | `graphify.llm` backend metadata | Readiness is separate from generation; cost/pricing comes from backend registry while model availability comes from local Ollama tags/list. [VERIFIED: graphify/llm.py] |
| Report persistence | Harness output directory | Markdown renderer | Reports should be saved in this fork's controlled planning output, not the consumer repo. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python stdlib (`pathlib`, `json`, `subprocess`, `difflib`, `dataclasses`) | Python 3.14.3 on current shell; package supports `>=3.10` | Implement read-only probes, report schema, and file comparisons without new dependencies. | Existing project is a Python CLI and already relies on stdlib command/file handling. [VERIFIED: terminal probe] [VERIFIED: pyproject.toml] |
| Existing Graphify package modules | `graphifyy` 0.7.9 active install | Reuse `_doctor`, `hooks.status`, `detect` include/ignore semantics, `llm.BACKENDS`, and `llm.detect_backend`. | Keeps harness aligned with actual product behavior and avoids divergent status logic. [VERIFIED: terminal probe] [VERIFIED: graphify/__main__.py] |
| Git CLI | 2.50.1 Apple Git | Read branch, dirty state, upstream ahead/behind, and `HEAD`. | Git state is repository state; subprocess probes are simple and portable enough for this local harness. [VERIFIED: terminal probe] [ASSUMED] |
| Ollama CLI or HTTP `/api/tags` | `ollama list` available; model list verified | Report local model availability without API keys. | Graphify's local backend uses Ollama-compatible endpoints and zero backend pricing. [VERIFIED: terminal probe] [VERIFIED: graphify/llm.py] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `pytest` | Not available through `uv run pytest --version` in this checkout during research | Unit tests for harness probes and report rendering. | Add or sync dev test dependency before validation if implementation needs runnable tests. [VERIFIED: terminal probe] |
| `networkx` | Declared dependency; not importable from system Python used in probe | No direct harness need unless validating graph JSON beyond counts. | Avoid requiring runtime imports for status checks; parse JSON directly unless graph traversal is added later. [VERIFIED: pyproject.toml] [VERIFIED: terminal probe] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Private `scripts/` entry point | Public `graphify status-harness` command in `__main__.py` | Public CLI is explicitly deferred and would add risk to the monolithic router. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [VERIFIED: .planning/codebase/CONCERNS.md] |
| JSON file reports under `.planning/phases/.../reports/` | Write status sidecars into target `graphify-out/` | Target writes violate Phase 1 read-only acceptance. [CITED: .planning/ROADMAP.md] |
| Direct JSON parsing | Import/export full graph objects | Direct parsing is enough for freshness, counts, and source paths; object construction is unnecessary and can drag optional dependencies into status checks. [VERIFIED: graphify/export.py] [ASSUMED] |

**Installation:** No new production package install is recommended for Phase 1. A pytest dev/test dependency is planned only to make the existing pytest verification commands runnable. [VERIFIED: pyproject.toml] [VERIFIED: terminal probe]

## Package Legitimacy Audit

Phase 1 implementation should use stdlib plus existing Graphify modules for production harness code. The only package metadata change planned is a dev/test dependency declaration for pytest because research verified `uv run pytest --version` was unavailable in the current checkout environment. [VERIFIED: pyproject.toml] [VERIFIED: terminal probe]

| Package | Registry | Classification | Evidence | Planned Use |
|---------|----------|----------------|----------|-------------|
| `pytest` | PyPI | [OK] | Official PyPI project `pytest`; verified details, trusted publishing for current release, Python >=3.10 support, MIT license, source project `pytest-dev/pytest`. [VERIFIED: https://pypi.org/project/pytest/] | Dev/test dependency only, used to run existing and new harness tests. |

## Architecture Patterns

### System Architecture Diagram

```text
Internal script invocation
  |
  v
Load target profile (second_brain)
  |
  v
Run read-only probes -----------------------------------------------------+
  |                                                                      |
  +--> Fork git probe -> branch/dirty/ahead-behind                       |
  +--> Active CLI probe -> graphify doctor/module/version/source          |
  +--> Skill drift probe -> repo skill vs installed Codex skill diff      |
  +--> Consumer git probe -> target branch/dirty/HEAD                    |
  +--> Consumer activation probe -> AGENTS.md + hook marker status        |
  +--> Consumer graph probe -> graph.json/manifest/cache/needs_update     |
  +--> Ollama readiness probe -> backend/pricing/local models             |
                                                                         |
                                                                         v
                                               Normalize checks into JSON schema
                                                                         |
                                                    severity + diagnosis reducer
                                                                         |
                                                                         v
                                             Write local JSON + Markdown reports
                                             under this fork's planning output
```

### Recommended Project Structure

```text
graphify/
├── status_harness.py          # Read-only probes, schema dataclasses, diagnosis reducer
└── status_profiles.py         # Target profile definitions, starting with second_brain
scripts/
└── graphify_status_harness.py # Internal/dev callable; no public CLI registration
tests/
└── test_status_harness.py     # Pure unit tests with tmp_path and monkeypatch
.planning/phases/01-read-only-status-harness/
└── reports/                   # Generated local reports; never written to target repo
```

### Pattern 1: Probe Functions Return Structured Check Results

**What:** Each probe returns a `CheckResult` or list of `CheckResult` objects with `id`, `layer`, `severity`, `category`, `summary`, `evidence`, and optional `remediation`. [ASSUMED]

**When to use:** Use for all fork/install/consumer/graph/Ollama checks so the diagnosis reducer does not parse prose. [ASSUMED]

**Example:**

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CheckResult:
    id: str
    layer: str
    severity: str
    category: str
    summary: str
    evidence: dict[str, object] = field(default_factory=dict)
    remediation: str | None = None
```

### Pattern 2: Read-Only Git Probes via Subprocess

**What:** Use `git -C <repo> ...` commands with timeout and captured output; never run hooks, refreshes, checkouts, resets, or writes. [ASSUMED]

**When to use:** Fork and consumer branch, dirty state, `HEAD`, and ahead/behind checks. [ASSUMED]

**Example:**

```python
def run_git(repo: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()
```

### Pattern 3: Profile-Driven Target Expectations

**What:** Encode Second Brain expectations as data: expected root path, expected hidden include globs, forbidden hidden/private globs, expected Ollama models, graph artifact paths, and smoke-query terms. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [ASSUMED]

**When to use:** Use for checks that are target-specific, especially `.claude/scripts/**/*.py` inclusion and `.claude/data/` exclusion. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

**Example:**

```python
SECOND_BRAIN_PROFILE = {
    "name": "second_brain",
    "root": "/Users/mase/Codebase/Personal-Projects/my-second-brain-build",
    "expected_hidden_includes": [".claude/scripts/**/*.py"],
    "forbidden_includes": [".claude/data/**", ".claude/**/*.db", ".claude/**/__pycache__/**"],
    "expected_ollama_models": ["gemma4:31b"],
}
```

### Pattern 4: Markdown Rendered From JSON

**What:** Generate Markdown only from the final JSON payload, not from a separate probe path. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [ASSUMED]

**When to use:** Always; this keeps agent-readable JSON authoritative and prevents divergent status narratives. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

### Anti-Patterns to Avoid

- **Adding a public CLI command in Phase 1:** It contradicts D-01 and increases risk in `graphify/__main__.py`. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [VERIFIED: .planning/codebase/CONCERNS.md]
- **Running `graphify update`, `graphify extract`, or semantic refresh during status:** These commands can write target graph artifacts and violate read-only acceptance. [VERIFIED: graphify/watch.py] [CITED: .planning/ROADMAP.md]
- **Using `needs_update` as the only freshness signal:** Current planning docs explicitly say it is insufficient; compare `built_at_commit` to `HEAD` and inspect manifest/cache too. [CITED: .planning/PROJECT.md] [VERIFIED: terminal probe]
- **Treating installed skill version stamp as content freshness:** Fork docs say `.graphify_version` is not proof of skill guidance parity. [CITED: docs/mase-fork-operating-model.md]
- **Calling live Ollama in default tests:** Existing test guidance avoids live LLM/network calls by default; mock backend availability and generation boundaries. [VERIFIED: .planning/codebase/TESTING.md] [VERIFIED: tests/test_ollama.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Active CLI source verification | Custom site-packages path guessing only | `graphify doctor --require-source` plus `_doctor()` evidence parsing | Existing implementation understands direct install metadata and module fallback. [VERIFIED: graphify/__main__.py] |
| Hook installation detection | Ad hoc `.git/hooks` string checks only | `graphify.hooks.status(path)` | Existing helper respects hook markers and `core.hooksPath` handling through `_hooks_dir`. [VERIFIED: graphify/hooks.py] |
| Include/ignore semantics | Custom glob walker for `.graphifyignore`/`.graphifyinclude` | Existing `graphify.detect` helpers and manifest data | Include/ignore handling has VCS-root ceilings, hidden directory rules, and negation behavior. [VERIFIED: graphify/detect.py] |
| Ollama pricing | Manual hardcoded "free" string | `graphify.llm.BACKENDS["ollama"]["pricing"]` | Backend registry already defines zero input/output pricing. [VERIFIED: graphify/llm.py] |
| Graph freshness metadata | Parse `GRAPH_REPORT.md` only | `graphify-out/graph.json` `built_at_commit` plus target git `HEAD` | JSON export writes the commit directly; report text is secondary. [VERIFIED: graphify/export.py] |
| Status prose | Independent Markdown checks | Render Markdown from JSON | JSON is locked as source of truth. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] |

**Key insight:** The harness is an observer, not a mini-Graphify runner. Reuse existing Graphify source-of-truth helpers and artifact contracts; do not reimplement graph generation or file discovery in a way that can drift from the product. [VERIFIED: .planning/codebase/ARCHITECTURE.md] [ASSUMED]

## Common Pitfalls

### Pitfall 1: Read-Only Harness Accidentally Writes Target Reports

**What goes wrong:** The harness writes JSON, Markdown, temp files, or generation fixtures inside the consumer repo. [ASSUMED]

**Why it happens:** The target repo is the natural current working directory for Graphify operations, and existing Graphify output defaults to `graphify-out/`. [VERIFIED: graphify/__main__.py]

**How to avoid:** Resolve report output under this fork's `.planning/phases/01-read-only-status-harness/reports/` and create generation fixtures under a harness-controlled temp directory only. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [ASSUMED]

**Warning signs:** `git -C <target> status --short` changes after a harness run, or `graphify-out/` mtimes change. [ASSUMED]

### Pitfall 2: Stale Graph Misclassified As Healthy Because Hooks Exist

**What goes wrong:** Installed hooks and Graphify guidance are treated as proof that graph artifacts are fresh. [CITED: .planning/REQUIREMENTS.md]

**Why it happens:** Hook status is an activation signal, not a freshness signal; docs/media only write `needs_update`, and branch switches/code changes are code-only rebuilds. [VERIFIED: graphify/hooks.py] [VERIFIED: graphify/watch.py]

**How to avoid:** Report activation and graph freshness as separate layers, and compare `built_at_commit` to target `HEAD`. [VERIFIED: graphify/export.py]

**Warning signs:** `post-commit: installed` with a mismatched `built_at_commit`, missing expected paths, or missing semantic cache. [VERIFIED: terminal probe]

### Pitfall 3: Hidden-Path Coverage Missed By Manifest-Only Counts

**What goes wrong:** Manifest count is nonzero, but `.claude/scripts/**/*.py` is absent. [VERIFIED: terminal probe]

**Why it happens:** Hidden directories are pruned unless `.graphifyinclude` explicitly allows them. [VERIFIED: graphify/detect.py]

**How to avoid:** Profile checks must search manifest paths for each expected include glob and separately verify forbidden paths remain absent. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [ASSUMED]

**Warning signs:** `.graphifyinclude` missing, no manifest paths under `.claude/scripts/`, or accidental inclusion of `.claude/data/`. [VERIFIED: terminal probe] [ASSUMED]

### Pitfall 4: Ollama "Zero Cost" Misread As "No Risk"

**What goes wrong:** Local generation is treated as safe to run during read-only status. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

**Why it happens:** `ollama` pricing is zero, but local model latency, JSON quality, timeouts, and non-loopback endpoints remain runtime/security risks. [VERIFIED: graphify/llm.py] [VERIFIED: .planning/codebase/CONCERNS.md]

**How to avoid:** Separate readiness from generation/stress checks. Default status mode should only detect backend, availability, model list, pricing, and risk flags. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

**Warning signs:** Default tests call real Ollama or status mode launches extraction. [VERIFIED: .planning/codebase/TESTING.md]

### Pitfall 5: Skill Drift Classification Too Naive

**What goes wrong:** Any skill diff is treated as fail, or all skill diffs are treated as warning. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

**Why it happens:** The installed `.codex` skill can intentionally contain local overlays, but drift around hooks, source verification, and refresh guidance is load-bearing. [CITED: docs/mase-fork-operating-model.md]

**How to avoid:** Report diff hash/summary and scan changed hunks for load-bearing keywords: `doctor`, `require-source`, `hook-check`, `needs_update`, `graphify-out`, `codex install`, `GRAPH_REPORT`, `community_labels`, and refresh/update guidance. [CITED: docs/mase-fork-operating-model.md] [ASSUMED]

**Warning signs:** `/Users/mase/.codex/skills/graphify/SKILL.md` differs without a classified reason. [CITED: docs/mase-fork-operating-model.md]

## Code Examples

### JSON Contract Skeleton

```python
payload = {
    "schema_version": 1,
    "generated_at": "2026-05-11T00:00:00Z",
    "target_profile": "second_brain",
    "target_root": "/Users/mase/Codebase/Personal-Projects/my-second-brain-build",
    "overall_status": "warn",
    "primary_diagnosis": "stale_graph_artifacts",
    "layers": {
        "fork": {"status": "pass", "checks": []},
        "installed_cli_skill": {"status": "warn", "checks": []},
        "consumer_activation": {"status": "fail", "checks": []},
        "consumer_graph": {"status": "warn", "checks": []},
        "ollama_readiness": {"status": "pass", "checks": []},
    },
    "recommended_next_action": "Capture baseline, then add a narrow .graphifyinclude in Phase 2.",
}
```

### Built Commit Freshness Check

```python
def check_built_commit(graph_json: Path, target_head: str) -> CheckResult:
    data = json.loads(graph_json.read_text(encoding="utf-8"))
    built = data.get("built_at_commit")
    severity = "pass" if built == target_head else "warn"
    return CheckResult(
        id="graph.built_commit",
        layer="consumer_graph",
        severity=severity,
        category="stale_graph_artifacts",
        summary="Graph built commit matches target HEAD" if severity == "pass" else "Graph built commit differs from target HEAD",
        evidence={"built_at_commit": built, "target_head": target_head},
    )
```

### Current Second Brain Baseline Evidence

```text
target HEAD: c49aa59297c752a388eca6828a87d30b26cbb2ea
graph built_at_commit: fe6f6398456ceb1ef1a942d52dc2a084f598f644
root graph nodes: 1826
root graph links: 4761
root manifest entries: 103
.graphifyinclude exists: false
manifest contains .claude/scripts/: false
ollama models include: gemma4:31b
```

Evidence above came from read-only terminal probes during research. [VERIFIED: terminal probe]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Treat `graphify hook-check` as active Codex reminder | Treat hook-check as silent/no-op in current Codex Desktop and rely on AGENTS/global skill guidance | Current fork docs last verified 2026-05-05 | Harness should report hooks/guidance state, not assume Codex reminder behavior. [CITED: docs/mase-fork-operating-model.md] |
| Rely on mtime or `needs_update` only | Compare `built_at_commit`, `needs_update`, manifest, cache, and expected path coverage | Existing export/write path supports `built_at_commit` | Prevents false "fresh" status when generated graph was built on an old commit. [VERIFIED: graphify/export.py] |
| Let local Ollama shadow paid keys automatically | Backend detection checks paid/API-key backends before local Ollama | Existing `detect_backend()` priority | Readiness report must show detected backend and local Ollama availability separately. [VERIFIED: graphify/llm.py] |
| Semantic extraction in hooks | Hooks rebuild code graph or mark `needs_update`; docs/media require manual semantic refresh | Existing hook/watch behavior | Phase 1 must not imply hooks perform semantic refresh. [VERIFIED: graphify/hooks.py] [VERIFIED: graphify/watch.py] |

**Deprecated/outdated:**
- Treating `.graphify_version` as proof of skill content freshness is outdated for this fork; docs require diff classification. [CITED: docs/mase-fork-operating-model.md]
- Describing `graphify codex install` as an active per-tool Codex reminder is outdated unless hook behavior changes and is verified. [CITED: AGENTS.md] [CITED: docs/mase-fork-operating-model.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `git rev-list --left-right --count @{u}...HEAD` is the right ahead/behind probe when upstream exists. | Phase Requirements / Standard Stack | Harness may misreport fork or target remote divergence in repos without upstream tracking. |
| A2 | Report directory should be `.planning/phases/01-read-only-status-harness/reports/`. | Summary / Architecture Patterns | Planner may choose a different controlled local output path. |
| A3 | Root semantic cache count should inspect `graphify-out/cache/semantic` or current semantic cache convention after implementation confirms cache layout. | Phase Requirements | Harness may initially miss semantic cache files if current layout differs. |
| A4 | Direct JSON parsing is enough for Phase 1 graph status. | Standard Stack | Later query/explain smoke checks may need graph loader/helper reuse. |
| A5 | Skill drift keyword classification can determine warn vs fail for load-bearing guidance. | Common Pitfalls | Human review may still be needed for ambiguous skill diffs. |

## Open Questions (RESOLVED)

1. **Exact semantic cache layout for root cache count**
   - Decision: Plan 01 must inspect `graphify/cache.py` before implementing the semantic cache count and then use the canonical cache path/key convention from that file. The probe must not assume `graphify-out/cache/semantic` unless `graphify/cache.py` confirms that layout. [RESOLVED]
   - Implementation implication: The semantic cache probe remains a read-only artifact inspection and reports missing cache as `warn` unless a prior approved refresh expectation exists per D-15. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

2. **Generation/stress callable boundary**
   - Decision: Phase 1 implements generation/stress behind an explicit non-default core/script flag or function. It includes one small smoke fixture and one larger stress-style fixture under a harness-controlled temporary directory. It must not run in default status mode and must not read from, refresh, or write to Second Brain per D-24 and D-25. [RESOLVED]
   - Implementation implication: Default readiness checks report backend, Ollama availability, model names, zero cost, and runtime risk only; generation/stress checks are separate structured results and are tested with mocks/temp fixtures. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]

3. **Dev test environment**
   - Decision: Plan 01 must validate pytest availability before pytest-based verification. If unavailable, it must declare pytest as a dev dependency in `pyproject.toml`, update `uv.lock` through uv, and run `uv sync --group dev` before `uv run --group dev pytest ...`. [RESOLVED]
   - Implementation implication: Test verification commands in Phase 1 plans use `uv sync --group dev` followed by `uv run --group dev pytest ...`; production harness code remains stdlib plus existing Graphify modules. [VERIFIED: terminal probe]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Harness implementation | Yes | 3.14.3 in shell; project supports `>=3.10` | Use the package/tool interpreter if system Python lacks deps. [VERIFIED: terminal probe] [VERIFIED: pyproject.toml] |
| Git | Fork and target repo probes | Yes | 2.50.1 Apple Git | None needed. [VERIFIED: terminal probe] |
| Graphify CLI | Active install/source probe | Yes | `graphifyy` 0.7.9; source `/Users/mase/Codebase/Personal-Projects/graphify` | Reinstall from checkout if doctor fails. [VERIFIED: terminal probe] [CITED: AGENTS.md] |
| uv | Test/dependency workflow | Yes | 0.9.28 | Use active tool install for CLI-only probes; sync before tests if pytest missing. [VERIFIED: terminal probe] |
| pytest | Harness tests | No via `uv run pytest --version` before remediation | Not available in current uv environment | Declare pytest as a dev dependency and run `uv sync --group dev` before validation. [VERIFIED: terminal probe] |
| Ollama CLI/service | Ollama readiness | Yes | CLI responded; models listed include `gemma4:31b` | If CLI unavailable, use HTTP `/api/tags` through `graphify.llm._ollama_tags_url`. [VERIFIED: terminal probe] [VERIFIED: graphify/llm.py] |
| Target Second Brain repo | Acceptance target | Yes | `main...origin/main [ahead 4]`, dirty/untracked files present | If unavailable, run harness against tmp fixture only and mark acceptance blocked. [VERIFIED: terminal probe] |

**Missing dependencies with no fallback:**
- None for read-only status probes. [VERIFIED: terminal probe] [ASSUMED]

**Missing dependencies with fallback:**
- `pytest` is missing from the current uv run path; Plan 01 resolves this by declaring pytest as a dev dependency, updating `uv.lock`, and running `uv sync --group dev` before test execution. [VERIFIED: terminal probe]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | Harness should not authenticate to external services; Ollama readiness must not require API keys. [CITED: .planning/REQUIREMENTS.md] |
| V3 Session Management | No | No sessions are created. [ASSUMED] |
| V4 Access Control | Yes | Restrict target paths to explicit profile/root arguments; do not broad-scan `/Users/mase/Codebase`. [CITED: /Users/mase/.codex/docs/reference/graphify.md] |
| V5 Input Validation | Yes | Resolve paths, require existing directories, prevent report writes under target repo for Phase 1. [ASSUMED] |
| V6 Cryptography | No | No cryptographic operations are required. [ASSUMED] |
| V10 Malicious Code | Yes | Do not execute target repo code or Git hooks; run only read-only git/filesystem/Ollama probes. [ASSUMED] |
| V12 File and Resources | Yes | Use bounded report output and avoid reading/exposing secrets/private data. [CITED: AGENTS.md] |

### Known Threat Patterns for Python CLI Status Harness

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Target repo mutation during status | Tampering | Keep all writes under harness report dir; verify pre/post target git status in acceptance. [CITED: .planning/ROADMAP.md] |
| Secret leakage in reports | Information Disclosure | Report paths/counts/status only; do not include file contents, env var values, tokens, or database content. [CITED: AGENTS.md] |
| Non-loopback Ollama endpoint | Information Disclosure | Surface `OLLAMA_BASE_URL` risk; Graphify currently warns but does not fail for non-loopback endpoints. [VERIFIED: graphify/llm.py] [VERIFIED: .planning/codebase/CONCERNS.md] |
| Hook execution by accident | Elevation/Tampering | Inspect hook marker files; do not invoke `.git/hooks/*` or `graphify update/extract`. [VERIFIED: graphify/hooks.py] |
| Broad workspace scan | Information Disclosure | Require explicit target path/profile and avoid recursive workspace discovery. [CITED: /Users/mase/.codex/docs/reference/graphify.md] |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md` - project-specific fork, install, skill sync, GSD, and validation rules. [CITED: AGENTS.md]
- `.planning/phases/01-read-only-status-harness/01-CONTEXT.md` - locked Phase 1 decisions and deferred scope. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md]
- `.planning/REQUIREMENTS.md` - Phase 1 requirement IDs and traceability. [CITED: .planning/REQUIREMENTS.md]
- `.planning/ROADMAP.md` - Phase 1 goal and success criteria. [CITED: .planning/ROADMAP.md]
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/TESTING.md`, `.planning/codebase/CONCERNS.md` - repo architecture, likely file homes, test patterns, risks. [CITED: .planning/codebase/*.md]
- `docs/mase-fork-operating-model.md` - fork/source/skill sync and Codex hook reality. [CITED: docs/mase-fork-operating-model.md]
- `/Users/mase/.codex/docs/reference/graphify.md` - global Graphify operating guide. [CITED: /Users/mase/.codex/docs/reference/graphify.md]
- `graphify/__main__.py`, `graphify/detect.py`, `graphify/hooks.py`, `graphify/watch.py`, `graphify/export.py`, `graphify/llm.py` - implementation source for probes. [VERIFIED: codebase grep]
- `tests/test_ollama.py`, `tests/test_hooks.py`, `tests/test_watch.py`, `tests/test_install.py`, `tests/test_incremental.py` - existing test patterns and contracts. [VERIFIED: codebase grep]

### Secondary (MEDIUM confidence)

- Read-only terminal probes run on 2026-05-11 for active CLI, target repo state, target graph metadata, manifest/path coverage, and Ollama model list. [VERIFIED: terminal probe]

### Tertiary (LOW confidence)

- No external web sources were needed; Phase 1 uses local project code, docs, and installed CLI behavior. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new external dependencies; all core pieces are local stdlib, existing Graphify modules, Git, and Ollama probes. [VERIFIED: pyproject.toml] [VERIFIED: terminal probe]
- Architecture: HIGH - phase constraints and codebase maps strongly indicate a private helper module plus internal script, not a public CLI command. [CITED: .planning/phases/01-read-only-status-harness/01-CONTEXT.md] [VERIFIED: .planning/codebase/STRUCTURE.md]
- Pitfalls: HIGH - risks are documented in project concerns and verified against current code paths. [VERIFIED: .planning/codebase/CONCERNS.md] [VERIFIED: codebase grep]
- Runtime target baseline: MEDIUM - current Second Brain state was probed read-only on 2026-05-11, but it is an active repo and can change at any time. [VERIFIED: terminal probe]

**Research date:** 2026-05-11
**Valid until:** 2026-05-18 for target repo baseline; 2026-06-10 for stable code architecture unless Graphify is rebased or dependencies change.
