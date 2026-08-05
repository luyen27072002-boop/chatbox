from __future__ import annotations

import json
from pathlib import Path

from prompting import build_instructions

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def _prompt_for(persona: str) -> str:
    personalities = _load("personas.json")
    rules = _load("conversation_rules.json")
    return build_instructions(
        personality=personalities[persona],
        conversation_rules=rules,
        mode="clarify",
        category="other",
        pronoun_style="tao_may",
        response_style=persona,
        tone_style="gentle",
        language="vi",
        memory_summary="",
        examples=[],
        tone_examples=[],
        latest_message="Thế mày phân tích đi.",
        recent_history=[],
        user_profile={},
        conversation_stage="opening",
        response_context="casual",
    )


def test_non_luyen_personas_do_not_receive_luyen_private_blocks():
    for persona in ["adaptive", "strict", "gentle", "rational", "practical", "light_humor"]:
        prompt = _prompt_for(persona)
        assert "CÁC MẶT TÌNH HUỐNG CỦA LUYỆN" not in prompt
        assert "LOGIC HỘI THOẠI RIÊNG CỦA LUYỆN" not in prompt
        assert "QUY TẮC RIÊNG CỦA LUYỆN" not in prompt


def test_luyen_keeps_luyen_private_blocks():
    prompt = _prompt_for("luyen")
    assert "CÁC MẶT TÌNH HUỐNG CỦA LUYỆN" in prompt
    assert "LOGIC HỘI THOẠI RIÊNG CỦA LUYỆN" in prompt
    assert "QUY TẮC RIÊNG CỦA LUYỆN" in prompt


def test_all_42_mode_persona_tone_combinations_build_cleanly():
    personalities = _load("personas.json")
    rules = _load("conversation_rules.json")
    for persona in ["adaptive", "strict", "gentle", "rational", "practical", "light_humor", "luyen"]:
        for mode in ["listen", "clarify", "advice"]:
            for tone in ["gentle", "realistic"]:
                prompt = build_instructions(
                    personality=personalities[persona],
                    conversation_rules=rules,
                    mode=mode,
                    category="other",
                    pronoun_style="tao_may",
                    response_style=persona,
                    tone_style=tone,
                    language="vi",
                    memory_summary="",
                    examples=[],
                    tone_examples=[],
                    latest_message="Tao đang không biết phải nghĩ thế nào.",
                    recent_history=[],
                    user_profile={},
                    conversation_stage="opening",
                    response_context="casual",
                )
                assert "MODE\n" in prompt
                assert "PERSONA ĐANG CHỌN" in prompt
                assert len(prompt) > 1000
