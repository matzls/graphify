"""Tests for graphify.semantic_eval."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from graphify import semantic_eval
from graphify.semantic_eval import (
    compare_suite_runs,
    judge_compare_suite_runs,
    judge_suite_run,
    run_suite,
    score_graph,
)


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
    try:
        payload = json.loads(out.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError("score CLI did not write valid JSON") from exc
    assert payload["scorer_version"] == semantic_eval.SCORER_VERSION
    assert payload["scores"]["concept_recall"] == 1.0
    assert "overall" in payload["scores"]


def test_score_graph_supports_aliases_edges_forbidden_and_source_coverage():
    result = score_graph(
        FIXTURES / "router_privacy_graph" / "graph.json",
        FIXTURES / "router_privacy" / "expected.json",
        labels_path=FIXTURES / "router_privacy_graph" / "labels.json",
    )

    assert result["scores"]["concept_recall"] == 1.0
    assert result["scores"]["deduplication"] == 1.0
    assert result["scores"]["expected_edge_coverage"] == 1.0
    assert result["scores"]["forbidden_concepts_absent"] == 1.0
    assert result["scores"]["forbidden_edges_absent"] == 1.0
    assert result["scores"]["source_coverage"] == 1.0
    assert result["details"]["missing_expected_edges"] == []
    assert result["details"]["forbidden_concept_hits"] == {}


def test_score_graph_folds_plural_and_camelcase_mechanical_variants(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "stale_state_marker", "label": "Stale-State Markers"},
                    {"id": "embedding_job", "label": "EmbeddingJob"},
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps(
            {
                "required_concepts": [
                    "stale state marker",
                    "embedding job",
                ],
                "dedup_watchlist": ["stale state markers"],
            }
        ),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    assert result["scores"]["concept_recall"] == 1.0
    assert result["scores"]["deduplication"] == 1.0


def test_score_graph_keeps_mechanical_folding_conservative(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "retry_policy", "label": "Retry Policy"},
                    {"id": "addres", "label": "Addres"},
                    {"id": "gateway_service", "label": "GatewayService"},
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps(
            {
                "required_concepts": [
                    "retry limit",
                    "address",
                    "integration gateway",
                ]
            }
        ),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    assert result["scores"]["concept_recall"] == 0.0
    assert result["details"]["missing_required_concepts"] == [
        "retry limit",
        "address",
        "integration gateway",
    ]


def test_score_graph_reports_near_misses_without_counting_them(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "failed_card_payment",
                        "label": "Failed Card Payment",
                        "source_file": "retry_policy.md",
                    }
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps({"required_concepts": ["Card Payments"]}),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    assert result["scores"]["concept_recall"] == 0.0
    assert result["details"]["missing_required_concepts"] == ["card payments"]
    diagnostics = result["details"]["missing_required_concept_diagnostics"]
    assert diagnostics[0]["concept"] == "card payments"
    assert diagnostics[0]["near_matches"][0]["label"] == "Failed Card Payment"


def test_score_graph_reports_expected_edge_relation_mismatch(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "billing", "label": "Billing Service", "source_file": "a.md"},
                    {"id": "gateway", "label": "Gateway Response", "source_file": "a.md"},
                ],
                "links": [
                    {
                        "source": "billing",
                        "target": "gateway",
                        "relation": "references",
                        "confidence": "EXTRACTED",
                        "source_file": "a.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps(
            {
                "expected_edges": [
                    {
                        "source": "Billing Service",
                        "target": "Gateway Response",
                        "relation_terms": ["records"],
                    }
                ],
                "generic_relations": [],
            }
        ),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    assert result["scorer_version"] == semantic_eval.SCORER_VERSION
    assert result["scores"]["overall"] == 1.0
    assert result["scores"]["expected_edge_coverage"] == 1.0
    assert result["scores"]["expected_edge_relation_agreement"] == 0.0
    assert result["details"]["missing_expected_edges"] == []
    assert result["details"]["expected_edge_relation_mismatches"] == [
        {
            "source": "Billing Service",
            "target": "Gateway Response",
            "relation_terms": ["records"],
            "candidate_relations": ["references"],
        }
    ]
    diagnostics = result["details"]["missing_expected_edge_diagnostics"]
    assert diagnostics[0]["failure_reason"] == "relation_mismatch"
    assert diagnostics[0]["source_found"]
    assert diagnostics[0]["target_found"]
    assert diagnostics[0]["candidate_edges"][0]["relation"] == "references"


def test_score_graph_reports_expected_edge_relation_agreement_and_undirected_match(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "source", "label": "Source Concept", "source_file": "a.md"},
                    {"id": "target", "label": "Target Concept", "source_file": "a.md"},
                    {"id": "left", "label": "Left Concept", "source_file": "a.md"},
                    {"id": "right", "label": "Right Concept", "source_file": "a.md"},
                ],
                "links": [
                    {
                        "source": "source",
                        "target": "target",
                        "relation": "writes",
                        "source_file": "a.md",
                    },
                    {
                        "source": "right",
                        "target": "left",
                        "relation": "routes",
                        "source_file": "a.md",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps(
            {
                "expected_edges": [
                    {
                        "source": "Source Concept",
                        "target": "Target Concept",
                        "relation_terms": ["writes"],
                        "directed": True,
                    },
                    {
                        "source": "Left Concept",
                        "target": "Right Concept",
                        "relation_terms": ["routes"],
                    },
                ],
                "generic_relations": [],
            }
        ),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    assert result["scores"]["expected_edge_coverage"] == 1.0
    assert result["scores"]["expected_edge_relation_agreement"] == 1.0
    assert result["details"]["missing_expected_edges"] == []
    assert result["details"]["expected_edge_relation_mismatches"] == []
    assert result["details"]["missing_expected_edge_diagnostics"] == []


def test_score_graph_reports_expected_edge_missing_endpoint(tmp_path):
    graph = tmp_path / "graph.json"
    expected = tmp_path / "expected.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "billing", "label": "Billing Service", "source_file": "a.md"},
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    expected.write_text(
        json.dumps(
            {
                "expected_edges": [
                    {
                        "source": "Billing Service",
                        "target": "Gateway Response",
                        "relation_terms": ["records"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = score_graph(graph, expected)

    diagnostics = result["details"]["missing_expected_edge_diagnostics"]
    assert diagnostics[0]["failure_reason"] == "endpoint_miss"
    assert diagnostics[0]["endpoint_miss"] == "target"
    assert diagnostics[0]["source_found"]
    assert not diagnostics[0]["target_found"]


def test_score_graph_penalizes_degraded_router_graph():
    result = score_graph(
        FIXTURES / "router_privacy_bad_graph" / "graph.json",
        FIXTURES / "router_privacy" / "expected.json",
        labels_path=FIXTURES / "router_privacy_bad_graph" / "labels.json",
    )

    assert result["scores"]["concept_recall"] < 1.0
    assert result["scores"]["deduplication"] < 1.0
    assert result["scores"]["expected_edge_coverage"] < 1.0
    assert result["scores"]["forbidden_concepts_absent"] == 0.0
    assert result["scores"]["forbidden_edges_absent"] == 0.0
    assert result["scores"]["inferred_confidence_calibration"] == 0.0
    assert "redaction stage" in result["details"]["duplicate_watchlist_hits"]
    assert result["details"]["forbidden_edge_hits"]


def test_score_graph_covers_public_realistic_graphify_slice():
    result = score_graph(
        FIXTURES / "graphify_public_slice_graph" / "graph.json",
        FIXTURES / "graphify_public_slice" / "expected.json",
        labels_path=FIXTURES / "graphify_public_slice_graph" / "labels.json",
    )

    assert result["scores"]["overall"] == 1.0
    assert result["scores"]["source_coverage"] == 1.0
    assert result["details"]["forbidden_concept_hits"] == {}


def test_score_graph_covers_image_diagram_fixture():
    diagram = FIXTURES / "diagram_workflow" / "diagram.png"
    assert diagram.read_bytes().startswith(b"\x89PNG")

    result = score_graph(
        FIXTURES / "diagram_workflow_graph" / "graph.json",
        FIXTURES / "diagram_workflow" / "expected.json",
        labels_path=FIXTURES / "diagram_workflow_graph" / "labels.json",
    )

    assert result["scores"]["overall"] == 1.0
    assert result["scores"]["expected_edge_coverage"] == 1.0
    assert result["scores"]["source_coverage"] == 1.0


def test_suite_manifest_paths_resolve():
    suite = semantic_eval._load_suite(FIXTURES / "suite.json")

    assert [fixture["id"] for fixture in suite["fixtures"]] == [
        "payment_retry",
        "router_privacy",
        "workflow_migration",
        "integration_gateway",
        "graphify_public_slice",
        "diagram_workflow",
    ]
    for fixture in suite["fixtures"]:
        assert fixture["corpus_path"].is_dir()
        assert fixture["expected_path"].is_file()


def test_suite_manifest_validation_rejects_duplicate_ids(tmp_path):
    suite = tmp_path / "suite.json"
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    expected = tmp_path / "expected.json"
    expected.write_text("{}", encoding="utf-8")
    suite.write_text(
        json.dumps(
            {
                "fixtures": [
                    {"id": "dup", "corpus": "corpus", "expected": "expected.json"},
                    {"id": "dup", "corpus": "corpus", "expected": "expected.json"},
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        semantic_eval._load_suite(suite)
    except ValueError as exc:
        assert "duplicated" in str(exc)
    else:
        raise AssertionError("duplicate suite fixture ids should be rejected")


def test_run_harness_stamps_success_and_failure_run_payloads(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "source.md").write_text("# Source\n", encoding="utf-8")
    expected = tmp_path / "expected.json"
    expected.write_text("{}", encoding="utf-8")

    def fake_success_cmd(cmd, *, cwd, env, timeout):
        if "extract" in cmd:
            run_root = Path(cmd[cmd.index("extract") + 1])
            graph_out = run_root / "graphify-out"
            graph_out.mkdir(parents=True, exist_ok=True)
            (graph_out / "graph.json").write_text(
                json.dumps({"nodes": [], "links": []}), encoding="utf-8"
            )
            (graph_out / ".graphify_labels.json").write_text("{}", encoding="utf-8")
        return {"returncode": 0, "elapsed_seconds": 0.0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(semantic_eval, "_run_cmd", fake_success_cmd)
    success_dir = tmp_path / "success"

    success = semantic_eval.run_harness(
        corpus,
        expected,
        success_dir,
        backend="ollama",
        model="test-model:cloud",
        timeout=1,
        token_budget=100,
    )

    try:
        success_payload = json.loads((success_dir / "run.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError("run_harness success did not write valid JSON") from exc
    assert success["scorer_version"] == semantic_eval.SCORER_VERSION
    assert success_payload["scorer_version"] == semantic_eval.SCORER_VERSION

    def fake_failure_cmd(cmd, *, cwd, env, timeout):
        return {"returncode": 1, "elapsed_seconds": 0.0, "stdout": "", "stderr": "boom"}

    monkeypatch.setattr(semantic_eval, "_run_cmd", fake_failure_cmd)
    failure_dir = tmp_path / "failure"

    try:
        semantic_eval.run_harness(
            corpus,
            expected,
            failure_dir,
            backend="ollama",
            model="test-model:cloud",
            timeout=1,
            token_budget=100,
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("run_harness should fail when the command fails")

    try:
        failure_payload = json.loads((failure_dir / "run.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError("run_harness failure did not write valid JSON") from exc
    assert failure_payload["scorer_version"] == semantic_eval.SCORER_VERSION


def test_run_suite_aggregates_fixture_scores_without_live_model_calls(tmp_path, monkeypatch):
    def fake_run_harness(corpus, expected, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        fixture_id = out_dir.name
        overall = 1.0 if fixture_id == "payment_retry" else 0.5
        return {
            "backend": backend,
            "model": model,
            "commands": [
                {
                    "returncode": 0,
                    "elapsed_seconds": 2.5,
                    "stdout": "[graphify extract] tokens: 10 in / 20 out",
                    "stderr": "",
                }
            ],
            "score": {
                "scores": {
                    "overall": overall,
                    "concept_recall": overall,
                    "expected_edge_coverage": overall,
                },
                "details": {
                    "missing_expected_edge_diagnostics": [
                        {
                            "source": "Billing Service",
                            "target": "Gateway Response",
                            "failure_reason": "relation_mismatch",
                            "source_found": True,
                            "target_found": True,
                            "candidate_edges": [{"relation": "references"}],
                        }
                    ]
                    if fixture_id == "payment_retry"
                    else []
                },
            },
        }

    monkeypatch.setattr(semantic_eval, "run_harness", fake_run_harness)

    summary = run_suite(
        FIXTURES / "suite.json",
        tmp_path / "suite-run",
        backend="ollama",
        model="test-model:cloud",
        timeout=1,
        token_budget=100,
    )

    assert summary["scorer_version"] == semantic_eval.SCORER_VERSION
    assert summary["scores"]["overall"] == 0.562
    assert summary["profile_scores"]["public-realistic"] == 0.5
    assert summary["profile_scores"]["multimodal"] == 0.5
    assert summary["profile_scores"]["text-only"] == 0.577
    assert "text-only" in summary["fixtures"][0]["profiles"]
    assert "text-only" not in summary["fixtures"][-1]["profiles"]
    assert summary["fixtures"][0]["expected_edge_failures"] == [
        {
            "source": "Billing Service",
            "target": "Gateway Response",
            "failure_reason": "relation_mismatch",
            "source_found": True,
            "target_found": True,
            "candidate_relation": "references",
        }
    ]
    assert not summary["gate_passed"]
    assert summary["total_elapsed_seconds"] == 15.0
    assert summary["total_input_tokens"] == 60
    assert summary["total_output_tokens"] == 120
    assert summary["failures"] == []
    assert (tmp_path / "suite-run" / "suite-run.json").exists()
    summary_md = (tmp_path / "suite-run" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "## Expected Edge Diagnostics" in summary_md


def test_run_suite_passes_calibrated_gate_at_floor(tmp_path, monkeypatch):
    def fake_run_harness(corpus, expected, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        return {
            "backend": backend,
            "model": model,
            "commands": [],
            "score": {
                "scores": {
                    "overall": 0.7,
                    "concept_recall": 0.45,
                    "expected_edge_coverage": 0.45,
                    "forbidden_concepts_absent": 1.0,
                    "forbidden_edges_absent": 1.0,
                    "source_coverage": 0.45,
                }
            },
        }

    monkeypatch.setattr(semantic_eval, "run_harness", fake_run_harness)

    summary = run_suite(
        FIXTURES / "suite.json",
        tmp_path / "suite-run-pass",
        backend="ollama",
        model="test-model:cloud",
        timeout=1,
        token_budget=100,
    )

    assert summary["gate_passed"]
    assert summary["gate_failures"] == []


def test_run_suite_fails_when_critical_dimension_below_calibrated_floor(tmp_path, monkeypatch):
    def fake_run_harness(corpus, expected, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        return {
            "backend": backend,
            "model": model,
            "commands": [],
            "score": {
                "scores": {
                    "overall": 0.71,
                    "concept_recall": 0.71,
                    "expected_edge_coverage": 0.449,
                    "forbidden_concepts_absent": 1.0,
                    "forbidden_edges_absent": 1.0,
                    "source_coverage": 1.0,
                }
            },
        }

    monkeypatch.setattr(semantic_eval, "run_harness", fake_run_harness)

    summary = run_suite(
        FIXTURES / "suite.json",
        tmp_path / "suite-run-critical-fail",
        backend="ollama",
        model="test-model:cloud",
        timeout=1,
        token_budget=100,
    )

    assert not summary["gate_passed"]
    assert summary["gate_failures"] == [
        "expected_edge_coverage 0.449 < minimum_critical_dimension 0.45"
    ]


def test_run_suite_records_fixture_failures_without_live_model_calls(tmp_path, monkeypatch):
    def fake_run_harness(corpus, expected, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        if out_dir.name == "router_privacy":
            (out_dir / "run.json").write_text(
                json.dumps(
                    {
                        "backend": backend,
                        "model": model,
                        "commands": [{"returncode": 1, "elapsed_seconds": 1.0}],
                        "score": {"scores": {}},
                    }
                ),
                encoding="utf-8",
            )
            raise SystemExit("router failed")
        return {
            "backend": backend,
            "model": model,
            "commands": [{"returncode": 0, "elapsed_seconds": 1.0}],
            "score": {"scores": {"overall": 1.0}},
        }

    monkeypatch.setattr(semantic_eval, "run_harness", fake_run_harness)

    summary = run_suite(
        FIXTURES / "suite.json",
        tmp_path / "suite-run-failure",
        backend="ollama",
        model="test-model:cloud",
        timeout=1,
        token_budget=100,
    )

    assert summary["failures"] == [{"id": "router_privacy", "error": "router failed"}]
    assert not summary["gate_passed"]
    assert "1 fixture(s) failed" in summary["gate_failures"]
    assert summary["fixtures"][1]["error"] == "router failed"
    summary_md = (tmp_path / "suite-run-failure" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "Quality gate: fail" in summary_md
    assert summary_md.count("router failed") == 1
    assert summary_md.count("## Fixture Scores") == 1


def test_run_suite_fails_gate_when_no_fixture_scores_complete(tmp_path, monkeypatch):
    def fake_run_harness(corpus, expected, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run.json").write_text(
            json.dumps(
                {
                    "backend": backend,
                    "model": model,
                    "commands": [{"returncode": 1, "elapsed_seconds": 1.0}],
                    "score": {"scores": {}},
                }
            ),
            encoding="utf-8",
        )
        raise SystemExit(f"{out_dir.name} failed")

    monkeypatch.setattr(semantic_eval, "run_harness", fake_run_harness)

    summary = run_suite(
        FIXTURES / "suite.json",
        tmp_path / "suite-run-all-failed",
        backend="ollama",
        model="deepseek-v4-flash:cloud",
        timeout=1,
        token_budget=100,
    )

    assert summary["scores"] == {}
    assert not summary["gate_passed"]
    assert "6 fixture(s) failed" in summary["gate_failures"]
    assert "no scored fixtures completed" in summary["gate_failures"]
    summary_md = (tmp_path / "suite-run-all-failed" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "Weighted overall: None" in summary_md
    assert "Quality gate: fail" in summary_md


def test_parse_judge_spec_allows_colon_in_model_name():
    assert semantic_eval._parse_judge_spec("ollama:kimi-k2.7-code:cloud") == {
        "backend": "ollama",
        "model": "kimi-k2.7-code:cloud",
        "id": "ollama:kimi-k2.7-code:cloud",
    }


def test_compare_suite_runs_reports_fixture_and_dimension_deltas(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(
        json.dumps(
            {
                "backend": "ollama",
                "model": "baseline-model",
                "gate_passed": True,
                "scores": {"overall": 0.7, "concept_recall": 0.8},
                "fixtures": [
                    {"id": "a", "overall": 0.8},
                    {"id": "b", "overall": 0.6},
                ],
            }
        ),
        encoding="utf-8",
    )
    candidate.write_text(
        json.dumps(
            {
                "backend": "ollama",
                "model": "candidate-model",
                "gate_passed": True,
                "scores": {"overall": 0.75, "concept_recall": 0.7},
                "fixtures": [
                    {"id": "a", "overall": 0.9},
                    {"id": "b", "overall": 0.5},
                ],
            }
        ),
        encoding="utf-8",
    )

    comparison = compare_suite_runs(baseline, candidate)

    assert comparison["warnings"] == []
    assert comparison["score_deltas"] == {"concept_recall": -0.1, "overall": 0.05}
    assert comparison["improvements"] == [
        {
            "id": "a",
            "baseline_overall": 0.8,
            "candidate_overall": 0.9,
            "delta": 0.1,
            "baseline_error": None,
            "candidate_error": None,
        }
    ]
    assert comparison["regressions"][0]["id"] == "b"


def test_compare_suite_runs_warns_when_scorer_versions_differ(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(
        json.dumps({"scorer_version": 1, "scores": {"overall": 0.5}, "fixtures": []}),
        encoding="utf-8",
    )
    candidate.write_text(
        json.dumps({"scorer_version": 2, "scores": {"overall": 0.75}, "fixtures": []}),
        encoding="utf-8",
    )

    comparison = compare_suite_runs(baseline, candidate)

    assert comparison["scorer_version"] == semantic_eval.SCORER_VERSION
    assert comparison["baseline"]["scorer_version"] == 1
    assert comparison["candidate"]["scorer_version"] == 2
    assert comparison["warnings"] == ["scorer_version mismatch: baseline=1, candidate=2"]


def test_compare_cli_writes_json_and_markdown(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "comparison.json"
    baseline.write_text(
        json.dumps({"model": "baseline", "scores": {"overall": 0.5}, "fixtures": []}),
        encoding="utf-8",
    )
    candidate.write_text(
        json.dumps({"model": "candidate", "scores": {"overall": 0.75}, "fixtures": []}),
        encoding="utf-8",
    )

    assert (
        semantic_eval.main(
            [
                "compare",
                "--baseline",
                str(baseline),
                "--candidate",
                str(candidate),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    try:
        payload = json.loads(out.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError("comparison CLI did not write valid JSON") from exc
    assert payload["scorer_version"] == semantic_eval.SCORER_VERSION
    assert payload["score_deltas"]["overall"] == 0.25
    assert out.with_suffix(".md").exists()


def test_run_suite_cli_returns_one_when_fixture_fails(tmp_path, monkeypatch):
    def fake_run_suite(suite_path, out_dir, *, backend, model, timeout, token_budget):
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "backend": backend,
            "model": model,
            "suite": "test-suite",
            "scores": {},
            "total_elapsed_seconds": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "fixtures": [{"id": "fixture", "error": "failed"}],
            "failures": [{"id": "fixture", "error": "failed"}],
        }
        (out_dir / "SUMMARY.md").write_text("failed", encoding="utf-8")
        return summary

    monkeypatch.setattr(semantic_eval, "run_suite", fake_run_suite)

    assert (
        semantic_eval.main(
            [
                "run-suite",
                "--suite",
                str(FIXTURES / "suite.json"),
                "--out-dir",
                str(tmp_path / "cli-suite"),
                "--backend",
                "ollama",
                "--model",
                "test-model:cloud",
            ]
        )
        == 1
    )


def _write_fake_suite_run(tmp_path, *, name="run", model="model-a"):
    artifact_dir = tmp_path / name / "router_privacy"
    graph_out = artifact_dir / "corpus" / "graphify-out"
    graph_out.mkdir(parents=True)
    shutil.copyfile(FIXTURES / "router_privacy_graph" / "graph.json", graph_out / "graph.json")
    shutil.copyfile(
        FIXTURES / "router_privacy_graph" / "labels.json", graph_out / ".graphify_labels.json"
    )
    suite = tmp_path / f"{name}-suite.json"
    suite.write_text(
        json.dumps(
            {
                "name": f"{name}-suite",
                "fixtures": [
                    {
                        "id": "router_privacy",
                        "corpus": str(FIXTURES / "router_privacy"),
                        "expected": str(FIXTURES / "router_privacy" / "expected.json"),
                        "profiles": ["synthetic", "privacy"],
                        "weight": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    suite_run = tmp_path / f"{name}-suite-run.json"
    suite_run.write_text(
        json.dumps(
            {
                "suite_path": str(suite),
                "model": model,
                "fixtures": [
                    {
                        "id": "router_privacy",
                        "artifact_dir": str(artifact_dir),
                        "scores": {"overall": 1.0, "concept_recall": 1.0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return suite_run


def test_judge_cli_requires_external_export_acknowledgement(tmp_path):
    try:
        semantic_eval.main(
            [
                "judge-suite",
                "--suite-run",
                str(tmp_path / "missing.json"),
                "--out-dir",
                str(tmp_path / "judge"),
                "--judge",
                "openai:gpt-test",
            ]
        )
    except SystemExit as exc:
        assert "--allow-external-judge" in str(exc)
    else:
        raise AssertionError("judge-suite should require explicit external judge acknowledgement")


def test_judge_suite_run_uses_configured_judge_without_live_call(tmp_path, monkeypatch):
    suite_run = _write_fake_suite_run(tmp_path)

    def fake_call(judge, system_prompt, user_prompt, *, image_paths=None):
        assert judge == {"backend": "openai", "model": "gpt-test", "id": "openai:gpt-test"}
        assert "Graphify semantic extraction quality" in system_prompt
        heading = "What Graphify " + "is"
        assert system_prompt.find(heading) >= 0
        assert "router_privacy" in user_prompt
        return {
            "scores": {
                "faithfulness": 5,
                "semantic_completeness": 5,
                "relation_quality": 4,
                "abstraction_quality": 4,
                "graph_usefulness": 5,
                "community_label_quality": 4,
                "source_grounding": 5,
                "risk_handling": 5,
            },
            "executive_summary": "The graph is source-grounded and useful for routing analysis.",
            "strengths": ["Preserves the redaction-to-classifier flow."],
            "weaknesses": ["Some labels could be more specific."],
            "evidence_examples": [
                {
                    "finding": "Redaction flow is preserved.",
                    "source_evidence": "README.md",
                    "graph_evidence": "redaction_stage -> classifier",
                }
            ],
            "critical_failures": [],
            "recommended_decision": "accept",
            "rationale": ["source-grounded graph"],
            "confidence": "high",
        }

    monkeypatch.setattr(semantic_eval, "_call_judge_model", fake_call)

    summary = judge_suite_run(suite_run, tmp_path / "judge", judges=["openai:gpt-test"])

    assert summary["results"][0]["average_score"] == 4.625
    assert (tmp_path / "judge" / "judge-run.json").exists()
    assert (tmp_path / "judge" / "JUDGE_REPORT.md").exists()


def test_call_judge_model_supports_pi_subscription_backend(monkeypatch):
    monkeypatch.setattr(semantic_eval.shutil, "which", lambda cmd: "/usr/local/bin/pi")
    calls = []

    def fake_run(args, **kwargs):
        prompt_args = [
            arg for arg in args if str(arg).startswith("@") and "judge-prompt" in str(arg)
        ]
        assert len(prompt_args) == 1
        prompt_path = Path(prompt_args[0][1:])
        assert prompt_path.read_text(encoding="utf-8") == "user"
        assert "user" not in args
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "scores": {key: 5 for key in semantic_eval._JUDGE_SCORE_KEYS},
                    "executive_summary": "Pi subscription judge worked.",
                    "strengths": ["specific"],
                    "weaknesses": [],
                    "evidence_examples": [],
                    "critical_failures": [],
                    "recommended_decision": "accept",
                    "rationale": ["valid JSON"],
                    "confidence": "high",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(semantic_eval.subprocess, "run", fake_run)

    result = semantic_eval._call_judge_model(
        {"backend": "pi", "model": "openai-codex/gpt-5.5:high", "id": "pi:test"},
        "system",
        "user",
    )

    assert result["executive_summary"] == "Pi subscription judge worked."
    args, kwargs = calls[0]
    assert args[:2] == ["pi", "--no-session"]
    assert "openai-codex/gpt-5.5:high" in args
    assert "--api-key" not in args
    assert any(str(arg).startswith("@") and "judge-prompt" in str(arg) for arg in args)
    assert kwargs["capture_output"]


def test_call_judge_model_supports_claude_cli_subscription_backend(monkeypatch):
    monkeypatch.setattr(semantic_eval.shutil, "which", lambda cmd: "/usr/local/bin/claude")
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "result": json.dumps(
                        {
                            "scores": {key: 4 for key in semantic_eval._JUDGE_SCORE_KEYS},
                            "executive_summary": "Claude subscription judge worked.",
                            "strengths": ["grounded"],
                            "weaknesses": [],
                            "evidence_examples": [],
                            "critical_failures": [],
                            "recommended_decision": "accept",
                            "rationale": ["valid JSON envelope"],
                            "confidence": "medium",
                        }
                    )
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(semantic_eval.subprocess, "run", fake_run)

    result = semantic_eval._call_judge_model(
        {"backend": "claude-cli", "model": "opus", "id": "claude-cli:opus"},
        "system",
        "user",
    )

    assert result["executive_summary"] == "Claude subscription judge worked."
    args, kwargs = calls[0]
    assert args[:2] == ["claude", "-p"]
    assert "opus" in args
    assert "--setting-sources" in args
    assert "--strict-mcp-config" in args
    assert "--tools" in args
    assert kwargs["input"] == "user"


def test_claude_cli_judge_images_are_staged_in_isolated_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_eval.shutil, "which", lambda cmd: "/usr/local/bin/claude")
    image_dir = tmp_path / "fixture"
    image_dir.mkdir()
    image = image_dir / "diagram.png"
    image.write_bytes(b"fake-png")
    secret_sibling = image_dir / "secret.txt"
    secret_sibling.write_text("do not expose", encoding="utf-8")
    seen = {}

    def fake_run(args, **kwargs):
        add_dir_index = args.index("--add-dir")
        allowed_dir = Path(args[add_dir_index + 1])
        staged_files = sorted(path.name for path in allowed_dir.iterdir())
        seen["allowed_dir"] = allowed_dir
        seen["staged_files"] = staged_files
        seen["input"] = kwargs["input"]
        assert allowed_dir != image_dir.resolve()
        assert staged_files == ["judge-image-1.png"]
        assert "secret.txt" not in staged_files
        assert str(image.resolve()) not in kwargs["input"]
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "result": json.dumps(
                        {
                            "scores": {key: 4 for key in semantic_eval._JUDGE_SCORE_KEYS},
                            "executive_summary": "Claude image staging worked.",
                            "strengths": [],
                            "weaknesses": [],
                            "evidence_examples": [],
                            "critical_failures": [],
                            "recommended_decision": "accept",
                            "rationale": [],
                            "confidence": "medium",
                        }
                    )
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(semantic_eval.subprocess, "run", fake_run)

    result = semantic_eval._call_judge_model(
        {"backend": "claude-cli", "model": "opus", "id": "claude-cli:opus"},
        "system",
        "user",
        image_paths=[image],
    )

    assert result["executive_summary"] == "Claude image staging worked."
    assert "IMAGE ATTACHMENT PATHS" in seen["input"]
    assert "judge-image-1.png" in seen["input"]


def test_judge_suite_run_records_invalid_judge_scores_as_failures(tmp_path, monkeypatch):
    suite_run = _write_fake_suite_run(tmp_path)

    def fake_call(judge, system_prompt, user_prompt, *, image_paths=None):
        return {
            "scores": {
                "faithfulness": 6,
                "semantic_completeness": 5,
                "relation_quality": 4,
                "abstraction_quality": 4,
                "graph_usefulness": 5,
                "community_label_quality": 4,
                "source_grounding": 5,
                "risk_handling": 5,
            },
            "executive_summary": "The graph would be good except the score is invalid.",
            "strengths": [],
            "weaknesses": [],
            "evidence_examples": [],
            "critical_failures": [],
            "recommended_decision": "accept",
            "rationale": [],
            "confidence": "high",
        }

    monkeypatch.setattr(semantic_eval, "_call_judge_model", fake_call)

    summary = judge_suite_run(suite_run, tmp_path / "judge", judges=["openai:gpt-test"])

    assert summary["results"] == []
    assert "must be in [1, 5]" in summary["failures"][0]["error"]
    assert (tmp_path / "judge" / "judge-run.json").exists()


def test_judge_compare_runs_both_orders_and_normalizes_votes(tmp_path, monkeypatch):
    baseline = _write_fake_suite_run(tmp_path, name="baseline", model="baseline-model")
    candidate = _write_fake_suite_run(tmp_path, name="candidate", model="candidate-model")
    calls = []

    def fake_call(judge, system_prompt, user_prompt, *, image_paths=None):
        calls.append(user_prompt)
        # Prefer candidate in both orders: first call baseline=A/candidate=B -> B;
        # second call candidate=A/baseline=B -> A.
        winner = "B" if len(calls) == 1 else "A"
        return {
            "winner": winner,
            "confidence": "medium",
            "dimension_winners": {key: winner for key in semantic_eval._JUDGE_SCORE_KEYS},
            "executive_summary": "The candidate graph is better for this fixture.",
            "graph_a_strengths": ["good coverage"],
            "graph_b_strengths": ["better relations"],
            "graph_a_weaknesses": [],
            "graph_b_weaknesses": [],
            "candidate_regressions_if_identifiable_from_context": [],
            "critical_failures": [],
            "human_review_needed": False,
            "rationale": ["candidate is better"],
        }

    monkeypatch.setattr(semantic_eval, "_call_judge_model", fake_call)

    summary = judge_compare_suite_runs(
        baseline,
        candidate,
        tmp_path / "pairwise",
        judges=["claude:opus-test"],
    )

    assert len(calls) == 2
    assert summary["vote_counts"] == {"baseline": 0, "candidate": 2, "tie": 0}
    assert summary["consensus"] == "candidate"
    assert (tmp_path / "pairwise" / "pairwise-judge.json").exists()
    assert (tmp_path / "pairwise" / "PAIRWISE_REPORT.md").exists()
