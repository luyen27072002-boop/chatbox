from __future__ import annotations

import json
from pathlib import Path

from prompting import retrieve_examples, retrieve_tone_examples

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    with (ROOT / "data" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def test_conversation_dataset_has_54_multi_turn_examples():
    examples = load("conversation_examples.json")
    assert len(examples) == 54
    assert {row["persona"] for row in examples} == {"luyen"}
    assert {row["mode"] for row in examples} == {"listen", "clarify", "advice"}
    assert all(row["assistant"].strip() for row in examples)


def test_tone_dataset_has_both_tones():
    examples = load("tone_examples.json")
    assert len(examples) >= 12
    assert all(row["gentle"].strip() for row in examples)
    assert all(row["realistic"].strip() for row in examples)
    assert any(row["gentle"] != row["realistic"] for row in examples)


def test_retrieval_returns_luyen_and_requested_tone():
    conversation_examples = load("conversation_examples.json")
    tone_examples = load("tone_examples.json")
    found = retrieve_examples(
        message="Tao muốn nhắn lại cho người yêu cũ.",
        mode="listen",
        category="love",
        examples=conversation_examples,
        persona="luyen",
        pronoun_style="tao_may",
        tone_style="realistic",
    )
    assert found
    assert all(row["persona"] == "luyen" for row in found)

    gentle = retrieve_tone_examples(
        message="Tao muốn nhắn lại cho người yêu cũ.",
        mode="listen",
        category="love",
        pronoun_style="tao_may",
        tone_style="gentle",
        examples=tone_examples,
        limit=1,
    )
    realistic = retrieve_tone_examples(
        message="Tao muốn nhắn lại cho người yêu cũ.",
        mode="listen",
        category="love",
        pronoun_style="tao_may",
        tone_style="realistic",
        examples=tone_examples,
        limit=1,
    )
    assert gentle and realistic
    assert gentle[0]["assistant"] != realistic[0]["assistant"]


def test_persona_profiles_cover_all_frontend_options():
    personas = load("personas.json")
    assert set(personas) == {
        "adaptive", "strict", "gentle", "rational",
        "practical", "light_humor", "luyen",
    }
    assert all(personas[key]["principles"] for key in personas)


def test_persona_examples_cover_non_luyen_modes_and_tones():
    examples = load("persona_examples.json")
    non_luyen = {"adaptive", "strict", "gentle", "rational", "practical", "light_humor"}
    assert {row["persona"] for row in examples} == non_luyen
    for persona in non_luyen:
        for mode in {"listen", "clarify", "advice"}:
            for tone in {"gentle", "realistic"}:
                assert any(
                    row["persona"] == persona
                    and row["mode"] == mode
                    and tone in row.get("tones", [])
                    for row in examples
                )
