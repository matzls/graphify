"""Tests for native semantic extraction prompt contract."""

from graphify import llm


def test_native_extraction_prompt_uses_guided_open_relations_and_canonical_names():
    preferred_verbs = [
        "writes",
        "stores",
        "routes",
        "validates",
        "gates",
        "feeds",
        "emits",
        "records",
        "converts",
        "governs",
        "precedes",
        "produces",
        "requires",
    ]

    for deep in (False, True):
        prompt = llm._extraction_system(deep=deep)

        assert "prefer a specific lowercase verb grounded in the source text" in prompt
        for verb in preferred_verbs:
            assert verb in prompt
        assert "another_specific_source_stated_verb" in prompt
        assert "document's own noun phrase" in prompt
        assert "headings, definitions, or explicit terms" in prompt
        assert "using singular form where natural" in prompt
        assert "Do not replace a documented concept name with a code identifier" in prompt
        assert "relation must be one of" not in prompt.lower()
        assert "relations must be one of" not in prompt.lower()
        assert (
            "calls|implements|references|cites|conceptually_related_to|shares_data_with"
            not in prompt
        )
