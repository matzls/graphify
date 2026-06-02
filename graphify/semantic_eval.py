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
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


_WORD_RE = re.compile(r"[a-z0-9]+")


def _norm(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _copy_corpus(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

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


def _relation_specificity(links: list[dict[str, Any]], generic_relations: set[str]) -> dict[str, Any]:
    if not links:
        return {"score": 0.0, "generic": 0, "total": 0}
    generic = sum(1 for e in links if str(e.get("relation", "")).lower() in generic_relations)
    return {
        "score": round((len(links) - generic) / len(links), 3),
        "generic": generic,
        "total": len(links),
    }


def score_graph(graph_path: Path, expected_path: Path, *, labels_path: Path | None = None) -> dict[str, Any]:
    graph = _load_json(graph_path)
    expected = _load_json(expected_path)
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    labels = _load_json(labels_path) if labels_path and labels_path.exists() else {}

    labels_by_norm: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        label = str(node.get("label", ""))
        if label:
            labels_by_norm.setdefault(_norm(label), []).append(node)

    required = [_norm(c) for c in expected.get("required_concepts", [])]
    found_required = [c for c in required if c in labels_by_norm]
    missing_required = [c for c in required if c not in labels_by_norm]

    duplicate_watchlist = [_norm(c) for c in expected.get("dedup_watchlist", [])]
    duplicate_hits = {
        c: [
            {
                "id": n.get("id"),
                "label": n.get("label"),
                "source_file": n.get("source_file"),
            }
            for n in labels_by_norm.get(c, [])
        ]
        for c in duplicate_watchlist
        if len(labels_by_norm.get(c, [])) > 1
    }

    inferred_edges = [e for e in links if str(e.get("confidence", "")).upper() == "INFERRED"]
    overconfident_inferred = [
        {
            "source": e.get("source"),
            "target": e.get("target"),
            "relation": e.get("relation"),
            "confidence_score": e.get("confidence_score"),
        }
        for e in inferred_edges
        if float(e.get("confidence_score", 0) or 0) >= 1.0
    ]

    generic_relations = {str(r).lower() for r in expected.get("generic_relations", ["references"])}
    relation_specificity = _relation_specificity(links, generic_relations)
    community_labels = _community_label_hits(labels, expected.get("expected_community_label_terms", []))

    concept_recall = round(len(found_required) / len(required), 3) if required else None
    dedup_score = (
        round((len(duplicate_watchlist) - len(duplicate_hits)) / len(duplicate_watchlist), 3)
        if duplicate_watchlist
        else None
    )
    inferred_confidence_score = (
        round((len(inferred_edges) - len(overconfident_inferred)) / len(inferred_edges), 3)
        if inferred_edges
        else None
    )

    numeric_scores = [
        s
        for s in [
            concept_recall,
            dedup_score,
            community_labels["score"],
            relation_specificity["score"],
            inferred_confidence_score,
        ]
        if s is not None
    ]

    return {
        "graph_path": str(graph_path),
        "expected_path": str(expected_path),
        "nodes": len(nodes),
        "edges": len(links),
        "scores": {
            "overall": round(sum(numeric_scores) / len(numeric_scores), 3) if numeric_scores else None,
            "concept_recall": concept_recall,
            "deduplication": dedup_score,
            "community_labels": community_labels["score"],
            "relation_specificity": relation_specificity["score"],
            "inferred_confidence_calibration": inferred_confidence_score,
        },
        "details": {
            "missing_required_concepts": missing_required,
            "duplicate_watchlist_hits": duplicate_hits,
            "community_label_hits": community_labels["hits"],
            "community_label_misses": community_labels["misses"],
            "generic_relations": relation_specificity,
            "inferred_edges": len(inferred_edges),
            "overconfident_inferred_edges": overconfident_inferred,
        },
    }


def _markdown_report(result: dict[str, Any], *, backend: str | None = None, model: str | None = None) -> str:
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
                shutil.rmtree(artifact_root)
            shutil.copytree(run_root, artifact_root)
            summary = {"backend": backend, "model": model, "commands": command_results}
            _write_json(out_dir / "run.json", summary)
            raise SystemExit(f"semantic eval command failed: {' '.join(cmd)}")

    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    shutil.copytree(run_root, artifact_root)

    score = score_graph(
        artifact_root / "graphify-out" / "graph.json",
        expected,
        labels_path=artifact_root / "graphify-out" / ".graphify_labels.json",
    )
    summary = {"backend": backend, "model": model, "commands": command_results, "score": score}
    _write_json(out_dir / "run.json", summary)
    (out_dir / "EVALUATION.md").write_text(
        _markdown_report(score, backend=backend, model=model),
        encoding="utf-8",
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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
