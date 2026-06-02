"""Tests for graphify.semantic_eval."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from graphify.semantic_eval import score_graph


FIXTURES = Path(__file__).parent / "fixtures" / "semantic_eval"


def test_score_graph_flags_known_smoke_weaknesses():
    result = score_graph(
        FIXTURES / "payment_retry_graph" / "graphify-out" / "graph.json",
        FIXTURES / "payment_retry" / "expected.json",
        labels_path=FIXTURES / "payment_retry_graph" / "graphify-out" / ".graphify_labels.json",
    )

    assert result["nodes"] == 15
    assert result["edges"] == 11
    assert result["scores"]["concept_recall"] == 1.0
    assert result["scores"]["community_labels"] == 1.0
    assert result["scores"]["deduplication"] < 1.0
    assert result["scores"]["relation_specificity"] < 1.0
    assert result["scores"]["inferred_confidence_calibration"] == 0.0
    assert "retry schedule" in result["details"]["duplicate_watchlist_hits"]
    assert result["details"]["overconfident_inferred_edges"]


def test_score_graph_cli_outputs_json(tmp_path):
    out = tmp_path / "score.json"
    cmd = [
        sys.executable,
        "-m",
        "graphify.semantic_eval",
        "score",
        "--graph",
        str(FIXTURES / "payment_retry_graph" / "graphify-out" / "graph.json"),
        "--expected",
        str(FIXTURES / "payment_retry" / "expected.json"),
        "--labels",
        str(FIXTURES / "payment_retry_graph" / "graphify-out" / ".graphify_labels.json"),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["scores"]["concept_recall"] == 1.0
    assert "overall" in payload["scores"]
