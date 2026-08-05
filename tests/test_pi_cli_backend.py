"""Offline contract tests for Graphify's isolated Pi CLI backend."""

from __future__ import annotations

import base64
from io import BytesIO
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import pytest  # pyright: ignore[reportMissingImports]

from graphify import llm


_REQUIRED_FLAGS = (
    "--print --no-session --no-tools --no-extensions --no-skills "
    "--no-prompt-templates --no-themes --no-context-files --offline --approve "
    "--model --thinking --list-models"
)
_VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_VALID_RASTERS = {
    "image/png": base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEElEQVR4nGP8zwACTGCSAQANHQEDgslx/wAAAABJRU5ErkJggg=="
    ),
    "image/jpeg": base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi6KKK+ZP3E//Z"
    ),
    "image/gif": base64.b64decode("R0lGODdhAgACAIEAAP8AAAAAAAAAAAAAACwAAAAAAgACAAAIBgABCAQQEAA7"),
    "image/webp": base64.b64decode(
        "UklGRjwAAABXRUJQVlA4IDAAAADQAQCdASoCAAIAAUAmJaACdLoB+AADsAD+8ut//NgVzXPv9//S4P0uD9Lg/9KQAAA="
    ),
}


def _final_response(
    text: str = '{"nodes":[{"id":"a"}],"edges":[],"hyperedges":[]}',
) -> str:
    """Return one raw final response emitted by the fake ``pi --print`` child."""
    return text


def _fake_pi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_response: str | None = None,
    *,
    mode: str = "normal",
    stderr_bytes: int | None = None,
):
    """Install a fake executable that records only safe invocation metadata."""
    log = tmp_path / "fake-pi-log.json"
    if final_response is None:
        final_response = _final_response()
    model_rows = {
        "openai-codex/gpt-5.6-luna": ("openai-codex", "gpt-5.6-luna", "yes"),
        "chosen-model": ("fake", "chosen-model", "yes"),
        "label-model": ("fake", "label-model", "yes"),
        "env-model": ("fake", "env-model", "yes"),
        "text-only-model": ("fake", "text-only-model", "no"),
    }
    metadata_log = tmp_path / "fake-pi-metadata.jsonl"
    script = tmp_path / "pi"
    script.write_text(
        textwrap.dedent(
            f"""
            #!{sys.executable}
            import json, os, subprocess, sys, time
            def log_metadata(kind):
                record = {{
                    'kind': kind,
                    'cwd': os.getcwd(),
                    'parent_env': {{key: os.environ.get(key) for key in (
                        'PI_CODING_AGENT', 'PI_CODING_AGENT_SESSION_DIR', 'PI_SESSION_ID',
                        'PI_SESSION_FILE', 'PI_PROVIDER', 'PI_MODEL', 'PI_REASONING_LEVEL',
                        'PI_SUBAGENT_PARENT_SESSION', 'GRAPHIFY_PI_CANARY_LEDGER',
                        'GRAPHIFY_PI_CANARY_ID', 'GRAPHIFY_PI_CANARY_EXPECTED_ATTEMPTS')}},
                    'offline': os.environ.get('PI_OFFLINE'),
                }}
                with open({str(metadata_log)!r}, 'a', encoding='utf-8') as stream:
                    stream.write(json.dumps(record) + '\\n')
            if '--help' in sys.argv:
                log_metadata('help')
                print({json.dumps(_REQUIRED_FLAGS)})
                raise SystemExit(0)
            if '--list-models' in sys.argv:
                log_metadata('list-models')
                rows = {model_rows!r}
                query = sys.argv[sys.argv.index('--list-models') + 1] if sys.argv.index('--list-models') + 1 < len(sys.argv) else ''
                print('provider model context max-out thinking images')
                for key, (provider, model, images) in rows.items():
                    if not query or query in key or query == model:
                        print(provider, model, '272K', '128K', 'yes', images)
                raise SystemExit(0)
            def emit_final():
                sys.stdout.write({final_response!r})
                sys.stdout.flush()
            if {mode!r} == 'stdin_stall':
                time.sleep(30)
            log_metadata('model')
            prompt = sys.stdin.read()
            settings = os.path.join(os.getcwd(), '.pi', 'settings.json')
            record = {{
                'pid': os.getpid(),
                'argv': sys.argv[1:],
                'cwd': os.getcwd(),
                'prompt': prompt,
                'parent_env': {{key: os.environ.get(key) for key in (
                    'PI_CODING_AGENT', 'PI_CODING_AGENT_SESSION_DIR', 'PI_SESSION_ID',
                    'PI_SESSION_FILE', 'PI_PROVIDER', 'PI_MODEL', 'PI_REASONING_LEVEL',
                    'PI_SUBAGENT_PARENT_SESSION', 'GRAPHIFY_PI_CANARY_LEDGER',
                    'GRAPHIFY_PI_CANARY_ID', 'GRAPHIFY_PI_CANARY_EXPECTED_ATTEMPTS')}} ,
                'offline': os.environ.get('PI_OFFLINE'),
                'settings': json.load(open(settings, encoding='utf-8')),
                'settings_path': settings,
                'attachments': [
                    {{'arg': arg, 'bytes': open(arg[1:], 'rb').read().hex()}}
                    for arg in sys.argv[1:] if arg.startswith('@')
                ],
            }}
            json.dump(record, open({str(log)!r}, 'w', encoding='utf-8'))
            if {mode!r} == 'timeout':
                child = subprocess.Popen(['sleep', '30'])
                time.sleep(30)
            elif {mode!r} == 'partial_timeout':
                child = subprocess.Popen(['sleep', '30'])
                open({str(tmp_path / "grandchild.pid")!r}, 'w', encoding='utf-8').write(str(child.pid))
                print('partial', flush=True)
                time.sleep(30)
            elif {mode!r} == 'linger_success':
                child = subprocess.Popen(
                    ['sleep', '30'],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                open({str(tmp_path / "grandchild.pid")!r}, 'w', encoding='utf-8').write(str(child.pid))
                emit_final()
            elif {mode!r} == 'stderr':
                sys.stderr.write('x' * {70000 if stderr_bytes is None else stderr_bytes})
                sys.stderr.flush()
                emit_final()
            elif {mode!r} == 'malformed_utf8':
                os.write(1, b'\\xff')
            elif {mode!r} == 'eof_hang':
                os.close(1)
                os.close(2)
                time.sleep(30)
            elif {mode!r} == 'exit':
                emit_final()
                raise SystemExit(7)
            else:
                emit_final()
            """
        ).lstrip(),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    return log


def test_registration_model_precedence_and_zero_pricing(monkeypatch):
    assert llm.BACKENDS["pi"]["pricing"] == {"input": 0.0, "output": 0.0}
    assert llm._default_model_for_backend("pi") == "openai-codex/gpt-5.6-luna"
    monkeypatch.setenv("GRAPHIFY_PI_MODEL", "openai-codex/test-model")
    assert llm._default_model_for_backend("pi") == "openai-codex/test-model"
    assert llm._default_model_for_backend("ollama") != "openai-codex/test-model"


def test_explicit_model_and_thinking_precedence(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_PI_MODEL", "env-model")
    monkeypatch.setenv("GRAPHIFY_PI_THINKING", "medium")
    assert llm._default_model_for_backend("pi") == "env-model"
    assert llm._resolve_pi_thinking() == "medium"
    monkeypatch.setenv("GRAPHIFY_PI_THINKING", "not-a-level")
    with pytest.raises(ValueError, match="GRAPHIFY_PI_THINKING"):
        llm._resolve_pi_thinking()


def test_capability_doctor_checks_flags_without_model_call(tmp_path, monkeypatch):
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    result = llm.validate_backend_dependencies("pi")
    assert result is None
    assert not log.exists(), "--help capability check must not launch a model request"


def test_pi_backend_dependency_requires_pillow(monkeypatch):
    original_find_spec = llm.find_spec
    monkeypatch.setattr(
        llm,
        "find_spec",
        lambda package: None if package == "PIL" else original_find_spec(package),
    )
    monkeypatch.setattr(
        llm,
        "_check_pi_capabilities",
        lambda **_kwargs: pytest.fail("capability subprocess must not run without Pillow"),
    )

    with pytest.raises(ImportError, match="requires Pillow"):
        llm.validate_backend_dependencies("pi")


def test_doctor_and_probe_use_fake_capability_metadata(tmp_path, monkeypatch):
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    from graphify.__main__ import _doctor

    assert _doctor(backend="pi", probe=True) == 0
    records = [
        json.loads(line)
        for line in (tmp_path / "fake-pi-metadata.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [record["kind"] for record in records] == ["help", "help", "help", "model"]
    assert log.is_file(), "the three capability checks must precede the model child"


def test_capability_metadata_isolated_from_target_project_and_parent_session(tmp_path, monkeypatch):
    target = tmp_path / "target"
    target_settings = target / ".pi" / "settings.json"
    target_settings.parent.mkdir(parents=True)
    target_settings.write_text('{"sentinel":"unchanged"}\n', encoding="utf-8")
    monkeypatch.chdir(target)
    for key in (
        "PI_CODING_AGENT",
        "PI_CODING_AGENT_SESSION_DIR",
        "PI_SESSION_ID",
        "PI_SESSION_FILE",
        "PI_PROVIDER",
        "PI_MODEL",
        "PI_REASONING_LEVEL",
        "PI_SUBAGENT_PARENT_SESSION",
    ):
        monkeypatch.setenv(key, "outer-private-session")
    _fake_pi(tmp_path, monkeypatch, _final_response())

    result = llm._check_pi_capabilities(model="chosen-model", require_image=True)

    records = [
        json.loads(line)
        for line in (tmp_path / "fake-pi-metadata.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert result["image_capable"] is True
    assert [record["kind"] for record in records] == ["help", "list-models"]
    assert all(Path(record["cwd"]) != target for record in records)
    assert all(not Path(record["cwd"]).exists() for record in records)
    assert all(all(value is None for value in record["parent_env"].values()) for record in records)
    assert all(record["offline"] == "1" for record in records)
    assert target_settings.read_text(encoding="utf-8") == '{"sentinel":"unchanged"}\n'


def test_capability_flags_require_exact_option_tokens(monkeypatch):
    near_matches = " ".join(f"{flag}-unsupported" for flag in llm._PI_REQUIRED_FLAGS)
    monkeypatch.setattr(llm, "_resolve_pi_executable", lambda: "/fake/pi")
    monkeypatch.setattr(llm, "_pi_metadata_output", lambda *_, **__: near_matches)

    with pytest.raises(RuntimeError, match="missing required capabilities") as exc:
        llm._check_pi_capabilities()

    assert "--print" in str(exc.value)


def test_invocation_isolated_stdin_and_safe_metadata(tmp_path, monkeypatch):
    source = tmp_path / "private-note.md"
    source.write_text("source only on stdin", encoding="utf-8")
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    monkeypatch.setenv("PI_SESSION_ID", "outer-session")
    result = llm.extract_files_direct([source], backend="pi", root=tmp_path, model="chosen-model")
    record = json.loads(log.read_text(encoding="utf-8"))
    assert result["nodes"] == [{"id": "a"}]
    assert result["usage_available"] is False
    assert "provider" not in result
    assert "model" not in result
    assert "usage" not in result
    assert "stop_reason" not in result
    assert result["requested_model"] == "chosen-model"
    assert result["requested_thinking"] == "high"
    assert result["elapsed_seconds"] >= 0
    assert "source only on stdin" in record["prompt"]
    assert all("source only" not in arg for arg in record["argv"])
    assert record["argv"] == [
        "--print",
        "--no-session",
        "--no-tools",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--offline",
        "--approve",
        "--model",
        "chosen-model",
        "--thinking",
        "high",
    ]
    assert "--mode" not in record["argv"]
    assert all(value is None for value in record["parent_env"].values())
    assert record["offline"] == "1"
    assert not Path(record["cwd"]).exists(), "temporary Pi project must be removed"


def test_print_plain_text_path_has_unavailable_usage(tmp_path, monkeypatch):
    log = _fake_pi(tmp_path, monkeypatch, _final_response("Order Flow"))
    usage: dict[str, int | bool] = {}
    text = llm._call_llm("name this", backend="pi", model="label-model", usage_out=usage)
    assert text == "Order Flow"
    assert usage == {"usage_available": False}
    record = json.loads(log.read_text(encoding="utf-8"))
    assert record["argv"][record["argv"].index("--model") + 1] == "label-model"


def test_pi_campaign_reserves_and_completes_at_dispatch_boundary(tmp_path, monkeypatch):
    from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
        CAMPAIGN_ENV_KEYS,
        campaign_environment,
        create_campaign,
        read_campaign,
    )

    ledger = tmp_path / "ledger.json"
    campaign_id = "campaign-12345678"
    create_campaign(ledger, campaign_id=campaign_id)
    for key, value in campaign_environment(ledger, campaign_id, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")

    result = llm.extract_files_direct([source], backend="pi", root=tmp_path)

    assert result["usage_available"] is False
    state = read_campaign(ledger, campaign_id)
    assert state["attempts_reserved"] == 1
    attempt = state["attempts"][0]
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
    child_record = json.loads(log.read_text(encoding="utf-8"))
    assert all(child_record["parent_env"][key] is None for key in CAMPAIGN_ENV_KEYS)


def test_pi_campaign_sixth_denied_before_popen(tmp_path, monkeypatch):
    from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
        CanaryLimitError,
        campaign_environment,
        create_campaign,
        reserve_attempt,
    )

    ledger = tmp_path / "ledger.json"
    campaign_id = "campaign-12345678"
    create_campaign(ledger, campaign_id=campaign_id)
    for expected in range(5):
        reserve_attempt(ledger, campaign_id, expected_attempts=expected)
    for key, value in campaign_environment(ledger, campaign_id, expected_attempts=5).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        llm,
        "_check_pi_capabilities",
        lambda **_kwargs: {"executable": "/must-not-launch/pi"},
    )
    launches = []

    def forbidden_popen(*args, **kwargs):
        launches.append((args, kwargs))
        raise AssertionError("exhausted campaign reached Popen")

    monkeypatch.setattr(subprocess, "Popen", forbidden_popen)

    with pytest.raises(CanaryLimitError, match="before child dispatch"):
        llm._pi_process(
            "prompt",
            model="openai-codex/gpt-5.6-luna",
            thinking="high",
            max_tokens=100,
        )

    assert launches == []


def test_pi_campaign_popen_failure_still_consumes_reservation(tmp_path, monkeypatch):
    from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
        campaign_environment,
        create_campaign,
        read_campaign,
    )

    ledger = tmp_path / "ledger.json"
    campaign_id = "campaign-12345678"
    create_campaign(ledger, campaign_id=campaign_id)
    for key, value in campaign_environment(ledger, campaign_id, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        llm,
        "_check_pi_capabilities",
        lambda **_kwargs: {"executable": "/fails-to-launch/pi"},
    )
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("launch failed")),
    )

    with pytest.raises(OSError, match="launch failed"):
        llm._pi_process(
            "prompt",
            model="openai-codex/gpt-5.6-luna",
            thinking="high",
            max_tokens=100,
        )

    state = read_campaign(ledger, campaign_id)
    assert state["attempts_reserved"] == 1
    assert state["attempts"][0]["status"] == "failed"
    assert state["attempts"][0]["failure_code"] == "launch"


def test_pi_extraction_chunks_are_forced_serial(tmp_path, monkeypatch):
    import threading
    import time

    files = [tmp_path / f"doc-{index}.md" for index in range(4)]
    for path in files:
        path.write_text(path.stem, encoding="utf-8")
    lock = threading.Lock()
    state = {"active": 0, "peak": 0}

    def fake_extract(chunk, **kwargs):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        time.sleep(0.02)
        with lock:
            state["active"] -= 1
        path = Path(chunk[0])
        return {
            "nodes": [{"id": path.stem, "source_file": str(path)}],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }

    monkeypatch.setattr(llm, "_extract_with_adaptive_retry", fake_extract)

    result = llm.extract_corpus_parallel(
        files,
        backend="pi",
        root=tmp_path,
        chunk_size=1,
        token_budget=None,
        max_concurrency=8,
        checkpoint_cache=False,
    )

    assert result["failed_chunks"] == 0
    assert state["peak"] == 1


def test_missing_capability_is_fail_closed(tmp_path, monkeypatch):
    log = tmp_path / "help.log"
    script = tmp_path / "pi"
    script.write_text(
        f"#!{sys.executable}\nopen({str(log)!r}, 'w').write('help')\nprint('--print')\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    with pytest.raises(RuntimeError, match="missing required capabilities"):
        llm.validate_backend_dependencies("pi")


@pytest.mark.parametrize(
    "final_response, expected",
    [
        ("not-json", "invalid final JSON"),
        ("", "hollow final response"),
        ('{"nodes":[],"edges":[],"hyperedges":[]}', "hollow final response"),
        ('{"type":"message_update"}', "invalid Graphify shape"),
        ("[]", "not a Graphify JSON object"),
        ('```json\n{"nodes":[{"id":"a"}],"edges":[],"hyperedges":[]}\n```', "invalid final JSON"),
        (
            'Here is the graph: {"nodes":[{"id":"a"}],"edges":[],"hyperedges":[]}',
            "invalid final JSON",
        ),
        (
            '{"nodes":[{"id":"a"}],"edges":[],"hyperedges":[]}\n{"nodes":[{"id":"b"}],"edges":[],"hyperedges":[]}',
            "invalid final JSON",
        ),
    ],
)
def test_strict_final_response_failures(tmp_path, monkeypatch, final_response, expected):
    _fake_pi(tmp_path, monkeypatch, final_response)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match=expected):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_malformed_utf8_final_response_fails_closed(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, mode="malformed_utf8")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match="malformed UTF-8"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_pi_campaign_final_bound_records_fixed_safe_code(tmp_path, monkeypatch):
    from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
        campaign_environment,
        create_campaign,
        read_campaign,
    )

    ledger = tmp_path / "ledger.json"
    campaign_id = "campaign-12345678"
    create_campaign(ledger, campaign_id=campaign_id)
    for key, value in campaign_environment(ledger, campaign_id, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": 3, "stderr_stream": 8},
    )
    _fake_pi(tmp_path, monkeypatch, "abcd")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")

    with pytest.raises(llm._PiOutputLimitError):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)

    state = read_campaign(ledger, campaign_id)
    assert state["attempts"][0]["status"] == "failed"
    assert state["attempts"][0]["failure_code"] == "output_stdout_stream"
    assert "abcd" not in json.dumps(state)


def test_pi_campaign_stdout_bound_records_fixed_stream_subtype(tmp_path, monkeypatch):
    from graphify.pi_canary import (  # pyright: ignore[reportMissingImports]
        campaign_environment,
        create_campaign,
        read_campaign,
    )

    ledger = tmp_path / "ledger.json"
    campaign_id = "campaign-12345678"
    create_campaign(ledger, campaign_id=campaign_id)
    for key, value in campaign_environment(ledger, campaign_id, expected_attempts=0).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": 100, "stderr_stream": 8},
    )
    _fake_pi(tmp_path, monkeypatch, "x" * 101)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")

    with pytest.raises(llm._PiOutputLimitError, match="final response"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)

    state = read_campaign(ledger, campaign_id)
    assert state["attempts"][0]["status"] == "failed"
    assert state["attempts"][0]["failure_code"] == "output_stdout_stream"


def test_print_response_omits_unavailable_length_metadata(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, _final_response())
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    result = llm.extract_files_direct([source], backend="pi", root=tmp_path)
    assert result["usage_available"] is False
    assert "finish_reason" not in result


def test_output_limit_error_adaptively_splits_and_merges(tmp_path, monkeypatch):
    files = [tmp_path / "left.md", tmp_path / "right.md"]
    for path in files:
        path.write_text(path.stem, encoding="utf-8")
    calls: list[list[Path]] = []

    def bounded_direct(chunk, **_kwargs):
        calls.append(list(chunk))
        if len(chunk) > 1:
            raise llm._PiOutputLimitError("bounded transport output")
        return {
            "nodes": [{"id": Path(chunk[0]).stem}],
            "edges": [],
            "hyperedges": [],
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "extract_files_direct", bounded_direct)

    result = llm._extract_with_adaptive_retry(
        files, "pi", None, None, tmp_path, max_depth=2, allow_image_upload=False
    )

    assert [node["id"] for node in result["nodes"]] == ["left", "right"]
    assert calls == [files, [files[0]], [files[1]]]
    assert result["partial_chunks"] == 0


def test_output_limit_error_at_unsplittable_leaf_is_partial(tmp_path, monkeypatch):
    source = tmp_path / "short.md"
    source.write_text("short", encoding="utf-8")
    monkeypatch.setattr(
        llm,
        "extract_files_direct",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            llm._PiOutputLimitError("bounded transport output")
        ),
    )

    result = llm._extract_with_adaptive_retry(
        [source], "pi", None, None, tmp_path, max_depth=2, allow_image_upload=False
    )

    assert result["nodes"] == []
    assert result["_partial_files"] == [str(source)]
    assert result["partial_chunks"] == 1


def test_pi_adaptive_split_merge_has_only_requested_metadata(tmp_path, monkeypatch):
    files = [tmp_path / "left.md", tmp_path / "right.md"]
    for path in files:
        path.write_text(path.stem, encoding="utf-8")

    def bounded_direct(chunk, **_kwargs):
        if len(chunk) > 1:
            raise llm._PiOutputLimitError("bounded transport output")
        return {
            "nodes": [{"id": Path(chunk[0]).stem}],
            "edges": [],
            "hyperedges": [],
            "model": "provider-response-model",
            "finish_reason": "stop",
            "usage_available": False,
            "requested_backend": "pi",
            "requested_model": "requested-model",
            "requested_thinking": "high",
        }

    monkeypatch.setattr(llm, "extract_files_direct", bounded_direct)
    result = llm._extract_with_adaptive_retry(
        files,
        "pi",
        None,
        "requested-model",
        tmp_path,
        max_depth=2,
        allow_image_upload=False,
    )

    assert result["usage_available"] is False
    assert result["requested_backend"] == "pi"
    assert result["requested_model"] == "requested-model"
    assert result["requested_thinking"] == "high"
    assert "model" not in result
    assert "finish_reason" not in result


def test_pi_adaptive_leaf_partial_has_only_requested_metadata(tmp_path, monkeypatch):
    source = tmp_path / "short.md"
    source.write_text("short", encoding="utf-8")

    monkeypatch.setattr(
        llm,
        "extract_files_direct",
        lambda *_args, **_kwargs: {
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "model": "provider-response-model",
            "finish_reason": "length",
            "usage_available": False,
            "requested_backend": "pi",
            "requested_model": "requested-model",
            "requested_thinking": "high",
        },
    )
    result = llm._extract_with_adaptive_retry(
        [source],
        "pi",
        None,
        "requested-model",
        tmp_path,
        max_depth=0,
        allow_image_upload=False,
    )

    assert result["usage_available"] is False
    assert result["requested_backend"] == "pi"
    assert result["requested_model"] == "requested-model"
    assert result["requested_thinking"] == "high"
    assert "model" not in result
    assert "finish_reason" not in result


def test_exact_incremental_limits_and_output_bound_cleanup(tmp_path, monkeypatch):
    limits = llm._pi_output_limits(100)
    assert limits == {"final_response": 1_048_576, "stderr_stream": 65_536}
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": 3, "stderr_stream": 8},
    )
    log = _fake_pi(tmp_path, monkeypatch, "abcd")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(llm._PiOutputLimitError, match="final response"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)
    record = json.loads(log.read_text(encoding="utf-8"))
    assert not Path(record["cwd"]).exists()
    if os.name != "nt":
        with pytest.raises(ProcessLookupError):
            os.kill(record["pid"], 0)


def test_timeout_and_process_group_cleanup(tmp_path, monkeypatch):
    log = _fake_pi(tmp_path, monkeypatch, mode="timeout")
    monkeypatch.setenv("GRAPHIFY_API_TIMEOUT", "0.1")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match="timed out"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)
    record = json.loads(log.read_text(encoding="utf-8"))
    assert not Path(record["cwd"]).exists()
    if os.name != "nt":
        with pytest.raises(ProcessLookupError):
            os.kill(record["pid"], 0)


def test_eof_then_hang_maps_to_safe_timeout_without_attachment_path(tmp_path, monkeypatch):
    image = tmp_path / "private-diagram.png"
    image.write_bytes(_VALID_PNG)
    log = _fake_pi(tmp_path, monkeypatch, mode="eof_hang")
    monkeypatch.setenv("GRAPHIFY_API_TIMEOUT", "0.1")

    with pytest.raises(RuntimeError, match="child process was terminated") as exc:
        llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)

    assert str(image) not in str(exc.value)
    assert "private-diagram" not in str(exc.value)
    record = json.loads(log.read_text(encoding="utf-8"))
    assert not Path(record["cwd"]).exists()
    if os.name != "nt":
        with pytest.raises(ProcessLookupError):
            os.kill(record["pid"], 0)


def test_pi_rejects_external_swap_before_image_snapshot(tmp_path, monkeypatch):
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    outside = tmp_path / "outside.png"
    outside.write_bytes(_VALID_PNG)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    original_resolve = llm._resolve_under_root
    calls = 0

    def swap_after_authorization(path, root):
        nonlocal calls
        resolved = original_resolve(path, root)
        calls += 1
        if calls == 1:
            image.unlink()
            image.symlink_to(outside)
        return resolved

    monkeypatch.setattr(llm, "_resolve_under_root", swap_after_authorization)
    with pytest.raises(ValueError, match="verified raster"):
        llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    assert not log.exists(), "unsafe replacement must never reach the Pi child"
    assert outside.read_bytes() == _VALID_PNG


def test_pi_rejects_regular_swap_after_authorization_before_descriptor_open(tmp_path, monkeypatch):
    """A valid replacement after auth cannot become pixel-derived Pi input."""
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    replacement_path = tmp_path / "replacement.png"
    replacement = _VALID_RASTERS["image/png"]
    replacement_path.write_bytes(replacement)
    assert replacement != _VALID_PNG
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    original_resolve = llm._resolve_under_root
    calls = 0

    def swap_after_authorization(path, root):
        nonlocal calls
        resolved = original_resolve(path, root)
        calls += 1
        if calls == 1:
            image.unlink()
            replacement_path.rename(image)
        return resolved

    monkeypatch.setattr(llm, "_resolve_under_root", swap_after_authorization)
    with pytest.raises(ValueError, match="verified raster"):
        llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    assert not log.exists(), "replaced raster must never be staged or sent to Pi"
    assert image.read_bytes() == replacement


def test_pi_rejects_regular_swap_after_snapshot_before_staging(tmp_path, monkeypatch):
    """A replacement observed before staging launches no Pi child."""
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    replacement_path = tmp_path / "replacement.png"
    replacement = _VALID_RASTERS["image/png"]
    replacement_path.write_bytes(replacement)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    original_stage = llm._stage_pi_images

    def swap_before_stage(images, project):
        image.unlink()
        replacement_path.rename(image)
        return original_stage(images, project)

    monkeypatch.setattr(llm, "_stage_pi_images", swap_before_stage)
    with pytest.raises(ValueError, match="source identity changed"):
        llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    assert not log.exists(), "pre-staging replacement must dispatch zero Pi attachments"
    assert image.read_bytes() == replacement


def test_pi_post_stage_replacement_is_partial_and_not_pixel_cacheable(tmp_path, monkeypatch):
    """A sent snapshot is retained only as partial output after a later replacement."""
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    replacement_path = tmp_path / "replacement.png"
    replacement = _VALID_RASTERS["image/png"]
    replacement_path.write_bytes(replacement)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    original_process = llm._pi_process

    def process_then_replace(prompt, **kwargs):
        result = original_process(prompt, **kwargs)
        image.unlink()
        replacement_path.rename(image)
        return result

    monkeypatch.setattr(llm, "_pi_process", process_then_replace)
    result = llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    assert (
        json.loads(log.read_text(encoding="utf-8"))["attachments"][0]["bytes"] == _VALID_PNG.hex()
    )
    assert result["partial_chunks"] == 1
    assert result["_partial_files"] == [str(image)]
    assert "_image_provenance" not in result

    from graphify.cache import cache_dir, file_hash, load_cached

    image.write_bytes(_VALID_PNG)
    replacement_path.write_bytes(replacement)
    cached = llm.extract_corpus_parallel(
        [image],
        backend="pi",
        root=tmp_path,
        cache_root=tmp_path / "cache",
        max_concurrency=1,
        checkpoint_cache=True,
        allow_image_upload=True,
    )
    assert cached["partial_chunks"] == 1
    cache_entries = list(
        cache_dir(tmp_path / "cache", "semantic").glob(
            f"p*/{file_hash(image, tmp_path, cache_root=tmp_path / 'cache')}.json"
        )
    )
    assert len(cache_entries) == 1
    payload = json.loads(cache_entries[0].read_text(encoding="utf-8"))
    assert payload["partial"] is True
    assert payload["image_provenance"] == "reference-only"
    assert load_cached(image, root=tmp_path, cache_root=tmp_path / "cache", kind="semantic") is None


def test_image_consent_native_attachment_settings_and_cleanup(tmp_path, monkeypatch):
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    with pytest.raises(ValueError, match="--allow-image-upload"):
        llm.extract_files_direct([image], backend="pi", root=tmp_path)
    assert not log.exists(), "denied image delivery must launch no Pi request"

    result = llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    record = json.loads(log.read_text(encoding="utf-8"))
    attachments = record["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["arg"].startswith("@")
    assert Path(attachments[0]["arg"][1:]) != image.resolve()
    assert Path(attachments[0]["arg"][1:]).name == "0000.png"
    assert attachments[0]["bytes"] == _VALID_PNG.hex()
    assert record["settings"]["images"] == {"blockImages": False}
    assert "image_provenance" not in result
    assert result["_image_provenance"] == {str(image): "pixel-derived"}
    assert not Path(record["cwd"]).exists()


def test_final_response_exact_limit_and_next_byte(tmp_path, monkeypatch):
    limit = 100
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": limit, "stderr_stream": 8},
    )
    graph = json.dumps({"nodes": [{"id": "x", "label": "x"}], "edges": [], "hyperedges": []})
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")

    exact_response = graph + (" " * (limit - len(graph)))
    assert len(exact_response.encode("utf-8")) == limit
    _fake_pi(tmp_path, monkeypatch, exact_response)
    assert llm.extract_files_direct([source], backend="pi", root=tmp_path)["nodes"] == [
        {"id": "x", "label": "x"}
    ]

    next_response = graph + (" " * (limit + 1 - len(graph)))
    assert len(next_response.encode("utf-8")) == limit + 1
    _fake_pi(tmp_path, monkeypatch, next_response)
    with pytest.raises(llm._PiOutputLimitError, match="final response"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_plain_text_print_response_has_no_usage_metadata(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, "PRIVATE_LABEL")
    usage: dict[str, int | bool] = {}
    assert (
        llm._call_llm("name this", backend="pi", model="label-model", usage_out=usage)
        == "PRIVATE_LABEL"
    )
    assert usage == {"usage_available": False}


def test_print_response_ignores_provider_usage_fields(tmp_path, monkeypatch):
    graph = (
        '{"nodes":[{"id":"a"}],"edges":[],"hyperedges":[],'
        '"provider":"private","usage":{"input":11},"stopReason":"stop"}'
    )
    _fake_pi(tmp_path, monkeypatch, graph)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    result = llm.extract_files_direct([source], backend="pi", root=tmp_path)
    assert result["usage_available"] is False
    assert "usage" not in result
    assert "provider" not in result
    assert "stop_reason" not in result


def test_literal_jsonl_event_output_is_rejected_as_one_final_response(tmp_path, monkeypatch):
    event = json.dumps(
        {"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "x"}}
    )
    _fake_pi(tmp_path, monkeypatch, event + "\n" + event)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid final JSON"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_stderr_exact_limit_and_next_byte(tmp_path, monkeypatch):
    stderr_limit = 8
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": 10000, "stderr_stream": stderr_limit},
    )
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")

    _fake_pi(tmp_path, monkeypatch, _final_response(), mode="stderr", stderr_bytes=stderr_limit)
    assert llm.extract_files_direct([source], backend="pi", root=tmp_path)["nodes"] == [{"id": "a"}]

    _fake_pi(
        tmp_path,
        monkeypatch,
        _final_response(),
        mode="stderr",
        stderr_bytes=stderr_limit + 1,
    )
    with pytest.raises(llm._PiOutputLimitError, match="stderr"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_nonzero_exit_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        llm,
        "_pi_output_limits",
        lambda _tokens: {"final_response": 10000, "stderr_stream": 8},
    )
    _fake_pi(tmp_path, monkeypatch, _final_response(), mode="exit")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match="status 7"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)


def test_partial_output_hang_and_grandchild_are_cleaned(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, mode="partial_timeout")
    monkeypatch.setenv("GRAPHIFY_API_TIMEOUT", "0.1")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(RuntimeError, match="timed out"):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)
    pid_file = tmp_path / "grandchild.pid"
    if pid_file.exists() and os.name != "nt":
        pid = int(pid_file.read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_termination_reaps_direct_child_and_group():
    proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
    llm._terminate_pi_process(proc, process_group_id=proc.pid)
    assert proc.poll() is not None
    proc.wait(timeout=1)


def test_windows_pi_launch_is_suspended_until_job_assignment_and_resume(monkeypatch):
    from types import SimpleNamespace

    events: list[str] = []

    class Boundary:
        def assign(self, _proc):
            events.append("assign")

        def resume(self, _proc):
            events.append("resume")

    process = SimpleNamespace(pid=123)

    def fake_popen(args, **kwargs):
        events.append("popen")
        assert kwargs["creationflags"] & 0x00000004
        return process

    monkeypatch.setattr(llm.os, "name", "nt")
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    assert llm._launch_pi_process(["pi"], {"creationflags": 0}, cast(Any, Boundary())) is process
    assert events == ["popen", "assign", "resume"]


def test_windows_pi_launch_failure_never_falls_back_uncontained(monkeypatch):
    from types import SimpleNamespace

    events: list[str] = []

    class Process:
        pid = 321

        def wait(self, **_kwargs):
            events.append("wait")
            return -1

        def kill(self):
            events.append("kill")

    class Boundary:
        assigned = False

        def assign(self, _proc):
            events.append("assign")
            raise OSError("assignment failed")

        def close(self):
            events.append("close")

    monkeypatch.setattr(llm.os, "name", "nt")
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    with pytest.raises(RuntimeError, match="refusing to run an uncontained"):
        llm._launch_pi_process(["pi"], {}, cast(Any, Boundary()))
    assert events == ["assign", "close", "wait"]


def test_windows_unassigned_job_cleanup_falls_back_to_tree_termination(monkeypatch):
    from types import SimpleNamespace

    class Process:
        pid = 654

        def wait(self, **_kwargs):
            return -1

        def kill(self):
            pytest.fail("taskkill should handle an unassigned process")

    boundary = SimpleNamespace(assigned=False, close=MagicMock())
    calls: list[list[str]] = []

    monkeypatch.setattr(llm.os, "name", "nt")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **_kwargs: calls.append(args) or SimpleNamespace(returncode=0),
    )
    llm._terminate_pi_process(Process(), process_tree_boundary=boundary)
    boundary.close.assert_called_once_with()
    assert calls == [["taskkill", "/PID", "654", "/T", "/F"]]


def test_windows_job_boundary_assigns_and_closes_with_kill_on_close(monkeypatch):
    """Exercise the Win32 Job Object lifecycle with a fake kernel32 surface."""
    import ctypes
    from types import SimpleNamespace

    class FakeFunction:
        def __init__(self, result=1):
            self.result = result
            self.calls = []
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    class FakeKernel32:
        def __init__(self):
            self.CreateJobObjectW = FakeFunction(101)
            self.SetInformationJobObject = FakeFunction(1)
            self.AssignProcessToJobObject = FakeFunction(1)
            self.CloseHandle = FakeFunction(1)

    kernel32 = FakeKernel32()
    monkeypatch.setattr(llm.os, "name", "nt")
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda _name, use_last_error=True: kernel32,
        raising=False,
    )
    boundary = llm._WindowsProcessTreeBoundary()
    boundary.assign(SimpleNamespace(_handle=202))
    boundary.close()
    boundary.close()

    set_information_args = kernel32.SetInformationJobObject.calls[0]
    assert set_information_args[1] == 9
    # The two 8-byte time-limit fields precede BasicLimitInformation.LimitFlags.
    limit_flags = ctypes.cast(set_information_args[2], ctypes.POINTER(ctypes.c_uint32))[4]
    assert limit_flags == llm._WindowsProcessTreeBoundary._KILL_ON_JOB_CLOSE == 0x2000
    assert kernel32.AssignProcessToJobObject.calls == [(101, 202)]
    assert kernel32.CloseHandle.calls == [(101,)]


def test_windows_success_cleanup_closes_job_without_taskkill(monkeypatch):
    """An exited parent still closes the durable descendant boundary."""
    from types import SimpleNamespace

    class ExitedProcess:
        pid = 404

        def wait(self, **_kwargs):
            return 0

        def kill(self):
            pytest.fail("an already-exited process must not require kill")

    boundary = SimpleNamespace(close=MagicMock())
    monkeypatch.setattr(llm.os, "name", "nt")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("taskkill is not the durable boundary"),
    )

    llm._terminate_pi_process(ExitedProcess(), process_tree_boundary=boundary)

    boundary.close.assert_called_once_with()


def test_keyboard_interrupt_cleans_child(tmp_path, monkeypatch):
    import queue

    log = _fake_pi(tmp_path, monkeypatch, mode="timeout")
    monkeypatch.setattr(
        llm,
        "_check_pi_capabilities",
        lambda **_kwargs: {"executable": str(tmp_path / "pi")},
    )
    original_get = queue.Queue.get
    interrupted = False

    def interrupt_once(self, *args, **kwargs):
        nonlocal interrupted
        if log.exists() and not interrupted:
            interrupted = True
            raise KeyboardInterrupt
        return original_get(self, *args, **kwargs)

    monkeypatch.setattr(queue.Queue, "get", interrupt_once)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    with pytest.raises(KeyboardInterrupt):
        llm.extract_files_direct([source], backend="pi", root=tmp_path)
    record = json.loads(log.read_text(encoding="utf-8"))
    assert not Path(record["cwd"]).exists()
    if os.name != "nt":
        with pytest.raises(ProcessLookupError):
            os.kill(record["pid"], 0)


def test_real_pi_list_models_table_shape_is_parsed_exactly():
    output = (
        "provider      model         context  max-out  thinking  images\n"
        "openai-codex  gpt-5.6-luna  272K     128K     yes       yes\n"
    )
    assert llm._pi_model_image_capability(output, "openai-codex/gpt-5.6-luna") is True
    assert llm._pi_model_image_capability(output, "gpt-5.6-luna") is True
    assert llm._pi_model_image_capability(output, "openai-codex/gpt-5.6") is False


@pytest.mark.parametrize(
    "name, raw",
    [
        ("truncated.png", b"\x89PNG\r\n\x1a\n"),
        ("truncated.jpg", b"\xff\xd8\xff\xe0"),
        ("truncated.gif", b"GIF89a"),
        ("truncated.webp", b"RIFF\x04\x00\x00\x00WEBP"),
        (
            "malformed.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            + b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            + b"\x00\x00\x00\x00\x00\x00\x00\x00IDAT\x00\x00\x00\x00"
            + b"\x00\x00\x00\x00IEND\x00\x00\x00\x00",
        ),
        (
            "malformed.jpg",
            b"\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x02\xff\xd9",
        ),
        (
            "malformed.gif",
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff,;",
        ),
        (
            "malformed.webp",
            b"RIFF\x0c\x00\x00\x00WEBPVP8 \x00\x00\x00\x00",
        ),
        (
            "decoder-rejected.jpg",
            _VALID_RASTERS["image/jpeg"][:21]
            + bytes([_VALID_RASTERS["image/jpeg"][21] ^ 0x20])
            + _VALID_RASTERS["image/jpeg"][22:],
        ),
        (
            "decoder-rejected.webp",
            _VALID_RASTERS["image/webp"][:20]
            + bytes([_VALID_RASTERS["image/webp"][20] ^ 0x80])
            + _VALID_RASTERS["image/webp"][21:],
        ),
    ],
)
def test_malformed_raster_is_not_treated_as_verified_pixels(tmp_path, monkeypatch, name, raw):
    image = tmp_path / name
    image.write_bytes(raw)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    with pytest.raises(ValueError, match="not a verified raster"):
        llm.extract_files_direct([image], backend="pi", root=tmp_path, allow_image_upload=True)
    assert not log.exists()


@pytest.mark.parametrize("media_type,raw", _VALID_RASTERS.items())
def test_complete_supported_rasters_are_verified(media_type, raw):
    assert llm._has_raster_signature(raw, media_type) is True


def test_animated_supported_rasters_decode_all_frames():
    from PIL import Image

    frames = [Image.new("RGB", (2, 2), color) for color in ((255, 0, 0), (0, 0, 255))]
    for image_format, media_type in (("GIF", "image/gif"), ("WEBP", "image/webp")):
        output = BytesIO()
        frames[0].save(
            output,
            format=image_format,
            save_all=True,
            append_images=frames[1:],
            duration=20,
            loop=0,
        )
        raw = output.getvalue()
        with Image.open(BytesIO(raw)) as decoded:
            assert getattr(decoded, "n_frames", 1) == 2
        assert llm._has_raster_signature(raw, media_type) is True


def test_model_metadata_is_unavailable_and_label_parse_stays_safe(tmp_path, monkeypatch):
    graph = '{"nodes":[{"id":"a"}],"edges":[],"hyperedges":[]}'
    _fake_pi(tmp_path, monkeypatch, graph)
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    result = llm.extract_files_direct([source], backend="pi", root=tmp_path)
    assert result["usage_available"] is False
    assert "provider" not in result

    with pytest.raises(ValueError, match="not parseable JSON") as label_exc:
        llm._parse_label_response("PRIVATE_SOURCE_LINE", [0])
    assert "PRIVATE_SOURCE_LINE" not in str(label_exc.value)


def test_stalled_stdin_write_obeys_request_deadline(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, mode="stdin_stall")
    monkeypatch.setenv("GRAPHIFY_API_TIMEOUT", "0.1")
    with pytest.raises(RuntimeError, match="timed out"):
        llm._pi_process(
            "x" * 1_000_000,
            model="chosen-model",
            thinking="high",
            max_tokens=100,
        )


def test_successful_parent_exit_cleans_lingering_process_group(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, _final_response(), mode="linger_success")
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    assert llm.extract_files_direct([source], backend="pi", root=tmp_path)["nodes"] == [{"id": "a"}]
    if os.name != "nt":
        pid = int((tmp_path / "grandchild.pid").read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_text_only_model_remains_supported_for_text(tmp_path, monkeypatch):
    _fake_pi(tmp_path, monkeypatch, _final_response())
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    result = llm.extract_files_direct(
        [source], backend="pi", model="text-only-model", root=tmp_path
    )
    assert result["nodes"] == [{"id": "a"}]


def test_text_only_model_denies_image_dispatch(tmp_path, monkeypatch):
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    log = _fake_pi(tmp_path, monkeypatch, _final_response())
    with pytest.raises(RuntimeError, match="does not advertise image capability"):
        llm.extract_files_direct(
            [image], backend="pi", model="text-only-model", root=tmp_path, allow_image_upload=True
        )
    assert not log.exists()


def test_svg_is_text_and_ollama_path_is_untouched(tmp_path, monkeypatch):
    svg = tmp_path / "diagram.svg"
    svg.write_text("<svg><text>source</text></svg>", encoding="utf-8")
    assert llm._partition_semantic_files([svg]) == ([svg], [])
    assert llm.detect_backend() == "ollama"
