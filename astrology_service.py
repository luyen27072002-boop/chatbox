from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from openai import OpenAI

from tuvi_engine import TuViEngineError, build_full_tuvi_chart, compact_chart_for_ai


class AstrologyServiceError(RuntimeError):
    pass


HEAVENLY_STEMS = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
EARTHLY_BRANCHES = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]
ZODIAC_ANIMALS = ["Chuột", "Trâu", "Hổ", "Mèo", "Rồng", "Rắn", "Ngựa", "Dê", "Khỉ", "Gà", "Chó", "Lợn"]
STEM_ELEMENTS = ["Mộc", "Mộc", "Hỏa", "Hỏa", "Thổ", "Thổ", "Kim", "Kim", "Thủy", "Thủy"]
NAP_AM = [
    ("Hải Trung Kim", "Kim"),
    ("Lư Trung Hỏa", "Hỏa"),
    ("Đại Lâm Mộc", "Mộc"),
    ("Lộ Bàng Thổ", "Thổ"),
    ("Kiếm Phong Kim", "Kim"),
    ("Sơn Đầu Hỏa", "Hỏa"),
    ("Giản Hạ Thủy", "Thủy"),
    ("Thành Đầu Thổ", "Thổ"),
    ("Bạch Lạp Kim", "Kim"),
    ("Dương Liễu Mộc", "Mộc"),
    ("Tuyền Trung Thủy", "Thủy"),
    ("Ốc Thượng Thổ", "Thổ"),
    ("Tích Lịch Hỏa", "Hỏa"),
    ("Tùng Bách Mộc", "Mộc"),
    ("Trường Lưu Thủy", "Thủy"),
    ("Sa Trung Kim", "Kim"),
    ("Sơn Hạ Hỏa", "Hỏa"),
    ("Bình Địa Mộc", "Mộc"),
    ("Bích Thượng Thổ", "Thổ"),
    ("Kim Bạch Kim", "Kim"),
    ("Phú Đăng Hỏa", "Hỏa"),
    ("Thiên Hà Thủy", "Thủy"),
    ("Đại Trạch Thổ", "Thổ"),
    ("Thoa Xuyến Kim", "Kim"),
    ("Tang Đố Mộc", "Mộc"),
    ("Đại Khê Thủy", "Thủy"),
    ("Sa Trung Thổ", "Thổ"),
    ("Thiên Thượng Hỏa", "Hỏa"),
    ("Thạch Lựu Mộc", "Mộc"),
    ("Đại Hải Thủy", "Thủy"),
]

AREA_KEYS = ["love", "career", "study", "money", "relationships"]
AREA_LABELS = {
    "vi": {"love": "Tình cảm", "career": "Công việc", "study": "Học tập", "money": "Tài chính", "relationships": "Mối quan hệ"},
    "en": {"love": "Love", "career": "Career", "study": "Study", "money": "Money", "relationships": "Relationships"},
    "zh": {"love": "感情", "career": "工作", "study": "學習", "money": "財務", "relationships": "人際關係"},
}


def _response_text(response: Any) -> str:
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


def _extract_json(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise AstrologyServiceError("Mô hình không trả về dữ liệu tử vi hợp lệ.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AstrologyServiceError("Mô hình không trả về dữ liệu tử vi hợp lệ.") from exc
    if not isinstance(parsed, dict):
        raise AstrologyServiceError("Dữ liệu tử vi trả về không đúng định dạng.")
    return parsed


def normalize_ui_language(value: str) -> str:
    text = str(value or "vi").lower()
    if text.startswith("en"):
        return "en"
    if text.startswith("zh"):
        return "zh"
    return "vi"


def hour_branch(hour: int | None) -> str:
    if hour is None:
        return "Không rõ"
    # Tý: 23:00-00:59, sau đó mỗi chi 2 giờ.
    index = ((hour + 1) // 2) % 12
    return EARTHLY_BRANCHES[index]


def calculate_birth_profile(*, birth_date: str, birth_time: str = "", birth_place: str = "", gender: str = "", display_name: str = "") -> dict[str, Any]:
    try:
        born = datetime.strptime(str(birth_date), "%Y-%m-%d").date()
    except ValueError as exc:
        raise AstrologyServiceError("Ngày sinh không hợp lệ.") from exc
    today = date.today()
    if born.year < 1900 or born > today:
        raise AstrologyServiceError("Ngày sinh phải nằm từ năm 1900 đến hiện tại.")

    hour_value: int | None = None
    minute_value: int | None = None
    birth_time = str(birth_time or "").strip()
    if not birth_time:
        raise AstrologyServiceError("Lá số Tử Vi Đẩu Số đầy đủ cần giờ sinh.")
    try:
        parsed_time = datetime.strptime(birth_time, "%H:%M").time()
        hour_value, minute_value = parsed_time.hour, parsed_time.minute
    except ValueError as exc:
        raise AstrologyServiceError("Giờ sinh không hợp lệ.") from exc
    gender_value = str(gender or "").strip()
    if gender_value not in {"male", "female"}:
        raise AstrologyServiceError("Để an sao đầy đủ, hãy chọn Nam hoặc Nữ.")

    stem_index = (born.year - 4) % 10
    branch_index = (born.year - 4) % 12
    cycle_index = (born.year - 1984) % 60
    nap_am_name, nap_am_element = NAP_AM[cycle_index // 2]
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    profile = {
        "display_name": str(display_name or "").strip()[:80],
        "birth_date": born.isoformat(),
        "birth_time": birth_time,
        "birth_place": str(birth_place or "").strip()[:120],
        "gender": gender_value,
        "age": max(0, age),
        "can_chi_year": f"{HEAVENLY_STEMS[stem_index]} {EARTHLY_BRANCHES[branch_index]}",
        "heavenly_stem": HEAVENLY_STEMS[stem_index],
        "earthly_branch": EARTHLY_BRANCHES[branch_index],
        "zodiac_animal": ZODIAC_ANIMALS[branch_index],
        "stem_element": STEM_ELEMENTS[stem_index],
        "yin_yang": "Dương" if stem_index % 2 == 0 else "Âm",
        "nap_am": nap_am_name,
        "nap_am_element": nap_am_element,
        "birth_hour_branch": hour_branch(hour_value),
        "birth_hour": hour_value,
        "birth_minute": minute_value,
    }
    try:
        profile["tuvi_chart"] = build_full_tuvi_chart(
            birth_date=profile["birth_date"],
            birth_time=profile["birth_time"],
            gender=profile["gender"],
            display_name=profile["display_name"],
            time_zone=7,
        )
    except TuViEngineError as exc:
        raise AstrologyServiceError(str(exc)) from exc
    return profile


def _stable_score(seed: str, key: str) -> int:
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    return 54 + digest[0] % 34  # 54-87, tránh cảm giác cực đoan.


def _fallback_reading(profile: dict[str, Any], ui_language: str) -> dict[str, Any]:
    lang = normalize_ui_language(ui_language)
    element = profile.get("nap_am_element", "Mộc")
    animal = profile.get("zodiac_animal", "")
    seed = f"{profile.get('birth_date')}:{profile.get('birth_time')}:{element}:{animal}:{date.today().isoformat()}"
    scores = {key: _stable_score(seed, key) for key in AREA_KEYS}
    labels = AREA_LABELS[lang]
    period_end = date.today() + timedelta(days=45)

    if lang == "en":
        overview = f"Your profile carries a {element} tone with the {animal} year. The next phase is better treated as a period for adjusting priorities rather than forcing a big breakthrough."
        personality = "You may do best when you have room to decide at your own pace, but you can lose energy when too many unfinished things compete for attention."
        should_do = ["Finish one important task before opening a new one.", "Say what you need more clearly in close relationships.", "Keep a little room in your schedule for unexpected changes."]
        watch_out = ["Do not make a major decision only because you feel rushed.", "Avoid reading too much into one message or one bad day.", "Be conservative with money when the reason for spending is emotional."]
        closing = "The useful theme is not to predict one event, but to notice where you can act with more clarity."
    elif lang == "zh":
        overview = f"你的基本資料帶有「{element}」的傾向，生肖為{animal}。接下來一段時間，比起強行突破，更適合整理優先順序與調整節奏。"
        personality = "你可能在能自己掌握節奏時表現最好；但當太多未完成的事情同時堆在一起時，容易消耗注意力。"
        should_do = ["先完成一件真正重要的事，再開新的目標。", "在親密關係裡把需要說得更清楚。", "行程保留一點彈性，方便應付臨時變化。"]
        watch_out = ["不要因為被催促就做重大決定。", "不要因一則訊息或一天的情緒過度下結論。", "情緒性消費時要更保守。"]
        closing = "這份內容的重點不是預言某件事一定發生，而是提醒你在哪些地方可以更清楚地行動。"
    else:
        overview = f"Lá số cơ bản mang sắc thái {element}, tuổi {animal}. Trong khoảng thời gian tới, nhịp phù hợp hơn là sắp lại ưu tiên và tiến từng bước thay vì cố ép một cú bứt phá lớn."
        personality = "Bạn thường phát huy tốt khi có quyền chủ động nhịp độ, nhưng dễ hụt năng lượng khi quá nhiều việc dang dở cùng kéo sự chú ý."
        should_do = ["Khép lại một việc quan trọng trước khi mở thêm mục tiêu mới.", "Nói rõ nhu cầu của mình hơn trong các mối quan hệ gần.", "Chừa một khoảng trống trong lịch để xử lý thay đổi bất ngờ."]
        watch_out = ["Không quyết định việc lớn chỉ vì đang bị thúc hoặc sốt ruột.", "Đừng suy diễn quá nhiều từ một tin nhắn hay một ngày không thuận.", "Cẩn trọng với chi tiêu mang tính giải tỏa cảm xúc."]
        closing = "Điểm đáng dùng của bản đọc này không phải đoán chính xác một sự kiện, mà là nhìn ra chỗ nào bạn nên chủ động hơn."

    area_summaries = []
    for key in AREA_KEYS:
        score = scores[key]
        if lang == "en":
            summary = "Momentum is fairly open; consistency matters more than speed." if score >= 70 else "Keep expectations moderate and focus on what you can control."
        elif lang == "zh":
            summary = "整體節奏偏順，穩定比速度更重要。" if score >= 70 else "先維持合理期待，把注意力放在可控制的事情上。"
        else:
            summary = "Nhịp khá mở; đều đặn quan trọng hơn làm thật nhanh." if score >= 70 else "Nên giữ kỳ vọng vừa phải và tập trung vào phần mình kiểm soát được."
        area_summaries.append({"key": key, "label": labels[key], "score": score, "summary": summary})

    return {
        "overview": overview,
        "personality": personality,
        "near_future": {
            "period": f"{date.today().strftime('%d/%m/%Y')} – {period_end.strftime('%d/%m/%Y')}",
            "summary": overview,
            "areas": area_summaries,
        },
        "should_do": should_do,
        "watch_out": watch_out,
        "closing": closing,
        "used_demo": True,
    }


@dataclass
class AstrologyService:
    api_key: str
    model: str
    reasoning_effort: str = "low"
    max_output_tokens: int = 2200

    def __post_init__(self) -> None:
        self.api_key = str(self.api_key or "").strip()
        self.model = str(self.model or "gpt-5.6-luna").strip() or "gpt-5.6-luna"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def generate_reading(self, *, profile: dict[str, Any], ui_language: str = "vi") -> dict[str, Any]:
        if self.client is None:
            return _fallback_reading(profile, ui_language)
        lang = normalize_ui_language(ui_language)
        language_name = {"vi": "Vietnamese", "en": "English", "zh": "Traditional Chinese"}[lang]
        start = date.today()
        end = start + timedelta(days=45)
        instructions = f"""You are a careful astrology-style interpretation writer for a youth lifestyle product.
The product is for entertainment and self-reflection, not scientific prediction.
Write in {language_name}.
The backend provides a deterministic Tử Vi Đẩu Số natal chart calculated by an an-sao engine. Never invent or move stars, palaces, major-cycle values, Tuần/Triệt, Can Chi, zodiac, element, or birth-hour values. Base interpretations on the supplied chart.
Do not claim that a specific event will definitely happen. Treat the next 30-45 days as tendencies and reflection prompts. When available, use the current-age đại hạn context and current-year information in the chart, but do not pretend this is a precise lưu nguyệt forecast.
Never use astrology to diagnose health, guarantee money, tell the user to gamble/invest, or make legal/medical decisions.
Keep the reading warm, concise, specific enough to feel useful, but not fatalistic.
Future window: {start.isoformat()} to {end.isoformat()}.
Return ONLY valid JSON with this exact structure:
{{
  "overview": "2-4 sentences",
  "personality": "2-4 sentences",
  "near_future": {{
    "period": "human-readable date range",
    "summary": "2-3 sentences",
    "areas": [
      {{"key":"love","label":"...","score":0-100,"summary":"1-2 sentences"}},
      {{"key":"career","label":"...","score":0-100,"summary":"1-2 sentences"}},
      {{"key":"study","label":"...","score":0-100,"summary":"1-2 sentences"}},
      {{"key":"money","label":"...","score":0-100,"summary":"1-2 sentences"}},
      {{"key":"relationships","label":"...","score":0-100,"summary":"1-2 sentences"}}
    ]
  }},
  "should_do": ["3 short practical items"],
  "watch_out": ["3 short caution items"],
  "closing": "1-2 sentence takeaway"
}}
Scores are visual entertainment indicators, not probabilities. Keep scores between 45 and 88."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps({**profile, "tuvi_chart": compact_chart_for_ai(profile.get("tuvi_chart") or {})}, ensure_ascii=False),
            "max_output_tokens": max(900, int(self.max_output_tokens)),
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        try:
            response = self.client.responses.create(**kwargs)
            data = _extract_json(_response_text(response))
            data["used_demo"] = False
            return self._sanitize_reading(data, lang, profile)
        except Exception:
            return _fallback_reading(profile, lang)

    def answer_question(
        self,
        *,
        profile: dict[str, Any],
        reading: dict[str, Any],
        question: str,
        history: list[dict[str, str]],
        ui_language: str = "vi",
    ) -> dict[str, Any]:
        lang = normalize_ui_language(ui_language)
        if self.client is None:
            return self._fallback_answer(profile, reading, question, lang)
        language_name = {"vi": "Vietnamese", "en": "English", "zh": "Traditional Chinese"}[lang]
        instructions = f"""You answer follow-up questions about an entertainment astrology reading.
Write in {language_name}. Focus only on what the user asked; do not repeat the entire chart.
Use the supplied birth profile and previous reading as context. Do not invent exact future events, exact dates, guaranteed outcomes, medical diagnoses, investment guarantees, or legal advice.
When the question is about the near future, phrase it as tendencies, things to watch for, and practical actions.
Return ONLY JSON: {{"answer":"3-8 concise sentences","takeaways":["1-3 short points"],"caution":"optional short caution"}}."""
        payload = {"profile": {**profile, "tuvi_chart": compact_chart_for_ai(profile.get("tuvi_chart") or {})}, "reading": reading, "question": question, "recent_history": history[-8:]}
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(payload, ensure_ascii=False),
            "max_output_tokens": 1300,
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        try:
            response = self.client.responses.create(**kwargs)
            data = _extract_json(_response_text(response))
            return {
                "answer": str(data.get("answer", "")).strip()[:2200],
                "takeaways": [str(x).strip()[:300] for x in (data.get("takeaways") or [])[:4] if str(x).strip()],
                "caution": str(data.get("caution", "")).strip()[:500],
                "used_demo": False,
            }
        except Exception:
            return self._fallback_answer(profile, reading, question, lang)

    def _sanitize_reading(self, data: dict[str, Any], lang: str, profile: dict[str, Any]) -> dict[str, Any]:
        fallback = _fallback_reading(profile, lang)
        near = data.get("near_future") if isinstance(data.get("near_future"), dict) else {}
        raw_areas = near.get("areas") if isinstance(near.get("areas"), list) else []
        raw_by_key = {str(item.get("key")): item for item in raw_areas if isinstance(item, dict)}
        labels = AREA_LABELS[lang]
        areas = []
        for key in AREA_KEYS:
            item = raw_by_key.get(key, {})
            try:
                score = int(item.get("score", 65))
            except (TypeError, ValueError):
                score = 65
            score = max(45, min(88, score))
            areas.append({
                "key": key,
                "label": str(item.get("label") or labels[key])[:80],
                "score": score,
                "summary": str(item.get("summary") or fallback["near_future"]["areas"][AREA_KEYS.index(key)]["summary"]).strip()[:500],
            })
        return {
            "overview": str(data.get("overview") or fallback["overview"]).strip()[:1800],
            "personality": str(data.get("personality") or fallback["personality"]).strip()[:1800],
            "near_future": {
                "period": str(near.get("period") or fallback["near_future"]["period"]).strip()[:120],
                "summary": str(near.get("summary") or fallback["near_future"]["summary"]).strip()[:1400],
                "areas": areas,
            },
            "should_do": [str(x).strip()[:320] for x in (data.get("should_do") or fallback["should_do"])[:5] if str(x).strip()],
            "watch_out": [str(x).strip()[:320] for x in (data.get("watch_out") or fallback["watch_out"])[:5] if str(x).strip()],
            "closing": str(data.get("closing") or fallback["closing"]).strip()[:1000],
            "used_demo": bool(data.get("used_demo", False)),
        }

    def _fallback_answer(self, profile: dict[str, Any], reading: dict[str, Any], question: str, lang: str) -> dict[str, Any]:
        q = str(question or "").lower()
        areas = {str(x.get("key")): x for x in (reading.get("near_future", {}).get("areas") or []) if isinstance(x, dict)}
        key = "career"
        if any(word in q for word in ["tình", "yêu", "love", "感情", "愛"]): key = "love"
        elif any(word in q for word in ["học", "thi", "study", "學"]): key = "study"
        elif any(word in q for word in ["tiền", "tài chính", "money", "財"]): key = "money"
        elif any(word in q for word in ["bạn", "quan hệ", "relationship", "人際"]): key = "relationships"
        item = areas.get(key, {})
        summary = str(item.get("summary") or reading.get("near_future", {}).get("summary") or reading.get("overview") or "")
        if lang == "en":
            answer = f"For this topic, the reading points more toward pacing and clear choices than a guaranteed event. {summary} Treat it as a prompt to notice patterns, then decide from real information in front of you."
            takeaways = ["Watch the pattern, not one isolated moment.", "Choose the next practical action you control."]
            caution = "Do not use this reading as the only basis for a major financial, health, or legal decision."
        elif lang == "zh":
            answer = f"這個主題比較像是提醒你注意節奏與選擇，而不是預告某件事一定發生。{summary} 可以把它當成觀察自己模式的提示，再根據現實資訊做決定。"
            takeaways = ["看整體模式，不要只看單一事件。", "先做一個你能控制的實際下一步。"]
            caution = "重大財務、健康或法律決定，不要只依賴這份內容。"
        else:
            answer = f"Ở chủ đề này, lá số nghiêng về việc quan sát nhịp và lựa chọn hơn là khẳng định một sự kiện chắc chắn. {summary} Hãy xem đây như một gợi ý để nhận ra mô thức của mình rồi quyết định dựa trên tình hình thật."
            takeaways = ["Nhìn cả một chuỗi dấu hiệu, đừng kết luận từ một khoảnh khắc.", "Chọn một bước thực tế mà bạn kiểm soát được ngay lúc này."]
            caution = "Không dùng bản đọc này làm căn cứ duy nhất cho quyết định lớn về tiền bạc, sức khỏe hoặc pháp lý."
        return {"answer": answer, "takeaways": takeaways, "caution": caution, "used_demo": True}
