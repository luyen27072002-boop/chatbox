from __future__ import annotations

import json
from pathlib import Path

from ai_service import _compact_reply
from prompting import (
    build_instructions,
    infer_luyen_context,
    retrieve_examples,
    wants_structured_response,
)

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    with (ROOT / "data" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def test_luyen_personality_has_situational_faces_and_boundaries():
    personality = load("personality.json")
    assert personality["version"].startswith("V3")
    assert set(personality["situational_personas"]) >= {
        "sadness", "pressure", "joy", "indecision", "conflict", "knowledge"
    }
    dont = " ".join(personality["dont"]).lower()
    assert "chửi bậy" in dont
    assert "tạo lệ thuộc" in dont


def test_context_detection_matches_questionnaire_design():
    assert infer_luyen_context("Tao buồn quá, chẳng muốn nói với ai", "listen", "other") == "sadness"
    assert infer_luyen_context("Deadline dí tao muốn xỉu", "listen", "study") == "pressure"
    assert infer_luyen_context("Tao đậu rồi hahahaha", "listen", "study") == "joy"
    assert infer_luyen_context("Tao không biết nên chọn cái nào", "advice", "career") == "indecision"
    assert infer_luyen_context("Giải thích precision và recall trong YOLO", "advice", "study") == "knowledge"


def test_structured_requests_are_not_forced_into_short_chat():
    message = "Phân tích rõ từng vấn đề, thứ nhất thứ hai thứ ba"
    context = infer_luyen_context(message, "clarify", "friends")
    assert context == "knowledge"
    assert wants_structured_response(message, context) is True

    structured = "1. Ý thứ nhất.\n2. Ý thứ hai.\n3. Ý thứ ba."
    assert _compact_reply(structured, message, preserve_structure=True) == structured


def test_casual_chat_is_still_compact():
    text = "Câu một. Câu hai. Câu ba."
    compact = _compact_reply(text, "Tao mệt quá")
    assert compact == "Câu một. Câu hai."


def test_luyen_examples_cover_questionnaire_situations():
    examples = load("luyen_response_examples.json")
    contexts = {row["context_type"] for row in examples}
    assert len(examples) >= 16
    assert {"sadness", "pressure", "joy", "indecision", "conflict", "knowledge"} <= contexts
    assert all(row["persona"] == "luyen" for row in examples)
    assert all(row["approved"] for row in examples)

    found = retrieve_examples(
        message="Tao đậu rồi hahahaha",
        mode="listen",
        category="study",
        examples=examples,
        persona="luyen",
        pronoun_style="tao_may",
        tone_style="realistic",
        context_type="joy",
        limit=1,
    )
    assert found and found[0]["context_type"] == "joy"


def test_prompt_contains_dynamic_luyen_policy_and_academic_exception():
    personality = load("personality.json")
    rules = load("conversation_rules.json")
    instructions = build_instructions(
        personality=personality,
        conversation_rules=rules,
        mode="advice",
        category="study",
        pronoun_style="minh_ban",
        response_style="luyen",
        tone_style="gentle",
        language="vi",
        memory_summary="",
        examples=[],
        tone_examples=[],
        latest_message="Giải thích học thuật về precision và recall trong YOLO",
        recent_history=[],
        user_profile=None,
        response_context="knowledge",
    )
    assert "MẶT KIẾN THỨC" in instructions
    assert "được dùng tiêu đề, đánh số" in instructions
    assert "Không dùng từ tục" in instructions
    assert "Đứng về phía người dùng trước" in instructions
