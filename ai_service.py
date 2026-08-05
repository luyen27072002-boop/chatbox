from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import re

from openai import OpenAI

from prompting import (
    build_instructions,
    infer_conversation_stage,
    infer_luyen_context,
    load_json,
    retrieve_examples,
    retrieve_tone_examples,
    wants_structured_response,
)


class AIServiceError(RuntimeError):
    pass


@dataclass
class ModerationDecision:
    requires_urgent_support: bool = False
    must_block: bool = False
    categories: dict[str, bool] | None = None


def _compact_reply(
    text: str,
    latest_message: str = "",
    recent_history: list[dict[str, Any]] | None = None,
    *,
    preserve_structure: bool = False,
) -> str:
    """Giữ chat đời thường gọn, nhưng không phá câu trả lời học thuật/có cấu trúc."""
    cleaned = str(text or "").strip()
    if not cleaned:
        return cleaned

    if preserve_structure:
        # Chỉ làm sạch khoảng trắng thừa. Giữ markdown, danh sách, đánh số và nhiều đoạn.
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if len(cleaned) > 5000:
            cleaned = cleaned[:5000].rsplit(" ", 1)[0].rstrip(" ,;:")
            if cleaned and cleaned[-1] not in ".!?":
                cleaned += "."
        return cleaned

    # Chat đời thường: bỏ markdown/list mà model đôi khi tự sinh.
    cleaned = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", cleaned)
    cleaned = re.sub(r"(?<!\w)\d+[.)]\s*", "", cleaned)
    cleaned = re.sub(r"\s*\n+\s*", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    previous_assistant = ""
    for row in reversed(recent_history or []):
        if row.get("role") == "assistant":
            previous_assistant = str(row.get("content", ""))
            break
    lower = str(latest_message or "").lower()
    playful_markers = (":))", ":)", "haha", "kk", "đùa", "giỡn", "nuôi tao", "thế thôi", "lol")
    max_sentences = 1 if (
        (previous_assistant and "?" in previous_assistant)
        or (len(latest_message.strip()) <= 90 and any(x in lower for x in playful_markers))
    ) else 2

    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) > max_sentences:
        parts = parts[:max_sentences]
    cleaned = " ".join(parts)

    if cleaned.count("?") > 1:
        first_q = cleaned.find("?")
        cleaned = cleaned[: first_q + 1].strip()

    if len(cleaned) > 420:
        shortened = cleaned[:420].rsplit(" ", 1)[0].rstrip(" ,;:")
        cleaned = shortened + ("." if shortened and shortened[-1] not in ".!?" else "")
    return cleaned.strip()


def _response_debug_info(response: Any) -> dict[str, Any]:
    """Lấy thông tin tối thiểu để nhìn lỗi trong Terminal mà không in nội dung riêng tư."""
    status = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    reason = getattr(incomplete, "reason", None) if incomplete is not None else None
    usage = getattr(response, "usage", None)
    output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
    reasoning_tokens = None
    details = getattr(usage, "output_tokens_details", None) if usage is not None else None
    if details is not None:
        reasoning_tokens = getattr(details, "reasoning_tokens", None)
    return {
        "status": status,
        "incomplete_reason": reason,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def _extract_response_text(response: Any) -> str:
    """Đọc text an toàn từ Responses API, kể cả khi output_text helper bị rỗng."""
    direct = str(getattr(response, "output_text", "") or "").strip()
    if direct:
        return direct

    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        item_type = getattr(item, "type", None)
        if item_type != "message":
            continue
        for part in getattr(item, "content", None) or []:
            part_type = getattr(part, "type", None)
            if part_type == "output_text":
                text = str(getattr(part, "text", "") or "").strip()
                if text:
                    chunks.append(text)
            elif part_type == "refusal":
                refusal = str(getattr(part, "refusal", "") or "").strip()
                if refusal:
                    chunks.append(refusal)
    return "\n".join(chunks).strip()


class AIService:
    def __init__(self, api_key: str, model: str, base_dir: Path) -> None:
        # Giữ GPT-5.6 Luna. Có thể đổi bằng OPENAI_REPLY_MODEL nếu sau này cần.
        self.model = os.getenv("OPENAI_REPLY_MODEL", model).strip() or "gpt-5.6-luna"
        self.reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "low").strip() or "low"
        self.chat_max_output_tokens = int(os.getenv("OPENAI_CHAT_MAX_OUTPUT_TOKENS", "4096"))
        self.chat_retry_max_output_tokens = int(os.getenv("OPENAI_CHAT_RETRY_MAX_OUTPUT_TOKENS", "8192"))
        self.api_key = api_key.strip()
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.personality = load_json(base_dir / "data" / "personality.json")
        self.personas = load_json(base_dir / "data" / "personas.json", {})
        self.examples = load_json(base_dir / "data" / "examples.json", [])
        self.persona_examples = load_json(base_dir / "data" / "persona_examples.json", [])
        self.conversation_examples = load_json(
            base_dir / "data" / "conversation_examples.json", []
        )
        self.luyen_response_examples = load_json(
            base_dir / "data" / "luyen_response_examples.json", []
        )
        self.tone_examples = load_json(base_dir / "data" / "tone_examples.json", [])
        self.conversation_rules = load_json(
            base_dir / "data" / "conversation_rules.json", {}
        )
        print(
            f"[AI] Reply model: {self.model} | reasoning={self.reasoning_effort} "
            f"| output={self.chat_max_output_tokens}/{self.chat_retry_max_output_tokens}"
        )

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def _require_client(self) -> OpenAI:
        if self.client is None:
            raise AIServiceError(
                "Thiếu OPENAI_API_KEY. Mở file .env, dán API key thật rồi chạy lại web."
            )
        return self.client

    def moderate(self, text: str) -> ModerationDecision:
        client = self._require_client()
        try:
            response = client.moderations.create(
                model="omni-moderation-latest",
                input=text,
            )
            result = response.results[0].model_dump(by_alias=True)
            categories = result.get("categories", {})
            urgent = bool(
                categories.get("self-harm/intent")
                or categories.get("self-harm/instructions")
            )
            must_block = bool(
                categories.get("sexual/minors")
                or categories.get("illicit/violent")
            )
            return ModerationDecision(
                requires_urgent_support=urgent,
                must_block=must_block,
                categories=categories,
            )
        except Exception:
            return ModerationDecision(categories={"moderation_error": True})

    def generate_reply(
        self,
        message: str,
        mode: str,
        category: str,
        pronoun_style: str,
        response_style: str,
        tone_style: str,
        language: str,
        memory_summary: str,
        recent_history: list[dict[str, Any]],
        user_profile: dict[str, Any] | None = None,
    ) -> str:
        conversation_stage = infer_conversation_stage(mode, recent_history)
        response_context = (
            infer_luyen_context(message, mode, category, recent_history)
            if response_style == "luyen" else "casual"
        )
        preserve_structure = wants_structured_response(message, response_context)
        relevant_examples: list[dict[str, Any]] = []
        relevant_tone_examples: list[dict[str, Any]] = []

        # Dataset V2 hiện viết bằng tiếng Việt; không đưa ví dụ tiếng Việt vào prompt ngôn ngữ khác.
        if language == "vi":
            if response_style == "luyen":
                relevant_examples = retrieve_examples(
                    message=message,
                    mode=mode,
                    examples=self.conversation_examples + self.luyen_response_examples,
                    limit=2,
                    category=category,
                    stage=conversation_stage,
                    pronoun_style=pronoun_style,
                    tone_style=tone_style,
                    recent_history=recent_history,
                    persona="luyen",
                    context_type=response_context,
                )
            else:
                relevant_examples = retrieve_examples(
                    message=message,
                    mode=mode,
                    examples=self.persona_examples,
                    limit=2,
                    category=category,
                    pronoun_style=pronoun_style,
                    tone_style=tone_style,
                    recent_history=recent_history,
                    persona=response_style,
                )

            relevant_tone_examples = retrieve_tone_examples(
                message=message,
                mode=mode,
                category=category,
                pronoun_style=pronoun_style,
                tone_style=tone_style,
                examples=self.tone_examples,
                limit=1,
            )

        self._require_client()

        selected_personality = self.personas.get(response_style, self.personality)
        instructions = build_instructions(
            personality=selected_personality,
            conversation_rules=self.conversation_rules,
            mode=mode,
            category=category,
            pronoun_style=pronoun_style,
            response_style=response_style,
            tone_style=tone_style,
            language=language,
            memory_summary=memory_summary,
            examples=relevant_examples,
            tone_examples=relevant_tone_examples,
            latest_message=message,
            recent_history=recent_history,
            user_profile=user_profile,
            conversation_stage=conversation_stage,
            response_context=response_context,
        )

        input_messages = [
            {"role": row["role"], "content": row["content"]}
            for row in recent_history[-14:]
            if row.get("role") in {"user", "assistant"}
        ]
        if not input_messages or input_messages[-1].get("content") != message:
            input_messages.append({"role": "user", "content": message})

        try:
            # Giữ GPT-5.6 Luna và cho model đủ chỗ suy luận.
            # max_output_tokens tính cả reasoning token và phần chữ nhìn thấy,
            # nên 500/900 trước đây quá thấp. Bản này dùng low + 4096, retry 8192.
            response = self._create_response(
                instructions=instructions,
                input_messages=input_messages,
                max_output_tokens=self.chat_max_output_tokens,
                reasoning_effort=self.reasoning_effort,
            )
            reply = _extract_response_text(response)

            if not reply:
                print(f"[AI] Empty first response: {_response_debug_info(response)}")
                response = self._create_response(
                    instructions=instructions,
                    input_messages=input_messages,
                    max_output_tokens=self.chat_retry_max_output_tokens,
                    reasoning_effort=self.reasoning_effort,
                )
                reply = _extract_response_text(response)

            reply = _compact_reply(
                reply, message, recent_history, preserve_structure=preserve_structure
            )
            if not reply:
                print(f"[AI] Empty retry response: {_response_debug_info(response)}")
                raise AIServiceError(
                    "Model chưa trả ra phần chữ. Xem dòng [AI] trong Terminal rồi gửi lại tao."
                )
            output_decision = self.moderate(reply)
            if output_decision.must_block:
                return (
                    "Tao không thể tiếp tục theo hướng đó. Kể mục tiêu thật phía sau đi, tao cùng tìm cách an toàn hơn."
                    if pronoun_style == "tao_may"
                    else "Mình không thể tiếp tục theo hướng đó. Bạn nói mục tiêu thật phía sau nhé, mình cùng tìm cách an toàn hơn."
                )
            return reply
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(
                "Chưa kết nối được dịch vụ trả lời. Kiểm tra OPENAI_API_KEY, model và hạn mức API."
            ) from exc

    def refresh_memory(
        self,
        old_memory: str,
        recent_history: list[dict[str, Any]],
    ) -> str | None:
        self._require_client()

        transcript = "\n".join(
            f"{row['role']}: {row['content']}" for row in recent_history[-18:]
        )
        instructions = """
Cập nhật bản tóm tắt cho CHÍNH CUỘC TRÒ CHUYỆN ĐANG MỞ. Chỉ giữ người/sự việc quan trọng,
mốc thời gian, điều đã xảy ra, điều người dùng trực tiếp nói hoặc xác nhận, quyết định đã đưa ra và
chuyện vẫn chưa giải quyết. Không thêm chẩn đoán hoặc suy đoán nhạy cảm. Tối đa 10 gạch đầu dòng,
tổng dưới 1800 ký tự. Nếu không có gì mới hữu ích thì giữ nguyên bản cũ. Không thêm lời dẫn.
""".strip()
        prompt = (
            f"TÓM TẮT PHẦN CŨ:\n{old_memory or '(trống)'}\n\n"
            f"HỘI THOẠI GẦN ĐÂY:\n{transcript}"
        )
        try:
            response = self._create_response(
                instructions=instructions,
                input_messages=[{"role": "user", "content": prompt}],
                max_output_tokens=2048,
                reasoning_effort="low",
            )
            memory = (response.output_text or "").strip()
            return memory[:2000] if memory else old_memory
        except Exception as exc:
            raise AIServiceError("Không thể cập nhật trí nhớ.") from exc

    def _create_response(
        self,
        instructions: str,
        input_messages: list[dict[str, str]],
        max_output_tokens: int,
        reasoning_effort: str = "none",
    ):
        client = self._require_client()
        kwargs = {
            "model": self.model,
            "instructions": instructions,
            "input": input_messages,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        # Không được âm thầm bỏ reasoning.effort. Nếu API/SDK không nhận tham số,
        # báo lỗi thật để sửa đúng thay vì quay về mức reasoning mặc định.
        return client.responses.create(
            **kwargs,
            reasoning={"effort": reasoning_effort},
            text={"verbosity": "low"},
        )
