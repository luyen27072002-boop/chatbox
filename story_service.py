from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


class LifeStoryServiceError(RuntimeError):
    pass


@dataclass
class LifeStoryService:
    api_key: str
    model: str

    def __post_init__(self) -> None:
        self.api_key = str(self.api_key or "").strip()
        self.model = (
            os.getenv("OPENAI_STORY_MODEL", "").strip()
            or str(self.model or "").strip()
            or "gpt-5.6-luna"
        )
        self.reasoning_effort = (
            os.getenv("OPENAI_STORY_REASONING_EFFORT", "low").strip() or "low"
        )
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def _require_client(self) -> OpenAI:
        if self.client is None:
            raise LifeStoryServiceError(
                "Thiếu OPENAI_API_KEY nên chưa thể viết lại câu chuyện."
            )
        return self.client

    def create_autobiography(
        self,
        *,
        raw_text: str,
        style: str,
        entry_date: str,
    ) -> dict[str, Any]:
        style_instructions = {
            "honest": "Chân thật, gần gũi, không tô hồng và không bi kịch hóa.",
            "gentle": "Nhẹ nhàng, ấm, giữ cảm xúc tinh tế và không sướt mướt.",
            "humorous": "Hài hước duyên, chỉ đùa vào tình huống, không chế giễu nỗi đau.",
            "cinematic": "Có nhịp kể điện ảnh, hình ảnh rõ nhưng không bịa cảnh hoặc chi tiết.",
            "mature": "Điềm tĩnh, trưởng thành, có chiều sâu nhưng không lên lớp.",
            "letter": "Viết như một lá thư gửi cho chính mình của ngày hôm nay.",
        }
        style_rule = style_instructions.get(style, style_instructions["honest"])
        instructions = f"""
Bạn là biên tập viên tự truyện cá nhân. Người dùng sẽ kể một ngày hoặc một sự việc bằng lời lộn xộn.
Nhiệm vụ là viết lại thành một chương ngắn có mạch kể, giữ nguyên sự thật người dùng cung cấp.

Phong cách: {style_rule}

Quy tắc bắt buộc:
- Không thêm người, địa điểm, lời thoại, hành động, cảm xúc hay kết luận chưa có trong bản gốc.
- Có thể diễn đạt cảm xúc ngầm chỉ khi bản gốc cho thấy rõ; nếu chưa chắc thì viết dè dặt.
- Không chẩn đoán tâm lý.
- Không biến thành bài học đạo đức.
- Giữ giọng ngôi thứ nhất để người dùng có cảm giác đây là tự truyện của chính họ.
- Độ dài phần narrative khoảng 180–420 từ tùy lượng dữ kiện.
- Trích ra tối đa 3 chuyện còn dang dở, chỉ khi bản gốc thực sự có.

Trả về JSON hợp lệ, không markdown, theo đúng cấu trúc:
{{
  "title": "tiêu đề ngắn và có sức gợi",
  "narrative": "chương tự truyện",
  "closing_line": "một câu kết ngắn, không giáo điều",
  "open_threads": [
    {{"title": "tên chuyện", "detail": "điều đang dang dở", "status": "unsaid|waiting|deciding|letting_go"}}
  ],
  "tags": ["tối đa 5 từ khóa"]
}}
""".strip()
        prompt = f"NGÀY GHI: {entry_date}\n\nBẢN GỐC:\n{raw_text.strip()}"
        return self._json_response(
            instructions=instructions,
            prompt=prompt,
            max_output_tokens=2600,
        )

    def create_unsent_piece(
        self,
        *,
        raw_text: str,
        relation: str,
        output_type: str,
    ) -> dict[str, Any]:
        type_rules = {
            "unsent_letter": (
                "Viết thành một lá thư không gửi. Có thể nói thật hơn bình thường, nhưng không xúc phạm."
            ),
            "sendable_message": (
                "Viết thành tin nhắn có thể gửi thật: rõ, ngắn, không đổ lỗi và không thao túng."
            ),
            "journal": (
                "Viết thành một đoạn nhật ký để người dùng hiểu điều mình đang muốn nói."
            ),
            "opening_line": (
                "Tạo một câu mở đầu tự nhiên để bắt đầu cuộc nói chuyện ngoài đời."
            ),
        }
        type_rule = type_rules.get(output_type, type_rules["unsent_letter"])
        instructions = f"""
Bạn giúp người dùng biến một điều khó nói thành lời.
Đối tượng người dùng đang nghĩ tới: {relation or 'không nêu rõ'}.
Dạng đầu ra: {type_rule}

Quy tắc:
- Không bịa sự kiện hoặc động cơ của người kia.
- Không chẩn đoán, đe dọa, thao túng, gây tội lỗi hoặc ép đối phương phản hồi.
- Giữ cảm xúc thật nhưng diễn đạt dễ hiểu.
- Nếu bản gốc quá nóng giận, hạ nhiệt câu chữ mà không xóa mất ý chính.
- Trả về JSON hợp lệ, không markdown.

Cấu trúc:
{{
  "title": "tiêu đề ngắn",
  "rewritten": "bản đã viết lại",
  "sendable_version": "bản ngắn có thể gửi, để trống nếu output_type không phù hợp",
  "core_feeling": "điều người dùng thực sự đang muốn nói, một câu",
  "caution": "một lưu ý ngắn nếu có, nếu không thì để trống"
}}
""".strip()
        return self._json_response(
            instructions=instructions,
            prompt=raw_text.strip(),
            max_output_tokens=1800,
        )

    def start_rehearsal(
        self,
        *,
        other_person: str,
        situation: str,
        goal: str,
        opening: str,
    ) -> dict[str, Any]:
        instructions = f"""
Bạn đang mô phỏng một cuộc nói chuyện khó để người dùng luyện trước.
Bạn đóng vai: {other_person or 'người đối diện'}.
Tình huống: {situation}.
Mục tiêu của người dùng: {goal or 'nói rõ điều mình cần nói'}.

Quy tắc:
- Phản ứng như người thật, không quá dễ cũng không cố tình gây hấn.
- Không xác nhận những điều chưa biết về người đối diện.
- Mỗi lượt đối phương chỉ 1–3 câu.
- Phần coach phải ngắn, chỉ nêu một điểm mạnh và một điểm có thể chỉnh.
- Không viết thay cả cuộc hội thoại.
- Trả về JSON hợp lệ, không markdown.

Cấu trúc:
{{
  "counterpart_reply": "phản hồi của người đối diện",
  "coach_note": "nhận xét ngắn cho người dùng",
  "suggested_reply": "một gợi ý người dùng có thể nói tiếp",
  "progress": "opening|tension|clarifying|closing"
}}
""".strip()
        return self._json_response(
            instructions=instructions,
            prompt=f"Câu mở đầu của người dùng:\n{opening.strip()}",
            max_output_tokens=1300,
        )

    def continue_rehearsal(
        self,
        *,
        other_person: str,
        situation: str,
        goal: str,
        transcript: list[dict[str, str]],
        user_message: str,
    ) -> dict[str, Any]:
        transcript_text = "\n".join(
            f"{row.get('role', 'unknown')}: {row.get('content', '')}"
            for row in transcript[-12:]
        )
        instructions = f"""
Tiếp tục mô phỏng một cuộc nói chuyện khó.
Bạn đóng vai: {other_person or 'người đối diện'}.
Tình huống: {situation}.
Mục tiêu của người dùng: {goal or 'nói rõ điều mình cần nói'}.

Quy tắc:
- Bám đúng những gì đã nói trong transcript, không bịa lịch sử mới.
- Phản ứng như người thật; có thể hiểu nhầm, phòng thủ nhẹ hoặc mềm lại tùy câu người dùng.
- Không làm đối phương trở thành nhân vật phản diện một chiều.
- Mỗi lượt đối phương 1–3 câu.
- Coach chỉ nêu tối đa 2 ý ngắn.
- Khi người dùng đã nói rõ và có thể kết thúc, progress là closing.
- Trả về JSON hợp lệ, không markdown.

Cấu trúc:
{{
  "counterpart_reply": "phản hồi của người đối diện",
  "coach_note": "nhận xét ngắn",
  "suggested_reply": "một gợi ý câu tiếp theo",
  "progress": "opening|tension|clarifying|closing"
}}
""".strip()
        prompt = (
            f"TRANSCRIPT:\n{transcript_text}\n\n"
            f"TIN NHẮN MỚI CỦA NGƯỜI DÙNG:\n{user_message.strip()}"
        )
        return self._json_response(
            instructions=instructions,
            prompt=prompt,
            max_output_tokens=1400,
        )

    def _json_response(
        self,
        *,
        instructions: str,
        prompt: str,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        client = self._require_client()
        try:
            response = client.responses.create(
                model=self.model,
                instructions=instructions,
                input=[{"role": "user", "content": prompt}],
                max_output_tokens=max_output_tokens,
                reasoning={"effort": self.reasoning_effort},
                text={"verbosity": "medium"},
                store=False,
            )
            raw = self._extract_text(response)
            payload = self._parse_json(raw)
            if not isinstance(payload, dict):
                raise LifeStoryServiceError("Dịch vụ chưa trả về đúng định dạng.")
            return payload
        except LifeStoryServiceError:
            raise
        except Exception as exc:
            raise LifeStoryServiceError(
                "Chưa tạo được nội dung. Kiểm tra API key, model và hạn mức rồi thử lại."
            ) from exc

    @staticmethod
    def _extract_text(response: Any) -> str:
        direct = str(getattr(response, "output_text", "") or "").strip()
        if direct:
            return direct
        chunks: list[str] = []
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "output_text":
                    text = str(getattr(part, "text", "") or "").strip()
                    if text:
                        chunks.append(text)
        return "\n".join(chunks).strip()

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        cleaned = str(raw or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if not match:
                raise LifeStoryServiceError("Không đọc được nội dung AI vừa tạo.")
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise LifeStoryServiceError(
                    "Nội dung AI trả về chưa đúng định dạng, hãy thử lại."
                ) from exc
