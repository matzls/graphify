"""Fail-closed attempt ledger for the bounded Pi backend canary.

Normal Graphify/Pi calls do not touch this module's lock or ledger unless the
complete canary environment is present.  The ledger records only safe dispatch
metadata; prompts, responses, credentials, image bytes, and parent session
identifiers never belong here.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Iterator, Mapping
import uuid

CAMPAIGN_LEDGER_ENV = "GRAPHIFY_PI_CANARY_LEDGER"
CAMPAIGN_ID_ENV = "GRAPHIFY_PI_CANARY_ID"
CAMPAIGN_EXPECTED_ENV = "GRAPHIFY_PI_CANARY_EXPECTED_ATTEMPTS"
CAMPAIGN_ENV_KEYS = (CAMPAIGN_LEDGER_ENV, CAMPAIGN_ID_ENV, CAMPAIGN_EXPECTED_ENV)
MAX_CAMPAIGN_ATTEMPTS = 5
CANARY_FAILURE_CODES = frozenset(
    {
        "launch",
        "timeout",
        "output_bound",
        "output_text_delta",
        "output_thinking_delta",
        "output_terminal_message",
        "output_stdout_stream",
        "output_jsonl_record",
        "child_exit",
        "transport",
        "provider",
        "terminal_contract",
    }
)
DEFAULT_TTL_SECONDS = 60 * 60
_LOCK_TIMEOUT_SECONDS = 1.0
_STATE_VERSION = 1
_CAMPAIGN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}\Z", flags=re.ASCII)
_SAFE_METADATA_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}\Z", flags=re.ASCII)


class CanaryStateError(RuntimeError):
    """The canary ledger is unavailable, invalid, stale, or out of sequence."""


class CanaryLimitError(CanaryStateError):
    """The canary's model-attempt ceiling was reached before dispatch."""


@dataclass(frozen=True)
class AttemptReservation:
    campaign_id: str
    number: int


def new_campaign_id() -> str:
    return uuid.uuid4().hex


def campaign_active(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return any(str(values.get(key, "")).strip() for key in CAMPAIGN_ENV_KEYS)


def campaign_environment(
    ledger_path: Path,
    campaign_id: str,
    *,
    expected_attempts: int,
) -> dict[str, str]:
    _validate_campaign_id(campaign_id)
    if isinstance(expected_attempts, bool) or expected_attempts < 0:
        raise ValueError("expected_attempts must be a non-negative integer")
    return {
        CAMPAIGN_LEDGER_ENV: str(Path(ledger_path).resolve()),
        CAMPAIGN_ID_ENV: campaign_id,
        CAMPAIGN_EXPECTED_ENV: str(expected_attempts),
    }


def create_campaign(
    ledger_path: Path,
    *,
    campaign_id: str | None = None,
    limit: int = MAX_CAMPAIGN_ATTEMPTS,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """Create one new campaign ledger without replacing existing state."""
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_CAMPAIGN_ATTEMPTS
    ):
        raise ValueError(f"campaign limit must be between 1 and {MAX_CAMPAIGN_ATTEMPTS}")
    if (
        isinstance(ttl_seconds, bool)
        or not isinstance(ttl_seconds, (int, float))
        or not _is_finite_number(ttl_seconds)
        or ttl_seconds <= 0
    ):
        raise ValueError("campaign ttl must be a positive finite number")
    campaign_id = campaign_id or new_campaign_id()
    _validate_campaign_id(campaign_id)
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise CanaryStateError("Pi canary ledger already exists")
    timestamp_value = time.time() if now is None else now
    if not _is_finite_number(timestamp_value):
        raise ValueError("campaign creation time must be finite")
    timestamp = float(timestamp_value)
    expires_at = timestamp + float(ttl_seconds)
    if not math.isfinite(expires_at):
        raise ValueError("campaign expiry must be finite")
    state: dict[str, Any] = {
        "version": _STATE_VERSION,
        "campaign_id": campaign_id,
        "limit": limit,
        "attempts_reserved": 0,
        "attempts": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "expires_at": expires_at,
        "revision": 0,
    }
    with _ledger_lock(path):
        if path.exists() or path.is_symlink():
            raise CanaryStateError("Pi canary ledger already exists")
        _write_state(path, state)
    return json.loads(json.dumps(state, allow_nan=False))


def reserve_attempt(
    ledger_path: Path,
    campaign_id: str,
    *,
    expected_attempts: int | None = None,
    now: float | None = None,
) -> AttemptReservation:
    """Atomically consume one model attempt before a Pi child is launched."""
    _validate_campaign_id(campaign_id)
    path = Path(ledger_path)
    timestamp_value = time.time() if now is None else now
    if not _is_finite_number(timestamp_value):
        raise CanaryStateError("Pi canary reservation time is invalid")
    timestamp = float(timestamp_value)
    with _ledger_lock(path):
        state = _read_and_validate(path, campaign_id=campaign_id, now=timestamp)
        count = int(state["attempts_reserved"])
        if expected_attempts is not None:
            if isinstance(expected_attempts, bool) or not isinstance(expected_attempts, int):
                raise CanaryStateError("Pi canary expected-attempt state is malformed")
            if count != expected_attempts:
                raise CanaryStateError(
                    "Pi canary counter rollback or out-of-order dispatch detected"
                )
        limit = int(state["limit"])
        if count >= limit:
            raise CanaryLimitError("Pi canary attempt limit reached before child dispatch")
        number = count + 1
        attempts = list(state["attempts"])
        attempts.append({"number": number, "reserved_at": timestamp, "status": "reserved"})
        state["attempts"] = attempts
        state["attempts_reserved"] = number
        state["updated_at"] = timestamp
        state["revision"] = int(state["revision"]) + 1
        _write_state(path, state)
    return AttemptReservation(campaign_id=campaign_id, number=number)


def reserve_attempt_from_env(
    env: Mapping[str, str] | None = None,
) -> AttemptReservation | None:
    """Reserve from the explicit canary environment, or no-op when fully absent."""
    values = env if env is not None else os.environ
    raw = {key: str(values.get(key, "")).strip() for key in CAMPAIGN_ENV_KEYS}
    present = {key for key, value in raw.items() if value}
    if not present:
        return None
    if present != set(CAMPAIGN_ENV_KEYS):
        raise CanaryStateError("Pi canary environment is incomplete")
    try:
        expected = int(raw[CAMPAIGN_EXPECTED_ENV])
    except ValueError as exc:
        raise CanaryStateError("Pi canary expected-attempt state is malformed") from exc
    if expected < 0:
        raise CanaryStateError("Pi canary expected-attempt state is malformed")
    return reserve_attempt(
        Path(raw[CAMPAIGN_LEDGER_ENV]),
        raw[CAMPAIGN_ID_ENV],
        expected_attempts=expected,
    )


def record_attempt_success(
    ledger_path: Path,
    reservation: AttemptReservation,
    *,
    elapsed_seconds: float,
    response_metadata_available: bool = False,
    now: float | None = None,
) -> None:
    """Complete one reservation without inventing unavailable Pi metadata.

    Pi ``--print`` exposes bounded final text but no supported terminal event
    metadata.  Keep that distinction explicit in the ledger: the reservation
    proves a dispatch completed, while provider/model/usage/stop identity is not
    recorded as if it came from the response.
    """
    if response_metadata_available is not False:
        raise CanaryStateError("Pi canary response metadata must be unavailable")
    if not _is_finite_number(elapsed_seconds):
        raise CanaryStateError("Pi canary elapsed time is invalid")
    elapsed = float(elapsed_seconds)
    if elapsed < 0:
        raise CanaryStateError("Pi canary elapsed time is invalid")

    path = Path(ledger_path)
    timestamp_value = time.time() if now is None else now
    if not _is_finite_number(timestamp_value):
        raise CanaryStateError("Pi canary completion time is invalid")
    timestamp = float(timestamp_value)
    with _ledger_lock(path):
        state = _read_and_validate(path, campaign_id=reservation.campaign_id, now=timestamp)
        attempts = list(state["attempts"])
        index = reservation.number - 1
        if index < 0 or index >= len(attempts):
            raise CanaryStateError("Pi canary reservation is missing")
        attempt = dict(attempts[index])
        if attempt.get("number") != reservation.number or attempt.get("status") != "reserved":
            raise CanaryStateError("Pi canary reservation cannot be completed")
        attempt.update(
            {
                "status": "completed",
                "completed_at": timestamp,
                "elapsed_seconds": round(elapsed, 3),
                "response_metadata_available": False,
            }
        )
        attempts[index] = attempt
        state["attempts"] = attempts
        state["updated_at"] = timestamp
        state["revision"] = int(state["revision"]) + 1
        _write_state(path, state)


def record_attempt_failure(
    ledger_path: Path,
    reservation: AttemptReservation,
    *,
    failure_code: str,
    elapsed_seconds: float,
    now: float | None = None,
) -> None:
    """Attach one fixed, payload-free failure code to a consumed reservation."""
    if failure_code not in CANARY_FAILURE_CODES:
        raise CanaryStateError("Pi canary failure code is invalid")
    if not _is_finite_number(elapsed_seconds):
        raise CanaryStateError("Pi canary elapsed time is invalid")
    elapsed = float(elapsed_seconds)
    if elapsed < 0:
        raise CanaryStateError("Pi canary elapsed time is invalid")

    path = Path(ledger_path)
    timestamp_value = time.time() if now is None else now
    if not _is_finite_number(timestamp_value):
        raise CanaryStateError("Pi canary failure time is invalid")
    timestamp = float(timestamp_value)
    with _ledger_lock(path):
        state = _read_and_validate(path, campaign_id=reservation.campaign_id, now=timestamp)
        attempts = list(state["attempts"])
        index = reservation.number - 1
        if index < 0 or index >= len(attempts):
            raise CanaryStateError("Pi canary reservation is missing")
        attempt = dict(attempts[index])
        if attempt.get("number") != reservation.number or attempt.get("status") != "reserved":
            raise CanaryStateError("Pi canary reservation cannot be finalized")
        attempt.update(
            {
                "status": "failed",
                "failed_at": timestamp,
                "failure_code": failure_code,
                "elapsed_seconds": round(elapsed, 3),
            }
        )
        attempts[index] = attempt
        state["attempts"] = attempts
        state["updated_at"] = timestamp
        state["revision"] = int(state["revision"]) + 1
        _write_state(path, state)


def record_attempt_success_from_env(
    reservation: AttemptReservation | None,
    *,
    elapsed_seconds: float,
    response_metadata_available: bool = False,
    env: Mapping[str, str] | None = None,
) -> None:
    if reservation is None:
        return
    values = env if env is not None else os.environ
    ledger = str(values.get(CAMPAIGN_LEDGER_ENV, "")).strip()
    campaign_id = str(values.get(CAMPAIGN_ID_ENV, "")).strip()
    if not ledger or campaign_id != reservation.campaign_id:
        raise CanaryStateError("Pi canary environment changed during dispatch")
    record_attempt_success(
        Path(ledger),
        reservation,
        elapsed_seconds=elapsed_seconds,
        response_metadata_available=response_metadata_available,
    )


def record_attempt_failure_from_env(
    reservation: AttemptReservation | None,
    *,
    failure_code: str,
    elapsed_seconds: float,
    env: Mapping[str, str] | None = None,
) -> None:
    if reservation is None:
        return
    values = env if env is not None else os.environ
    ledger = str(values.get(CAMPAIGN_LEDGER_ENV, "")).strip()
    campaign_id = str(values.get(CAMPAIGN_ID_ENV, "")).strip()
    if not ledger or campaign_id != reservation.campaign_id:
        raise CanaryStateError("Pi canary environment changed during dispatch")
    record_attempt_failure(
        Path(ledger),
        reservation,
        failure_code=failure_code,
        elapsed_seconds=elapsed_seconds,
    )


def read_campaign(
    ledger_path: Path,
    campaign_id: str,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    path = Path(ledger_path)
    timestamp_value = time.time() if now is None else now
    if not _is_finite_number(timestamp_value):
        raise CanaryStateError("Pi canary read time is invalid")
    timestamp = float(timestamp_value)
    with _ledger_lock(path):
        state = _read_and_validate(path, campaign_id=campaign_id, now=timestamp)
    return json.loads(json.dumps(state, allow_nan=False))


def prove_sixth_denied(ledger_path: Path, campaign_id: str) -> bool:
    """Prove an exhausted campaign denies before dispatch without incrementing."""
    before = read_campaign(ledger_path, campaign_id)
    try:
        reserve_attempt(
            ledger_path,
            campaign_id,
            expected_attempts=int(before["attempts_reserved"]),
        )
    except CanaryLimitError:
        after = read_campaign(ledger_path, campaign_id)
        return after["attempts_reserved"] == before["attempts_reserved"]
    raise CanaryStateError("Pi canary sixth reservation unexpectedly succeeded")


def _validate_campaign_id(campaign_id: str) -> None:
    if not isinstance(campaign_id, str) or not _CAMPAIGN_ID_RE.fullmatch(campaign_id):
        raise ValueError("campaign_id must be an opaque 8-128 character identifier")


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _safe_name(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > 256
        or _SAFE_METADATA_RE.fullmatch(value) is None
    ):
        raise CanaryStateError(f"Pi canary {field} metadata is invalid")
    return value


def _read_and_validate(path: Path, *, campaign_id: str, now: float) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CanaryStateError("Pi canary ledger is missing or unsafe")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise CanaryStateError("Pi canary ledger is unreadable or malformed") from exc
    if not isinstance(payload, dict):
        raise CanaryStateError("Pi canary ledger is malformed")
    required = {
        "version",
        "campaign_id",
        "limit",
        "attempts_reserved",
        "attempts",
        "created_at",
        "updated_at",
        "expires_at",
        "revision",
    }
    if not required.issubset(payload):
        raise CanaryStateError("Pi canary ledger is malformed")
    if payload["version"] != _STATE_VERSION or payload["campaign_id"] != campaign_id:
        raise CanaryStateError("Pi canary ledger belongs to a different campaign")
    limit = payload["limit"]
    count = payload["attempts_reserved"]
    revision = payload["revision"]
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_CAMPAIGN_ATTEMPTS
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= limit
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < count
    ):
        raise CanaryStateError("Pi canary counter state is malformed")
    attempts = payload["attempts"]
    if not isinstance(attempts, list) or len(attempts) != count:
        raise CanaryStateError("Pi canary counter rollback or malformed history detected")
    finalized = 0
    for expected_number, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict) or attempt.get("number") != expected_number:
            raise CanaryStateError("Pi canary counter rollback or malformed history detected")
        status = attempt.get("status")
        if status not in {"reserved", "completed", "failed"}:
            raise CanaryStateError("Pi canary attempt history is malformed")
        reserved_at = attempt.get("reserved_at")
        if not _is_finite_number(reserved_at):
            raise CanaryStateError("Pi canary attempt history is malformed")
        allowed_keys = {"number", "reserved_at", "status"}
        if status == "completed":
            finalized += 1
            allowed_keys |= {
                "completed_at",
                "elapsed_seconds",
                "response_metadata_available",
            }
            if attempt.get("response_metadata_available") is not False:
                raise CanaryStateError("Pi canary attempt history is malformed")
            timestamp_keys = ("completed_at", "elapsed_seconds")
        elif status == "failed":
            finalized += 1
            allowed_keys |= {"failed_at", "failure_code", "elapsed_seconds"}
            if attempt.get("failure_code") not in CANARY_FAILURE_CODES:
                raise CanaryStateError("Pi canary attempt history is malformed")
            timestamp_keys = ("failed_at", "elapsed_seconds")
        else:
            timestamp_keys = ()
        for key in timestamp_keys:
            value = attempt.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
                or not _is_finite_number(value)
            ):
                raise CanaryStateError("Pi canary attempt history is malformed")
        if set(attempt) != allowed_keys:
            raise CanaryStateError("Pi canary attempt history contains unsafe metadata")
    if revision < count + finalized:
        raise CanaryStateError("Pi canary revision rollback detected")
    timestamps = [payload["created_at"], payload["updated_at"], payload["expires_at"]]
    if any(not _is_finite_number(value) for value in timestamps):
        raise CanaryStateError("Pi canary timestamps are malformed")
    created, updated, expires = (float(value) for value in timestamps)
    if created > updated or expires <= created or updated > now + 300:
        raise CanaryStateError("Pi canary timestamps are malformed")
    if now >= expires:
        raise CanaryStateError("Pi canary ledger is stale")
    return payload


def _write_state(path: Path, state: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(
                state,
                stream,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _ledger_lock(path: Path, *, timeout: float = _LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    lock_path = path.with_name(path.name + ".lock")
    if lock_path.is_symlink():
        raise CanaryStateError("Pi canary ledger lock is unsafe")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise CanaryStateError("Pi canary ledger lock is unavailable") from exc
    stream = os.fdopen(fd, "r+b", buffering=0)
    if stream.seek(0, os.SEEK_END) == 0:
        stream.write(b"0")
        stream.flush()
    deadline = time.monotonic() + timeout
    locked = False
    try:
        while not locked:
            try:
                _lock_stream(stream)
                locked = True
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise CanaryStateError("Pi canary ledger lock is unavailable or stale")
                time.sleep(0.02)
        yield
    finally:
        if locked:
            try:
                _unlock_stream(stream)
            except OSError:
                pass
        stream.close()


def _lock_stream(stream: object) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)  # type: ignore[attr-defined]
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]


def _unlock_stream(stream: object) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)  # type: ignore[attr-defined]
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
