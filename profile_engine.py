from __future__ import annotations

import math
from typing import Any

# The onboarding questionnaire is adapted from the public-domain Mini-IPIP
# Big-Five item set. It is used here for product personalization, not diagnosis.
TRAITS = (
    "extraversion",
    "agreeableness",
    "conscientiousness",
    "emotional_stability",
    "openness",
)

COMMUNICATION_DIMENSIONS = (
    "directness",
    "emotional_support",
    "challenge_level",
    "detail_level",
    "humor_level",
    "action_orientation",
)

OPTION_LABELS = {
    "gender": {
        "male": "Nam",
        "female": "Nữ",
        "nonbinary": "Phi nhị nguyên",
        "self_described": "Tự mô tả",
        "prefer_not_say": "Không muốn cung cấp",
    },
    "age_group": {
        "under_18": "Dưới 18 tuổi",
        "18_22": "18–22 tuổi",
        "23_30": "23–30 tuổi",
        "31_45": "31–45 tuổi",
        "46_60": "46–60 tuổi",
        "61_plus": "Từ 61 tuổi",
        "prefer_not_say": "Không muốn cung cấp",
    },
    "life_stage": {
        "school_student": "Học sinh",
        "university_student": "Sinh viên",
        "early_career": "Người mới đi làm",
        "employee": "Người đi làm",
        "entrepreneur": "Kinh doanh hoặc doanh nhân",
        "homemaker_caregiver": "Nội trợ hoặc chăm sóc gia đình",
        "retired": "Đã nghỉ hưu",
        "older_adult": "Người cao tuổi",
        "other": "Giai đoạn khác",
    },
    "relationship_status": {
        "single": "Độc thân hoặc chưa kết hôn",
        "dating": "Đang hẹn hò",
        "married": "Đã kết hôn",
        "separated": "Đang ly thân",
        "divorced": "Đã ly hôn",
        "widowed": "Góa",
        "prefer_not_say": "Không muốn cung cấp",
    },
    "children_status": {
        "none": "Chưa có con",
        "expecting": "Đang chuẩn bị có con",
        "young_children": "Có con nhỏ",
        "teen_children": "Có con tuổi thiếu niên",
        "adult_children": "Có con đã trưởng thành",
        "prefer_not_say": "Không muốn cung cấp",
    },
    "living_context": {
        "with_family": "Sống cùng gia đình",
        "alone": "Sống một mình",
        "with_partner": "Sống cùng bạn đời",
        "dorm_shared": "Ký túc xá hoặc ở ghép",
        "assisted_living": "Có người hỗ trợ chăm sóc",
        "other": "Khác",
        "prefer_not_say": "Không muốn cung cấp",
    },
}

LIFE_STAGE_PROMPTS = {
    "school_student": (
        "Người dùng là học sinh. Tôn trọng việc họ có ít quyền tự quyết và nguồn lực hơn người lớn. "
        "Ưu tiên phương án an toàn, phù hợp trường học và gia đình; khi chuyện nghiêm trọng nên gợi ý một "
        "người lớn đáng tin. Không khuyến khích che giấu, gặp riêng người lạ hoặc hành vi nguy hiểm."
    ),
    "university_student": (
        "Người dùng là sinh viên. Đặt vấn đề trong bối cảnh ngành học, học phí, tiền trọ, sống xa nhà, "
        "đồ án, thực tập, tình cảm và quá trình chuyển sang đi làm."
    ),
    "early_career": (
        "Người dùng mới đi làm. Chú ý sự thiếu kinh nghiệm, áp lực chứng minh bản thân, lương, hợp đồng, "
        "quan hệ với quản lý và việc xây nền nghề nghiệp."
    ),
    "employee": (
        "Người dùng đang đi làm. Cân nhắc thời gian, tài chính, nghĩa vụ công việc, sức bền và hậu quả nghề nghiệp."
    ),
    "entrepreneur": (
        "Người dùng kinh doanh hoặc điều hành công việc. Cân nhắc dòng tiền, nhân sự, trách nhiệm, rủi ro, "
        "tốc độ ra quyết định và sự cô đơn của người chịu trách nhiệm cuối."
    ),
    "homemaker_caregiver": (
        "Người dùng đang nội trợ hoặc chăm sóc người thân. Không coi công việc chăm sóc là nhàn; chú ý tải vô hình, "
        "sức khỏe, tài chính, sự phụ thuộc và nhu cầu có thời gian cho bản thân."
    ),
    "retired": (
        "Người dùng đã nghỉ hưu. Chú ý thay đổi vai trò, nhịp sống, sức khỏe, tài chính, quan hệ gia đình, cô đơn "
        "và nhu cầu vẫn được tôn trọng như một người tự quyết."
    ),
    "older_adult": (
        "Người dùng là người cao tuổi. Dùng câu rõ ràng, không infantilize, không giả định họ yếu hoặc kém hiểu biết. "
        "Cân nhắc sức khỏe, khả năng tiếp cận công nghệ, gia đình, mất mát và sự độc lập."
    ),
    "other": "Không áp đặt một bối cảnh sống cụ thể; hỏi lại khi thông tin đó thực sự làm thay đổi lời khuyên.",
}

RELATIONSHIP_PROMPTS = {
    "single": "Người dùng đang độc thân hoặc chưa kết hôn; không coi kết hôn là mục tiêu mặc định.",
    "dating": "Người dùng đang hẹn hò; phân biệt kỳ vọng, ranh giới và mức cam kết hiện tại.",
    "married": "Người dùng đã kết hôn; cân nhắc cam kết, tài chính chung, gia đình hai bên và trách nhiệm chung, nhưng không mặc định họ phải chịu đựng một mối quan hệ có hại.",
    "separated": "Người dùng đang ly thân; tránh ép hòa giải hoặc ly hôn, ưu tiên an toàn, thông tin và quyền tự quyết.",
    "divorced": "Người dùng đã ly hôn; không xem đó là thất bại mặc định và chú ý các trách nhiệm còn tiếp diễn nếu có.",
    "widowed": "Người dùng góa; nói về mất mát cẩn trọng, không thúc ép 'bước tiếp' theo một thời hạn giả định.",
    "prefer_not_say": "Không suy diễn tình trạng quan hệ của người dùng.",
}

CHILDREN_PROMPTS = {
    "none": "Không mặc định người dùng muốn hoặc phải có con.",
    "expecting": "Người dùng đang chuẩn bị có con; cân nhắc thay đổi sức khỏe, tài chính, vai trò và quan hệ.",
    "young_children": "Người dùng có con nhỏ; cân nhắc thiếu ngủ, thời gian hạn chế, chi phí và trách nhiệm chăm sóc.",
    "teen_children": "Người dùng có con tuổi thiếu niên; tôn trọng cả ranh giới của cha mẹ và sự phát triển độc lập của con.",
    "adult_children": "Người dùng có con trưởng thành; không mặc định cha mẹ phải kiểm soát quyết định của con hoặc ngược lại.",
    "prefer_not_say": "Không suy diễn việc người dùng có con hay không.",
}

LIKERT_OPTIONS = [
    {"id": "1", "label": "Rất không giống tôi", "score": 1},
    {"id": "2", "label": "Không giống tôi lắm", "score": 2},
    {"id": "3", "label": "Lúc đúng lúc không", "score": 3},
    {"id": "4", "label": "Khá giống tôi", "score": 4},
    {"id": "5", "label": "Rất giống tôi", "score": 5},
]


def _question(question_id: str, text: str, trait: str, reverse: bool = False) -> dict[str, Any]:
    return {
        "id": question_id,
        "text": text,
        "trait": trait,
        "reverse": reverse,
        "options": LIKERT_OPTIONS,
    }


QUESTIONNAIRE = [
    _question("e1", "Tôi thường là người khuấy động không khí trong một nhóm.", "extraversion"),
    _question("e2", "Ở chỗ đông người, tôi dễ bắt chuyện với nhiều người.", "extraversion"),
    _question("e3", "Tôi thường không nói nhiều.", "extraversion", reverse=True),
    _question("e4", "Tôi hay đứng phía sau hơn là trở thành tâm điểm.", "extraversion", reverse=True),
    _question("a1", "Tôi dễ cảm thông với cảm xúc của người khác.", "agreeableness"),
    _question("a2", "Tôi thường nhận ra người khác đang cảm thấy thế nào.", "agreeableness"),
    _question("a3", "Tôi ít quan tâm đến vấn đề của người khác.", "agreeableness", reverse=True),
    _question("a4", "Tôi không thực sự hứng thú tìm hiểu về người khác.", "agreeableness", reverse=True),
    _question("c1", "Có việc cần làm là tôi thường bắt tay vào sớm.", "conscientiousness"),
    _question("c2", "Tôi thích mọi thứ có trật tự.", "conscientiousness"),
    _question("c3", "Tôi hay quên đặt đồ về đúng chỗ.", "conscientiousness", reverse=True),
    _question("c4", "Tôi dễ để mọi thứ trở nên bừa bộn.", "conscientiousness", reverse=True),
    _question("s1", "Tâm trạng của tôi thay đổi khá thường xuyên.", "emotional_stability", reverse=True),
    _question("s2", "Tôi dễ bị chuyện nhỏ làm bực hoặc buồn.", "emotional_stability", reverse=True),
    _question("s3", "Phần lớn thời gian tôi khá thư giãn.", "emotional_stability"),
    _question("s4", "Tôi hiếm khi thấy buồn vô cớ.", "emotional_stability"),
    _question("o1", "Tôi có trí tưởng tượng phong phú.", "openness"),
    _question("o2", "Tôi khó hiểu những ý tưởng trừu tượng.", "openness", reverse=True),
    _question("o3", "Tôi không hứng thú lắm với những ý tưởng trừu tượng.", "openness", reverse=True),
    _question("o4", "Tôi không giỏi tưởng tượng ra những khả năng khác nhau.", "openness", reverse=True),
]

ARCHETYPES = {
    "balanced": {
        "label": "Cân bằng và thích nghi",
        "description": "Không quá nghiêng về một phía, thường đổi cách ứng xử theo tình huống.",
        "target": {"extraversion": 52, "agreeableness": 58, "conscientiousness": 58, "emotional_stability": 58, "openness": 58},
    },
    "social_spark": {
        "label": "Cởi mở và giàu năng lượng",
        "description": "Dễ kết nối, thích trao đổi và thường mang năng lượng vào cuộc trò chuyện.",
        "target": {"extraversion": 90, "agreeableness": 62, "conscientiousness": 52, "emotional_stability": 62, "openness": 65},
    },
    "warm_connector": {
        "label": "Ấm áp và dễ đồng cảm",
        "description": "Nhạy với cảm xúc của người khác và coi trọng sự hòa hợp trong quan hệ.",
        "target": {"extraversion": 55, "agreeableness": 92, "conscientiousness": 58, "emotional_stability": 48, "openness": 60},
    },
    "steady_builder": {
        "label": "Kỷ luật và đáng tin",
        "description": "Có xu hướng chuẩn bị kỹ, giữ lời và muốn mọi thứ tiến lên rõ ràng.",
        "target": {"extraversion": 45, "agreeableness": 62, "conscientiousness": 92, "emotional_stability": 76, "openness": 48},
    },
    "calm_observer": {
        "label": "Điềm tĩnh và quan sát",
        "description": "Không cần quá nhiều náo nhiệt, thường nhìn kỹ trước khi phản ứng.",
        "target": {"extraversion": 20, "agreeableness": 56, "conscientiousness": 68, "emotional_stability": 90, "openness": 62},
    },
    "imaginative_explorer": {
        "label": "Cởi mở và nhiều ý tưởng",
        "description": "Thích khám phá khả năng mới, liên tưởng rộng và nhìn vấn đề từ nhiều góc.",
        "target": {"extraversion": 58, "agreeableness": 58, "conscientiousness": 48, "emotional_stability": 58, "openness": 94},
    },
    "quiet_depth": {
        "label": "Kín đáo và suy nghĩ sâu",
        "description": "Ít phô bày nhưng thường để ý nhiều lớp ý nghĩa và chi tiết bên trong.",
        "target": {"extraversion": 18, "agreeableness": 68, "conscientiousness": 60, "emotional_stability": 52, "openness": 88},
    },
    "independent_realist": {
        "label": "Độc lập và thực tế",
        "description": "Không dễ bị cuốn theo số đông, thích tự kiểm tra và nói chuyện thẳng vào việc.",
        "target": {"extraversion": 48, "agreeableness": 28, "conscientiousness": 72, "emotional_stability": 82, "openness": 48},
    },
    "sensitive_thinker": {
        "label": "Nhạy cảm và suy nghĩ nhiều",
        "description": "Cảm nhận mạnh, để ý sắc thái và thường nghiền ngẫm chuyện đã xảy ra.",
        "target": {"extraversion": 35, "agreeableness": 82, "conscientiousness": 48, "emotional_stability": 20, "openness": 72},
    },
    "free_spirit": {
        "label": "Linh hoạt và tự do",
        "description": "Thích trải nghiệm, không quá chuộng khuôn mẫu và dễ đổi hướng khi thấy điều thú vị.",
        "target": {"extraversion": 72, "agreeableness": 52, "conscientiousness": 22, "emotional_stability": 52, "openness": 88},
    },
}


def profile_schema() -> dict[str, Any]:
    return {
        "options": OPTION_LABELS,
        "questionnaire": QUESTIONNAIRE,
        "traits": list(TRAITS),
        "archetypes": {
            key: {"label": value["label"], "description": value["description"]}
            for key, value in ARCHETYPES.items()
        },
        "questionnaire_version": 2,
    }


def default_profile() -> dict[str, Any]:
    traits = {trait: 50 for trait in TRAITS}
    communication = communication_from_traits(traits)
    return {
        "gender": "prefer_not_say",
        "gender_note": "",
        "age_group": "prefer_not_say",
        "life_stage": "other",
        "relationship_status": "prefer_not_say",
        "children_status": "prefer_not_say",
        "living_context": "prefer_not_say",
        "quiz_answers": {},
        "quiz_version": 2,
        "personality_traits": traits,
        "communication": communication,
        "archetype": "balanced",
        "archetype_label": ARCHETYPES["balanced"]["label"],
        "archetype_description": ARCHETYPES["balanced"]["description"],
    }


def normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    profile = default_profile()
    for field in OPTION_LABELS:
        value = str(payload.get(field, profile[field])).strip()
        if value not in OPTION_LABELS[field]:
            raise ValueError(f"Giá trị {field} không hợp lệ.")
        profile[field] = value

    gender_note = str(payload.get("gender_note", "")).strip()[:80]
    profile["gender_note"] = gender_note if profile["gender"] == "self_described" else ""

    raw_answers = payload.get("quiz_answers", {})
    if not isinstance(raw_answers, dict):
        raise ValueError("Câu trả lời trắc nghiệm không hợp lệ.")

    valid_questions = {question["id"]: question for question in QUESTIONNAIRE}
    answers: dict[str, str] = {}
    for question_id, question in valid_questions.items():
        answer = str(raw_answers.get(question_id, "")).strip()
        if not answer:
            continue
        option_ids = {option["id"] for option in question["options"]}
        if answer not in option_ids:
            raise ValueError(f"Câu trả lời {question_id} không hợp lệ.")
        answers[question_id] = answer
    # Unknown keys from V5 are ignored so existing profiles continue to load.
    profile["quiz_answers"] = answers
    profile["quiz_version"] = 2

    supplied_traits = payload.get("personality_traits")
    supplied_communication = payload.get("communication")

    if answers:
        traits = score_personality(answers)
        communication = communication_from_traits(traits)
    elif isinstance(supplied_traits, dict):
        traits = {trait: _clamp_score(supplied_traits.get(trait, 50)) for trait in TRAITS}
        communication = communication_from_traits(traits)
    elif isinstance(supplied_communication, dict):
        # Preserve V5 personalization until the user retakes the new questionnaire.
        traits = profile["personality_traits"]
        communication = {
            dimension: _clamp_score(supplied_communication.get(dimension, 50))
            for dimension in COMMUNICATION_DIMENSIONS
        }
    else:
        traits = profile["personality_traits"]
        communication = profile["communication"]

    profile["personality_traits"] = traits
    profile["communication"] = communication
    archetype = derive_archetype(traits)
    profile["archetype"] = archetype
    profile["archetype_label"] = ARCHETYPES[archetype]["label"]
    profile["archetype_description"] = ARCHETYPES[archetype]["description"]
    return profile


def score_personality(answers: dict[str, str]) -> dict[str, int]:
    values: dict[str, list[float]] = {trait: [] for trait in TRAITS}
    for question in QUESTIONNAIRE:
        answer_id = answers.get(question["id"])
        if not answer_id:
            continue
        selected = next((option for option in question["options"] if option["id"] == answer_id), None)
        if not selected:
            continue
        raw = float(selected["score"])
        scored = 6.0 - raw if question.get("reverse") else raw
        values[question["trait"]].append(scored)

    result: dict[str, int] = {}
    for trait, scores in values.items():
        if not scores:
            result[trait] = 50
            continue
        average = sum(scores) / len(scores)
        result[trait] = _clamp_score((average - 1.0) / 4.0 * 100.0)
    return result


def communication_from_traits(traits: dict[str, int]) -> dict[str, int]:
    e = float(traits.get("extraversion", 50)) - 50
    a = float(traits.get("agreeableness", 50)) - 50
    c = float(traits.get("conscientiousness", 50)) - 50
    s = float(traits.get("emotional_stability", 50)) - 50
    o = float(traits.get("openness", 50)) - 50
    return {
        "directness": _clamp_score(50 + 0.18 * e - 0.22 * a + 0.18 * s),
        "emotional_support": _clamp_score(52 + 0.38 * a - 0.22 * s),
        "challenge_level": _clamp_score(50 - 0.28 * a + 0.25 * s + 0.10 * c),
        "detail_level": _clamp_score(50 + 0.35 * o + 0.15 * c - 0.10 * e),
        "humor_level": _clamp_score(44 + 0.30 * e + 0.18 * o),
        "action_orientation": _clamp_score(50 + 0.35 * c + 0.18 * e + 0.10 * s),
    }


def derive_archetype(traits: dict[str, int]) -> str:
    best_key = "balanced"
    best_distance = math.inf
    for key, archetype in ARCHETYPES.items():
        target = archetype["target"]
        distance = sum(
            (float(traits.get(trait, 50)) - float(target[trait])) ** 2
            for trait in TRAITS
        )
        if distance < best_distance:
            best_distance = distance
            best_key = key
    return best_key


def build_profile_prompt(profile: dict[str, Any] | None) -> str:
    normalized = normalize_profile(profile or {})
    communication = normalized["communication"]
    traits = normalized["personality_traits"]
    labels = {field: OPTION_LABELS[field][normalized[field]] for field in OPTION_LABELS}
    gender_text = labels["gender"]
    if normalized["gender"] == "self_described" and normalized.get("gender_note"):
        gender_text = f"Tự mô tả: {normalized['gender_note']}"

    tuning = _communication_tuning(communication)
    trait_tuning = _personality_tuning(traits)
    minor_rule = ""
    if normalized["age_group"] == "under_18" or normalized["life_stage"] == "school_student":
        minor_rule = (
            "\n- Đây có thể là người chưa thành niên: không tình dục hóa, không nhập vai tình cảm phụ thuộc, "
            "không khuyên giữ bí mật với người lớn đáng tin, không xin địa chỉ hoặc thông tin liên lạc. Với bạo lực, "
            "tự hại, lạm dụng hoặc nguy hiểm, ưu tiên tìm người lớn đáng tin và hỗ trợ khẩn cấp tại địa phương."
        )

    return f"""
HỒ SƠ BỐI CẢNH CỦA NGƯỜI DÙNG
- Độ tuổi: {labels['age_group']}
- Giai đoạn cuộc sống: {labels['life_stage']}
- Giới tính tự khai: {gender_text}
- Tình trạng quan hệ: {labels['relationship_status']}
- Con cái: {labels['children_status']}
- Hoàn cảnh sống: {labels['living_context']}
- Nét tính cách nổi bật: {normalized['archetype_label']} — {normalized['archetype_description']}
- Hướng ngoại: {traits['extraversion']}/100
- Dễ đồng cảm: {traits['agreeableness']}/100
- Kỷ luật: {traits['conscientiousness']}/100
- Điềm tĩnh cảm xúc: {traits['emotional_stability']}/100
- Cởi mở với ý tưởng: {traits['openness']}/100

KHUYNH HƯỚNG TÍNH CÁCH CÓ THỂ LIÊN QUAN
{trait_tuning}

CÁCH TINH CHỈNH NHỊP TRẢ LỜI
{tuning}

BỐI CẢNH GIAI ĐOẠN SỐNG
{LIFE_STAGE_PROMPTS[normalized['life_stage']]}

BỐI CẢNH QUAN HỆ
{RELATIONSHIP_PROMPTS[normalized['relationship_status']]}

BỐI CẢNH CON CÁI
{CHILDREN_PROMPTS[normalized['children_status']]}

QUY TẮC CHỐNG RẬP KHUÔN
- Điểm tính cách là khuynh hướng từ bảng hỏi ngắn, không phải chẩn đoán và không phải sự thật tuyệt đối.
- Giới tính, tuổi, hôn nhân và nghề nghiệp chỉ là bối cảnh, không phải bằng chứng về tính cách.
- Không nói kiểu 'vì bạn là phụ nữ/đàn ông/người già/doanh nhân nên...'.
- Chỉ dùng một thông tin hồ sơ khi nó thật sự liên quan đến tin nhắn hiện tại; không đọc lại hồ sơ cho người dùng.
- Mục đích trò chuyện đang chọn có ưu tiên cao nhất. Nhân vật được chọn quyết định giọng chính. Hồ sơ chỉ tinh chỉnh nhịp, độ dài và mức phản biện.
- Nếu hồ sơ xung đột với điều người dùng nói ngay lúc này, tin nhắn hiện tại quan trọng hơn hồ sơ.{minor_rule}
""".strip()


def _personality_tuning(traits: dict[str, int]) -> str:
    rules: list[str] = []
    if traits["extraversion"] >= 72:
        rules.append("- Có thể giữ nhịp trao đổi nhanh, phản hồi sinh động và chủ động nối ý.")
    elif traits["extraversion"] <= 30:
        rules.append("- Đừng hỏi dồn hoặc ép bộc lộ nhanh; cho khoảng trống và giữ nhịp bình tĩnh.")

    if traits["agreeableness"] >= 72:
        rules.append("- Người dùng dễ để ý cảm xúc và quan hệ; phản biện nên chỉ rõ vấn đề nhưng tránh giọng đối đầu.")
    elif traits["agreeableness"] <= 32:
        rules.append("- Có thể nói thẳng và tranh luận bằng lý do; đừng phủ quá nhiều lớp lời an ủi.")

    if traits["conscientiousness"] >= 72:
        rules.append("- Khi phù hợp, dùng cấu trúc rõ và nối lời khuyên với việc theo dõi tiến độ.")
    elif traits["conscientiousness"] <= 30:
        rules.append("- Tránh kế hoạch cứng hoặc quá nhiều bước; ưu tiên một việc nhỏ, linh hoạt và dễ bắt đầu.")

    if traits["emotional_stability"] >= 72:
        rules.append("- Có thể đi thẳng vào phân tích sớm hơn nếu tin nhắn hiện tại không cho thấy họ đang quá tải.")
    elif traits["emotional_stability"] <= 30:
        rules.append("- Khi họ đang căng, hạ nhịp trước rồi mới phản biện; tránh làm mọi khả năng xấu nghe như chắc chắn.")

    if traits["openness"] >= 72:
        rules.append("- Có thể dùng góc nhìn mới, ẩn dụ nhẹ hoặc nhiều khả năng khác nhau khi chúng giúp nhìn rõ vấn đề.")
    elif traits["openness"] <= 30:
        rules.append("- Ưu tiên ví dụ cụ thể, ngôn ngữ trực tiếp và điều có thể kiểm chứng trong đời thật.")

    return "\n".join(rules) or "- Không cần điều chỉnh mạnh theo một nét tính cách riêng."


def _communication_tuning(communication: dict[str, int]) -> str:
    rules: list[str] = []
    if communication["directness"] >= 72:
        rules.append("- Đi vào ý chính sớm, không bọc quá nhiều lớp lời an ủi.")
    elif communication["directness"] <= 35:
        rules.append("- Nói mềm, tránh câu phán xét dứt khoát khi chưa đủ dữ kiện.")
    else:
        rules.append("- Nói rõ nhưng giữ giọng bình thường, không quá mềm cũng không quá gắt.")

    if communication["emotional_support"] >= 72:
        rules.append("- Trước khi phản biện, cho thấy đã bắt đúng điều đang làm họ nặng lòng bằng một câu cụ thể.")
    elif communication["emotional_support"] <= 35:
        rules.append("- Không kéo dài phần an ủi; ưu tiên nội dung và quan điểm.")

    if communication["challenge_level"] >= 72:
        rules.append("- Được phép chỉ thẳng suy diễn, mâu thuẫn hoặc trách nhiệm mà họ đang né.")
    elif communication["challenge_level"] <= 35:
        rules.append("- Phản biện bằng câu hỏi hoặc gợi ý, không dồn người dùng vào thế tự vệ.")

    if communication["detail_level"] >= 72:
        rules.append("- Có thể phân tích thêm nguyên nhân và hậu quả, nhưng vẫn giữ đoạn ngắn.")
    elif communication["detail_level"] <= 30:
        rules.append("- Trả lời rất gọn; một đến ba ý là đủ trừ khi người dùng yêu cầu sâu hơn.")

    if communication["humor_level"] >= 72:
        rules.append("- Có thể dùng một nét hài hước tự nhiên khi tình huống không nghiêm trọng.")
    elif communication["humor_level"] <= 20:
        rules.append("- Hạn chế đùa; giữ giọng chân thành và thẳng.")

    if communication["action_orientation"] >= 72:
        rules.append("- Khi mode cho phép, chốt một bước nhỏ cụ thể và thời điểm làm.")
    elif communication["action_orientation"] <= 30:
        rules.append("- Không thúc quyết định sớm; giúp họ nhìn rõ trước khi hành động.")
    return "\n".join(rules)


def _clamp_score(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = 50
    return max(0, min(100, number))
