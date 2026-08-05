#!/usr/bin/env python3
"""Run the explicitly authorized five-attempt Graphify/Pi backend canary.

The command is inert unless ``--live`` is present.  It never stores prompts,
model responses, credentials, image bytes, parent session identifiers, or raw
subprocess output in the receipt.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graphify.cache import check_semantic_cache
from graphify.llm import _extraction_system, _pack_chunks_by_tokens
from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
    CAMPAIGN_ENV_KEYS,
    CANARY_FAILURE_CODES,
    MAX_CAMPAIGN_ATTEMPTS,
    CanaryStateError,
    campaign_environment,
    create_campaign,
    new_campaign_id,
    prove_sixth_denied,
    read_campaign,
)
from graphify.semantic_eval import score_graph

AUTHORIZED_MODEL = "openai-codex/gpt-5.6-luna"
AUTHORIZED_THINKING = "high"
TOKEN_BUDGET = 60_000
CANARY_MAX_OUTPUT_TOKENS = 32_768
CANARY_API_TIMEOUT_SECONDS = 540
CANARY_CAPABILITY_COMMANDS = 3
CANARY_CAPABILITY_TIMEOUT_SECONDS = 30
CANARY_CLEANUP_MARGIN_SECONDS = 30
# Each Graphify stage may spend the model deadline plus three bounded Pi
# capability checks. Keep a positive margin for process-tree cleanup and
# receipt finalization so the outer subprocess cannot undercut that budget.
COMMAND_TIMEOUT_SECONDS = (
    CANARY_API_TIMEOUT_SECONDS
    + CANARY_CAPABILITY_COMMANDS * CANARY_CAPABILITY_TIMEOUT_SECONDS
    + CANARY_CLEANUP_MARGIN_SECONDS
)

_FIXTURE_HASHES = {
    "tests/fixtures/semantic_eval/graphify_public_slice/architecture_excerpt.md": "e82b620b360cc91c8b1fd458a57b6f892a56e0940d1c0170f01b2e076f763221",
    "tests/fixtures/semantic_eval/graphify_public_slice/backend_excerpt.md": "c7eb26d7f4736bbfe9b804df9a12306eb6a50922ff020629232d7eae380e9226",
    "tests/fixtures/semantic_eval/graphify_public_slice/expected.json": "0be806da2552f56e53176d1cba7cb1829c6c591ad16d545ec15197822290a951",
    "tests/fixtures/semantic_eval/graphify_public_slice/llm_backend_excerpt.py": "91298a67d54dbe3cd9b2046c8b469dbfd06bb3d39cf2b2df5c80a0fad1074ca2",
    "tests/fixtures/semantic_eval/diagram_workflow/expected.json": "26280cb35d39fa9597deef6f8c7629b6118cd7e3782d5e9b2ba485d41edc122c",
    "tests/fixtures/semantic_eval/diagram_workflow/README.md": "0b6fb8f3736fd1f4a446d593409f7844d73a1680f9ec0680f61806f14d0c951e",
    "tests/fixtures/semantic_eval/diagram_workflow/diagram.png": "38180f8ddcf9234bfc8b928403654aadf7fee6aabde9d8241da430737d2395c2",
}
_TEXT_SOURCE_NAMES = (
    "architecture_excerpt.md",
    "backend_excerpt.md",
    "llm_backend_excerpt.py",
)
_IMAGE_SOURCE_NAMES = ("README.md", "diagram.png")


class CampaignFailure(RuntimeError):
    """A safe, receipt-ready campaign failure code."""


@dataclass(frozen=True)
class Stage:
    name: str
    expected_attempts: int
    command: tuple[str, ...]


@dataclass(frozen=True)
class CampaignPaths:
    out_dir: Path
    ledger: Path
    receipt: Path
    text_corpus: Path
    text_result: Path
    image_corpus: Path
    image_result: Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fail-closed five-attempt Pi backend canary. No model request "
            "is made unless --live is supplied explicitly."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="explicitly authorize the bounded live campaign after CP-2",
    )
    parser.add_argument(
        "--require-outer-pi",
        action="store_true",
        help="require evidence that the driver itself is running inside a Pi session",
    )
    parser.add_argument("--model", default=AUTHORIZED_MODEL)
    parser.add_argument("--thinking", default=AUTHORIZED_THINKING)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fixture_hashes(repo_root: Path = REPO_ROOT) -> None:
    for relative, expected in _FIXTURE_HASHES.items():
        path = repo_root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise CampaignFailure("fixture_hash_mismatch")


def _source_paths(repo_root: Path = REPO_ROOT) -> tuple[list[Path], list[Path]]:
    text_root = repo_root / "tests/fixtures/semantic_eval/graphify_public_slice"
    image_root = repo_root / "tests/fixtures/semantic_eval/diagram_workflow"
    return (
        [text_root / name for name in _TEXT_SOURCE_NAMES],
        [image_root / name for name in _IMAGE_SOURCE_NAMES],
    )


def verify_single_chunk_preflight(repo_root: Path = REPO_ROOT) -> dict[str, int]:
    text_sources, image_sources = _source_paths(repo_root)
    counts = {
        "text": len(_pack_chunks_by_tokens(text_sources, TOKEN_BUDGET)),
        "image": len(_pack_chunks_by_tokens(image_sources, TOKEN_BUDGET)),
    }
    if counts != {"text": 1, "image": 1}:
        raise CampaignFailure("fixture_chunk_preflight_failed")
    return counts


def _outer_pi_present(env: Mapping[str, str]) -> bool:
    return any(
        str(env.get(key, "")).strip()
        for key in (
            "PI_CODING_AGENT",
            "PI_CODING_AGENT_SESSION_DIR",
            "PI_SESSION_ID",
            "PI_SESSION_FILE",
        )
    )


def _campaign_paths(out_dir: Path) -> CampaignPaths:
    out = out_dir.resolve()
    return CampaignPaths(
        out_dir=out,
        ledger=out / "attempt-ledger.json",
        receipt=out / "receipt.json",
        text_corpus=out / "text-corpus",
        text_result=out / "text-result",
        image_corpus=out / "image-corpus",
        image_result=out / "image-result",
    )


def _prepare_paths(paths: CampaignPaths, repo_root: Path = REPO_ROOT) -> None:
    paths.out_dir.mkdir(parents=True, exist_ok=True)
    if any(paths.out_dir.iterdir()):
        raise CampaignFailure("output_directory_not_empty")
    paths.text_corpus.mkdir()
    paths.image_corpus.mkdir()
    text_sources, image_sources = _source_paths(repo_root)
    for source in text_sources:
        shutil.copy2(source, paths.text_corpus / source.name)
    for source in image_sources:
        shutil.copy2(source, paths.image_corpus / source.name)


def campaign_stages(
    paths: CampaignPaths,
    *,
    model: str,
    python_executable: str = sys.executable,
) -> list[Stage]:
    base = (python_executable, "-m", "graphify")
    extract_common = (
        "--backend",
        "pi",
        "--model",
        model,
        "--force",
        "--token-budget",
        str(TOKEN_BUDGET),
        "--max-concurrency",
        "1",
        "--no-cluster",
    )
    label_common = (
        "--backend",
        "pi",
        "--model",
        model,
        "--max-concurrency",
        "1",
        "--batch-size",
        "1000",
        "--no-viz",
    )
    return [
        Stage("doctor_probe", 0, base + ("doctor", "--backend", "pi", "--probe")),
        Stage(
            "text_extract",
            1,
            base
            + ("extract", str(paths.text_corpus), *extract_common, "--out", str(paths.text_result)),
        ),
        Stage("text_label", 2, base + ("cluster-only", str(paths.text_result), *label_common)),
        Stage(
            "image_extract",
            3,
            base
            + (
                "extract",
                str(paths.image_corpus),
                *extract_common,
                "--allow-image-upload",
                "--out",
                str(paths.image_result),
            ),
        ),
        Stage("image_label", 4, base + ("cluster-only", str(paths.image_result), *label_common)),
    ]


def _run_stage(
    command: Sequence[str], *, env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        env=dict(env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )


def _stage_environment(
    base_env: Mapping[str, str],
    *,
    ledger: Path,
    campaign_id: str,
    expected_attempts: int,
    model: str,
    thinking: str,
) -> dict[str, str]:
    env = {key: value for key, value in base_env.items() if key not in CAMPAIGN_ENV_KEYS}
    env.update(
        campaign_environment(
            ledger,
            campaign_id,
            expected_attempts=expected_attempts,
        )
    )
    env.update(
        {
            "GRAPHIFY_PI_MODEL": model,
            "GRAPHIFY_PI_THINKING": thinking,
            "GRAPHIFY_API_TIMEOUT": str(CANARY_API_TIMEOUT_SECONDS),
            "GRAPHIFY_MAX_OUTPUT_TOKENS": str(CANARY_MAX_OUTPUT_TOKENS),
            "GRAPHIFY_MAX_RETRIES": "0",
        }
    )
    return env


def _stage_failure_code(state: Mapping[str, Any], stage: Stage) -> str:
    """Project an already-validated fixed ledger failure code into the receipt."""
    attempts = state.get("attempts")
    latest = attempts[-1] if isinstance(attempts, list) and attempts else None
    if isinstance(latest, dict) and latest.get("status") == "failed":
        failure_code = latest.get("failure_code")
        if failure_code in CANARY_FAILURE_CODES:
            return f"{stage.name}_{failure_code}"
    return f"{stage.name}_command_failed"


def _attempt_summaries(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project ledger attempts into a payload-free receipt summary."""
    summaries = []
    for attempt in state.get("attempts", []):
        if not isinstance(attempt, dict):
            continue
        summary = {
            key: attempt[key]
            for key in (
                "number",
                "status",
                "failure_code",
                "elapsed_seconds",
                "response_metadata_available",
            )
            if key in attempt
        }
        summaries.append(summary)
    return summaries


def _assert_stage_completed(state: Mapping[str, Any], stage: Stage) -> None:
    """Require one metadata-free completed reservation for a successful stage."""
    if state.get("attempts_reserved") != stage.expected_attempts + 1:
        raise CampaignFailure(f"{stage.name}_dispatch_count_mismatch")
    attempts = state.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise CampaignFailure(f"{stage.name}_reservation_missing")
    latest = attempts[-1]
    if isinstance(latest, dict) and latest.get("status") == "failed":
        raise CampaignFailure(_stage_failure_code(state, stage))
    if not isinstance(latest, dict) or latest.get("status") != "completed":
        raise CampaignFailure(f"{stage.name}_terminal_contract_missing")
    if latest.get("response_metadata_available") is not False:
        raise CampaignFailure(f"{stage.name}_response_metadata_available")


def _labels_are_substantive(path: Path) -> bool:
    try:
        labels = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(labels, dict) or not labels:
        return False
    return any(
        isinstance(value, str)
        and value.strip()
        and re.fullmatch(r"Community\s+\d+", value.strip()) is None
        for value in labels.values()
    )


def _is_finite_score(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _score_fixture(result_root: Path, expected: Path) -> dict[str, Any]:
    graphify_out = result_root / "graphify-out"
    graph = graphify_out / "graph.json"
    labels = graphify_out / ".graphify_labels.json"
    if not graph.is_file() or not _labels_are_substantive(labels):
        raise CampaignFailure("graph_or_substantive_labels_missing")
    score = score_graph(graph, expected, labels_path=labels)
    scores = score.get("scores")
    if not isinstance(scores, dict):
        raise CampaignFailure("deterministic_score_missing")
    safe_scores: dict[str, int | float] = {}
    for key, value in scores.items():
        if value is None:
            continue
        if not _is_finite_score(value):
            raise CampaignFailure("deterministic_score_invalid")
        safe_scores[key] = value
    return safe_scores


def _passes_committed_gate(scores: Mapping[str, Any]) -> bool:
    overall = scores.get("overall")
    if (
        isinstance(overall, bool)
        or not isinstance(overall, (int, float))
        or not _is_finite_score(overall)
        or overall < 0.7
    ):
        return False
    community_labels = scores.get("community_labels")
    if (
        isinstance(community_labels, bool)
        or not isinstance(community_labels, (int, float))
        or not _is_finite_score(community_labels)
        or community_labels < 0.45
    ):
        return False
    for key in (
        "concept_recall",
        "expected_edge_coverage",
        "forbidden_concepts_absent",
        "forbidden_edges_absent",
        "source_coverage",
    ):
        value = scores.get(key)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not _is_finite_score(value)
            or value < 0.45
        ):
            return False
    return True


def _image_cache_is_pixel_derived(paths: CampaignPaths) -> bool:
    image = paths.image_corpus / "diagram.png"
    nodes, _, _, misses = check_semantic_cache(
        [str(image)],
        root=paths.image_corpus,
        cache_root=paths.image_result,
        prompt=_extraction_system(deep=False),
        require_pixel_derived=True,
    )
    return bool(nodes) and not misses


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def run_campaign(
    *,
    out_dir: Path,
    model: str,
    thinking: str,
    require_outer_pi: bool,
    base_env: Mapping[str, str] | None = None,
    repo_root: Path = REPO_ROOT,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_stage,
) -> dict[str, Any]:
    if model != AUTHORIZED_MODEL or thinking != AUTHORIZED_THINKING:
        raise CampaignFailure("unauthorized_model_or_thinking")
    env = dict(os.environ if base_env is None else base_env)
    if require_outer_pi and not _outer_pi_present(env):
        raise CampaignFailure("outer_pi_session_not_detected")
    verify_fixture_hashes(repo_root)
    chunk_counts = verify_single_chunk_preflight(repo_root)
    paths = _campaign_paths(out_dir)
    _prepare_paths(paths, repo_root)
    campaign_id = new_campaign_id()
    create_campaign(paths.ledger, campaign_id=campaign_id, limit=MAX_CAMPAIGN_ATTEMPTS)
    started = time.time()
    failure: str | None = None
    scores: dict[str, Any] = {}
    sixth_denied = False
    stages = campaign_stages(paths, model=model)

    try:
        for stage in stages:
            stage_env = _stage_environment(
                env,
                ledger=paths.ledger,
                campaign_id=campaign_id,
                expected_attempts=stage.expected_attempts,
                model=model,
                thinking=thinking,
            )
            completed = runner(stage.command, env=stage_env)
            state = read_campaign(paths.ledger, campaign_id)
            if completed.returncode != 0:
                raise CampaignFailure(_stage_failure_code(state, stage))
            _assert_stage_completed(state, stage)
        sixth_denied = prove_sixth_denied(paths.ledger, campaign_id)

        text_expected = (
            repo_root / "tests/fixtures/semantic_eval/graphify_public_slice/expected.json"
        )
        image_expected = repo_root / "tests/fixtures/semantic_eval/diagram_workflow/expected.json"
        text_scores = _score_fixture(paths.text_result, text_expected)
        image_scores = _score_fixture(paths.image_result, image_expected)
        scores = {"text": text_scores, "image": image_scores}
        if not _passes_committed_gate(text_scores):
            raise CampaignFailure("text_score_gate_failed")
        if not _passes_committed_gate(image_scores):
            raise CampaignFailure("image_score_gate_failed")
        if any(
            image_scores.get(key) != 1.0
            for key in ("concept_recall", "expected_edge_coverage", "source_coverage")
        ):
            raise CampaignFailure("image_exact_recovery_gate_failed")
        if not _image_cache_is_pixel_derived(paths):
            raise CampaignFailure("image_pixel_provenance_missing")
    except CampaignFailure as exc:
        failure = str(exc)
    except subprocess.TimeoutExpired:
        failure = "campaign_command_timeout"
    except CanaryStateError:
        failure = "campaign_ledger_invalid"
    except Exception:
        # Once a campaign has started, every unexpected validation/runtime
        # failure still produces a fixed-code, payload-free failed receipt.
        failure = "campaign_internal_failure"

    try:
        state = read_campaign(paths.ledger, campaign_id)
    except CanaryStateError:
        failure = "campaign_ledger_invalid"
        state = {"attempts_reserved": None, "attempts": []}
    attempts = _attempt_summaries(state)
    for index, attempt in enumerate(attempts):
        if index < len(stages):
            attempt["stage"] = stages[index].name
    terminal_contract_passed = len(attempts) == MAX_CAMPAIGN_ATTEMPTS and all(
        attempt.get("status") == "completed" and attempt.get("response_metadata_available") is False
        for attempt in attempts
    )
    passed = (
        failure is None
        and state.get("attempts_reserved") == MAX_CAMPAIGN_ATTEMPTS
        and terminal_contract_passed
        and sixth_denied
    )
    receipt = {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "passed": passed,
        "failure": failure,
        "requested_model": model,
        "requested_thinking": thinking,
        "response_metadata_available": False,
        "outer_pi_required": require_outer_pi,
        "outer_pi_detected": _outer_pi_present(env),
        "fixture_hashes_verified": True,
        "chunk_counts": chunk_counts,
        "label_batch_size": 1000,
        "api_timeout_seconds": CANARY_API_TIMEOUT_SECONDS,
        "max_output_tokens": CANARY_MAX_OUTPUT_TOKENS,
        "graphify_retries_disabled": True,
        "pi_retries_disabled": True,
        "retry_events": 0,
        "attempts_reserved": state.get("attempts_reserved"),
        "attempts": attempts,
        "sixth_denied_before_dispatch": sixth_denied,
        "scores": scores,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    _write_receipt(paths.receipt, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.live:
        print("error: --live is required; no Pi model request was made", file=sys.stderr)
        return 2
    try:
        receipt = run_campaign(
            out_dir=args.out_dir,
            model=args.model,
            thinking=args.thinking,
            require_outer_pi=args.require_outer_pi,
        )
    except CampaignFailure as exc:
        print(f"error: Pi canary preflight failed ({exc})", file=sys.stderr)
        return 1
    receipt_path = _campaign_paths(args.out_dir).receipt
    print(receipt_path)
    return 0 if receipt.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
