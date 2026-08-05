"""Offline tests for the fail-closed five-attempt Pi canary ledger and driver."""

from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import subprocess

import pytest  # pyright: ignore[reportMissingImports]

from graphify import llm
from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
    CAMPAIGN_ENV_KEYS,
    AttemptReservation,
    CanaryLimitError,
    CanaryStateError,
    campaign_environment,
    create_campaign,
    prove_sixth_denied,
    read_campaign,
    record_attempt_success,
    record_attempt_success_from_env,
    record_attempt_failure_from_env,
    reserve_attempt,
    reserve_attempt_from_env,
)
import scripts.pi_backend_canary as driver


_CAMPAIGN_ID = "campaign-12345678"


def _reservation_worker(ledger: str, queue) -> None:
    try:
        reservation = reserve_attempt(Path(ledger), _CAMPAIGN_ID)
        queue.put(("reserved", reservation.number))
    except CanaryLimitError:
        queue.put(("denied", None))
    except Exception as exc:  # pragma: no cover - reported by parent assertion
        queue.put(("error", type(exc).__name__))


def _write_state(path: Path, mutate) -> None:
    state = json.loads(path.read_text(encoding="utf-8"))
    mutate(state)
    path.write_text(json.dumps(state), encoding="utf-8")


def test_campaign_environment_absent_is_inactive(monkeypatch, tmp_path):
    for key in CAMPAIGN_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    assert reserve_attempt_from_env() is None
    assert not (tmp_path / "ledger.json.lock").exists()


def test_campaign_incomplete_environment_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv(CAMPAIGN_ENV_KEYS[0], str(tmp_path / "missing.json"))
    for key in CAMPAIGN_ENV_KEYS[1:]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(CanaryStateError, match="environment is incomplete"):
        reserve_attempt_from_env()


def test_campaign_reserves_five_and_denies_sixth_without_increment(tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)

    reservations = [
        reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=index) for index in range(5)
    ]

    assert [reservation.number for reservation in reservations] == [1, 2, 3, 4, 5]
    assert prove_sixth_denied(ledger, _CAMPAIGN_ID) is True
    assert read_campaign(ledger, _CAMPAIGN_ID)["attempts_reserved"] == 5


def test_campaign_six_concurrent_reservations_allow_exactly_five(tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    workers = [
        context.Process(target=_reservation_worker, args=(str(ledger), queue)) for _ in range(6)
    ]

    for worker in workers:
        worker.start()
    results = [queue.get(timeout=10) for _ in workers]
    for worker in workers:
        worker.join(timeout=10)
        assert worker.exitcode == 0

    assert sum(kind == "reserved" for kind, _ in results) == 5
    assert sum(kind == "denied" for kind, _ in results) == 1
    assert not [result for result in results if result[0] == "error"]
    assert read_campaign(ledger, _CAMPAIGN_ID)["attempts_reserved"] == 5


@pytest.mark.parametrize("case", ["corrupt", "wrong_id", "stale", "limit", "rollback"])
def test_campaign_malformed_stale_wrong_or_rollback_state_fails_closed(tmp_path, case):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID, now=100.0, ttl_seconds=60.0)

    if case == "corrupt":
        ledger.write_text("{", encoding="utf-8")
    elif case == "limit":
        _write_state(ledger, lambda state: state.update(limit=6))
    elif case == "rollback":
        _write_state(ledger, lambda state: state.update(attempts_reserved=1, attempts=[]))

    with pytest.raises((CanaryStateError, ValueError)):
        if case == "wrong_id":
            reserve_attempt(ledger, "different-campaign", now=110.0)
        elif case == "stale":
            reserve_attempt(ledger, _CAMPAIGN_ID, now=200.0)
        else:
            reserve_attempt(ledger, _CAMPAIGN_ID, now=110.0)


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_campaign_non_finite_state_fails_closed(tmp_path, non_finite):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    _write_state(ledger, lambda state: state.update(expires_at=non_finite))

    with pytest.raises(CanaryStateError, match="unreadable or malformed"):
        read_campaign(ledger, _CAMPAIGN_ID)


def test_campaign_oversized_integer_state_and_inputs_fail_closed(tmp_path):
    oversized = 10**400
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    _write_state(ledger, lambda state: state.update(expires_at=oversized))

    with pytest.raises(CanaryStateError, match="timestamps are malformed"):
        read_campaign(ledger, _CAMPAIGN_ID)
    with pytest.raises(ValueError, match="finite"):
        create_campaign(
            tmp_path / "invalid.json",
            campaign_id=_CAMPAIGN_ID,
            ttl_seconds=oversized,
        )
    with pytest.raises(ValueError, match="finite"):
        create_campaign(
            tmp_path / "invalid-now.json",
            campaign_id=_CAMPAIGN_ID,
            now=oversized,
        )

    valid = tmp_path / "valid.json"
    create_campaign(valid, campaign_id=_CAMPAIGN_ID)
    with pytest.raises(CanaryStateError, match="reservation time is invalid"):
        reserve_attempt(valid, _CAMPAIGN_ID, now=oversized)
    with pytest.raises(CanaryStateError, match="read time is invalid"):
        read_campaign(valid, _CAMPAIGN_ID, now=oversized)
    reservation = reserve_attempt(valid, _CAMPAIGN_ID, expected_attempts=0)
    with pytest.raises(CanaryStateError, match="completion time is invalid"):
        record_attempt_success(
            valid,
            reservation,
            elapsed_seconds=0.1,
            response_metadata_available=False,
            now=oversized,
        )


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_campaign_rejects_non_finite_inputs_and_completion(tmp_path, non_finite):
    with pytest.raises(ValueError, match="finite"):
        create_campaign(
            tmp_path / "invalid.json",
            campaign_id=_CAMPAIGN_ID,
            ttl_seconds=non_finite,
        )

    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    reservation = reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)
    with pytest.raises(CanaryStateError, match="elapsed time is invalid"):
        record_attempt_success(
            ledger,
            reservation,
            elapsed_seconds=non_finite,
            response_metadata_available=False,
        )


@pytest.mark.skipif(os.name == "nt", reason="Unix flock contention probe")
def test_campaign_stale_locked_ledger_fails_closed(tmp_path):
    import fcntl

    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    lock_path = ledger.with_name(ledger.name + ".lock")
    with lock_path.open("r+b", buffering=0) as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(CanaryStateError, match="lock is unavailable or stale"):
                reserve_attempt(ledger, _CAMPAIGN_ID)
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def test_campaign_expected_counter_detects_rollback_or_duplicate_retry(tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)

    with pytest.raises(CanaryStateError, match="rollback or out-of-order"):
        reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)

    assert read_campaign(ledger, _CAMPAIGN_ID)["attempts_reserved"] == 1


def test_campaign_completion_records_only_safe_terminal_metadata(tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    reservation = reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)

    record_attempt_success(
        ledger,
        reservation,
        elapsed_seconds=0.25,
        response_metadata_available=False,
    )

    serialized = ledger.read_text(encoding="utf-8")
    assert "prompt" not in serialized
    assert "session" not in serialized
    attempt = read_campaign(ledger, _CAMPAIGN_ID)["attempts"][0]
    assert attempt["status"] == "completed"
    assert attempt["response_metadata_available"] is False
    assert set(attempt) == {
        "number",
        "reserved_at",
        "status",
        "completed_at",
        "elapsed_seconds",
        "response_metadata_available",
    }
    assert not {"provider", "model", "usage", "stop_reason"} & set(attempt)


def test_campaign_completion_rejects_available_response_metadata(tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    reservation = reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)

    with pytest.raises(CanaryStateError, match="metadata must be unavailable"):
        record_attempt_success(
            ledger,
            reservation,
            elapsed_seconds=0.1,
            response_metadata_available=True,
        )

    assert read_campaign(ledger, _CAMPAIGN_ID)["attempts"][0]["status"] == "reserved"


@pytest.mark.parametrize("unsafe_key", ["prompt", "provider", "model", "usage", "stop_reason"])
def test_campaign_receipt_rejects_unsafe_attempt_metadata(tmp_path, unsafe_key):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    reserve_attempt(ledger, _CAMPAIGN_ID, expected_attempts=0)

    def inject_unsafe_metadata(state):
        state["attempts"][0][unsafe_key] = "private source"

    _write_state(ledger, inject_unsafe_metadata)

    with pytest.raises(CanaryStateError, match="unsafe metadata"):
        read_campaign(ledger, _CAMPAIGN_ID)


def test_campaign_driver_preflights_hashes_chunks_and_exact_stage_plan(tmp_path):
    driver.verify_fixture_hashes()
    assert driver.verify_single_chunk_preflight() == {"text": 1, "image": 1}
    paths = driver._campaign_paths(tmp_path)

    stages = driver.campaign_stages(
        paths, model=driver.AUTHORIZED_MODEL, python_executable="python"
    )

    assert [stage.name for stage in stages] == [
        "doctor_probe",
        "text_extract",
        "text_label",
        "image_extract",
        "image_label",
    ]
    assert [stage.expected_attempts for stage in stages] == [0, 1, 2, 3, 4]
    assert "--force" in stages[1].command and "--force" in stages[3].command
    assert "--allow-image-upload" not in stages[1].command
    assert "--allow-image-upload" in stages[3].command
    assert all("1000" in stage.command for stage in (stages[2], stages[4]))
    environment = driver._stage_environment(
        {
            "GRAPHIFY_API_TIMEOUT": "45",
            "GRAPHIFY_MAX_OUTPUT_TOKENS": "4096",
        },
        ledger=tmp_path / "ledger.json",
        campaign_id=_CAMPAIGN_ID,
        expected_attempts=0,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
    )
    assert driver.CANARY_API_TIMEOUT_SECONDS == 540
    assert environment["GRAPHIFY_API_TIMEOUT"] == "540"
    assert driver.CANARY_MAX_OUTPUT_TOKENS == 32_768
    assert environment["GRAPHIFY_MAX_OUTPUT_TOKENS"] == "32768"


def test_campaign_outer_timeout_covers_model_capability_and_cleanup_budget(monkeypatch):
    assert driver.CANARY_API_TIMEOUT_SECONDS == 540
    assert driver.CANARY_CAPABILITY_COMMANDS == 3
    assert driver.CANARY_CAPABILITY_TIMEOUT_SECONDS == 30
    assert driver.CANARY_CLEANUP_MARGIN_SECONDS == 30
    required = (
        driver.CANARY_API_TIMEOUT_SECONDS
        + driver.CANARY_CAPABILITY_COMMANDS * driver.CANARY_CAPABILITY_TIMEOUT_SECONDS
        + driver.CANARY_CLEANUP_MARGIN_SECONDS
    )
    assert required == 660
    assert driver.COMMAND_TIMEOUT_SECONDS == required
    assert driver.CANARY_CLEANUP_MARGIN_SECONDS > 0

    captured = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(driver.subprocess, "run", fake_run)
    driver._run_stage(("graphify", "doctor"), env={})
    assert captured["kwargs"]["timeout"] == required


def test_campaign_driver_without_live_is_inert(tmp_path):
    assert driver.main(["--out-dir", str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []


def test_campaign_driver_fake_run_uses_one_counter_and_sanitized_receipt(tmp_path, monkeypatch):
    complete_scores = {
        "overall": 1.0,
        "concept_recall": 1.0,
        "expected_edge_coverage": 1.0,
        "forbidden_concepts_absent": 1.0,
        "source_coverage": 1.0,
        "community_labels": 1.0,
    }

    def fake_runner(command, *, env):
        reservation = reserve_attempt_from_env(env)
        assert isinstance(reservation, AttemptReservation)
        record_attempt_success_from_env(
            reservation,
            elapsed_seconds=0.01,
            response_metadata_available=False,
            env=env,
        )
        return subprocess.CompletedProcess(command, 0, stdout="PRIVATE_SOURCE", stderr="")

    monkeypatch.setattr(driver, "_score_fixture", lambda *_args, **_kwargs: complete_scores)
    monkeypatch.setattr(driver, "_image_cache_is_pixel_derived", lambda _paths: True)

    receipt = driver.run_campaign(
        out_dir=tmp_path,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
        require_outer_pi=True,
        base_env={"PI_CODING_AGENT": "1", "PRIVATE_TOKEN": "secret"},
        runner=fake_runner,
    )

    assert receipt["passed"] is True
    assert receipt["attempts_reserved"] == 5
    assert receipt["sixth_denied_before_dispatch"] is True
    assert receipt["api_timeout_seconds"] == driver.CANARY_API_TIMEOUT_SECONDS
    assert receipt["max_output_tokens"] == driver.CANARY_MAX_OUTPUT_TOKENS
    assert receipt["requested_model"] == driver.AUTHORIZED_MODEL
    assert receipt["requested_thinking"] == driver.AUTHORIZED_THINKING
    assert receipt["response_metadata_available"] is False
    assert [attempt["number"] for attempt in receipt["attempts"]] == [1, 2, 3, 4, 5]
    assert all(
        set(attempt)
        == {"number", "status", "elapsed_seconds", "response_metadata_available", "stage"}
        for attempt in receipt["attempts"]
    )
    assert not {
        "provider",
        "model",
        "usage",
        "stop_reason",
    } & set(receipt)
    serialized = (tmp_path / "receipt.json").read_text(encoding="utf-8")
    assert "PRIVATE_SOURCE" not in serialized
    assert "PRIVATE_TOKEN" not in serialized
    assert "secret" not in serialized
    assert "PI_CODING_AGENT" not in serialized


@pytest.mark.parametrize(
    ("failure_code", "expected_failure"),
    [
        ("timeout", "text_extract_timeout"),
        ("output_thinking_delta", "text_extract_output_thinking_delta"),
    ],
)
def test_campaign_driver_uses_ledger_failure_code_without_payload(
    tmp_path, failure_code, expected_failure
):
    def fake_runner(command, *, env):
        reservation = reserve_attempt_from_env(env)
        assert isinstance(reservation, AttemptReservation)
        if reservation.number == 1:
            record_attempt_success_from_env(
                reservation,
                elapsed_seconds=0.01,
                response_metadata_available=False,
                env=env,
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        record_attempt_failure_from_env(
            reservation,
            failure_code=failure_code,
            elapsed_seconds=0.01,
            env=env,
        )
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="PRIVATE MODEL OUTPUT",
            stderr="PRIVATE STDERR",
        )

    receipt = driver.run_campaign(
        out_dir=tmp_path,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
        require_outer_pi=False,
        base_env={},
        runner=fake_runner,
    )

    assert receipt["passed"] is False
    assert receipt["failure"] == expected_failure
    assert receipt["attempts_reserved"] == 2
    assert receipt["attempts"][-1]["failure_code"] == failure_code
    serialized = (tmp_path / "receipt.json").read_text(encoding="utf-8")
    assert "PRIVATE MODEL OUTPUT" not in serialized
    assert "PRIVATE STDERR" not in serialized


def test_campaign_driver_accepts_metadata_free_completion():
    state = {
        "attempts_reserved": 1,
        "attempts": [
            {
                "number": 1,
                "status": "completed",
                "elapsed_seconds": 0.1,
                "response_metadata_available": False,
            }
        ],
    }
    stage = driver.Stage("doctor_probe", 0, ("graphify", "doctor"))

    driver._assert_stage_completed(state, stage)
    assert driver._attempt_summaries(state) == [
        {
            "number": 1,
            "status": "completed",
            "elapsed_seconds": 0.1,
            "response_metadata_available": False,
        }
    ]


def test_campaign_driver_writes_fixed_failure_receipt_for_ledger_error(tmp_path):
    def failing_runner(command, *, env):
        reservation = reserve_attempt_from_env(env)
        assert isinstance(reservation, AttemptReservation)
        raise CanaryStateError("PRIVATE SOURCE SHOULD NOT REACH RECEIPT")

    receipt = driver.run_campaign(
        out_dir=tmp_path,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
        require_outer_pi=False,
        base_env={},
        runner=failing_runner,
    )

    assert receipt["passed"] is False
    assert receipt["failure"] == "campaign_ledger_invalid"
    serialized = (tmp_path / "receipt.json").read_text(encoding="utf-8")
    assert "PRIVATE SOURCE" not in serialized


def test_campaign_driver_writes_receipt_for_oversized_ledger_integer(tmp_path):
    def corrupting_runner(command, *, env):
        reservation = reserve_attempt_from_env(env)
        assert isinstance(reservation, AttemptReservation)
        ledger = Path(env[CAMPAIGN_ENV_KEYS[0]])
        _write_state(ledger, lambda state: state.update(expires_at=10**400))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    receipt = driver.run_campaign(
        out_dir=tmp_path,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
        require_outer_pi=False,
        base_env={},
        runner=corrupting_runner,
    )

    assert receipt["passed"] is False
    assert receipt["failure"] == "campaign_ledger_invalid"
    assert (tmp_path / "receipt.json").is_file()


def test_campaign_driver_rejects_non_finite_receipt_values(tmp_path):
    with pytest.raises(ValueError):
        driver._write_receipt(tmp_path / "receipt.json", {"score": float("nan")})
    assert not (tmp_path / "receipt.json").exists()
    assert driver._passes_committed_gate({"overall": 10**400}) is False


@pytest.mark.parametrize(
    ("community_labels", "expected"),
    [(None, False), (0.0, False), (0.44, False), (0.45, True), (1.0, True), (float("nan"), False)],
)
def test_campaign_driver_requires_a_finite_community_label_score(community_labels, expected):
    scores = {
        "overall": 1.0,
        "concept_recall": 1.0,
        "expected_edge_coverage": 1.0,
        "forbidden_concepts_absent": 1.0,
        "source_coverage": 1.0,
        "community_labels": community_labels,
    }
    assert driver._passes_committed_gate(scores) is expected


def test_campaign_driver_rejects_zero_community_label_score_receipt(tmp_path, monkeypatch):
    complete_scores = {
        "overall": 1.0,
        "concept_recall": 1.0,
        "expected_edge_coverage": 1.0,
        "forbidden_concepts_absent": 1.0,
        "source_coverage": 1.0,
        "community_labels": 0.0,
    }

    def fake_runner(command, *, env):
        reservation = reserve_attempt_from_env(env)
        assert isinstance(reservation, AttemptReservation)
        record_attempt_success_from_env(
            reservation,
            elapsed_seconds=0.01,
            response_metadata_available=False,
            env=env,
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(driver, "_score_fixture", lambda *_args, **_kwargs: complete_scores)
    monkeypatch.setattr(driver, "_image_cache_is_pixel_derived", lambda _paths: True)

    receipt = driver.run_campaign(
        out_dir=tmp_path,
        model=driver.AUTHORIZED_MODEL,
        thinking=driver.AUTHORIZED_THINKING,
        require_outer_pi=False,
        base_env={},
        runner=fake_runner,
    )

    assert receipt["passed"] is False
    assert receipt["failure"] == "text_score_gate_failed"
    assert receipt["attempts_reserved"] == 5
    assert receipt["scores"]["text"]["community_labels"] == 0.0


def test_campaign_disables_extraction_adaptive_retry(monkeypatch, tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    for key, value in campaign_environment(ledger, _CAMPAIGN_ID, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    files = [tmp_path / "left.md", tmp_path / "right.md"]
    for path in files:
        path.write_text(path.stem, encoding="utf-8")
    calls = []

    def truncated_direct(chunk, **_kwargs):
        calls.append(list(chunk))
        return {
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "finish_reason": "length",
        }

    monkeypatch.setattr(llm, "extract_files_direct", truncated_direct)

    result = llm._extract_with_adaptive_retry(
        files,
        backend="pi",
        api_key=None,
        model=driver.AUTHORIZED_MODEL,
        root=tmp_path,
        max_depth=3,
    )

    assert len(calls) == 1
    assert result["partial_chunks"] == 1


def test_campaign_disables_label_split_retry(monkeypatch, tmp_path):
    ledger = tmp_path / "ledger.json"
    create_campaign(ledger, campaign_id=_CAMPAIGN_ID)
    for key, value in campaign_environment(ledger, _CAMPAIGN_ID, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    calls = []

    def malformed_call(*_args, **_kwargs):
        calls.append(1)
        return "not json"

    monkeypatch.setattr(llm, "_call_llm", malformed_call)

    with pytest.raises((ValueError, json.JSONDecodeError)):
        llm._label_batch_with_retry(
            [0, 1],
            ["Community 0: A", "Community 1: B"],
            backend="pi",
            model=driver.AUTHORIZED_MODEL,
        )

    assert len(calls) == 1
