"""Small semantic-model quality harness for Graphify outputs.

The harness is intentionally lightweight:

- ``run`` copies a fixture corpus into an output directory, runs the backend
  Graphify pipeline, and writes a quality report.
- ``score`` evaluates an existing ``graphify-out/`` directory against an
  expected-contract JSON file.

It is not a benchmark suite. It gives repeatable smoke-quality signals for
choosing a semantic extraction model.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from graphify import llm


SCORER_VERSION = 3
SCORER_V1_VERSION = 1

_WORD_RE = re.compile(r"[a-z0-9]+")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _norm(text: str) -> str:
    prepared = _CAMEL_BOUNDARY_RE.sub(" ", text)
    return " ".join(_WORD_RE.findall(prepared.lower()))


def _fold_plural_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _comparison_norm(text: str) -> str:
    return " ".join(_fold_plural_token(token) for token in _norm(text).split())


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"failed to load JSON from {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _paths_sha256(paths: list[Path], *, root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            relative = Path("__external__") / path.name
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _corpus_sha256(corpus: Path) -> str:
    paths = [
        path
        for path in corpus.rglob("*")
        if path.is_file()
        and path.name != "expected.json"
        and "graphify-out" not in path.relative_to(corpus).parts
    ]
    return _paths_sha256(paths, root=corpus)


def _suite_contract_sha256(suite_path: Path, suite: dict[str, Any]) -> str:
    paths = [suite_path, *(fixture["expected_path"] for fixture in suite["fixtures"])]
    return _paths_sha256(paths, root=suite_path.parent)


def _suite_corpus_sha256(suite_path: Path, suite: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for fixture in suite["fixtures"]:
        digest.update(fixture["id"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(_corpus_sha256(fixture["corpus_path"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _extraction_prompt_sha256() -> str:
    return hashlib.sha256(llm._extraction_system(deep=False).encode("utf-8")).hexdigest()


def _git_evidence() -> dict[str, Any]:
    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

    head = _git("rev-parse", "HEAD")
    status = _git("status", "--short")
    unstaged = _git("diff", "--no-ext-diff", "--binary")
    staged = _git("diff", "--cached", "--no-ext-diff", "--binary")
    untracked = _git("ls-files", "--others", "--exclude-standard", "-z")
    commands = (head, status, unstaged, staged, untracked)
    if any(command.returncode != 0 for command in commands):
        return {"available": False}

    digest = hashlib.sha256()
    for payload in (status.stdout, unstaged.stdout, staged.stdout):
        digest.update(payload.encode("utf-8"))
        digest.update(b"\0")
    for relative in sorted(path for path in untracked.stdout.split("\0") if path):
        path = Path.cwd() / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "available": True,
        "head": head.stdout.strip(),
        "dirty": bool(status.stdout.strip()),
        "diff_sha256": digest.hexdigest(),
    }


def _evaluation_operational_config(
    *, backend: str, model: str, timeout: int, token_budget: int
) -> dict[str, Any]:
    env_names = (
        "GRAPHIFY_DISABLE_THINKING",
        "GRAPHIFY_LLM_TEMPERATURE",
        "GRAPHIFY_MAX_OUTPUT_TOKENS",
        "GRAPHIFY_MAX_RETRIES",
        "GRAPHIFY_NO_INCREMENTAL_CACHE",
        "GRAPHIFY_OLLAMA_KEEP_ALIVE",
        "GRAPHIFY_OLLAMA_NUM_CTX",
        "GRAPHIFY_OLLAMA_PARALLEL",
        "GRAPHIFY_OLLAMA_REASONING_EFFORT",
        "GRAPHIFY_OLLAMA_VISION",
        "GRAPHIFY_SEMANTIC_EVAL_THINKING_LEVEL",
        "GRAPHIFY_SEMANTIC_EVAL_TRANSPORT",
        "GRAPHIFY_SEMANTIC_EVAL_VISION_MODE",
    )
    endpoint = ""
    backend_config = llm.BACKENDS.get(backend, {})
    if backend == "ollama":
        endpoint = llm._resolve_ollama_base_url(str(backend_config.get("base_url") or ""))
    elif backend_config.get("base_url"):
        endpoint = str(backend_config["base_url"])
    return {
        "backend": backend,
        "model": model,
        "timeout_seconds": timeout,
        "token_budget": token_budget,
        "endpoint_sha256": hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
        if endpoint
        else None,
        "environment": {name: os.environ[name] for name in env_names if name in os.environ},
    }


def _safe_rmtree(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return


def _safe_name(value: str) -> str:
    """Return a filesystem-safe, readable identifier for model/fixture names."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unnamed"


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_loads_or_none(raw: str) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _as_weight(value: Any, *, default: float = 1.0) -> float:
    weight = _as_float(value, default=default)
    return weight if weight > 0 else default


def _concept_spec(item: Any) -> dict[str, Any]:
    """Normalize concept specs from expected.json.

    Backward-compatible form: ``"Billing Service"``.
    Rich form: ``{"name": "Billing Service", "aliases": [...], "weight": 2}``.
    """
    if isinstance(item, str):
        return {"name": item, "aliases": [], "weight": 1.0}
    if isinstance(item, dict):
        name = str(item.get("name") or item.get("label") or item.get("concept") or "").strip()
        aliases = item.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        return {
            "name": name,
            "aliases": [str(a) for a in aliases if str(a).strip()],
            "weight": _as_weight(item.get("weight")),
        }
    return {"name": str(item), "aliases": [], "weight": 1.0}


def _concept_specs(items: list[Any]) -> list[dict[str, Any]]:
    return [spec for spec in (_concept_spec(item) for item in items) if spec["name"]]


def _concept_spec_with_required_aliases(
    item: Any, required_specs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Add aliases declared by the matching required-concept contract."""
    spec = _concept_spec(item)
    spec_norms = {_comparison_norm(value) for value in [spec["name"], *spec["aliases"]] if value}
    matches = []
    for required in required_specs:
        required_values = [required["name"], *required["aliases"]]
        required_norms = {_comparison_norm(value) for value in required_values if value}
        if spec_norms.intersection(required_norms):
            matches.append(required)
    if len(matches) != 1:
        return spec

    alias_owner_counts: dict[str, int] = {}
    for required in required_specs:
        owner_norms = {
            _comparison_norm(value)
            for value in [required["name"], *required["aliases"]]
            if _comparison_norm(value)
        }
        for normalized in owner_norms:
            alias_owner_counts[normalized] = alias_owner_counts.get(normalized, 0) + 1

    aliases = list(spec["aliases"])
    required_values = [matches[0]["name"], *matches[0]["aliases"]]
    seen = {_comparison_norm(spec["name"]), *(_comparison_norm(value) for value in aliases)}
    for value in required_values:
        normalized = _comparison_norm(value)
        if normalized and normalized not in seen and alias_owner_counts.get(normalized) == 1:
            aliases.append(value)
            seen.add(normalized)
    return {**spec, "aliases": aliases}


def _edge_specs_with_required_aliases(
    edges: list[dict[str, Any]], required_specs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply fixture-wide required-concept aliases to edge endpoints."""
    return [
        {
            **edge,
            "source": _concept_spec_with_required_aliases(edge.get("source", ""), required_specs),
            "target": _concept_spec_with_required_aliases(edge.get("target", ""), required_specs),
        }
        for edge in edges
    ]


def _concept_norms(spec: dict[str, Any]) -> set[str]:
    return {
        _comparison_norm(v) for v in [spec["name"], *spec.get("aliases", [])] if _comparison_norm(v)
    }


def _node_norms(node: dict[str, Any]) -> set[str]:
    values = [node.get("label", ""), str(node.get("id", "")).replace("_", " ")]
    return {_comparison_norm(v) for v in values if _comparison_norm(v)}


def _diagnostic_node_norms(node: dict[str, Any]) -> set[str]:
    label_norm = _norm(str(node.get("label", "")))
    if label_norm:
        return {label_norm}
    return _node_norms(node)


def _matching_nodes(nodes: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = _concept_norms(spec)
    return [node for node in nodes if _node_norms(node) & wanted]


def _token_overlap_score(expected: str, candidate: str) -> float:
    expected_tokens = set(_comparison_norm(expected).split())
    candidate_tokens = set(_comparison_norm(candidate).split())
    if not expected_tokens or not candidate_tokens:
        return 0.0
    overlap = len(expected_tokens & candidate_tokens)
    return (2 * overlap) / (len(expected_tokens) + len(candidate_tokens))


def _near_match_score(expected: str, candidate: str) -> float:
    if not expected or not candidate:
        return 0.0
    min_token_count = min(len(expected.split()), len(candidate.split()))
    containment = (
        0.9 if min_token_count >= 2 and (expected in candidate or candidate in expected) else 0.0
    )
    lexical = difflib.SequenceMatcher(a=expected, b=candidate).ratio()
    return round(max(containment, lexical, _token_overlap_score(expected, candidate)), 3)


def _near_concept_matches(
    nodes: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    limit: int = 3,
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Return close-but-not-exact node-label matches for a required concept.

    These diagnostics do not affect scoring. They exist to show where a fixture
    likely needs a conservative alias or where the model used a related but
    non-equivalent label.
    """
    wanted = _concept_norms(spec)
    candidates: dict[str, dict[str, Any]] = {}
    for node in nodes:
        best_expected = ""
        best_candidate = ""
        best_score = 0.0
        for expected_norm in sorted(wanted):
            for node_norm in sorted(_diagnostic_node_norms(node)):
                score = _near_match_score(expected_norm, node_norm)
                if score > best_score:
                    best_expected = expected_norm
                    best_candidate = node_norm
                    best_score = score
        if best_score < threshold:
            continue
        node_id = str(node.get("id", ""))
        current = candidates.get(node_id)
        if current and _as_float(current["similarity"]) >= best_score:
            continue
        candidates[node_id] = {
            "id": node.get("id"),
            "label": node.get("label"),
            "source_file": node.get("source_file"),
            "similarity": best_score,
            "expected_norm": best_expected,
            "candidate_norm": best_candidate,
        }
    return sorted(
        candidates.values(), key=lambda item: _as_float(item["similarity"]), reverse=True
    )[:limit]


def _weighted_score(hits: list[tuple[bool, float]]) -> float | None:
    if not hits:
        return None
    total = sum(weight for _, weight in hits)
    if not total:
        return None
    return round(sum(weight for ok, weight in hits if ok) / total, 3)


def _copy_corpus(src: Path, dst: Path) -> None:
    if dst.exists():
        _safe_rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {"graphify-out", "expected.json"}
        return {n for n in names if n in ignored or n.startswith(".")}

    shutil.copytree(src, dst, ignore=ignore)


def _run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _community_label_hits(labels: dict[str, str], expected: list[list[str]]) -> dict[str, Any]:
    label_text = "\n".join(str(v).lower() for v in labels.values())
    hits: list[str] = []
    misses: list[list[str]] = []
    for group in expected:
        if any(term.lower() in label_text for term in group):
            hits.append(" / ".join(group))
        else:
            misses.append(group)
    total = len(expected)
    return {
        "score": round(len(hits) / total, 3) if total else None,
        "hits": hits,
        "misses": misses,
    }


def _relation_specificity(
    links: list[dict[str, Any]], generic_relations: set[str]
) -> dict[str, Any]:
    if not links:
        return {"score": 0.0, "generic": 0, "total": 0}
    generic = sum(1 for e in links if str(e.get("relation", "")).lower() in generic_relations)
    return {
        "score": round((len(links) - generic) / len(links), 3),
        "generic": generic,
        "total": len(links),
    }


def _edge_matches(
    edge: dict[str, Any],
    *,
    source_ids: set[str],
    target_ids: set[str],
    relation_terms: list[str],
    directed: bool,
    respect_relation_polarity: bool = False,
) -> bool:
    source = str(edge.get("source", ""))
    target = str(edge.get("target", ""))
    endpoints_match = source in source_ids and target in target_ids
    if not directed:
        endpoints_match = endpoints_match or (source in target_ids and target in source_ids)
    if not endpoints_match:
        return False
    return _edge_relation_matches(edge, relation_terms, respect_polarity=respect_relation_polarity)


def _relation_is_explicitly_negative(value: str) -> bool:
    tokens = _norm(value).split()
    if not tokens:
        return False
    if tokens[0] in {
        "avoid",
        "avoids",
        "cannot",
        "forbid",
        "forbids",
        "never",
        "no",
        "not",
        "prevent",
        "prevents",
        "prohibit",
        "prohibits",
        "without",
    }:
        return True
    return "not" in tokens[:3] and tokens[0] in {
        "are",
        "can",
        "did",
        "do",
        "does",
        "is",
        "must",
        "should",
        "was",
        "were",
        "will",
    }


def _contains_token_phrase(tokens: list[str], phrase: list[str]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    return any(
        tokens[index : index + len(phrase)] == phrase
        for index in range(len(tokens) - len(phrase) + 1)
    )


def _relation_matches_required_polarity(edge: dict[str, Any], required: str | None) -> bool:
    if required is None:
        return True
    if required not in {"negative", "positive"}:
        raise ValueError(f"unsupported expected-edge polarity: {required!r}")
    is_negative = _relation_is_explicitly_negative(str(edge.get("relation", "")))
    return is_negative if required == "negative" else not is_negative


def _edge_relation_matches(
    edge: dict[str, Any], relation_terms: list[str], *, respect_polarity: bool = False
) -> bool:
    if not relation_terms:
        return True
    relation = _comparison_norm(str(edge.get("relation", "")))
    relation_tokens = relation.split()
    relation_is_negative = _relation_is_explicitly_negative(str(edge.get("relation", "")))
    for term in relation_terms:
        normalized_term = _comparison_norm(term)
        if not normalized_term or not _contains_token_phrase(
            relation_tokens, normalized_term.split()
        ):
            continue
        if respect_polarity and relation_is_negative and not _relation_is_explicitly_negative(term):
            continue
        return True
    return False


def _edge_endpoint_matches(
    edge: dict[str, Any],
    *,
    source_ids: set[str],
    target_ids: set[str],
    directed: bool,
) -> bool:
    source = str(edge.get("source", ""))
    target = str(edge.get("target", ""))
    endpoints_match = source in source_ids and target in target_ids
    if not directed:
        endpoints_match = endpoints_match or (source in target_ids and target in source_ids)
    return endpoints_match


def _node_brief(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "label": node.get("label"),
        "source_file": node.get("source_file"),
    }


def _edge_brief(edge: dict[str, Any], node_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_id = str(edge.get("source", ""))
    target_id = str(edge.get("target", ""))
    source_node = node_by_id.get(source_id, {})
    target_node = node_by_id.get(target_id, {})
    return {
        "source": source_id,
        "source_label": source_node.get("label"),
        "target": target_id,
        "target_label": target_node.get("label"),
        "relation": edge.get("relation"),
        "confidence": edge.get("confidence"),
        "source_file": edge.get("source_file"),
    }


def _neighbor_edges(
    links: list[dict[str, Any]],
    node_ids: set[str],
    node_by_id: dict[str, dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    neighbors = [
        _edge_brief(edge, node_by_id)
        for edge in links
        if str(edge.get("source", "")) in node_ids or str(edge.get("target", "")) in node_ids
    ]
    return neighbors[:limit]


def _expected_edge_diagnostic(
    nodes: list[dict[str, Any]],
    links: list[dict[str, Any]],
    *,
    source_spec: dict[str, Any],
    target_spec: dict[str, Any],
    relation_terms: list[str],
    directed: bool,
    required_polarity: str | None = None,
) -> dict[str, Any]:
    node_by_id = {str(node.get("id", "")): node for node in nodes}
    source_matches = _matching_nodes(nodes, source_spec)
    target_matches = _matching_nodes(nodes, target_spec)
    source_ids = {str(n.get("id")) for n in source_matches}
    target_ids = {str(n.get("id")) for n in target_matches}
    diagnostic: dict[str, Any] = {
        "source": source_spec["name"],
        "target": target_spec["name"],
        "relation_terms": relation_terms,
        "directed": directed,
        "source_found": bool(source_ids),
        "target_found": bool(target_ids),
        "source_matches": [_node_brief(node) for node in source_matches[:3]],
        "target_matches": [_node_brief(node) for node in target_matches[:3]],
    }
    if not source_ids:
        diagnostic["source_near_matches"] = _near_concept_matches(nodes, source_spec)
    if not target_ids:
        diagnostic["target_near_matches"] = _near_concept_matches(nodes, target_spec)
    if not source_ids and not target_ids:
        diagnostic["failure_reason"] = "endpoint_miss"
        diagnostic["endpoint_miss"] = "both"
        return diagnostic
    if not source_ids:
        diagnostic["failure_reason"] = "endpoint_miss"
        diagnostic["endpoint_miss"] = "source"
        diagnostic["target_neighbor_edges"] = _neighbor_edges(links, target_ids, node_by_id)
        return diagnostic
    if not target_ids:
        diagnostic["failure_reason"] = "endpoint_miss"
        diagnostic["endpoint_miss"] = "target"
        diagnostic["source_neighbor_edges"] = _neighbor_edges(links, source_ids, node_by_id)
        return diagnostic

    endpoint_edges = [
        edge
        for edge in links
        if _edge_endpoint_matches(
            edge,
            source_ids=source_ids,
            target_ids=target_ids,
            directed=directed,
        )
    ]
    if (
        required_polarity
        and endpoint_edges
        and not any(
            _relation_matches_required_polarity(edge, required_polarity) for edge in endpoint_edges
        )
    ):
        diagnostic["failure_reason"] = "polarity_mismatch"
        diagnostic["required_polarity"] = required_polarity
        diagnostic["candidate_edges"] = [
            _edge_brief(edge, node_by_id) for edge in endpoint_edges[:3]
        ]
        return diagnostic
    if endpoint_edges:
        diagnostic["failure_reason"] = "relation_mismatch"
        diagnostic["candidate_edges"] = [
            _edge_brief(edge, node_by_id) for edge in endpoint_edges[:3]
        ]
        return diagnostic

    diagnostic["failure_reason"] = "edge_miss"
    diagnostic["source_neighbor_edges"] = _neighbor_edges(links, source_ids, node_by_id)
    diagnostic["target_neighbor_edges"] = _neighbor_edges(links, target_ids, node_by_id)
    return diagnostic


def _expected_edge_coverage(
    nodes: list[dict[str, Any]],
    links: list[dict[str, Any]],
    expected_edges: list[dict[str, Any]],
    *,
    default_directed: bool = False,
) -> dict[str, Any]:
    checks: list[tuple[bool, float]] = []
    relation_checks: list[tuple[bool, float]] = []
    missing: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    relation_mismatches: list[dict[str, Any]] = []
    for spec in expected_edges:
        source_spec = _concept_spec(spec.get("source", ""))
        target_spec = _concept_spec(spec.get("target", ""))
        source_ids = {str(n.get("id")) for n in _matching_nodes(nodes, source_spec)}
        target_ids = {str(n.get("id")) for n in _matching_nodes(nodes, target_spec)}
        relation_terms = spec.get("relation_terms") or spec.get("relations") or []
        if isinstance(relation_terms, str):
            relation_terms = [relation_terms]
        normalized_relation_terms = [str(term) for term in relation_terms]
        directed = bool(spec.get("directed", default_directed))
        required_polarity = spec.get("polarity")
        if required_polarity is not None:
            required_polarity = str(required_polarity).strip().lower()
        weight = _as_weight(spec.get("weight"))
        endpoint_edges = [
            edge
            for edge in links
            if _edge_endpoint_matches(
                edge,
                source_ids=source_ids,
                target_ids=target_ids,
                directed=directed,
            )
            and _relation_matches_required_polarity(edge, required_polarity)
        ]
        endpoint_ok = bool(source_ids and target_ids and endpoint_edges)
        checks.append((endpoint_ok, weight))
        relation_ok = any(
            _edge_relation_matches(
                edge,
                normalized_relation_terms,
                respect_polarity=required_polarity is not None,
            )
            for edge in endpoint_edges
        )
        if endpoint_ok and normalized_relation_terms:
            relation_checks.append((relation_ok, weight))
        if not endpoint_ok or (normalized_relation_terms and not relation_ok):
            diagnostic = _expected_edge_diagnostic(
                nodes,
                links,
                source_spec=source_spec,
                target_spec=target_spec,
                relation_terms=normalized_relation_terms,
                directed=directed,
                required_polarity=required_polarity,
            )
            diagnostics.append(diagnostic)
        if not endpoint_ok:
            missing.append(
                {
                    "source": source_spec["name"],
                    "target": target_spec["name"],
                    "relation_terms": normalized_relation_terms,
                }
            )
        elif normalized_relation_terms and not relation_ok:
            relation_mismatches.append(
                {
                    "source": source_spec["name"],
                    "target": target_spec["name"],
                    "relation_terms": normalized_relation_terms,
                    "candidate_relations": [
                        str(edge.get("relation", ""))
                        for edge in endpoint_edges
                        if edge.get("relation")
                    ],
                }
            )
    return {
        "score": _weighted_score(checks),
        "relation_agreement": _weighted_score(relation_checks),
        "missing": missing,
        "relation_mismatches": relation_mismatches,
        "diagnostics": diagnostics,
        "total": len(expected_edges),
        "relation_total": len(relation_checks),
    }


def _forbidden_edge_absence(
    nodes: list[dict[str, Any]], links: list[dict[str, Any]], forbidden_edges: list[dict[str, Any]]
) -> dict[str, Any]:
    if not forbidden_edges:
        return {"score": None, "hits": [], "total": 0}
    hits: list[dict[str, Any]] = []
    for spec in forbidden_edges:
        source_spec = _concept_spec(spec.get("source", ""))
        target_spec = _concept_spec(spec.get("target", ""))
        source_ids = {str(n.get("id")) for n in _matching_nodes(nodes, source_spec)}
        target_ids = {str(n.get("id")) for n in _matching_nodes(nodes, target_spec)}
        relation_terms = spec.get("relation_terms") or spec.get("relations") or []
        if isinstance(relation_terms, str):
            relation_terms = [relation_terms]
        directed = bool(spec.get("directed", False))
        if source_ids and target_ids:
            matches = [
                edge
                for edge in links
                if _edge_matches(
                    edge,
                    source_ids=source_ids,
                    target_ids=target_ids,
                    relation_terms=[str(term) for term in relation_terms],
                    directed=directed,
                    respect_relation_polarity=True,
                )
            ]
            for edge in matches:
                hits.append(
                    {
                        "source": source_spec["name"],
                        "target": target_spec["name"],
                        "relation": edge.get("relation"),
                    }
                )
    return {
        "score": round(max(0, len(forbidden_edges) - len(hits)) / len(forbidden_edges), 3),
        "hits": hits,
        "total": len(forbidden_edges),
    }


def _source_coverage(
    nodes: list[dict[str, Any]], links: list[dict[str, Any]], expected_files: list[str]
) -> dict[str, Any]:
    if not expected_files:
        return {"score": None, "missing": [], "total": 0}
    seen: set[str] = set()
    for item in [*nodes, *links]:
        source = str(item.get("source_file", "")).replace("\\", "/")
        if source:
            seen.add(source)
    missing = []
    for expected_file in expected_files:
        wanted = str(expected_file).replace("\\", "/")
        if not any(source == wanted or source.endswith("/" + wanted) for source in seen):
            missing.append(expected_file)
    return {
        "score": round((len(expected_files) - len(missing)) / len(expected_files), 3),
        "missing": missing,
        "total": len(expected_files),
    }


def score_graph(
    graph_path: Path, expected_path: Path, *, labels_path: Path | None = None
) -> dict[str, Any]:
    graph = _load_json(graph_path)
    expected = _load_json(expected_path)
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    labels = _load_json(labels_path) if labels_path and labels_path.exists() else {}

    required_specs = _concept_specs(expected.get("required_concepts", []))
    found_required: list[str] = []
    missing_required: list[str] = []
    concept_checks: list[tuple[bool, float]] = []
    for spec in required_specs:
        found = bool(_matching_nodes(nodes, spec))
        concept_checks.append((found, spec["weight"]))
        (found_required if found else missing_required).append(_norm(spec["name"]))
    missing_required_diagnostics = [
        {
            "concept": _norm(spec["name"]),
            "name": spec["name"],
            "aliases": spec.get("aliases", []),
            "near_matches": _near_concept_matches(nodes, spec),
        }
        for spec in required_specs
        if not _matching_nodes(nodes, spec)
    ]

    duplicate_specs = _concept_specs(expected.get("dedup_watchlist", []))
    duplicate_hits = {}
    for spec in duplicate_specs:
        matches = _matching_nodes(nodes, spec)
        if len(matches) > 1:
            duplicate_hits[_norm(spec["name"])] = [
                {
                    "id": n.get("id"),
                    "label": n.get("label"),
                    "source_file": n.get("source_file"),
                }
                for n in matches
            ]

    inferred_edges = [e for e in links if str(e.get("confidence", "")).upper() == "INFERRED"]
    overconfident_inferred = [
        {
            "source": e.get("source"),
            "target": e.get("target"),
            "relation": e.get("relation"),
            "confidence_score": e.get("confidence_score"),
        }
        for e in inferred_edges
        if _as_float(e.get("confidence_score", 0) or 0) >= 1.0
    ]

    forbidden_specs = _concept_specs(expected.get("forbidden_concepts", []))
    forbidden_hits = {
        _norm(spec["name"]): [
            {"id": n.get("id"), "label": n.get("label"), "source_file": n.get("source_file")}
            for n in _matching_nodes(nodes, spec)
        ]
        for spec in forbidden_specs
        if _matching_nodes(nodes, spec)
    }

    expected_edges = _edge_specs_with_required_aliases(
        expected.get("expected_edges", []), required_specs
    )
    edge_coverage = (
        _expected_edge_coverage(
            nodes,
            links,
            expected_edges,
            default_directed=bool(expected.get("expected_edges_directed", False)),
        )
        if expected_edges
        else {
            "score": None,
            "relation_agreement": None,
            "missing": [],
            "relation_mismatches": [],
            "diagnostics": [],
            "total": 0,
            "relation_total": 0,
        }
    )
    forbidden_edge_specs = _edge_specs_with_required_aliases(
        expected.get("forbidden_edges", []), required_specs
    )
    forbidden_edges = _forbidden_edge_absence(nodes, links, forbidden_edge_specs)
    source_coverage = _source_coverage(nodes, links, expected.get("expected_source_files", []))

    generic_relations = {str(r).lower() for r in expected.get("generic_relations", ["references"])}
    relation_specificity = _relation_specificity(links, generic_relations)
    community_labels = _community_label_hits(
        labels, expected.get("expected_community_label_terms", [])
    )

    concept_recall = _weighted_score(concept_checks)
    dedup_score = (
        round((len(duplicate_specs) - len(duplicate_hits)) / len(duplicate_specs), 3)
        if duplicate_specs
        else None
    )
    inferred_confidence_score = (
        round((len(inferred_edges) - len(overconfident_inferred)) / len(inferred_edges), 3)
        if inferred_edges
        else None
    )
    forbidden_score = (0.0 if forbidden_hits else 1.0) if forbidden_specs else None

    scores = {
        "concept_recall": concept_recall,
        "deduplication": dedup_score,
        "community_labels": community_labels["score"],
        "relation_specificity": relation_specificity["score"],
        "inferred_confidence_calibration": inferred_confidence_score,
        "expected_edge_coverage": edge_coverage["score"],
        "expected_edge_relation_agreement": edge_coverage["relation_agreement"],
        "forbidden_concepts_absent": forbidden_score,
        "forbidden_edges_absent": forbidden_edges["score"],
        "source_coverage": source_coverage["score"],
    }
    score_weights = (
        expected.get("score_weights", {}) if isinstance(expected.get("score_weights"), dict) else {}
    )
    weighted_dimensions = [
        (value, _as_weight(score_weights.get(key)))
        for key, value in scores.items()
        if value is not None and key != "expected_edge_relation_agreement"
    ]
    if weighted_dimensions:
        scores["overall"] = round(
            sum(value * weight for value, weight in weighted_dimensions)
            / sum(weight for _, weight in weighted_dimensions),
            3,
        )
    else:
        scores["overall"] = None

    return {
        "scorer_version": SCORER_VERSION,
        "graph_path": str(graph_path),
        "expected_path": str(expected_path),
        "nodes": len(nodes),
        "edges": len(links),
        "scores": {
            "overall": scores["overall"],
            "concept_recall": concept_recall,
            "deduplication": dedup_score,
            "community_labels": community_labels["score"],
            "relation_specificity": relation_specificity["score"],
            "inferred_confidence_calibration": inferred_confidence_score,
            "expected_edge_coverage": edge_coverage["score"],
            "expected_edge_relation_agreement": edge_coverage["relation_agreement"],
            "forbidden_concepts_absent": forbidden_score,
            "forbidden_edges_absent": forbidden_edges["score"],
            "source_coverage": source_coverage["score"],
        },
        "details": {
            "missing_required_concepts": missing_required,
            "missing_required_concept_diagnostics": missing_required_diagnostics,
            "found_required_concepts": found_required,
            "duplicate_watchlist_hits": duplicate_hits,
            "community_label_hits": community_labels["hits"],
            "community_label_misses": community_labels["misses"],
            "generic_relations": relation_specificity,
            "inferred_edges": len(inferred_edges),
            "overconfident_inferred_edges": overconfident_inferred,
            "missing_expected_edges": edge_coverage["missing"],
            "expected_edge_relation_mismatches": edge_coverage["relation_mismatches"],
            "missing_expected_edge_diagnostics": edge_coverage["diagnostics"],
            "forbidden_concept_hits": forbidden_hits,
            "forbidden_edge_hits": forbidden_edges["hits"],
            "missing_source_files": source_coverage["missing"],
        },
    }


def _markdown_report(
    result: dict[str, Any], *, backend: str | None = None, model: str | None = None
) -> str:
    scores = result["scores"]
    lines = [
        "# Graphify Semantic Model Evaluation",
        "",
    ]
    if backend or model:
        lines += [f"- Backend: `{backend or ''}`", f"- Model: `{model or ''}`", ""]
    lines += [
        f"- Nodes: {result['nodes']}",
        f"- Edges: {result['edges']}",
        f"- Overall score: {scores.get('overall')}",
        "",
        "## Scores",
        "",
        "| Dimension | Score |",
        "|---|---:|",
    ]
    for key, value in scores.items():
        lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
    details = result["details"]
    lines += [
        "",
        "## Findings",
        "",
        f"- Missing required concepts: {', '.join(details['missing_required_concepts']) or 'none'}",
        f"- Duplicate watchlist hits: {len(details['duplicate_watchlist_hits'])}",
        f"- Overconfident inferred edges: {len(details['overconfident_inferred_edges'])}",
        f"- Community label hits: {', '.join(details['community_label_hits']) or 'none'}",
    ]
    if details["community_label_misses"]:
        misses = [" / ".join(group) for group in details["community_label_misses"]]
        lines.append(f"- Community label misses: {', '.join(misses)}")
    diagnostics = details.get("missing_required_concept_diagnostics", [])
    if diagnostics:
        lines += ["", "## Missing Concept Diagnostics", ""]
        for item in diagnostics:
            matches = item.get("near_matches") or []
            if not matches:
                lines.append(f"- `{item['concept']}`: no close node labels found")
                continue
            rendered = ", ".join(
                f"`{match.get('label')}` ({match.get('similarity')})" for match in matches
            )
            lines.append(f"- `{item['concept']}`: {rendered}")
    edge_diagnostics = details.get("missing_expected_edge_diagnostics", [])
    if edge_diagnostics:
        lines += ["", "## Missing Edge Diagnostics", ""]
        for item in edge_diagnostics:
            reason = str(item.get("failure_reason", "missing"))
            source = item.get("source")
            target = item.get("target")
            lines.append(f"- `{source}` -> `{target}`: {reason.replace('_', ' ')}")
            candidate_edges = item.get("candidate_edges") or []
            if candidate_edges:
                rendered = ", ".join(
                    f"`{edge.get('source_label')}` -[{edge.get('relation')}]-> "
                    f"`{edge.get('target_label')}`"
                    for edge in candidate_edges
                )
                lines.append(f"  Candidate edges: {rendered}")
    return "\n".join(lines) + "\n"


def run_harness(
    corpus: Path,
    expected: Path,
    out_dir: Path,
    *,
    backend: str,
    model: str,
    timeout: int,
    token_budget: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(tempfile.mkdtemp(prefix="graphify-semantic-eval-"))
    run_root = tmp_root / "corpus"
    artifact_root = out_dir / "corpus"
    _copy_corpus(corpus, run_root)
    env = os.environ.copy()
    env.setdefault("OLLAMA_API_KEY", "ollama")
    env.setdefault("GRAPHIFY_LLM_TRACE", "1")
    evidence = {
        "expected_contract_sha256": _paths_sha256([expected], root=expected.parent),
        "corpus_sha256": _corpus_sha256(corpus),
        "extraction_prompt_sha256": _extraction_prompt_sha256(),
        "operational_config": _evaluation_operational_config(
            backend=backend,
            model=model,
            timeout=timeout,
            token_budget=token_budget,
        ),
        "git_state": _git_evidence(),
    }

    commands = [
        [
            sys.executable,
            "-m",
            "graphify",
            "extract",
            str(run_root),
            "--backend",
            backend,
            "--model",
            model,
            "--token-budget",
            str(token_budget),
            "--max-concurrency",
            "1",
            "--api-timeout",
            str(timeout),
        ],
        [
            sys.executable,
            "-m",
            "graphify",
            "cluster-only",
            str(run_root),
            "--backend",
            backend,
            "--model",
            model,
            "--no-viz",
        ],
        [
            sys.executable,
            "-m",
            "graphify",
            "export",
            "wiki",
            "--graph",
            str(run_root / "graphify-out" / "graph.json"),
            "--labels",
            str(run_root / "graphify-out" / ".graphify_labels.json"),
        ],
    ]

    command_results = []
    for cmd in commands:
        result = _run_cmd(cmd, cwd=Path.cwd(), env=env, timeout=timeout + 30)
        command_results.append(result)
        if result["returncode"] != 0:
            if artifact_root.exists():
                _safe_rmtree(artifact_root)
            shutil.copytree(run_root, artifact_root)
            summary = {
                "scorer_version": SCORER_VERSION,
                "backend": backend,
                "model": model,
                **evidence,
                "commands": command_results,
            }
            _write_json(out_dir / "run.json", summary)
            raise SystemExit(f"semantic eval command failed: {' '.join(cmd)}")

    if artifact_root.exists():
        _safe_rmtree(artifact_root)
    shutil.copytree(run_root, artifact_root)

    score = score_graph(
        artifact_root / "graphify-out" / "graph.json",
        expected,
        labels_path=artifact_root / "graphify-out" / ".graphify_labels.json",
    )
    summary = {
        "scorer_version": SCORER_VERSION,
        "backend": backend,
        "model": model,
        **evidence,
        "commands": command_results,
        "score": score,
    }
    _write_json(out_dir / "run.json", summary)
    (out_dir / "EVALUATION.md").write_text(
        _markdown_report(score, backend=backend, model=model),
        encoding="utf-8",
    )
    return summary


def _resolve_fixture_path(suite_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else suite_path.parent / path


def _load_suite(suite_path: Path) -> dict[str, Any]:
    suite = _load_json(suite_path)
    fixtures = suite.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError(f"suite {suite_path} must contain a non-empty 'fixtures' list")
    normalized = dict(suite)
    normalized["fixtures"] = []
    seen_ids: set[str] = set()
    seen_output_names: set[str] = set()
    for item in fixtures:
        if not isinstance(item, dict):
            raise ValueError("suite fixture entries must be objects")
        fixture_id = str(item.get("id") or "").strip()
        if not fixture_id:
            raise ValueError("suite fixture entry is missing 'id'")
        if fixture_id in seen_ids:
            raise ValueError(f"suite fixture id {fixture_id!r} is duplicated")
        seen_ids.add(fixture_id)
        output_name = _safe_name(fixture_id)
        if output_name in seen_output_names:
            raise ValueError(
                f"suite fixture id {fixture_id!r} collides on output name {output_name!r}"
            )
        seen_output_names.add(output_name)
        corpus_value = str(item.get("corpus") or "").strip()
        expected_value = str(item.get("expected") or "").strip()
        if not corpus_value:
            raise ValueError(f"suite fixture {fixture_id!r} is missing 'corpus'")
        if not expected_value:
            raise ValueError(f"suite fixture {fixture_id!r} is missing 'expected'")
        corpus = _resolve_fixture_path(suite_path, corpus_value)
        expected = _resolve_fixture_path(suite_path, expected_value)
        if not corpus.is_dir():
            raise FileNotFoundError(
                f"suite fixture {fixture_id!r} corpus directory not found: {corpus}"
            )
        if not expected.is_file():
            raise FileNotFoundError(
                f"suite fixture {fixture_id!r} expected file not found: {expected}"
            )
        normalized["fixtures"].append(
            {
                **item,
                "id": fixture_id,
                "corpus_path": corpus,
                "expected_path": expected,
                "weight": _as_weight(item.get("weight")),
            }
        )
    return normalized


def _sum_command_elapsed(commands: list[dict[str, Any]]) -> float:
    return round(sum(_as_float(cmd.get("elapsed_seconds", 0) or 0) for cmd in commands), 2)


def _token_counts(commands: list[dict[str, Any]]) -> dict[str, int]:
    text = "\n".join(
        str(cmd.get("stdout", "")) + "\n" + str(cmd.get("stderr", "")) for cmd in commands
    )
    matches = re.findall(r"tokens:\s*([0-9,]+)\s+in\s*/\s*([0-9,]+)\s+out", text)
    if not matches:
        return {"input": 0, "output": 0}
    input_tokens = sum(_as_int(i.replace(",", "")) for i, _ in matches)
    output_tokens = sum(_as_int(o.replace(",", "")) for _, o in matches)
    return {"input": input_tokens, "output": output_tokens}


def _weighted_average(values: list[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _, weight in values)
    if not values or not total_weight:
        return None
    return round(sum(value * weight for value, weight in values) / total_weight, 3)


_MULTIMODAL_PROFILES = {"multimodal", "image", "diagram", "vision"}


def _fixture_profiles(fixture: dict[str, Any]) -> list[str]:
    profiles = [str(profile) for profile in fixture.get("profiles", [])]
    if not (set(profiles) & _MULTIMODAL_PROFILES):
        profiles.append("text-only")
    return profiles


def _concept_near_miss_summary(score: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    details = score.get("details", {}) if isinstance(score.get("details"), dict) else {}
    diagnostics = details.get("missing_required_concept_diagnostics", [])
    if not isinstance(diagnostics, list):
        return []
    items: list[dict[str, Any]] = []
    for item in diagnostics:
        if not isinstance(item, dict):
            continue
        matches = item.get("near_matches")
        if not isinstance(matches, list) or not matches:
            continue
        top = matches[0]
        if not isinstance(top, dict):
            continue
        items.append(
            {
                "concept": item.get("concept"),
                "top_label": top.get("label"),
                "top_source_file": top.get("source_file"),
                "similarity": top.get("similarity"),
            }
        )
    return items[:limit]


def _expected_edge_failure_summary(
    score: dict[str, Any], *, limit: int = 5
) -> list[dict[str, Any]]:
    details = score.get("details", {}) if isinstance(score.get("details"), dict) else {}
    diagnostics = details.get("missing_expected_edge_diagnostics", [])
    if not isinstance(diagnostics, list):
        return []
    items: list[dict[str, Any]] = []
    for item in diagnostics:
        if not isinstance(item, dict):
            continue
        candidate_edges = item.get("candidate_edges")
        first_candidate = (
            candidate_edges[0] if isinstance(candidate_edges, list) and candidate_edges else {}
        )
        items.append(
            {
                "source": item.get("source"),
                "target": item.get("target"),
                "failure_reason": item.get("failure_reason"),
                "source_found": item.get("source_found"),
                "target_found": item.get("target_found"),
                "candidate_relation": first_candidate.get("relation")
                if isinstance(first_candidate, dict)
                else None,
            }
        )
    return items[:limit]


def _aggregate_suite(suite: dict[str, Any], fixture_runs: list[dict[str, Any]]) -> dict[str, Any]:
    dimension_values: dict[str, list[tuple[float, float]]] = {}
    profile_values: dict[str, list[tuple[float, float]]] = {}
    fixture_summaries: list[dict[str, Any]] = []
    fixture_by_id = {fixture["id"]: fixture for fixture in suite["fixtures"]}
    for run in fixture_runs:
        fixture = fixture_by_id[run["fixture_id"]]
        weight = _as_float(fixture["weight"])
        score = run.get("score", {})
        scores = score.get("scores", {})
        for key, value in scores.items():
            if value is not None:
                dimension_values.setdefault(key, []).append((_as_float(value), weight))
        if scores.get("overall") is not None:
            for profile in _fixture_profiles(fixture):
                profile_values.setdefault(profile, []).append(
                    (_as_float(scores["overall"]), weight)
                )
        tokens = _token_counts(run.get("commands", []))
        fixture_summaries.append(
            {
                "id": run["fixture_id"],
                "weight": weight,
                "profiles": _fixture_profiles(fixture),
                "overall": scores.get("overall"),
                "scores": scores,
                "concept_near_misses": _concept_near_miss_summary(score),
                "expected_edge_failures": _expected_edge_failure_summary(score),
                "elapsed_seconds": _sum_command_elapsed(run.get("commands", [])),
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "artifact_dir": run.get("artifact_dir"),
                "error": run.get("error"),
            }
        )
    aggregate_scores = {
        key: score
        for key, values in sorted(dimension_values.items())
        if (score := _weighted_average(values)) is not None
    }
    profile_scores = {
        key: score
        for key, values in sorted(profile_values.items())
        if (score := _weighted_average(values)) is not None
    }
    quality_gate = (
        suite.get("quality_gate", {}) if isinstance(suite.get("quality_gate"), dict) else {}
    )
    minimum_overall = quality_gate.get("minimum_overall")
    minimum_critical = quality_gate.get("minimum_critical_dimension")
    minimum_profiles = quality_gate.get("minimum_profile_scores", {})
    if not isinstance(minimum_profiles, dict):
        minimum_profiles = {}
    critical_dimensions = [str(d) for d in quality_gate.get("critical_dimensions", [])]
    fixture_failures = [
        {"id": fixture["id"], "error": fixture["error"]}
        for fixture in fixture_summaries
        if fixture.get("error")
    ]
    gate_failures: list[str] = []
    if fixture_failures:
        gate_failures.append(f"{len(fixture_failures)} fixture(s) failed")
    if not any(fixture.get("overall") is not None for fixture in fixture_summaries):
        gate_failures.append("no scored fixtures completed")
    if minimum_overall is not None:
        if aggregate_scores.get("overall") is None:
            gate_failures.append(f"overall score missing; minimum_overall {minimum_overall}")
        elif _as_float(aggregate_scores["overall"]) < _as_float(minimum_overall):
            gate_failures.append(
                f"overall {aggregate_scores['overall']} < minimum_overall {minimum_overall}"
            )
    if minimum_critical is not None:
        for dimension in critical_dimensions:
            value = aggregate_scores.get(dimension)
            if value is not None and _as_float(value) < _as_float(minimum_critical):
                gate_failures.append(
                    f"{dimension} {value} < minimum_critical_dimension {minimum_critical}"
                )
    for profile, minimum in sorted(minimum_profiles.items()):
        value = profile_scores.get(str(profile))
        if value is None:
            gate_failures.append(
                f"{profile} profile score missing; minimum_profile_score {minimum}"
            )
        elif _as_float(value) < _as_float(minimum):
            gate_failures.append(f"{profile} profile {value} < minimum_profile_score {minimum}")
    return {
        "scorer_version": SCORER_VERSION,
        "suite": suite.get("name", "semantic-eval-suite"),
        "fixtures": fixture_summaries,
        "scores": aggregate_scores,
        "total_elapsed_seconds": round(sum(f["elapsed_seconds"] for f in fixture_summaries), 2),
        "total_input_tokens": sum(f["input_tokens"] for f in fixture_summaries),
        "total_output_tokens": sum(f["output_tokens"] for f in fixture_summaries),
        "profile_scores": profile_scores,
        "quality_gate": quality_gate,
        "gate_passed": not gate_failures,
        "gate_failures": gate_failures,
        "failures": fixture_failures,
    }


def _suite_markdown(summary: dict[str, Any], *, backend: str, model: str) -> str:
    lines = [
        "# Graphify Semantic Model Suite Evaluation",
        "",
        f"- Backend: `{backend}`",
        f"- Model: `{model}`",
        f"- Suite: `{summary['suite']}`",
        f"- Weighted overall: {summary['scores'].get('overall')}",
        f"- Quality gate: {'pass' if summary.get('gate_passed') else 'fail'}",
        f"- Total elapsed: {summary['total_elapsed_seconds']}s",
        f"- Total tokens: {summary['total_input_tokens']:,} in / {summary['total_output_tokens']:,} out",
    ]
    if summary.get("failures") or summary.get("gate_failures"):
        lines += ["", "## Failures", ""]
        for failure in summary.get("failures", []):
            lines.append(f"- `{failure['id']}`: {failure['error']}")
        for failure in summary.get("gate_failures", []):
            lines.append(f"- quality gate: {failure}")
    lines += [
        "",
        "## Fixture Scores",
        "",
        "| Fixture | Weight | Overall | Elapsed | Status | Profiles |",
        "|---|---:|---:|---:|---|---|",
    ]
    for fixture in summary["fixtures"]:
        profiles = ", ".join(fixture.get("profiles", []))
        status = "failed" if fixture.get("error") else "ok"
        lines.append(
            f"| `{fixture['id']}` | {fixture['weight']} | {fixture['overall']} | "
            f"{fixture['elapsed_seconds']}s | {status} | {profiles} |"
        )
    lines += ["", "## Aggregate Dimensions", "", "| Dimension | Weighted Score |", "|---|---:|"]
    for key, value in summary["scores"].items():
        lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
    if summary.get("profile_scores"):
        lines += ["", "## Profile Scores", "", "| Profile | Weighted Overall |", "|---|---:|"]
        for key, value in summary["profile_scores"].items():
            lines.append(f"| `{key}` | {value} |")
    near_misses = [
        (fixture["id"], item)
        for fixture in summary["fixtures"]
        for item in fixture.get("concept_near_misses", [])
    ]
    if near_misses:
        lines += [
            "",
            "## Concept Near Matches",
            "",
            "| Fixture | Missing Concept | Closest Node | Similarity | Source |",
            "|---|---|---|---:|---|",
        ]
        for fixture_id, item in near_misses:
            lines.append(
                f"| `{fixture_id}` | `{item.get('concept')}` | `{item.get('top_label')}` | "
                f"{item.get('similarity')} | `{item.get('top_source_file')}` |"
            )
    edge_failures = [
        (fixture["id"], item)
        for fixture in summary["fixtures"]
        for item in fixture.get("expected_edge_failures", [])
    ]
    if edge_failures:
        lines += [
            "",
            "## Expected Edge Diagnostics",
            "",
            "| Fixture | Expected Edge | Failure | Endpoints Found | Candidate Relation |",
            "|---|---|---|---|---|",
        ]
        for fixture_id, item in edge_failures:
            endpoints = (
                f"{'yes' if item.get('source_found') else 'no'} / "
                f"{'yes' if item.get('target_found') else 'no'}"
            )
            lines.append(
                f"| `{fixture_id}` | `{item.get('source')}` -> `{item.get('target')}` | "
                f"{str(item.get('failure_reason')).replace('_', ' ')} | {endpoints} | "
                f"`{item.get('candidate_relation') or ''}` |"
            )
    return "\n".join(lines) + "\n"


def compare_suite_runs(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    baseline = _load_json(baseline_path)
    candidate = _load_json(candidate_path)
    baseline_scores = baseline.get("scores", {})
    candidate_scores = candidate.get("scores", {})
    baseline_scorer_version = baseline.get("scorer_version")
    candidate_scorer_version = candidate.get("scorer_version")
    warnings = []
    if baseline_scorer_version != candidate_scorer_version:
        warnings.append(
            "scorer_version mismatch: "
            f"baseline={baseline_scorer_version!r}, candidate={candidate_scorer_version!r}"
        )
    for key in (
        "suite_version",
        "suite_contract_sha256",
        "suite_corpus_sha256",
        "extraction_prompt_sha256",
    ):
        baseline_value = baseline.get(key)
        candidate_value = candidate.get(key)
        if baseline_value is None and candidate_value is None:
            continue
        if baseline_value != candidate_value:
            warnings.append(
                f"{key} mismatch: baseline={baseline_value!r}, candidate={candidate_value!r}"
            )
    dimensions = sorted(set(baseline_scores) | set(candidate_scores))
    score_deltas = {}
    for key in dimensions:
        b = baseline_scores.get(key)
        c = candidate_scores.get(key)
        score_deltas[key] = (
            None if b is None or c is None else round(_as_float(c) - _as_float(b), 3)
        )

    baseline_fixtures = {f.get("id"): f for f in baseline.get("fixtures", [])}
    candidate_fixtures = {f.get("id"): f for f in candidate.get("fixtures", [])}
    fixture_deltas = []
    for fixture_id in sorted(set(baseline_fixtures) | set(candidate_fixtures)):
        b = baseline_fixtures.get(fixture_id, {})
        c = candidate_fixtures.get(fixture_id, {})
        b_overall = b.get("overall")
        c_overall = c.get("overall")
        delta = (
            None
            if b_overall is None or c_overall is None
            else round(_as_float(c_overall) - _as_float(b_overall), 3)
        )
        fixture_deltas.append(
            {
                "id": fixture_id,
                "baseline_overall": b_overall,
                "candidate_overall": c_overall,
                "delta": delta,
                "baseline_error": b.get("error"),
                "candidate_error": c.get("error"),
            }
        )

    regressions = [f for f in fixture_deltas if f["delta"] is not None and f["delta"] < 0]
    improvements = [f for f in fixture_deltas if f["delta"] is not None and f["delta"] > 0]
    return {
        "scorer_version": SCORER_VERSION,
        "baseline": {
            "path": str(baseline_path),
            "backend": baseline.get("backend"),
            "model": baseline.get("model"),
            "overall": baseline_scores.get("overall"),
            "gate_passed": baseline.get("gate_passed"),
            "scorer_version": baseline_scorer_version,
            "suite_version": baseline.get("suite_version"),
            "suite_contract_sha256": baseline.get("suite_contract_sha256"),
            "suite_corpus_sha256": baseline.get("suite_corpus_sha256"),
            "extraction_prompt_sha256": baseline.get("extraction_prompt_sha256"),
        },
        "candidate": {
            "path": str(candidate_path),
            "backend": candidate.get("backend"),
            "model": candidate.get("model"),
            "overall": candidate_scores.get("overall"),
            "gate_passed": candidate.get("gate_passed"),
            "scorer_version": candidate_scorer_version,
            "suite_version": candidate.get("suite_version"),
            "suite_contract_sha256": candidate.get("suite_contract_sha256"),
            "suite_corpus_sha256": candidate.get("suite_corpus_sha256"),
            "extraction_prompt_sha256": candidate.get("extraction_prompt_sha256"),
        },
        "warnings": warnings,
        "score_deltas": score_deltas,
        "fixture_deltas": fixture_deltas,
        "regressions": regressions,
        "improvements": improvements,
    }


def _score_graph_v1_compat(
    graph_path: Path, expected_path: Path, *, labels_path: Path | None = None
) -> dict[str, Any]:
    """Score with the pre-v2 semantics for offline re-baseline comparisons."""

    def raw_norm(text: str) -> str:
        return " ".join(_WORD_RE.findall(text.lower()))

    def concept_norms(spec: dict[str, Any]) -> set[str]:
        return {raw_norm(v) for v in [spec["name"], *spec.get("aliases", [])] if raw_norm(v)}

    def node_norms(node: dict[str, Any]) -> set[str]:
        values = [node.get("label", ""), str(node.get("id", "")).replace("_", " ")]
        return {raw_norm(v) for v in values if raw_norm(v)}

    def matching_nodes(nodes: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
        wanted = concept_norms(spec)
        return [node for node in nodes if node_norms(node) & wanted]

    def edge_relation_matches(edge: dict[str, Any], relation_terms: list[str]) -> bool:
        if not relation_terms:
            return True
        relation = raw_norm(str(edge.get("relation", "")))
        return any(raw_norm(term) in relation for term in relation_terms if raw_norm(term))

    def edge_matches(
        edge: dict[str, Any],
        *,
        source_ids: set[str],
        target_ids: set[str],
        relation_terms: list[str],
        directed: bool,
    ) -> bool:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        endpoints_match = source in source_ids and target in target_ids
        if not directed:
            endpoints_match = endpoints_match or (source in target_ids and target in source_ids)
        return endpoints_match and edge_relation_matches(edge, relation_terms)

    def expected_edge_coverage(
        nodes: list[dict[str, Any]],
        links: list[dict[str, Any]],
        expected_edges: list[dict[str, Any]],
    ) -> float | None:
        checks: list[tuple[bool, float]] = []
        for spec in expected_edges:
            source_spec = _concept_spec(spec.get("source", ""))
            target_spec = _concept_spec(spec.get("target", ""))
            source_ids = {str(n.get("id")) for n in matching_nodes(nodes, source_spec)}
            target_ids = {str(n.get("id")) for n in matching_nodes(nodes, target_spec)}
            relation_terms = spec.get("relation_terms") or spec.get("relations") or []
            if isinstance(relation_terms, str):
                relation_terms = [relation_terms]
            terms = [str(term) for term in relation_terms]
            directed = bool(spec.get("directed", False))
            ok = bool(source_ids and target_ids) and any(
                edge_matches(
                    edge,
                    source_ids=source_ids,
                    target_ids=target_ids,
                    relation_terms=terms,
                    directed=directed,
                )
                for edge in links
            )
            checks.append((ok, _as_weight(spec.get("weight"))))
        return _weighted_score(checks)

    graph = _load_json(graph_path)
    expected = _load_json(expected_path)
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    labels = _load_json(labels_path) if labels_path and labels_path.exists() else {}

    required_specs = _concept_specs(expected.get("required_concepts", []))
    concept_checks = [
        (bool(matching_nodes(nodes, spec)), spec["weight"]) for spec in required_specs
    ]
    duplicate_specs = _concept_specs(expected.get("dedup_watchlist", []))
    duplicate_hits = {
        raw_norm(spec["name"]): matching_nodes(nodes, spec)
        for spec in duplicate_specs
        if len(matching_nodes(nodes, spec)) > 1
    }
    forbidden_specs = _concept_specs(expected.get("forbidden_concepts", []))
    forbidden_hits = [spec for spec in forbidden_specs if matching_nodes(nodes, spec)]
    forbidden_edges = []
    for spec in expected.get("forbidden_edges", []):
        source_spec = _concept_spec(spec.get("source", ""))
        target_spec = _concept_spec(spec.get("target", ""))
        source_ids = {str(n.get("id")) for n in matching_nodes(nodes, source_spec)}
        target_ids = {str(n.get("id")) for n in matching_nodes(nodes, target_spec)}
        relation_terms = spec.get("relation_terms") or spec.get("relations") or []
        if isinstance(relation_terms, str):
            relation_terms = [relation_terms]
        if source_ids and target_ids:
            forbidden_edges.extend(
                edge
                for edge in links
                if edge_matches(
                    edge,
                    source_ids=source_ids,
                    target_ids=target_ids,
                    relation_terms=[str(term) for term in relation_terms],
                    directed=bool(spec.get("directed", False)),
                )
            )
    inferred_edges = [e for e in links if str(e.get("confidence", "")).upper() == "INFERRED"]
    overconfident_inferred = [
        e for e in inferred_edges if _as_float(e.get("confidence_score", 0) or 0) >= 1.0
    ]

    expected_edges = expected.get("expected_edges", [])
    source_coverage = _source_coverage(nodes, links, expected.get("expected_source_files", []))
    relation_specificity = _relation_specificity(
        links, {str(r).lower() for r in expected.get("generic_relations", ["references"])}
    )
    community_labels = _community_label_hits(
        labels, expected.get("expected_community_label_terms", [])
    )
    dedup_score = (
        round((len(duplicate_specs) - len(duplicate_hits)) / len(duplicate_specs), 3)
        if duplicate_specs
        else None
    )
    inferred_confidence_score = (
        round((len(inferred_edges) - len(overconfident_inferred)) / len(inferred_edges), 3)
        if inferred_edges
        else None
    )
    forbidden_score = (0.0 if forbidden_hits else 1.0) if forbidden_specs else None
    forbidden_edge_score = (
        round(
            max(0, len(expected.get("forbidden_edges", [])) - len(forbidden_edges))
            / len(expected.get("forbidden_edges", [])),
            3,
        )
        if expected.get("forbidden_edges", [])
        else None
    )
    scores = {
        "concept_recall": _weighted_score(concept_checks),
        "deduplication": dedup_score,
        "community_labels": community_labels["score"],
        "relation_specificity": relation_specificity["score"],
        "inferred_confidence_calibration": inferred_confidence_score,
        "expected_edge_coverage": expected_edge_coverage(nodes, links, expected_edges)
        if expected_edges
        else None,
        "forbidden_concepts_absent": forbidden_score,
        "forbidden_edges_absent": forbidden_edge_score,
        "source_coverage": source_coverage["score"],
    }
    score_weights = (
        expected.get("score_weights", {}) if isinstance(expected.get("score_weights"), dict) else {}
    )
    weighted_dimensions = [
        (value, _as_weight(score_weights.get(key)))
        for key, value in scores.items()
        if value is not None
    ]
    scores["overall"] = (
        round(
            sum(value * weight for value, weight in weighted_dimensions)
            / sum(weight for _, weight in weighted_dimensions),
            3,
        )
        if weighted_dimensions
        else None
    )
    return {
        "scorer_version": SCORER_V1_VERSION,
        "graph_path": str(graph_path),
        "expected_path": str(expected_path),
        "nodes": len(nodes),
        "edges": len(links),
        "scores": {
            "overall": scores["overall"],
            **{k: v for k, v in scores.items() if k != "overall"},
        },
    }


def _fixture_id_for_saved_graph(
    graph_path: Path, semantic_eval_root: Path, fixture_ids: set[str]
) -> tuple[str | None, str]:
    run_or_fixture = graph_path.parents[2]
    if run_or_fixture.name in fixture_ids:
        return run_or_fixture.name, str(run_or_fixture.parent.relative_to(semantic_eval_root))
    run_root = run_or_fixture
    run_id = str(run_root.relative_to(semantic_eval_root))
    normalized_run_name = run_root.name.replace("-", "_")
    for fixture_id in sorted(fixture_ids, key=len, reverse=True):
        if fixture_id in normalized_run_name:
            return fixture_id, run_id
    run_json = run_root / "run.json"
    if run_json.exists():
        data = _load_json(run_json)
        corpus = str(data.get("corpus") or data.get("corpus_path") or "")
        for fixture_id in sorted(fixture_ids, key=len, reverse=True):
            if fixture_id in corpus:
                return fixture_id, run_id
    return None, run_id


def _weighted_aggregate_scores(
    fixture_records: list[dict[str, Any]], suite: dict[str, Any], *, score_key: str
) -> dict[str, float | None]:
    weights = {fixture["id"]: _as_weight(fixture.get("weight")) for fixture in suite["fixtures"]}
    dimension_values: dict[str, list[tuple[float, float]]] = {}
    for record in fixture_records:
        weight = weights.get(record["fixture_id"], 1.0)
        scores = record[score_key].get("scores", {})
        for key, value in scores.items():
            if value is not None:
                dimension_values.setdefault(key, []).append((_as_float(value), weight))
    return {
        key: score
        for key, values in sorted(dimension_values.items())
        if (score := _weighted_average(values)) is not None
    }


def _run_gate(scores: dict[str, Any], quality_gate: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    minimum_overall = quality_gate.get("minimum_overall")
    minimum_critical = quality_gate.get("minimum_critical_dimension")
    if minimum_overall is not None and scores.get("overall") is not None:
        if _as_float(scores["overall"]) < _as_float(minimum_overall):
            failures.append(f"overall {scores['overall']} < minimum_overall {minimum_overall}")
    if minimum_critical is not None:
        for dimension in [str(d) for d in quality_gate.get("critical_dimensions", [])]:
            value = scores.get(dimension)
            if value is not None and _as_float(value) < _as_float(minimum_critical):
                failures.append(
                    f"{dimension} {value} < minimum_critical_dimension {minimum_critical}"
                )
    return {"passed": not failures, "failures": failures}


def rebaseline_saved_artifacts(
    semantic_eval_root: Path,
    suite_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    suite = _load_suite(suite_path)
    fixture_ids = {fixture["id"] for fixture in suite["fixtures"]}
    fixture_by_id = {fixture["id"]: fixture for fixture in suite["fixtures"]}
    required_targets = [
        semantic_eval_root / "glm-5.2-cloud-suite-amended-20260629-151816",
        semantic_eval_root / "deepseek-v4-pro-cloud-suite-20260701-compare",
        semantic_eval_root / "minimax-m3-cloud-suite-20260614-112409",
        semantic_eval_root / "claude-cli-sonnet-integration-gateway-20260706",
    ]
    comparison_root = semantic_eval_root / "model-quality-comparison-20260614-191220"
    if comparison_root.exists():
        required_targets.extend(sorted(path for path in comparison_root.iterdir() if path.is_dir()))

    graph_paths = []
    for graph_path in sorted(semantic_eval_root.glob("**/corpus/graphify-out/graph.json")):
        relative_parts = graph_path.relative_to(semantic_eval_root).parts
        if "comparisons" in relative_parts:
            continue
        graph_paths.append(graph_path)

    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for graph_path in graph_paths:
        fixture_id, run_id = _fixture_id_for_saved_graph(
            graph_path, semantic_eval_root, fixture_ids
        )
        if fixture_id is None:
            skipped.append(
                {
                    "path": str(graph_path),
                    "reason": "fixture could not be inferred from graph path or run metadata",
                }
            )
            continue
        expected_path = fixture_by_id[fixture_id]["expected_path"]
        labels_path = graph_path.with_name(".graphify_labels.json")
        if not expected_path.exists():
            skipped.append({"path": str(graph_path), "reason": "expected.json missing"})
            continue
        if not labels_path.exists():
            skipped.append({"path": str(graph_path), "reason": ".graphify_labels.json missing"})
            continue
        old_score = _score_graph_v1_compat(graph_path, expected_path, labels_path=labels_path)
        new_score = score_graph(graph_path, expected_path, labels_path=labels_path)
        old_scores = old_score["scores"]
        new_scores = new_score["scores"]
        records.append(
            {
                "run_id": run_id,
                "fixture_id": fixture_id,
                "graph_path": str(graph_path),
                "labels_path": str(labels_path),
                "expected_path": str(expected_path),
                "old_score": old_score,
                "new_score": new_score,
                "deltas": {
                    key: None
                    if old_scores.get(key) is None or new_scores.get(key) is None
                    else round(_as_float(new_scores[key]) - _as_float(old_scores[key]), 3)
                    for key in sorted(set(old_scores) | set(new_scores))
                },
            }
        )

    for target in required_targets:
        if not target.exists():
            skipped.append({"path": str(target), "reason": "required artifact directory missing"})
            continue
        if not list(target.glob("**/corpus/graphify-out/graph.json")):
            skipped.append({"path": str(target), "reason": "no graph-bearing artifacts found"})

    groups: list[dict[str, Any]] = []
    for run_id in sorted({record["run_id"] for record in records}):
        group_records = [record for record in records if record["run_id"] == run_id]
        old_aggregate = _weighted_aggregate_scores(group_records, suite, score_key="old_score")
        current_summary = _aggregate_suite(
            suite,
            [
                {
                    "fixture_id": record["fixture_id"],
                    "score": record["new_score"],
                    "commands": [],
                }
                for record in group_records
            ],
        )
        new_aggregate = current_summary["scores"]
        groups.append(
            {
                "run_id": run_id,
                "fixture_count": len(group_records),
                "fixtures": sorted(record["fixture_id"] for record in group_records),
                "old_scores": old_aggregate,
                "new_scores": new_aggregate,
                "score_deltas": {
                    key: None
                    if old_aggregate.get(key) is None or new_aggregate.get(key) is None
                    else round(_as_float(new_aggregate[key]) - _as_float(old_aggregate[key]), 3)
                    for key in sorted(set(old_aggregate) | set(new_aggregate))
                },
                "profile_scores": current_summary["profile_scores"],
                "quality_gate_current": {
                    "passed": current_summary["gate_passed"],
                    "failures": current_summary["gate_failures"],
                },
            }
        )

    sonnet_spot_checks = [
        record
        for record in records
        if record["run_id"] == "claude-cli-sonnet-integration-gateway-20260706"
        and record["fixture_id"] == "integration_gateway"
    ]
    payload = {
        "scorer_version": SCORER_VERSION,
        "old_scorer_version": SCORER_V1_VERSION,
        "suite_path": str(suite_path),
        "semantic_eval_root": str(semantic_eval_root),
        "artifact_dir": str(out_dir),
        "methodology": {
            "model_calls": False,
            "graph_glob": "**/corpus/graphify-out/graph.json",
            "snapshot_subdirectories_excluded": True,
            "old_scorer": "compatibility implementation of scorer-v1 exact concept and relation-matched edge semantics",
            "new_scorer": "current graphify.semantic_eval.score_graph",
        },
        "summary": {
            "processed_graphs": len(records),
            "processed_runs": len(groups),
            "skipped_artifacts": len(skipped),
            "sonnet_integration_gateway_new_edge_coverage": sonnet_spot_checks[0]["new_score"][
                "scores"
            ].get("expected_edge_coverage")
            if sonnet_spot_checks
            else None,
        },
        "runs": groups,
        "fixtures": records,
        "skipped_artifacts": sorted(skipped, key=lambda item: (item["path"], item["reason"])),
    }
    _write_json(out_dir / "rebaseline.json", payload)
    (out_dir / "rebaseline.md").write_text(_rebaseline_markdown(payload), encoding="utf-8")
    return payload


def _rebaseline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Scorer v{SCORER_VERSION} Re-baseline",
        "",
        "No model calls were made. Graphs were scored from saved `corpus/graphify-out/graph.json` artifacts only; dated snapshot subdirectories under `graphify-out/` were not globbed.",
        "",
        f"- Processed graphs: {payload['summary']['processed_graphs']}",
        f"- Processed runs: {payload['summary']['processed_runs']}",
        f"- Skipped artifacts: {payload['summary']['skipped_artifacts']}",
        f"- Sonnet integration-gateway current edge coverage spot check: {payload['summary']['sonnet_integration_gateway_new_edge_coverage']}",
        "",
        "## Run Aggregates",
        "",
        "| Run | Fixtures | Old Overall | New Overall | New Concept Recall | New Edge Coverage | New Relation Agreement | Current Gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in payload["runs"]:
        new_scores = run["new_scores"]
        old_scores = run["old_scores"]
        gate = "pass" if run["quality_gate_current"]["passed"] else "fail"
        lines.append(
            f"| `{run['run_id']}` | {run['fixture_count']} | {old_scores.get('overall')} | "
            f"{new_scores.get('overall')} | {new_scores.get('concept_recall')} | "
            f"{new_scores.get('expected_edge_coverage')} | "
            f"{new_scores.get('expected_edge_relation_agreement')} | {gate} |"
        )
    lines += [
        "",
        "## Per-fixture Scores",
        "",
        "| Run | Fixture | Old Overall | New Overall | Old Edge Coverage | New Edge Coverage | New Relation Agreement | New Concept Recall |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in payload["fixtures"]:
        old_scores = record["old_score"]["scores"]
        new_scores = record["new_score"]["scores"]
        lines.append(
            f"| `{record['run_id']}` | `{record['fixture_id']}` | {old_scores.get('overall')} | "
            f"{new_scores.get('overall')} | {old_scores.get('expected_edge_coverage')} | "
            f"{new_scores.get('expected_edge_coverage')} | "
            f"{new_scores.get('expected_edge_relation_agreement')} | "
            f"{new_scores.get('concept_recall')} |"
        )
    if payload.get("skipped_artifacts"):
        lines += ["", "## Skipped Artifacts", ""]
        for item in payload["skipped_artifacts"]:
            lines.append(f"- `{item['path']}` — {item['reason']}")
    return "\n".join(lines) + "\n"


def _comparison_markdown(comparison: dict[str, Any]) -> str:
    baseline = comparison["baseline"]
    candidate = comparison["candidate"]
    lines = [
        "# Graphify Semantic Model Suite Comparison",
        "",
        f"- Baseline: `{baseline.get('model')}` ({baseline.get('overall')})",
        f"- Candidate: `{candidate.get('model')}` ({candidate.get('overall')})",
        f"- Overall delta: {comparison['score_deltas'].get('overall')}",
        f"- Baseline gate: {'pass' if baseline.get('gate_passed') else 'fail'}",
        f"- Candidate gate: {'pass' if candidate.get('gate_passed') else 'fail'}",
    ]
    if comparison.get("warnings"):
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {warning}" for warning in comparison["warnings"])
    lines += [
        "",
        "## Aggregate Deltas",
        "",
        "| Dimension | Candidate - Baseline |",
        "|---|---:|",
    ]
    for key, value in comparison["score_deltas"].items():
        lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
    lines += [
        "",
        "## Fixture Deltas",
        "",
        "| Fixture | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
    ]
    for fixture in comparison["fixture_deltas"]:
        lines.append(
            f"| `{fixture['id']}` | {fixture['baseline_overall']} | "
            f"{fixture['candidate_overall']} | {fixture['delta']} |"
        )
    if comparison["regressions"]:
        lines += ["", "## Regressions", ""]
        for fixture in comparison["regressions"]:
            lines.append(f"- `{fixture['id']}`: {fixture['delta']}")
    return "\n".join(lines) + "\n"


_JUDGE_PROMPT_VERSION = "semantic-eval-judge-v2"
_JUDGE_SCORE_KEYS = [
    "faithfulness",
    "semantic_completeness",
    "relation_quality",
    "abstraction_quality",
    "graph_usefulness",
    "community_label_quality",
    "source_grounding",
    "risk_handling",
]
_IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_MAX_JUDGE_IMAGE_BYTES = 5 * 1024 * 1024


def _parse_judge_spec(spec: str) -> dict[str, str]:
    """Parse a judge spec like ``openai:gpt-5.1`` or ``claude:opus``."""
    raw = spec.strip()
    if not raw:
        raise ValueError("judge spec cannot be empty")
    if ":" in raw:
        backend, model = raw.split(":", 1)
    else:
        backend, model = raw, ""
    backend = backend.strip()
    model = model.strip()
    if not backend:
        raise ValueError(f"invalid judge spec {spec!r}")
    return {"backend": backend, "model": model, "id": raw}


def _parse_llm_json_response(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    if not cleaned.startswith("{"):
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("judge returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("judge returned non-object JSON")
    return data


def _require_external_judge_allowed(*, allow_external_judge: bool) -> None:
    if allow_external_judge:
        return
    if os.environ.get("GRAPHIFY_ALLOW_EXTERNAL_JUDGE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    raise SystemExit(
        "judge commands send fixture source text, expected contracts, graph samples, and optionally "
        "images to the judge backend. Re-run with --allow-external-judge or set "
        "GRAPHIFY_ALLOW_EXTERNAL_JUDGE=1."
    )


def _validate_score(value: Any, *, key: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"judge score {key!r} is not numeric: {value!r}") from exc
    if math.isnan(score) or score < 1 or score > 5:
        raise ValueError(f"judge score {key!r} must be in [1, 5], got {value!r}")
    return score


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"judge response {field} must be a list")
    return [str(item) for item in value]


def _validate_evidence_examples(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("pointwise judge response evidence_examples must be a list")
    examples: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("pointwise judge evidence_examples entries must be objects")
        examples.append(
            {
                "finding": str(item.get("finding", "")),
                "source_evidence": str(item.get("source_evidence", "")),
                "graph_evidence": str(item.get("graph_evidence", "")),
            }
        )
    return examples


def _validate_pointwise_judgment(judgment: dict[str, Any]) -> dict[str, Any]:
    scores = judgment.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("pointwise judge response missing object 'scores'")
    normalized_scores = {
        key: _validate_score(scores.get(key), key=key) for key in _JUDGE_SCORE_KEYS
    }
    confidence = str(judgment.get("confidence", "")).lower()
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("pointwise judge response confidence must be low|medium|high")
    decision = str(judgment.get("recommended_decision", "")).lower()
    if decision not in {"accept", "reject", "needs_human_review"}:
        raise ValueError(
            "pointwise judge response recommended_decision must be accept|reject|needs_human_review"
        )
    executive_summary = str(judgment.get("executive_summary", "")).strip()
    if not executive_summary:
        raise ValueError("pointwise judge response executive_summary is required")
    return {
        **judgment,
        "scores": normalized_scores,
        "confidence": confidence,
        "recommended_decision": decision,
        "executive_summary": executive_summary,
        "strengths": _string_list(judgment.get("strengths", []), field="strengths"),
        "weaknesses": _string_list(judgment.get("weaknesses", []), field="weaknesses"),
        "evidence_examples": _validate_evidence_examples(judgment.get("evidence_examples", [])),
        "critical_failures": _string_list(
            judgment.get("critical_failures", []), field="critical_failures"
        ),
        "rationale": _string_list(judgment.get("rationale", []), field="rationale"),
    }


def _validate_pairwise_judgment(judgment: dict[str, Any]) -> dict[str, Any]:
    winner = str(judgment.get("winner", "")).lower()
    if winner not in {"a", "b", "tie"}:
        raise ValueError("pairwise judge response winner must be A|B|tie")
    confidence = str(judgment.get("confidence", "")).lower()
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("pairwise judge response confidence must be low|medium|high")
    executive_summary = str(judgment.get("executive_summary", "")).strip()
    if not executive_summary:
        raise ValueError("pairwise judge response executive_summary is required")
    dimension_winners = judgment.get("dimension_winners", {})
    if not isinstance(dimension_winners, dict):
        raise ValueError("pairwise judge response dimension_winners must be an object")
    normalized_dimensions = {}
    for key in _JUDGE_SCORE_KEYS:
        value = str(dimension_winners.get(key, "tie")).lower()
        if value not in {"a", "b", "tie"}:
            raise ValueError(f"pairwise judge dimension {key!r} must be A|B|tie")
        normalized_dimensions[key] = value
    return {
        **judgment,
        "winner": winner,
        "confidence": confidence,
        "dimension_winners": normalized_dimensions,
        "executive_summary": executive_summary,
        "graph_a_strengths": _string_list(
            judgment.get("graph_a_strengths", []), field="graph_a_strengths"
        ),
        "graph_b_strengths": _string_list(
            judgment.get("graph_b_strengths", []), field="graph_b_strengths"
        ),
        "graph_a_weaknesses": _string_list(
            judgment.get("graph_a_weaknesses", []), field="graph_a_weaknesses"
        ),
        "graph_b_weaknesses": _string_list(
            judgment.get("graph_b_weaknesses", []), field="graph_b_weaknesses"
        ),
        "candidate_regressions_if_identifiable_from_context": _string_list(
            judgment.get("candidate_regressions_if_identifiable_from_context", []),
            field="candidate_regressions_if_identifiable_from_context",
        ),
        "critical_failures": _string_list(
            judgment.get("critical_failures", []), field="critical_failures"
        ),
        "rationale": _string_list(judgment.get("rationale", []), field="rationale"),
        "human_review_needed": bool(judgment.get("human_review_needed", False)),
    }


def _image_blocks_for_openai(image_paths: list[Path]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for path in image_paths:
        media_type = _IMAGE_MEDIA_TYPES.get(path.suffix.lower())
        if not media_type or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        blocks.append(
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
        )
    return blocks


def _image_blocks_for_anthropic(image_paths: list[Path]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for path in image_paths:
        media_type = _IMAGE_MEDIA_TYPES.get(path.suffix.lower())
        if not media_type or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        blocks.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            }
        )
    return blocks


def _judge_timeout_seconds() -> float:
    raw = os.environ.get("GRAPHIFY_JUDGE_TIMEOUT") or os.environ.get("GRAPHIFY_API_TIMEOUT")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return 600.0


def _valid_judge_image_paths(image_paths: list[Path]) -> list[Path]:
    valid: list[Path] = []
    for path in image_paths:
        if (
            path.suffix.lower() in _IMAGE_MEDIA_TYPES
            and path.is_file()
            and path.stat().st_size <= _MAX_JUDGE_IMAGE_BYTES
        ):
            valid.append(path)
    return valid


def _stage_judge_images(image_paths: list[Path], directory: Path) -> list[Path]:
    staged: list[Path] = []
    for index, path in enumerate(_valid_judge_image_paths(image_paths), start=1):
        staged_path = directory / f"judge-image-{index}{path.suffix.lower()}"
        shutil.copyfile(path, staged_path)
        staged.append(staged_path)
    return staged


def _judge_image_paths_note(image_paths: list[Path]) -> str:
    if not image_paths:
        return ""
    lines = [
        "",
        "IMAGE ATTACHMENT PATHS",
        "The judge command was invoked with image inclusion enabled. These paths are isolated temporary copies of the approved fixture images; inspect only these files as image evidence:",
    ]
    lines.extend(f"- {path.resolve()}" for path in image_paths)
    return "\n".join(lines)


def _call_pi_judge_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    image_paths: list[Path],
) -> dict[str, Any]:
    if shutil.which("pi") is None:
        raise RuntimeError("Pi CLI not found on $PATH")
    selected_model = model or "openai-codex/gpt-5.5:high"
    with tempfile.TemporaryDirectory(prefix="graphify-judge-pi-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        staged_images = _stage_judge_images(image_paths, temp_dir)
        prompt_file = temp_dir / "judge-prompt.json"
        prompt_file.write_text(
            user_prompt + _judge_image_paths_note(staged_images), encoding="utf-8"
        )
        args = [
            "pi",
            "--no-session",
            "--no-extensions",
            "--no-skills",
            "--no-prompt-templates",
            "--no-themes",
            "--no-context-files",
            "--no-approve",
            "--model",
            selected_model,
            "--tools",
            "",
            "--system-prompt",
            system_prompt,
            "-p",
            f"@{prompt_file.resolve()}",
        ]
        args.extend(f"@{path.resolve()}" for path in staged_images)
        args.append(
            "Follow the attached judge prompt file exactly. Return only the requested JSON."
        )
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_judge_timeout_seconds(),
            check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"pi judge exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    return _parse_llm_json_response(proc.stdout or "{}")


def _call_claude_cli_judge_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    image_paths: list[Path],
) -> dict[str, Any]:
    if shutil.which("claude") is None:
        raise RuntimeError(
            "Claude Code CLI not found on $PATH. Install Claude Code and run `claude auth login`."
        )
    selected_model = model or "opus"
    with tempfile.TemporaryDirectory(prefix="graphify-judge-claude-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        staged_images = _stage_judge_images(image_paths, temp_dir)
        prompt = user_prompt + _judge_image_paths_note(staged_images)
        args = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--setting-sources",
            "user",
            "--disable-slash-commands",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--model",
            selected_model,
            "--effort",
            "high",
            "--system-prompt",
            system_prompt,
        ]
        if staged_images:
            args.extend(["--add-dir", str(temp_dir.resolve()), "--tools", "Read"])
        else:
            args.extend(["--tools", ""])
        proc = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_judge_timeout_seconds(),
            check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"claude judge exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    envelope = _json_loads_or_none(proc.stdout)
    if envelope is None:
        return _parse_llm_json_response(proc.stdout or "{}")
    raw = envelope.get("result") if isinstance(envelope, dict) else None
    if not isinstance(raw, str):
        raw = proc.stdout
    return _parse_llm_json_response(raw or "{}")


def _call_judge_model(
    judge: dict[str, str],
    system_prompt: str,
    user_prompt: str,
    *,
    image_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Call an external judge model and parse its JSON response.

    Tests monkeypatch this function, so normal validation remains offline. Live
    use requires explicit ``judge-suite`` or ``judge-compare`` commands.
    """
    from graphify.llm import (
        BACKENDS,
        _default_model_for_backend,
        _get_backend_api_key,
        _resolve_temperature,
        validate_backend_dependencies,
    )

    backend = judge["backend"]
    model = judge.get("model", "")
    if backend == "pi":
        return _call_pi_judge_model(
            model,
            system_prompt,
            user_prompt,
            image_paths=image_paths or [],
        )
    if backend == "claude-cli":
        return _call_claude_cli_judge_model(
            model,
            system_prompt,
            user_prompt,
            image_paths=image_paths or [],
        )
    if backend not in BACKENDS:
        raise ValueError(f"unknown judge backend {backend!r}")
    validate_backend_dependencies(backend)
    cfg = BACKENDS[backend]
    model = model or _default_model_for_backend(backend)
    api_key = _get_backend_api_key(backend)
    if backend == "ollama" and not api_key:
        api_key = "ollama"
    if not api_key and backend not in {"bedrock", "claude-cli"}:
        raise ValueError(f"judge backend {backend!r} is missing API credentials")
    supports_images = bool(cfg.get("vision")) or (
        backend == "ollama"
        and os.environ.get("GRAPHIFY_OLLAMA_VISION", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    images = (image_paths or []) if supports_images else []

    if backend == "claude":
        import anthropic  # pyright: ignore[reportMissingImports]

        client = anthropic.Anthropic(api_key=api_key, timeout=600)
        anthropic_blocks: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        anthropic_blocks.extend(_image_blocks_for_anthropic(images))
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": anthropic_blocks}],
        )
        raw = "".join(getattr(block, "text", "") for block in response.content)
        return _parse_llm_json_response(raw)

    if "base_url" not in cfg:
        raise ValueError(f"judge backend {backend!r} is not supported by semantic_eval judge")
    from openai import OpenAI  # pyright: ignore[reportMissingImports]

    client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=600)
    openai_user_content: str | list[dict[str, Any]] = user_prompt
    image_blocks = _image_blocks_for_openai(images)
    if image_blocks:
        openai_user_content = [{"type": "text", "text": user_prompt}, *image_blocks]
    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_completion_tokens": 4096,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": openai_user_content},
        ],
    }
    temperature = _resolve_temperature(0, model)
    if temperature is not None:
        request_kwargs["temperature"] = temperature
    reasoning_effort = cfg.get("reasoning_effort")
    if reasoning_effort is not None:
        request_kwargs["reasoning_effort"] = reasoning_effort
    extra_body = cfg.get("extra_body")
    if extra_body is not None:
        request_kwargs["extra_body"] = extra_body
    elif "moonshot" in str(cfg.get("base_url", "")):
        request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    response = client.chat.completions.create(**request_kwargs)
    raw = response.choices[0].message.content if response.choices else "{}"
    return _parse_llm_json_response(raw or "{}")


def _read_text_fixture_sources(
    corpus: Path, *, max_file_chars: int = 6000, max_total_chars: int = 24000
) -> tuple[list[dict[str, str]], list[Path]]:
    sources: list[dict[str, str]] = []
    image_paths: list[Path] = []
    total = 0
    for path in sorted(corpus.rglob("*")):
        if not path.is_file() or "graphify-out" in path.parts or path.name == "expected.json":
            continue
        rel = path.relative_to(corpus).as_posix()
        if path.suffix.lower() in _IMAGE_MEDIA_TYPES:
            image_paths.append(path)
            sources.append(
                {
                    "path": rel,
                    "kind": "image",
                    "content": "[image attached if judge backend supports vision]",
                }
            )
            continue
        if path.suffix.lower() not in {
            ".md",
            ".txt",
            ".rst",
            ".py",
            ".ts",
            ".tsx",
            ".json",
            ".yaml",
            ".yml",
            ".html",
        }:
            sources.append(
                {
                    "path": rel,
                    "kind": "other",
                    "content": "[binary or unsupported text fixture file]",
                }
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[:max_file_chars]
        remaining = max_total_chars - total
        if remaining <= 0:
            break
        text = text[:remaining]
        total += len(text)
        sources.append({"path": rel, "kind": "text", "content": text})
    return sources, image_paths


def _load_labels(path: Path) -> dict[str, Any]:
    return _load_json(path) if path.exists() else {}


def _compact_graph(
    graph_path: Path,
    labels_path: Path | None = None,
    *,
    node_limit: int = 80,
    edge_limit: int = 120,
) -> dict[str, Any]:
    graph = _load_json(graph_path)
    labels = _load_labels(labels_path) if labels_path else {}
    nodes = graph.get("nodes", [])[:node_limit]
    edges = graph.get("links", graph.get("edges", []))[:edge_limit]
    return {
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("links", graph.get("edges", []))),
        "nodes_sample": nodes,
        "edges_sample": edges,
        "community_labels": labels,
        "truncated": len(graph.get("nodes", [])) > node_limit
        or len(graph.get("links", graph.get("edges", []))) > edge_limit,
    }


def _fixture_for_suite_run(suite: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    for fixture in suite["fixtures"]:
        if fixture["id"] == fixture_id:
            return fixture
    raise KeyError(f"fixture {fixture_id!r} not found in suite")


def _fixture_judge_context(
    suite_run: dict[str, Any], fixture_run: dict[str, Any]
) -> dict[str, Any]:
    suite_path = Path(suite_run.get("suite_path", ""))
    if not suite_path.is_file():
        raise FileNotFoundError(
            "suite-run.json must include a valid suite_path for judge evaluation"
        )
    suite = _load_suite(suite_path)
    fixture = _fixture_for_suite_run(suite, str(fixture_run["id"]))
    artifact_dir = Path(str(fixture_run.get("artifact_dir") or ""))
    graph_path = artifact_dir / "corpus" / "graphify-out" / "graph.json"
    labels_path = artifact_dir / "corpus" / "graphify-out" / ".graphify_labels.json"
    if not graph_path.is_file():
        raise FileNotFoundError(
            f"graph artifact missing for fixture {fixture['id']!r}: {graph_path}"
        )
    sources, image_paths = _read_text_fixture_sources(fixture["corpus_path"])
    return {
        "fixture": {k: v for k, v in fixture.items() if k not in {"corpus_path", "expected_path"}},
        "source_files": sources,
        "image_paths": image_paths,
        "expected_contract": _load_json(fixture["expected_path"]),
        "deterministic_scores": fixture_run.get("scores", {}),
        "graph": _compact_graph(graph_path, labels_path),
    }


def _judge_system_prompt(*, mode: str) -> str:
    if mode == "pairwise":
        task = "Compare two anonymized Graphify outputs for the same corpus."
    else:
        task = "Evaluate one Graphify output for semantic graph quality."
    return f"""You are an independent expert evaluator for Graphify semantic extraction quality.
{task}

Assume you have no prior knowledge of Graphify. Use only the material provided in
this evaluation prompt: source corpus excerpts and image attachments, expected
contract/rubric, deterministic metric scores, extracted graph nodes, edges, and
community labels. Do not use outside knowledge about the project, repository,
model, or provider. Do not infer which model produced the graph unless explicitly
shown. Do not reward a graph for being larger, more verbose, or more confident.
Reward only useful, faithful, source-grounded semantic structure.

What Graphify is: Graphify turns a corpus into a knowledge graph for coding
agents and operators. A good Graphify graph helps an agent understand and
navigate architecture, workflows, policies, dependencies, decisions, and
cross-file relationships.

Graphify outputs:
- Nodes: meaningful concepts, components, workflows, files, policies, data
  structures, decisions, or visual elements.
- Edges: relationships between nodes, such as calls, implements, references,
  depends on, routes to, validates, records, produces, stores, governs, or
  conceptually relates to.
- Confidence: EXTRACTED is directly supported, INFERRED is reasonably inferred,
  and AMBIGUOUS is uncertain and worth review.
- Source attribution should make graph claims auditable.

A good graph is faithful to the source, complete enough to preserve important
concepts and flows, appropriately abstracted, source-grounded, useful for future
architecture/workflow questions, and safe.

Penalize hallucinated components, missing central concepts, generic relation
labels when a specific relation is visible, duplicate nodes, over-broad nodes,
over-fragmented nodes, overstated causality/dependency, wrong source attribution,
vague community labels, overconfident inferred edges, missing image-only concepts
in visual fixtures, and privacy/safety mistakes.

Use this general 1-5 scoring scale:
5 = excellent: faithful, useful, source-grounded, no material issues.
4 = good: minor omissions or genericness, still clearly useful.
3 = mixed: captures some important structure but has meaningful omissions,
    weak abstractions, or generic relationships.
2 = poor: misses important concepts, has weak grounding, or would mislead an
    agent in important ways.
1 = failing: mostly unusable, hallucinated, unsafe, or contradicts the source.

Return ONLY valid JSON matching the requested schema. Do not include markdown."""


def _pointwise_judge_prompt(context: dict[str, Any]) -> str:
    payload = {
        "prompt_version": _JUDGE_PROMPT_VERSION,
        "task": "Evaluate this Graphify graph for semantic quality and usefulness.",
        "graphify_use_case": {
            "primary_user": "coding agent or operator",
            "goal": "use the graph to understand, navigate, and reason about the source corpus",
            "important_behavior": [
                "preserve important concepts and flows",
                "make relationships specific and useful",
                "keep claims auditable through source attribution",
                "avoid hallucinated or unsafe structure",
            ],
        },
        "rubric": {
            "faithfulness": {
                "question": "Are nodes and edges supported by source evidence?",
                "5": "All important graph claims are source-supported.",
                "3": "Some useful claims are supported, but there are unsupported or overstated claims.",
                "1": "Graph contains major hallucinations or contradicts the source.",
            },
            "semantic_completeness": {
                "question": "Did the graph capture the important concepts, workflows, and branches?",
                "5": "Captures all central concepts and flows.",
                "3": "Captures some central concepts but misses meaningful pieces.",
                "1": "Misses most important semantics.",
            },
            "relation_quality": {
                "question": "Are edges specific, meaningful, and useful?",
                "5": "Important relationships are specific and source-grounded.",
                "3": "Many relationships are generic or weak but partly useful.",
                "1": "Edges are mostly generic, wrong, or misleading.",
            },
            "abstraction_quality": {
                "question": "Are nodes at the right conceptual level?",
                "5": "Clear, useful concepts with little duplication or fragmentation.",
                "3": "Some over-broad, over-fragmented, or duplicate concepts.",
                "1": "Abstractions obscure the source rather than clarify it.",
            },
            "graph_usefulness": {
                "question": "Would this graph help an agent answer architecture/workflow questions?",
                "5": "Very useful for navigation and reasoning.",
                "3": "Somewhat useful but requires substantial source rereading.",
                "1": "Not useful or actively misleading.",
            },
            "community_label_quality": {
                "question": "Are community labels coherent and orienting?",
                "5": "Labels clearly summarize useful topic clusters.",
                "3": "Labels are partially useful but vague or incomplete.",
                "1": "Labels are misleading or unhelpful.",
            },
            "source_grounding": {
                "question": "Are graph claims traceable to the right source files or images?",
                "5": "Source attribution is complete and correct.",
                "3": "Some attribution exists but is incomplete or uneven.",
                "1": "Claims are not auditable.",
            },
            "risk_handling": {
                "question": "Does the graph avoid unsafe, privacy-breaking, or unsupported interpretations?",
                "5": "No material risk issues.",
                "3": "Minor ambiguous risk issues.",
                "1": "Major unsafe or privacy-breaking hallucination.",
            },
        },
        "output_schema": {
            "scores": {key: "integer 1-5" for key in _JUDGE_SCORE_KEYS},
            "executive_summary": "2-5 sentences explaining overall quality",
            "strengths": ["specific strengths"],
            "weaknesses": ["specific weaknesses"],
            "evidence_examples": [
                {
                    "finding": "what you observed",
                    "source_evidence": "source file/image or excerpt reference",
                    "graph_evidence": "node/edge/community label evidence",
                }
            ],
            "critical_failures": ["critical issues, or empty list"],
            "recommended_decision": "accept|reject|needs_human_review",
            "rationale": ["string"],
            "confidence": "low|medium|high",
        },
        "context": {k: v for k, v in context.items() if k != "image_paths"},
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _pairwise_judge_prompt(
    context: dict[str, Any], graph_a: dict[str, Any], graph_b: dict[str, Any]
) -> str:
    payload = {
        "prompt_version": _JUDGE_PROMPT_VERSION,
        "task": (
            "Compare Graph A and Graph B for the same fixture. Choose the graph "
            "that is more faithful, useful, source-grounded, and semantically complete "
            "for Graphify's use case. Prefer tie when quality is materially equivalent."
        ),
        "graphify_use_case": {
            "primary_user": "coding agent or operator",
            "goal": "use the graph to understand, navigate, and reason about the source corpus",
        },
        "rubric": {
            "faithfulness": "Which graph is more source-grounded and less hallucinatory?",
            "semantic_completeness": "Which graph captures more important concepts and flows?",
            "relation_quality": "Which graph has more useful and specific edges?",
            "abstraction_quality": "Which graph has better conceptual granularity?",
            "graph_usefulness": "Which graph is more useful for an agent navigating the corpus?",
            "community_label_quality": "Which graph has better community labels?",
            "source_grounding": "Which graph cites source evidence better?",
            "risk_handling": "Which graph better avoids unsafe or privacy-breaking interpretations?",
        },
        "output_schema": {
            "winner": "A|B|tie",
            "confidence": "low|medium|high",
            "dimension_winners": {key: "A|B|tie" for key in _JUDGE_SCORE_KEYS},
            "executive_summary": "natural language comparison",
            "graph_a_strengths": ["string"],
            "graph_b_strengths": ["string"],
            "graph_a_weaknesses": ["string"],
            "graph_b_weaknesses": ["string"],
            "candidate_regressions_if_identifiable_from_context": ["string"],
            "critical_failures": ["string"],
            "human_review_needed": "boolean",
            "rationale": ["string"],
        },
        "fixture_context": {
            k: v
            for k, v in context.items()
            if k not in {"image_paths", "graph", "deterministic_scores"}
        },
        "graph_a": graph_a,
        "graph_b": graph_b,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _average_judge_score(scores: dict[str, Any]) -> float | None:
    values = [_validate_score(scores[key], key=key) for key in _JUDGE_SCORE_KEYS]
    return round(sum(values) / len(values), 3) if values else None


def judge_suite_run(
    suite_run_path: Path,
    out_dir: Path,
    *,
    judges: list[str],
    include_images: bool = False,
) -> dict[str, Any]:
    suite_run = _load_json(suite_run_path)
    judge_specs = [_parse_judge_spec(spec) for spec in judges]
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for fixture_run in suite_run.get("fixtures", []):
        if fixture_run.get("error"):
            continue
        try:
            context = _fixture_judge_context(suite_run, fixture_run)
        except Exception as exc:
            failures.append({"fixture_id": fixture_run.get("id"), "error": str(exc)})
            continue
        prompt = _pointwise_judge_prompt(context)
        image_paths = context["image_paths"] if include_images else []
        for judge in judge_specs:
            try:
                judged = _call_judge_model(
                    judge,
                    _judge_system_prompt(mode="pointwise"),
                    prompt,
                    image_paths=image_paths,
                )
                judged = _validate_pointwise_judgment(judged)
                results.append(
                    {
                        "fixture_id": fixture_run["id"],
                        "judge": judge,
                        "prompt_version": _JUDGE_PROMPT_VERSION,
                        "judgment": judged,
                        "average_score": _average_judge_score(judged["scores"]),
                    }
                )
            except Exception as exc:
                failures.append(
                    {"fixture_id": fixture_run.get("id"), "judge": judge, "error": str(exc)}
                )
    summary = {
        "suite_run_path": str(suite_run_path),
        "suite_model": suite_run.get("model"),
        "judges": judge_specs,
        "include_images": include_images,
        "results": results,
        "failures": failures,
    }
    _write_json(out_dir / "judge-run.json", summary)
    (out_dir / "JUDGE_REPORT.md").write_text(_judge_suite_markdown(summary), encoding="utf-8")
    return summary


def _judge_suite_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Graphify Semantic Eval Judge Report",
        "",
        f"- Suite model: `{summary.get('suite_model')}`",
        f"- Judges: {', '.join(j['id'] for j in summary.get('judges', []))}",
        f"- Images included: {summary.get('include_images', False)}",
    ]
    if summary.get("failures"):
        lines += ["", "## Failures", ""]
        for failure in summary["failures"]:
            judge = (
                failure.get("judge", {}).get("id")
                if isinstance(failure.get("judge"), dict)
                else None
            )
            prefix = f" `{judge}`" if judge else ""
            lines.append(f"- `{failure.get('fixture_id')}`{prefix}: {failure.get('error')}")
    lines += [
        "",
        "| Fixture | Judge | Average | Decision | Confidence | Critical Failures |",
        "|---|---|---:|---|---|---:|",
    ]
    for result in summary.get("results", []):
        judgment = result.get("judgment", {})
        failures = len(judgment.get("critical_failures", []) or [])
        lines.append(
            f"| `{result['fixture_id']}` | `{result['judge']['id']}` | {result.get('average_score')} | "
            f"{judgment.get('recommended_decision')} | {judgment.get('confidence')} | {failures} |"
        )
    if summary.get("results"):
        lines += ["", "## Judge Summaries", ""]
        for result in summary.get("results", []):
            judgment = result.get("judgment", {})
            lines.append(
                f"### {result['fixture_id']} — {result['judge']['id']}\n\n"
                f"{judgment.get('executive_summary', '')}\n"
            )
            strengths = judgment.get("strengths", [])
            weaknesses = judgment.get("weaknesses", [])
            if strengths:
                lines.append("Strengths: " + "; ".join(str(s) for s in strengths))
            if weaknesses:
                lines.append("Weaknesses: " + "; ".join(str(w) for w in weaknesses))
            lines.append("")
    return "\n".join(lines) + "\n"


def _suite_fixture_run_by_id(suite_run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("id")): f for f in suite_run.get("fixtures", [])}


def _suite_contract_fingerprint(suite_run: dict[str, Any]) -> dict[str, str]:
    suite_path = Path(suite_run.get("suite_path", ""))
    if not suite_path.is_file():
        raise FileNotFoundError(
            "suite-run.json must include a valid suite_path for judge comparison"
        )
    suite = _load_suite(suite_path)
    return {fixture["id"]: str(fixture["expected_path"].resolve()) for fixture in suite["fixtures"]}


def _assert_compatible_suite_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    baseline_contract = _suite_contract_fingerprint(baseline)
    candidate_contract = _suite_contract_fingerprint(candidate)
    if baseline_contract != candidate_contract:
        raise ValueError(
            "baseline and candidate suite runs use different fixture contracts; "
            "do not run pairwise judge comparison across different suite versions"
        )


def judge_compare_suite_runs(
    baseline_path: Path,
    candidate_path: Path,
    out_dir: Path,
    *,
    judges: list[str],
    include_images: bool = False,
) -> dict[str, Any]:
    baseline = _load_json(baseline_path)
    candidate = _load_json(candidate_path)
    _assert_compatible_suite_runs(baseline, candidate)
    judge_specs = [_parse_judge_spec(spec) for spec in judges]
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_fixtures = _suite_fixture_run_by_id(baseline)
    candidate_fixtures = _suite_fixture_run_by_id(candidate)
    fixture_ids = sorted(set(baseline_fixtures) & set(candidate_fixtures))
    judgments: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    vote_counts = {"baseline": 0, "candidate": 0, "tie": 0}
    for fixture_id in fixture_ids:
        if baseline_fixtures[fixture_id].get("error") or candidate_fixtures[fixture_id].get(
            "error"
        ):
            continue
        try:
            base_context = _fixture_judge_context(baseline, baseline_fixtures[fixture_id])
            cand_context = _fixture_judge_context(candidate, candidate_fixtures[fixture_id])
        except Exception as exc:
            failures.append({"fixture_id": fixture_id, "error": str(exc)})
            continue
        shared_context = {
            k: v for k, v in base_context.items() if k not in {"graph", "deterministic_scores"}
        }
        graph_baseline = {
            "deterministic_scores": baseline_fixtures[fixture_id].get("scores", {}),
            "graph": base_context["graph"],
        }
        graph_candidate = {
            "deterministic_scores": candidate_fixtures[fixture_id].get("scores", {}),
            "graph": cand_context["graph"],
        }
        for judge in judge_specs:
            for order, graph_a, graph_b in [
                ("baseline_as_a", graph_baseline, graph_candidate),
                ("candidate_as_a", graph_candidate, graph_baseline),
            ]:
                prompt = _pairwise_judge_prompt(shared_context, graph_a, graph_b)
                try:
                    judged = _call_judge_model(
                        judge,
                        _judge_system_prompt(mode="pairwise"),
                        prompt,
                        image_paths=base_context["image_paths"] if include_images else [],
                    )
                    judged = _validate_pairwise_judgment(judged)
                except Exception as exc:
                    failures.append(
                        {
                            "fixture_id": fixture_id,
                            "judge": judge,
                            "order": order,
                            "error": str(exc),
                        }
                    )
                    continue
                raw_winner = str(judged.get("winner", "tie")).lower()
                if raw_winner == "tie":
                    normalized = "tie"
                elif (order == "baseline_as_a" and raw_winner == "a") or (
                    order == "candidate_as_a" and raw_winner == "b"
                ):
                    normalized = "baseline"
                else:
                    normalized = "candidate"
                vote_counts[normalized] += 1
                judgments.append(
                    {
                        "fixture_id": fixture_id,
                        "judge": judge,
                        "order": order,
                        "winner": normalized,
                        "raw_judgment": judged,
                    }
                )
    if (
        vote_counts["candidate"] > vote_counts["baseline"]
        and vote_counts["candidate"] >= vote_counts["tie"]
    ):
        consensus = "candidate"
    elif (
        vote_counts["baseline"] > vote_counts["candidate"]
        and vote_counts["baseline"] >= vote_counts["tie"]
    ):
        consensus = "baseline"
    else:
        consensus = "needs_human_review"
    summary = {
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "baseline_model": baseline.get("model"),
        "candidate_model": candidate.get("model"),
        "judges": judge_specs,
        "include_images": include_images,
        "vote_counts": vote_counts,
        "consensus": consensus,
        "judgments": judgments,
        "failures": failures,
    }
    _write_json(out_dir / "pairwise-judge.json", summary)
    (out_dir / "PAIRWISE_REPORT.md").write_text(_judge_compare_markdown(summary), encoding="utf-8")
    return summary


def _judge_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Graphify Semantic Eval Pairwise Judge Report",
        "",
        f"- Baseline: `{summary.get('baseline_model')}`",
        f"- Candidate: `{summary.get('candidate_model')}`",
        f"- Consensus: `{summary.get('consensus')}`",
        f"- Votes: {summary.get('vote_counts')}",
        f"- Images included: {summary.get('include_images', False)}",
    ]
    if summary.get("failures"):
        lines += ["", "## Failures", ""]
        for failure in summary["failures"]:
            judge = (
                failure.get("judge", {}).get("id")
                if isinstance(failure.get("judge"), dict)
                else None
            )
            judge_note = f" `{judge}`" if judge else ""
            order_note = f" {failure.get('order')}" if failure.get("order") else ""
            lines.append(
                f"- `{failure.get('fixture_id')}`{judge_note}{order_note}: {failure.get('error')}"
            )
    lines += [
        "",
        "| Fixture | Judge | Order | Winner | Confidence | Human Review |",
        "|---|---|---|---|---|---|",
    ]
    for item in summary.get("judgments", []):
        raw = item.get("raw_judgment", {})
        lines.append(
            f"| `{item['fixture_id']}` | `{item['judge']['id']}` | {item['order']} | "
            f"{item['winner']} | {raw.get('confidence')} | {raw.get('human_review_needed')} |"
        )
    if summary.get("judgments"):
        lines += ["", "## Judge Summaries", ""]
        for item in summary.get("judgments", []):
            raw = item.get("raw_judgment", {})
            lines.append(
                f"### {item['fixture_id']} — {item['judge']['id']} — {item['order']}\n\n"
                f"{raw.get('executive_summary', '')}\n"
            )
    return "\n".join(lines) + "\n"


def run_suite(
    suite_path: Path,
    out_dir: Path,
    *,
    backend: str,
    model: str,
    timeout: int,
    token_budget: int,
) -> dict[str, Any]:
    suite = _load_suite(suite_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    fixture_runs: list[dict[str, Any]] = []
    for fixture in suite["fixtures"]:
        fixture_out = out_dir / _safe_name(fixture["id"])
        try:
            run = run_harness(
                fixture["corpus_path"],
                fixture["expected_path"],
                fixture_out,
                backend=backend,
                model=model,
                timeout=timeout,
                token_budget=token_budget,
            )
        except SystemExit as exc:
            run_path = fixture_out / "run.json"
            if run_path.exists():
                run = _load_json(run_path)
            else:
                run = {"backend": backend, "model": model, "commands": [], "score": {"scores": {}}}
            run["error"] = str(exc)
        fixture_runs.append(
            {**run, "fixture_id": fixture["id"], "artifact_dir": str(fixture_out.resolve())}
        )
    summary = {
        "backend": backend,
        "model": model,
        "suite_path": str(suite_path.resolve()),
        "suite_version": suite.get("version"),
        "suite_contract_sha256": _suite_contract_sha256(suite_path, suite),
        "suite_corpus_sha256": _suite_corpus_sha256(suite_path, suite),
        "extraction_prompt_sha256": _extraction_prompt_sha256(),
        "operational_config": _evaluation_operational_config(
            backend=backend,
            model=model,
            timeout=timeout,
            token_budget=token_budget,
        ),
        "git_state": _git_evidence(),
        **_aggregate_suite(suite, fixture_runs),
    }
    _write_json(out_dir / "suite-run.json", summary)
    (out_dir / "SUMMARY.md").write_text(
        _suite_markdown(summary, backend=backend, model=model), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Graphify semantic model quality harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    score_p = sub.add_parser("score", help="score an existing graphify-out graph")
    score_p.add_argument("--graph", required=True, type=Path)
    score_p.add_argument("--expected", required=True, type=Path)
    score_p.add_argument("--labels", type=Path)
    score_p.add_argument("--out", type=Path)

    run_p = sub.add_parser("run", help="run Graphify on a corpus and score the output")
    run_p.add_argument("--corpus", required=True, type=Path)
    run_p.add_argument("--expected", required=True, type=Path)
    run_p.add_argument("--out-dir", required=True, type=Path)
    run_p.add_argument("--backend", required=True)
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--timeout", type=int, default=180)
    run_p.add_argument("--token-budget", type=int, default=1200)

    suite_p = sub.add_parser("run-suite", help="run all fixtures in a semantic eval suite")
    suite_p.add_argument("--suite", required=True, type=Path)
    suite_p.add_argument("--out-dir", required=True, type=Path)
    suite_p.add_argument("--backend", required=True)
    suite_p.add_argument("--model", required=True)
    suite_p.add_argument("--timeout", type=int, default=180)
    suite_p.add_argument("--token-budget", type=int, default=1200)

    compare_p = sub.add_parser("compare", help="compare two suite-run.json artifacts")
    compare_p.add_argument("--baseline", required=True, type=Path)
    compare_p.add_argument("--candidate", required=True, type=Path)
    compare_p.add_argument("--out", type=Path)

    rebaseline_p = sub.add_parser(
        "rebaseline-saved", help="offline re-score saved .semantic-evals graph artifacts"
    )
    rebaseline_p.add_argument("--root", type=Path, default=Path(".semantic-evals"))
    rebaseline_p.add_argument(
        "--suite", type=Path, default=Path("tests/fixtures/semantic_eval/suite.json")
    )
    rebaseline_p.add_argument(
        "--out-dir",
        type=Path,
        default=Path(f".semantic-evals/comparisons/scorer-v{SCORER_VERSION}-rebaseline"),
    )

    judge_suite_p = sub.add_parser("judge-suite", help="LLM-judge one suite-run.json artifact")
    judge_suite_p.add_argument("--suite-run", required=True, type=Path)
    judge_suite_p.add_argument("--out-dir", required=True, type=Path)
    judge_suite_p.add_argument(
        "--judge", action="append", required=True, help="judge backend:model; repeat for two judges"
    )
    judge_suite_p.add_argument(
        "--allow-external-judge",
        action="store_true",
        help="acknowledge that fixture sources, expected contracts, graph samples, and judge images (if enabled) are sent to the judge backend",
    )
    judge_suite_p.add_argument(
        "--include-images",
        action="store_true",
        help="attach fixture image pixels to judge requests when the judge backend supports vision",
    )

    judge_compare_p = sub.add_parser(
        "judge-compare", help="LLM-judge two suite-run.json artifacts pairwise"
    )
    judge_compare_p.add_argument("--baseline", required=True, type=Path)
    judge_compare_p.add_argument("--candidate", required=True, type=Path)
    judge_compare_p.add_argument("--out-dir", required=True, type=Path)
    judge_compare_p.add_argument(
        "--judge", action="append", required=True, help="judge backend:model; repeat for two judges"
    )
    judge_compare_p.add_argument(
        "--allow-external-judge",
        action="store_true",
        help="acknowledge that fixture sources, expected contracts, graph samples, and judge images (if enabled) are sent to the judge backend",
    )
    judge_compare_p.add_argument(
        "--include-images",
        action="store_true",
        help="attach fixture image pixels to judge requests when the judge backend supports vision",
    )

    args = parser.parse_args(argv)
    if args.cmd == "score":
        result = score_graph(args.graph, args.expected, labels_path=args.labels)
        text = json.dumps(result, indent=2, ensure_ascii=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0

    if args.cmd == "run":
        summary = run_harness(
            args.corpus,
            args.expected,
            args.out_dir,
            backend=args.backend,
            model=args.model,
            timeout=args.timeout,
            token_budget=args.token_budget,
        )
        print(json.dumps(summary["score"]["scores"], indent=2))
        print(f"wrote {args.out_dir / 'EVALUATION.md'}")
        return 0

    if args.cmd == "run-suite":
        summary = run_suite(
            args.suite,
            args.out_dir,
            backend=args.backend,
            model=args.model,
            timeout=args.timeout,
            token_budget=args.token_budget,
        )
        print(json.dumps(summary["scores"], indent=2))
        print(f"wrote {args.out_dir / 'SUMMARY.md'}")
        return 1 if summary.get("failures") or not summary.get("gate_passed", True) else 0

    if args.cmd == "compare":
        comparison = compare_suite_runs(args.baseline, args.candidate)
        text = json.dumps(comparison, indent=2, ensure_ascii=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
            args.out.with_suffix(".md").write_text(
                _comparison_markdown(comparison), encoding="utf-8"
            )
        print(text)
        return 0

    if args.cmd == "rebaseline-saved":
        payload = rebaseline_saved_artifacts(args.root, args.suite, args.out_dir)
        print(
            json.dumps(
                {
                    "processed_graphs": payload["summary"]["processed_graphs"],
                    "processed_runs": payload["summary"]["processed_runs"],
                    "skipped_artifacts": payload["summary"]["skipped_artifacts"],
                    "artifact_dir": str(args.out_dir),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "judge-suite":
        _require_external_judge_allowed(allow_external_judge=args.allow_external_judge)
        summary = judge_suite_run(
            args.suite_run,
            args.out_dir,
            judges=args.judge,
            include_images=args.include_images,
        )
        print(
            json.dumps(
                {"judgments": len(summary["results"]), "judges": summary["judges"]}, indent=2
            )
        )
        print(f"wrote {args.out_dir / 'JUDGE_REPORT.md'}")
        return 0

    if args.cmd == "judge-compare":
        _require_external_judge_allowed(allow_external_judge=args.allow_external_judge)
        summary = judge_compare_suite_runs(
            args.baseline,
            args.candidate,
            args.out_dir,
            judges=args.judge,
            include_images=args.include_images,
        )
        print(
            json.dumps(
                {"consensus": summary["consensus"], "votes": summary["vote_counts"]}, indent=2
            )
        )
        print(f"wrote {args.out_dir / 'PAIRWISE_REPORT.md'}")
        return 0 if summary["consensus"] == "candidate" else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
