"""Tests for image-vision support across the direct extraction backends.

Covers the structured-message split (text vs raster image), the per-backend
payload rendering (Anthropic base64 blocks, OpenAI/Gemini image_url data URIs,
Bedrock raw-bytes Converse blocks, the claude-cli Read-tool path), and the vision-capability gating that sends pixels only to
backends whose model can see them.

Every backend is mocked (fake SDK module / subprocess), so the suite runs on CI
with no API keys, no network, and no `claude` binary.
"""

from __future__ import annotations

import base64
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest  # pyright: ignore[reportMissingImports]

from graphify import llm

# A 1x1 PNG is unnecessary — the renderers never decode pixels, they only base64
# the bytes — so any non-empty byte string stands in for image content.
_PNG_BYTES = b"\x89PNG\r\n\x1a\nFAKEPIXELDATA"
_VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_NODE_JSON = json.dumps(
    {
        "nodes": [{"id": "x", "label": "L", "file_type": "image", "source_file": "a.png"}],
        "edges": [],
        "hyperedges": [],
    }
)


def _make_corpus(tmp_path):
    """A corpus with one raster image, one svg (text), and one markdown doc."""
    (tmp_path / "sub").mkdir()
    img = tmp_path / "sub" / "diagram.png"
    img.write_bytes(_PNG_BYTES)
    svg = tmp_path / "icon.svg"
    svg.write_text("<svg><rect/></svg>")
    doc = tmp_path / "README.md"
    doc.write_text("# Title\nbody")
    return img, svg, doc


# ── pure helpers ──────────────────────────────────────────────────────────────


def test_pdf_routed_through_pypdf_not_readtext(tmp_path, monkeypatch):
    # A PDF is binary; reading it as text yields garbage (the bug). It must be
    # routed through the pypdf extractor, and the raw bytes must never reach the
    # prompt.
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 RAWBINARYGARBAGE\x00\xff")
    import graphify.detect as detect

    monkeypatch.setattr(detect, "extract_pdf_text", lambda p: "EXTRACTED PDF TEXT")
    out = llm._read_files([pdf], tmp_path)
    assert "EXTRACTED PDF TEXT" in out
    assert "RAWBINARYGARBAGE" not in out


def test_pdf_is_not_treated_as_vision_image(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    text_files, image_files = llm._partition_semantic_files([pdf])
    assert text_files == [pdf] and image_files == []


def test_non_pdf_still_read_as_plain_text(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# hello")
    assert "# hello" in llm._file_to_text(md)


def test_read_files_skips_out_of_root_symlink(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.md"
    secret.write_text("SECRET SHOULD NOT REACH THE PROMPT")
    link = root / "secret.md"
    link.symlink_to(secret)

    out = llm._read_files([link], root)

    assert out == ""
    assert "SECRET SHOULD NOT REACH THE PROMPT" not in out


def test_partition_splits_raster_from_text(tmp_path):
    img, svg, doc = _make_corpus(tmp_path)
    text_files, image_files = llm._partition_semantic_files([doc, img, svg])
    assert image_files == [img]
    # svg is XML markup, so it stays on the text side (read as source, not pixels)
    assert set(text_files) == {doc, svg}


def test_build_image_refs_sets_rel_media_and_bytes(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    (ref,) = llm._build_image_refs([img], tmp_path)
    assert ref.rel == "sub/diagram.png"
    assert ref.media_type == "image/png"
    assert ref.raw == _PNG_BYTES
    assert ref.b64  # non-empty base64
    assert ref.bedrock_format == "png"


def test_pi_rejects_caller_symlink_replacement_before_staging(tmp_path):
    """A source replacement fails closed instead of staging the old snapshot."""
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    (ref,) = llm._build_image_refs([image], tmp_path)
    assert ref.raw == _VALID_PNG
    assert ref.source_identity is not None
    assert ref.lexical_path == image.resolve()

    outside = tmp_path / "outside.png"
    outside.write_bytes(b"attacker-controlled replacement")
    image.unlink()
    image.symlink_to(outside)

    project = tmp_path / "pi-project"
    project.mkdir()
    with pytest.raises(ValueError, match="source identity changed"):
        llm._stage_pi_images([ref], project)
    assert not (project / ".graphify-images").exists()


def test_pi_incremental_checkpoint_refuses_replacement_inside_cache_hash(monkeypatch, tmp_path):
    """The llm checkpoint cannot hash replacement B under A's Pi semantics."""
    import graphify.cache as cache_mod

    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    source = image.resolve()
    identity = llm._ImageSourceIdentity(
        source,
        llm._image_stat_identity(image.stat()),
        source,
        tmp_path.resolve(),
    )

    def fake_extract(_files, **_kwargs):
        return {
            "nodes": [{"id": "A-semantics", "source_file": image.name, "file_type": "image"}],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
            "finish_reason": "stop",
            "_image_provenance": {str(source): "pixel-derived"},
            "_image_identity": {str(source): identity},
        }

    original_hash = cache_mod._file_hash_bound_to_identity
    swapped = False

    def replace_before_cache_hash(path, root, expected, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            image.unlink()
            image.write_bytes(b"replacement-B")
        return original_hash(path, root, expected, **kwargs)

    monkeypatch.setattr(llm, "extract_files_direct", fake_extract)
    monkeypatch.setattr(cache_mod, "_file_hash_bound_to_identity", replace_before_cache_hash)
    with pytest.warns(RuntimeWarning, match="identity mismatch"):
        result = llm.extract_corpus_parallel(
            [image],
            backend="pi",
            root=tmp_path,
            max_concurrency=1,
            token_budget=None,
            checkpoint_cache=True,
            allow_image_upload=True,
        )

    assert swapped
    assert result["nodes"] == []
    assert result["partial_chunks"] == 1
    assert result["_partial_files"] == [str(source)]
    assert not list(cache_mod.cache_dir(tmp_path, "semantic").glob("**/*.json"))


def test_merge_conflicting_image_identities_downgrades_and_drops_pixel_semantics(tmp_path):
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    source = image.resolve()
    identity_a = llm._ImageSourceIdentity(
        source,
        (1, 10, 0o100644, 1, 2, 3),
        source,
        tmp_path.resolve(),
    )
    identity_b = llm._ImageSourceIdentity(
        source,
        (1, 11, 0o100644, 1, 2, 3),
        source,
        tmp_path.resolve(),
    )
    merged = {
        "nodes": [],
        "edges": [],
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "partial_chunks": 0,
    }
    llm._merge_into(
        merged,
        {
            "nodes": [{"id": "A", "source_file": image.name}],
            "edges": [],
            "hyperedges": [],
            "_image_provenance": {str(source): "pixel-derived"},
            "_image_identity": {str(source): identity_a},
        },
    )
    llm._merge_into(
        merged,
        {
            "nodes": [{"id": "B", "source_file": image.name}],
            "edges": [],
            "hyperedges": [],
            "_image_provenance": {str(source): "pixel-derived"},
            "_image_identity": {str(source): identity_b},
        },
    )

    assert merged["partial_chunks"] >= 1
    assert not merged["nodes"]
    assert not merged.get("_image_provenance")
    assert str(source) in merged["_partial_files"]


def test_build_image_refs_rejects_external_swap_before_snapshot(tmp_path, monkeypatch):
    """A race before the snapshot cannot redirect raster bytes outside root."""
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    outside = tmp_path / "outside.png"
    outside.write_bytes(_VALID_PNG + b"EXTERNAL")
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
    assert llm._build_image_refs([image], tmp_path) == []


def test_build_image_refs_rejects_identity_swap_during_snapshot(tmp_path, monkeypatch):
    image = tmp_path / "diagram.png"
    image.write_bytes(_VALID_PNG)
    outside = tmp_path / "outside.png"
    outside.write_bytes(_VALID_PNG)
    original_read = llm.os.read
    swapped = False

    def swap_after_descriptor_read(fd, size):
        nonlocal swapped
        data = original_read(fd, size)
        if not swapped:
            swapped = True
            image.unlink()
            image.symlink_to(outside)
        return data

    monkeypatch.setattr(llm.os, "read", swap_after_descriptor_read)
    assert llm._build_image_refs([image], tmp_path) == []


def test_build_image_refs_skips_out_of_root_symlink(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.png"
    secret.write_bytes(_PNG_BYTES)
    link = root / "secret.png"
    link.symlink_to(secret)

    refs = llm._build_image_refs([link], root)

    assert refs == []


def test_build_image_refs_drops_oversized(tmp_path, monkeypatch):
    big = tmp_path / "big.jpg"
    big.write_bytes(b"x" * 64)
    monkeypatch.setattr(llm, "_MAX_IMAGE_BYTES", 8)
    (ref,) = llm._build_image_refs([big], tmp_path)
    assert ref.raw is None  # too large -> reference node only, no pixels
    assert ref.media_type == "image/jpeg"


def test_path_backend_skips_byte_read_and_size_cap(tmp_path, monkeypatch):
    # Path-based backends (claude-cli) read the file themselves, so
    # _build_image_refs(read_bytes=False) loads no bytes and applies no size cap.
    big = tmp_path / "huge.png"
    big.write_bytes(b"x" * 64)
    monkeypatch.setattr(llm, "_MAX_IMAGE_BYTES", 8)
    (ref,) = llm._build_image_refs([big], tmp_path, read_bytes=False)
    assert ref.raw is None  # never read
    assert ref.rel == "huge.png" and ref.path.name == "huge.png"  # path still usable


def test_claude_cli_passes_oversized_image_by_path(tmp_path, monkeypatch):
    # An image over the inline base64 cap must still reach claude-cli by path —
    # opus reads it via the Read tool, no size limit on that route.
    big = tmp_path / "huge.png"
    big.write_bytes(_VALID_PNG)
    monkeypatch.setattr(llm, "_MAX_IMAGE_BYTES", 8)
    refs = llm._build_image_refs([big], tmp_path, read_bytes=False, secure_snapshot=True)
    envelope = {"result": _NODE_JSON, "usage": {"output_tokens": 1}, "stop_reason": "end_turn"}
    seen: dict = {}

    def fake_run(args, **kw):
        seen["input"] = kw.get("input", "")
        return MagicMock(returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr(llm, "_response_is_hollow", lambda r, p: False)
    with (
        patch("shutil.which", return_value="/fake/claude"),
        patch("subprocess.run", side_effect=fake_run),
    ):
        llm._call_claude_cli("CORPUS", images=refs)
    assert str(refs[0].path) not in seen["input"]
    assert ".graphify-images" in seen["input"]


def test_capability_flags(monkeypatch):
    for b in ("claude", "claude-cli", "openai", "gemini", "bedrock", "kimi"):
        assert llm._backend_supports_vision(b), b
    assert not llm._backend_supports_vision("deepseek")
    # ollama is opt-in via env (default model is text-only)
    monkeypatch.delenv("GRAPHIFY_OLLAMA_VISION", raising=False)
    assert not llm._backend_supports_vision("ollama")
    monkeypatch.setenv("GRAPHIFY_OLLAMA_VISION", "1")
    assert llm._backend_supports_vision("ollama")


def test_image_token_estimate_is_flat(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    assert llm._estimate_file_tokens(img) == llm._IMAGE_TOKEN_ESTIMATE


def test_chunk_packing_caps_images_per_chunk(tmp_path):
    # Many images + a huge token budget must still cap images per chunk so a
    # single request never exceeds provider image limits.
    imgs = []
    for i in range(llm._MAX_IMAGES_PER_CHUNK * 2 + 3):
        p = tmp_path / f"img{i:03d}.png"
        p.write_bytes(_PNG_BYTES)
        imgs.append(p)
    chunks = llm._pack_chunks_by_tokens(imgs, token_budget=10_000_000)
    assert len(chunks) >= 3  # would be 1 chunk without the cap
    for chunk in chunks:
        n_imgs = sum(1 for p in chunk if isinstance(p, Path) and llm._is_vision_image(p))
        assert n_imgs <= llm._MAX_IMAGES_PER_CHUNK


# ── content builders ──────────────────────────────────────────────────────────


def test_anthropic_content_has_base64_block(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    content = llm._anthropic_content("CORPUS", refs)
    assert isinstance(content, list)
    assert content[0]["type"] == "image"
    assert content[0]["source"] == {
        "type": "base64",
        "media_type": "image/png",
        "data": refs[0].b64,
    }
    assert content[-1]["type"] == "text" and "CORPUS" in content[-1]["text"]


def test_openai_content_has_data_uri(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    content = cast(Any, llm._openai_content("CORPUS", refs))
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == f"data:image/png;base64,{refs[0].b64}"


def test_bedrock_content_uses_raw_bytes(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    content = llm._bedrock_content("CORPUS", refs)
    assert content[0]["image"]["format"] == "png"
    # Converse takes raw bytes, NOT base64 (the SDK encodes on the wire)
    assert content[0]["image"]["source"]["bytes"] == _PNG_BYTES
    assert content[-1]["text"] and "CORPUS" in content[-1]["text"]  # text block carries the corpus


def test_builders_fall_back_to_string_without_pixels(tmp_path):
    img, _, _ = _make_corpus(tmp_path)
    stripped = llm._strip_pixels(llm._build_image_refs([img], tmp_path))
    # No pixels -> Anthropic/OpenAI render a plain string carrying the note
    ac = llm._anthropic_content("CORPUS", stripped)
    oc = llm._openai_content("CORPUS", stripped)
    assert isinstance(ac, str) and "sub/diagram.png" in ac
    assert isinstance(oc, str) and "sub/diagram.png" in oc


def test_no_images_is_byte_identical(tmp_path):
    # With no image refs, the user content must be exactly the text blob.
    assert llm._anthropic_content("PLAIN", []) == "PLAIN"
    assert llm._openai_content("PLAIN", []) == "PLAIN"


# ── fake SDK modules ──────────────────────────────────────────────────────────


def _fake_anthropic(monkeypatch, captured):
    class _Messages:
        def create(self, **kw):
            captured.update(kw)
            return SimpleNamespace(
                content=[SimpleNamespace(text=_NODE_JSON)],
                usage=SimpleNamespace(input_tokens=5, output_tokens=7),
                stop_reason="end_turn",
            )

    mod = types.ModuleType("anthropic")
    setattr(mod, "Anthropic", lambda **kw: SimpleNamespace(messages=_Messages()))
    monkeypatch.setitem(sys.modules, "anthropic", mod)


def _fake_openai(monkeypatch, captured):
    class _Completions:
        def create(self, **kw):
            captured.update(kw)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=_NODE_JSON), finish_reason="stop"
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
            )

    mod = types.ModuleType("openai")
    setattr(
        mod,
        "OpenAI",
        lambda **kw: SimpleNamespace(chat=SimpleNamespace(completions=_Completions())),
    )
    monkeypatch.setitem(sys.modules, "openai", mod)


def _fake_boto3(monkeypatch, captured):
    class _Client:
        def converse(self, **kw):
            captured.update(kw)
            return {
                "output": {"message": {"content": [{"text": _NODE_JSON}]}},
                "usage": {"inputTokens": 1, "outputTokens": 2},
                "stopReason": "end_turn",
            }

    boto3 = types.ModuleType("boto3")
    setattr(boto3, "Session", lambda **kw: SimpleNamespace(client=lambda svc: _Client()))
    monkeypatch.setitem(sys.modules, "boto3", boto3)
    botocore = types.ModuleType("botocore")
    exc = types.ModuleType("botocore.exceptions")
    setattr(exc, "ClientError", type("ClientError", (Exception,), {}))
    setattr(botocore, "exceptions", exc)
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exc)


# ── backend payload shape (mocked) ────────────────────────────────────────────


def test_call_claude_sends_image_block(tmp_path, monkeypatch):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    captured: dict = {}
    _fake_anthropic(monkeypatch, captured)
    llm._call_claude("k", "claude-sonnet-4-6", "CORPUS", images=refs)
    content = captured["messages"][0]["content"]
    assert any(b.get("type") == "image" for b in content)


def test_call_openai_compat_sends_image_url(tmp_path, monkeypatch):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    captured: dict = {}
    _fake_openai(monkeypatch, captured)
    llm._call_openai_compat("http://x", "k", "gpt", "CORPUS", images=refs)
    content = captured["messages"][1]["content"]
    assert any(p.get("type") == "image_url" for p in content)


def test_call_openai_compat_text_only_without_images(monkeypatch):
    captured: dict = {}
    _fake_openai(monkeypatch, captured)
    llm._call_openai_compat("http://x", "k", "gpt", "CORPUS", images=[])
    assert captured["messages"][1]["content"] == "CORPUS"


def test_call_bedrock_sends_raw_image_bytes(tmp_path, monkeypatch):
    img, _, _ = _make_corpus(tmp_path)
    refs = llm._build_image_refs([img], tmp_path)
    captured: dict = {}
    _fake_boto3(monkeypatch, captured)
    llm._call_bedrock("model", "CORPUS", images=refs)
    content = captured["messages"][0]["content"]
    img_block = next(b for b in content if "image" in b)
    assert img_block["image"]["source"]["bytes"] == _PNG_BYTES


# ── CLI backends (mocked subprocess) ──────────────────────────────────────────


def test_claude_cli_adds_dir_and_read_instruction(tmp_path, monkeypatch):
    img, _, _ = _make_corpus(tmp_path)
    img.write_bytes(_VALID_PNG)
    refs = llm._build_image_refs([img], tmp_path)
    envelope = {"result": _NODE_JSON, "usage": {"output_tokens": 1}, "stop_reason": "end_turn"}
    seen: dict = {}

    def fake_run(args, **kw):
        seen["args"] = args
        seen["input"] = kw.get("input", "")
        return MagicMock(returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr(llm, "_response_is_hollow", lambda raw, parsed: False)
    with (
        patch("shutil.which", return_value="/fake/claude"),
        patch("subprocess.run", side_effect=fake_run),
    ):
        llm._call_claude_cli("CORPUS", images=refs)

    assert "--add-dir" in seen["args"]
    assert str(refs[0].path.parent) not in seen["args"]
    assert any(".graphify-images" in arg for arg in seen["args"])
    # the prompt sent on stdin tells the model to Read only the staged image path
    assert "Read tool" in seen["input"] and ".graphify-images" in seen["input"]
    assert str(refs[0].path) not in seen["input"]


# ── dispatch-level vision gating ──────────────────────────────────────────────


def test_extract_files_direct_gates_pixels_by_capability(tmp_path, monkeypatch):
    img, _, doc = _make_corpus(tmp_path)
    captured: dict = {}
    _fake_openai(monkeypatch, captured)

    # vision backend (openai) -> content is a list carrying an image_url block
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    llm.extract_files_direct([doc, img], backend="openai", root=tmp_path)
    assert isinstance(captured["messages"][1]["content"], list)

    # non-vision backend (deepseek) -> pixels stripped, content is a plain string
    captured.clear()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    llm.extract_files_direct([doc, img], backend="deepseek", root=tmp_path)
    content = captured["messages"][1]["content"]
    assert isinstance(content, str) and "sub/diagram.png" in content
