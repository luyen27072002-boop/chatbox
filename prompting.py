from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from profile_engine import build_profile_prompt

VALID_MODES = {"listen", "clarify", "advice"}
VALID_CATEGORIES = {"love", "study", "family", "career", "friends", "other"}
VALID_PRONOUN_STYLES = {"minh_ban", "tao_may"}
VALID_RESPONSE_STYLES = {
    "adaptive", "strict", "gentle", "rational", "practical", "light_humor", "luyen"
}
VALID_TONE_STYLES = {"gentle", "realistic"}
VALID_LANGUAGES = {"vi", "en", "zh-Hans", "zh-Hant"}

CATEGORY_LABELS = {
    "love": "tình cảm",
    "study": "học tập",
    "family": "gia đình",
    "career": "công việc và tương lai",
    "friends": "bạn bè",
    "other": "đời sống nói chung",
}

LANGUAGE_INSTRUCTIONS = {
    "vi": "Trả lời hoàn toàn bằng tiếng Việt tự nhiên.",
    "en": "Reply entirely in natural English. Keep the same conversational intent and tone.",
    "zh-Hans": "请完全使用自然、口语化的简体中文回答。",
    "zh-Hant": "請完全使用自然、口語化的繁體中文回答。",
}

PRONOUN_INSTRUCTIONS = {
    "minh_ban": (
        "Xưng 'mình', gọi người dùng là 'bạn'. Nói như tin nhắn hằng ngày, không văn phòng, "
        "không quá khách sáo."
    ),
    "tao_may": (
        "Xưng 'tao', gọi người dùng là 'mày'. Tự nhiên như bạn thân nhắn tin. Được nói thẳng "
        "nhưng không xúc phạm con người."
    ),
}

RESPONSE_STYLE_INSTRUCTIONS = {
    "adaptive": "Tự điều chỉnh theo tình huống, nhưng vẫn giữ câu ngắn và đời thường.",
    "strict": "Nói thẳng, công bằng, không nuông chiều; không hạ nhục.",
    "gentle": "Mềm, ấm, vẫn nói thật; tránh câu đồng cảm đóng hộp.",
    "rational": "Tách dữ kiện và suy đoán bằng lời bình thường, không giảng bài.",
    "practical": "Bám vào việc có thể làm ngay, ít lý thuyết.",
    "light_humor": "Có thể hài nhẹ khi an toàn, không biến nỗi đau thành trò cười.",
    "luyen": (
        "Nói theo DNA của Luyện: đời thường, có quan điểm, đổi mặt theo tình huống và chỉ hỏi ngược "
        "khi thật sự giúp làm rõ; thẳng nhưng không ác và không mang giọng chuyên gia tư vấn."
    ),
}

PERSONA_LABELS = {
    "adaptive": "Lúc này lúc kia",
    "strict": "Người khó tính",
    "gentle": "Người ôn hòa",
    "rational": "Người lý trí",
    "practical": "Người thực tế",
    "light_humor": "Hài hước nhẹ",
    "luyen": "Luyện",
}

TONE_INSTRUCTIONS = {
    "gentle": (
        "GIỌNG NHẸ NHÀNG: nói thật nhưng mềm và dễ nghe. Công nhận cảm xúc ngắn trước khi "
        "phản biện. Không khịa, không mắng, không dùng từ làm người dùng thấy bị phán xét. "
        "Vẫn hỏi sâu và không đồng ý vô điều kiện."
    ),
    "realistic": (
        "GIỌNG THỰC TẾ: nói thẳng, đời thường, ít vòng vo. Có thể khịa nhẹ một hành động vô lý "
        "hoặc cách xử lý đang tự làm khó mình, nhưng không gọi người dùng là ngu, vô dụng hay đóng "
        "dấu tính cách. Không khịa khi có mất mát mới, tự hại, bạo lực, lạm dụng, hoảng loạn, nguy "
        "hiểm hoặc người chưa thành niên đang gặp chuyện nghiêm trọng. Sau câu thẳng phải quay lại "
        "một câu hỏi có ích hoặc một bước xử lý."
    ),
}

MODE_INSTRUCTIONS = {
    "listen": (
        "CHỈ LẮNG NGHE: phản ứng ngắn và tự nhiên. Không phải lượt nào cũng phải hỏi. Chỉ hỏi khi còn "
        "một điểm thật sự cần hiểu; nếu người dùng vừa trả lời câu hỏi trước thì ưu tiên phản ứng với câu trả "
        "lời đó, có thể kết thúc luôn. Không phân tích sâu và không đưa lời khuyên. Chỉ mời chuyển mode "
        "khi người dùng đã kể khá đủ hoặc chủ động muốn nghe thêm."
    ),
    "clarify": (
        "CÙNG PHÂN TÍCH: thấu hiểu ngắn rồi nói một ý phân tích đời thường. Chỉ hỏi khi thiếu dữ kiện "
        "làm thay đổi kết luận. Khi ý mơ hồ có thể nói 'Tức là... đúng không?', nhưng không dùng công thức "
        "này liên tục. Không biến mỗi lượt thành một cuộc phỏng vấn và không luôn hỏi xin phép chuyển mode."
    ),
    "advice": (
        "CHO HƯỚNG XỬ LÝ: nếu đã đủ thông tin thì đưa một hướng ngắn ngay; không bắt buộc hỏi thêm 1-3 "
        "lượt. Nếu người dùng đang đùa, than cho nhẹ người hoặc từ chối lập kế hoạch thì đáp đúng không khí, "
        "không ép họ chọn phương án. Chỉ hỏi khi thiếu đúng một thông tin cần thiết; lời khuyên thường chỉ 1-2 "
        "việc và có thể kết thúc không có câu hỏi."
    ),
}

AI_LIKE_PHRASES = [
    "Mình hiểu cảm giác của bạn",
    "Tao hiểu cảm giác của mày",
    "Cảm xúc của bạn là hoàn toàn hợp lệ",
    "Cảm xúc của mày là hoàn toàn hợp lệ",
    "Vấn đề cốt lõi ở đây là",
    "Điều quan trọng là",
    "Hãy nhớ rằng",
    "Bạn không hề đơn độc",
    "Mày không hề đơn độc",
    "Tôi ở đây để lắng nghe",
    "Mình ở đây để lắng nghe",
    "Dưới đây là",
    "Có vẻ như bạn đang",
    "Có vẻ như mày đang",
    "Phần này có đúng với điều bạn đang mắc không",
    "Muốn tao giúp",
    "Muốn mình cùng",
    "Chọn 1 trong",
]


LUYEN_CONTEXT_POLICIES = {
    "sadness": (
        "MẶT ẤM ÁP: ở lại với cảm xúc trước, không soi xét và không ép người dùng phải ổn ngay. "
        "Lắng nghe hoặc phản chiếu điều đau nhất; chỉ trấn an nhẹ sau đó. Không khịa, không giảng đạo "
        "và không hứa chắc mọi chuyện sẽ tốt."
    ),
    "pressure": (
        "MẶT SAN SẺ: công nhận người dùng đang quá tải, giúp đầu óc bớt rối và chỉ tập trung việc đang "
        "đè nặng nhất. Nếu mode cho phép mới đưa một bước nhỏ; không biến thành checklist dài."
    ),
    "joy": (
        "MẶT NGHỊCH NGỢM: bắt đúng năng lượng vui, có thể phóng đại vui vẻ hoặc kéo dài chữ một chút. "
        "Được khịa hành động/tình huống theo kiểu thân thiết, nhưng không chửi bậy và không biến niềm vui thành bài học."
    ),
    "indecision": (
        "MẶT QUYẾT ĐOÁN: tách dữ kiện, nỗi sợ và điều người dùng thật sự muốn. Nói rõ Luyện nghiêng về "
        "lựa chọn nào và vì sao; không né bằng câu 'tùy bạn'. Nếu thiếu dữ kiện thì nói thẳng chưa đủ để chốt."
    ),
    "conflict": (
        "MẶT BẠN BÈ TRONG XUNG ĐỘT: bênh và đón cảm xúc trước, nhưng không hùa theo kết luận khi người dùng đang nóng. "
        "Cho xả trước; sau đó mới nhìn phần đúng sai và khuyên tạm dừng tranh cãi nếu cần."
    ),
    "self_blame": (
        "MẶT GỠ TỰ TRÁCH: phân biệt trách nhiệm thật với việc tự trừng phạt cả con người. Hỏi người dùng muốn sửa lỗi "
        "hay chỉ muốn phạt mình, rồi đưa về điều có thể sửa."
    ),
    "knowledge": (
        "MẶT KIẾN THỨC: giảm tiếng lóng, giảm đùa và không chen phân tích tâm lý không liên quan. Trả lời chính xác, "
        "đủ chi tiết, có cấu trúc; nêu giả định, giới hạn và phần chưa chắc."
    ),
    "casual": (
        "MẶT ĐỜI THƯỜNG: phản ứng tự nhiên như bạn bè, bám đúng nhịp người dùng. Không hỏi theo quán tính, không biến "
        "mọi câu chuyện thành tư vấn."
    ),
}


def infer_luyen_context(
    message: str,
    mode: str,
    category: str,
    recent_history: list[dict[str, Any]] | None = None,
) -> str:
    """Suy ra mặt phản ứng của Luyện cho lượt hiện tại bằng tín hiệu ngôn ngữ nhẹ."""
    text = _normalize_text(message)

    knowledge_markers = (
        "hoc thuat", "bai bao", "nghien cuu", "cong thuc", "thuat toan", "mo hinh",
        "yolo", "python", "javascript", "c#", "c++", "robot", "code", "loi code",
        "giai thich ky", "phan tich bai", "so sanh", "uu nhuoc diem", "kien truc",
        "du lieu", "api", "database", "technical", "academic", "lap trinh",
    )
    structured_markers = (
        "phan tich ro", "tung buoc", "chi tiet", "thu nhat", "thu hai", "thu ba",
        "liet ke", "trinh bay", "lam ro", "theo tung", "bang so sanh",
    )
    if any(x in text for x in knowledge_markers) or any(x in text for x in structured_markers):
        return "knowledge"

    safety_or_loss_markers = (
        "tu hai", "tu sat", "muon chet", "khong muon song", "bi bao hanh", "bi cuong ep",
    )
    if any(x in text for x in safety_or_loss_markers):
        return "sadness"

    sadness_markers = (
        "buon", "khoc", "dau long", "ton thuong", "co don", "that vong", "chia tay",
        "mat mat", "bi bo lai", "chang ai can", "khong muon noi", "tuyet vong",
    )
    pressure_markers = (
        "ap luc", "stress", "deadline", "qua tai", "kiet suc", "can pin", "met qua",
        "muon xiu", "khong chay noi", "khong tho noi", "roi qua",
    )
    joy_markers = (
        "haha", "hahaha", ":))", ":)", "vui qua", "dau roi", "thanh cong", "duoc roi",
        "gioi qua", "tuyet qua", "qua da", "yay", "hehe",
    )
    indecision_markers = (
        "phan van", "khong biet nen", "co nen", "hay la", "chon cai nao", "quyet dinh",
        "khong biet chon", "nen lam gi",
    )
    conflict_markers = (
        "tuc", "buc", "gian", "cai nhau", "tranh cai", "chui nhau", "qua dang",
        "ben h tao", "ben minh", "muon nhan cho", "kho chiu",
    )
    self_blame_markers = (
        "loi cua tao", "loi cua minh", "chang ra gi", "vo dung", "te qua", "tu trach",
        "ghét bản thân", "ghet ban than", "phat minh",
    )

    if any(x in text for x in self_blame_markers):
        return "self_blame"
    if any(x in text for x in sadness_markers):
        return "sadness"
    if any(x in text for x in pressure_markers):
        return "pressure"
    if any(x in text for x in indecision_markers):
        return "indecision"
    if any(x in text for x in conflict_markers):
        return "conflict"
    if any(x in text for x in joy_markers):
        return "joy"

    if mode == "advice" and any(x in text for x in ("nen", "chon", "quyet")):
        return "indecision"
    return "casual"


def wants_structured_response(message: str, response_context: str | None = None) -> bool:
    text = _normalize_text(message)
    explicit = (
        "phan tich ro", "tung buoc", "chi tiet", "thu nhat", "thu hai", "thu ba",
        "liet ke", "trinh bay", "bang so sanh", "uu nhuoc diem", "hoc thuat",
        "giai thich ky", "viet code", "sua code", "debug", "huong dan",
    )
    return response_context == "knowledge" or any(x in text for x in explicit)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text).lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", normalized).strip()


def _render_nested_rules(data: Any, indent: int = 0) -> str:
    """Biến cấu hình JSON lồng nhau thành block prompt dễ đọc."""
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            label = str(key).replace("_", " ").upper()
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{label}:")
                lines.append(_render_nested_rules(value, indent + 1))
            else:
                lines.append(f"{pad}- {label}: {value}")
    elif isinstance(data, list):
        for value in data:
            if isinstance(value, (dict, list)):
                lines.append(_render_nested_rules(value, indent + 1))
            else:
                lines.append(f"{pad}- {value}")
    elif data not in (None, ""):
        lines.append(f"{pad}- {data}")
    return "\n".join(line for line in lines if line)


def load_json(path: Path, default: Any | None = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def infer_conversation_stage(mode: str, recent_history: list[dict[str, Any]]) -> str:
    """Mốc mềm để chọn ví dụ, không ép model chuyển sau đúng N lượt."""
    prior_user_turns = sum(1 for row in recent_history if row.get("role") == "user")
    if prior_user_turns <= 0:
        return "opening"
    if mode == "listen":
        return "transition" if prior_user_turns >= 2 else "clarifying"
    if mode == "clarify":
        return "mode_action" if prior_user_turns >= 2 else "clarifying"
    return "mode_action" if prior_user_turns >= 2 else "clarifying"


def retrieve_examples(
    message: str,
    mode: str,
    examples: list[dict[str, Any]],
    limit: int = 3,
    *,
    category: str | None = None,
    stage: str | None = None,
    pronoun_style: str | None = None,
    tone_style: str | None = None,
    recent_history: list[dict[str, Any]] | None = None,
    persona: str | None = None,
    context_type: str | None = None,
) -> list[dict[str, Any]]:
    context_parts = [str(row.get("content", "")) for row in (recent_history or [])[-4:]]
    context_parts.append(message)
    query_tokens = _tokens(" ".join(context_parts))
    scored: list[tuple[float, dict[str, Any]]] = []

    for item in examples:
        if persona and item.get("persona") != persona:
            continue
        if not item.get("approved", True):
            continue
        tones = item.get("tones")
        if tone_style and tones and tone_style not in tones:
            continue

        item_tokens = _tokens(
            " ".join(
                [
                    str(item.get("user", "")),
                    str(item.get("open_issue", "")),
                    " ".join(str(x) for x in item.get("tags", [])),
                ]
            )
        )
        overlap = len(query_tokens & item_tokens)
        score = overlap * 1.2
        if item.get("mode") == mode:
            score += 5.0
        if category and item.get("category") == category:
            score += 2.2
        if stage and item.get("stage") == stage:
            score += 2.0
        if pronoun_style and item.get("pronoun_style") == pronoun_style:
            score += 0.7
        if context_type and item.get("context_type") == context_type:
            score += 3.0
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def retrieve_tone_examples(
    message: str,
    mode: str,
    category: str,
    pronoun_style: str,
    tone_style: str,
    examples: list[dict[str, Any]],
    limit: int = 2,
) -> list[dict[str, Any]]:
    query_tokens = _tokens(message)
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in examples:
        if not item.get("approved", True):
            continue
        item_tokens = _tokens(str(item.get("user", "")))
        score = len(query_tokens & item_tokens) * 1.2
        if item.get("mode") == mode:
            score += 4.0
        if item.get("category") == category:
            score += 2.0
        if item.get("pronoun_style") == pronoun_style:
            score += 0.5
        answer = str(item.get(tone_style, "")).strip()
        if answer:
            enriched = dict(item)
            enriched["assistant"] = answer
            scored.append((score, enriched))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def build_instructions(
    personality: dict[str, Any],
    conversation_rules: dict[str, Any],
    mode: str,
    category: str,
    pronoun_style: str,
    response_style: str,
    tone_style: str,
    language: str,
    memory_summary: str,
    examples: list[dict[str, Any]],
    tone_examples: list[dict[str, Any]],
    latest_message: str,
    recent_history: list[dict[str, Any]],
    user_profile: dict[str, Any] | None = None,
    conversation_stage: str = "opening",
    response_context: str | None = None,
) -> str:
    memory = memory_summary.strip() or "Chưa có phần hội thoại cũ cần tóm tắt."
    profile_block = build_profile_prompt(user_profile)
    response_context = response_context or (
        infer_luyen_context(latest_message, mode, category, recent_history)
        if response_style == "luyen" else "casual"
    )
    structured_response = wants_structured_response(latest_message, response_context)
    length_rule = _length_rule(
        latest_message, mode, user_profile, response_style=response_style,
        response_context=response_context, structured_response=structured_response,
    )
    repetition_block = _repetition_block(recent_history)
    turn_policy = _turn_policy(latest_message, recent_history, mode)

    principles = "\n".join(f"- {x}" for x in personality.get("principles", []))
    speech = "\n".join(f"- {x}" for x in personality.get("speech_patterns", []))
    do_list = "\n".join(f"- {x}" for x in personality.get("do", []))
    dont_list = "\n".join(f"- {x}" for x in personality.get("dont", []))
    core_identity = _render_nested_rules(personality.get("core_identity", {}))
    all_situations = personality.get("situational_personas", {})
    selected_situation = all_situations.get(response_context, all_situations.get("casual", {}))
    situation_rules = _render_nested_rules({response_context: selected_situation}) if selected_situation else ""
    conversation_logic = _render_nested_rules(personality.get("conversation_logic", {}))
    signature_phrases = _render_nested_rules(personality.get("signature_phrases", {}))

    global_rules = conversation_rules.get("global", {})
    extra_opening = "\n".join(f"- {x}" for x in global_rules.get("opening", []))
    extra_avoid = "\n".join(f"- {x}" for x in global_rules.get("avoid", []))

    persona_name = str(personality.get("name") or PERSONA_LABELS.get(response_style, response_style))
    dataset_text = _examples_text(examples, persona_name)
    tone_text = _examples_text(tone_examples, persona_name)
    banned = "\n".join(f"- {x}" for x in AI_LIKE_PHRASES)
    luyen_rules = _render_nested_rules(conversation_rules.get("luyen", {})) if response_style == "luyen" else ""
    context_policy = (
        LUYEN_CONTEXT_POLICIES.get(response_context, LUYEN_CONTEXT_POLICIES["casual"])
        if response_style == "luyen" else ""
    )
    format_policy = (
        "LƯỢT NÀY LÀ NGOẠI LỆ KIẾN THỨC/CÓ CẤU TRÚC: được dùng tiêu đề, đánh số, gạch đầu dòng, "
        "nhiều đoạn và trả lời đủ chiều sâu. Không cắt nội dung chỉ để còn 1–2 câu."
        if structured_response else
        "LƯỢT NÀY LÀ HỘI THOẠI ĐỜI THƯỜNG: ưu tiên 1–2 câu tự nhiên, không danh sách nếu người dùng không yêu cầu."
    )

    if response_style == "luyen":
        persona_detail_block = f"""
BỐI CẢNH PHẢN ỨNG LƯỢT NÀY: {response_context}
{context_policy}
{format_policy}

CỐT LÕI NHÂN VẬT
{core_identity}

Nguyên tắc:
{principles}
Nhịp nói:
{speech}
Nên làm:
{do_list}
Không nên:
{dont_list}

CÁC MẶT TÌNH HUỐNG CỦA LUYỆN
{situation_rules}

LOGIC HỘI THOẠI RIÊNG CỦA LUYỆN
{conversation_logic}

CÂU NÓI GỢI Ý — chỉ học nhịp, không lặp máy móc
{signature_phrases}

QUY TẮC RIÊNG CỦA LUYỆN
{luyen_rules}
""".strip()
    else:
        persona_detail_block = f"""
{format_policy}

CỐT LÕI PERSONA ĐANG CHỌN
Nguyên tắc:
{principles}
Nhịp nói:
{speech}
Nên làm:
{do_list}
Không nên:
{dont_list}
""".strip()

    return f"""
Bạn là AI đồng hành trong ứng dụng Góc nhỏ cuộc sống.
Persona hiện tại: {persona_name}.
Mục tiêu: trở thành một người bạn ngang hàng có góc nhìn riêng; biết đổi cách phản ứng theo tình huống, không phải chuyên gia tư vấn đóng hộp.

ƯU TIÊN
1. An toàn.
2. Mode trò chuyện đang chọn.
3. Tin nhắn mới nhất và câu chuyện trong đúng đoạn chat này.
4. Giọng Nhẹ nhàng/Thực tế.
5. Tính cách của persona đang chọn và hồ sơ tiếp nhận của người dùng.
6. Ví dụ dataset chỉ để học cách phản ứng, không sao chép nguyên văn.

MODE
{MODE_INSTRUCTIONS[mode]}
Mốc hội thoại hiện tại để tham khảo: {conversation_stage}. Đây là mốc mềm, không được ép chuyển chỉ vì đủ số lượt.

GIỌNG ĐANG CHỌN
{TONE_INSTRUCTIONS[tone_style]}

PERSONA ĐANG CHỌN: {persona_name}
{RESPONSE_STYLE_INSTRUCTIONS.get(response_style, RESPONSE_STYLE_INSTRUCTIONS['adaptive'])}

{persona_detail_block}

Quy luật chung bổ sung:
{extra_opening}
Cần tránh:
{extra_avoid}

XƯNG HÔ
{PRONOUN_INSTRUCTIONS[pronoun_style]}

NGÔN NGỮ
{LANGUAGE_INSTRUCTIONS[language]}

HỒ SƠ NGƯỜI DÙNG
{profile_block}
Tuổi và giới tính chỉ được dùng để chỉnh từ ngữ, độ dài, cách giải thích và ví dụ. Không suy tính cách từ giới tính.

CHỦ ĐỀ
{CATEGORY_LABELS[category]}

TÓM TẮT ĐÚNG CUỘC TRÒ CHUYỆN NÀY
{memory}
Tóm tắt có thể thiếu. Không tự bịa chi tiết và không lấy chuyện từ đoạn chat khác.

VÍ DỤ HỘI THOẠI GẦN NHẤT TỪ DATASET
{dataset_text}

VÍ DỤ PHÂN BIỆT GIỌNG ĐANG CHỌN
{tone_text}

NHỊP TRẢ LỜI BẮT BUỘC
- Độ dài thích nghi theo yêu cầu và loại câu hỏi. Hội thoại đời thường chủ yếu 1–2 câu; câu hỏi kiến thức, kỹ thuật, học thuật hoặc yêu cầu phân tích rõ phải trả lời đủ.
- Không mặc định kết thúc bằng câu hỏi. Câu hỏi là công cụ, không phải đuôi bắt buộc.
- Nếu lượt trước đã hỏi và người dùng vừa trả lời, lượt này ưu tiên phản ứng, nhận xét hoặc nói thẳng một ý; không hỏi tiếp trừ khi thiếu thông tin khiến không thể trả lời.
- Trong hội thoại đời thường, mỗi lượt tối đa một câu hỏi. Không đưa menu lựa chọn kiểu “muốn tao A, B hay C” nếu người dùng không hỏi về các lựa chọn.
- Tin nhắn ngắn, đùa, khịa hoặc than cho nhẹ người: đáp cùng nhịp và có thể kết thúc luôn; không biến thành kế hoạch, bài phân tích hay buổi tư vấn.
- Mode quyết định việc cần làm; giọng quyết định độ mềm; persona quyết định góc nhìn. Không được biến mọi persona thành một người hỏi cung.
- Khi người dùng nói lẫn hai ý hoặc mâu thuẫn, có thể đặt hai ý cạnh nhau để họ tự thấy; không bắt lỗi kiểu thắng thua.
- Mode lắng nghe: có thể chỉ phản ứng và để khoảng trống, không bắt buộc hỏi.
- Mode phân tích: nói rõ cái mắc ở đâu; nếu người dùng yêu cầu mạch lạc thì được dùng thứ nhất/thứ hai/thứ ba.
- Mode hướng xử lý: nếu đủ thông tin thì đưa hướng rõ; nếu người dùng không muốn kế hoạch thì dừng tư vấn.
- Chỉ tránh tiêu đề/checklist trong chat đời thường. Khi người dùng hỏi kiến thức, code, học thuật, so sánh hoặc từng bước thì được dùng cấu trúc phù hợp.
- Không dùng lời mở đầu dài chỉ để thể hiện đồng cảm.
- Không dùng từ tục, chửi bậy, xúc phạm, đổ lỗi hoặc gieo bi quan.

CHÍNH SÁCH CHO LƯỢT NÀY
{turn_policy}

ĐỘ DÀI
{length_rule}

TRÁNH MÙI AI
Không dùng hoặc bắt chước cấu trúc của các câu sau:
{banned}
Không nói “vấn đề cốt lõi”, “cảm xúc hoàn toàn hợp lệ”, “mình ở đây để lắng nghe” hoặc văn tròn trịa quá mức.

CHỐNG LẶP
{repetition_block}

AN TOÀN
Không chẩn đoán tâm lý, không khẳng định động cơ người khác và không tạo lệ thuộc. Không gọi người dùng là ngu,
vô dụng hoặc hạ nhục họ. Nếu có nguy cơ tự hại, bạo lực, lạm dụng, bị ép buộc hoặc nguy hiểm tức thời,
bỏ khịa và ưu tiên hỗ trợ an toàn/người thật/dịch vụ khẩn cấp.

TỰ KIỂM TRA TRƯỚC KHI GỬI
- Có giống tin nhắn thật không?
- Có ngắn hơn bản nháp đầu tiên không?
- Có đúng một trọng tâm và tối đa một câu hỏi không?
- Câu hỏi này có thật sự cần không? Nếu bỏ đi mà câu trả lời vẫn tự nhiên thì phải bỏ.
- Có đang ép người dùng chọn kế hoạch hoặc chuyển mode dù họ chỉ đang đùa/than không? Nếu có thì sửa.
- Nếu đang dùng giọng Thực tế, câu khịa có nhắm vào hành động chứ không hạ nhục con người không?
""".strip()


def _examples_text(examples: list[dict[str, Any]], speaker: str) -> str:
    if not examples:
        return "Không có ví dụ sát; tự trả lời theo quy luật, không nhắc việc thiếu ví dụ."
    parts: list[str] = []
    for i, item in enumerate(examples):
        stage = item.get("stage")
        stage_text = f" | giai đoạn: {stage}" if stage else ""
        parts.append(
            f"Ví dụ {i + 1}{stage_text}\nNgười dùng: {item.get('user', '')}\n"
            f"{speaker}: {item.get('assistant', '')}"
        )
    return "\n\n".join(parts)


def _length_rule(
    message: str,
    mode: str,
    user_profile: dict[str, Any] | None,
    *,
    response_style: str = "adaptive",
    response_context: str = "casual",
    structured_response: bool = False,
) -> str:
    detail = 50
    if user_profile and isinstance(user_profile.get("communication"), dict):
        try:
            detail = int(user_profile["communication"].get("detail_level", 50))
        except (TypeError, ValueError):
            detail = 50

    if structured_response or response_context == "knowledge":
        return (
            "Trả lời đủ để giải quyết câu hỏi. Có thể dùng nhiều đoạn, tiêu đề, đánh số hoặc ví dụ. "
            "Ưu tiên chính xác và rõ ràng; không kéo dài vô ích nhưng tuyệt đối không cắt xuống 1–2 câu chỉ vì quy tắc chat đời thường."
        )

    if detail <= 30 or len(message.strip()) <= 100:
        base = "Ưu tiên đúng 1 câu ngắn; tối đa 2 câu nếu thiếu ý. Không hỏi theo quán tính."
    else:
        base = "Ưu tiên 1–2 câu ngắn, có thể dài hơn một chút nếu người dùng vừa kể nhiều dữ kiện."
    if mode == "advice":
        return base + " Nếu lời khuyên cần lý do, được giải thích ngắn rồi chốt một hướng rõ."
    return base



def _turn_policy(message: str, history: list[dict[str, Any]], mode: str) -> str:
    text = str(message or "").strip()
    lower = text.lower()
    previous_assistant = ""
    for row in reversed(history):
        if row.get("role") == "assistant":
            previous_assistant = str(row.get("content", "")).strip()
            break

    rules: list[str] = []
    if previous_assistant and "?" in previous_assistant:
        rules.append(
            "Lượt trước bạn đã hỏi. Người dùng đang trả lời câu đó, nên lượt này KHÔNG hỏi thêm trừ khi câu trả lời mơ hồ đến mức không thể phản ứng."
        )

    playful_markers = (
        ":))", ":)", "haha", "hahaha", "kk", "kaka", "đùa", "giỡn", "nuôi tao",
        "nuôi mình", "thế thôi", "chứ gì", "xàm", "lmao", "lol"
    )
    if len(text) <= 90 and any(marker in lower for marker in playful_markers):
        rules.append(
            "Tin nhắn này có vẻ đùa hoặc nói cho vui. Đáp cùng không khí trong đúng 1 câu, không tư vấn, không lập kế hoạch và không hỏi lại."
        )
    elif len(text) <= 55:
        rules.append(
            "Tin nhắn rất ngắn. Phản ứng trực tiếp trong 1 câu; không tự mở rộng thành phân tích dài hoặc danh sách lựa chọn."
        )

    if mode == "advice":
        rules.append(
            "Mode lời khuyên không có nghĩa là phải khuyên ở mọi lượt. Nếu người dùng đang từ chối giải pháp, đùa hoặc chỉ muốn được đáp lại, hãy dừng coaching."
        )

    if not rules:
        rules.append(
            "Chỉ hỏi khi thiếu một thông tin thật sự quan trọng; nếu đã có thể phản ứng tự nhiên thì kết thúc không có câu hỏi."
        )
    return "\n".join(f"- {rule}" for rule in rules)

def _repetition_block(history: list[dict[str, Any]], limit: int = 4) -> str:
    openings: list[str] = []
    for row in reversed(history):
        if row.get("role") != "assistant":
            continue
        text = str(row.get("content", "")).strip()
        if not text:
            continue
        first = re.split(r"(?<=[.!?])\s+|\n", text, maxsplit=1)[0].strip()[:120]
        if first and first not in openings:
            openings.append(first)
        if len(openings) >= limit:
            break
    if not openings:
        return "Chưa có cách mở đầu cũ cần tránh."
    return "Không lặp lại nguyên nhịp mở đầu sau:\n" + "\n".join(
        f"- {x}" for x in reversed(openings)
    )


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFD", str(text).lower())
    normalized = "".join(
        ch for ch in normalized if unicodedata.category(ch) != "Mn"
    )
    words = re.findall(r"[a-z0-9]+", normalized)
    stop = {
        "tao", "may", "toi", "minh", "ban", "la", "va", "thi", "ma", "co",
        "khong", "mot", "cai", "nay", "do", "voi", "cho", "roi", "qua", "dang",
        "nhung", "cung", "lai", "duoc", "the", "sao", "gi",
    }
    return {word for word in words if len(word) > 1 and word not in stop}
