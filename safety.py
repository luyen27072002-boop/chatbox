from __future__ import annotations

import re

URGENT_PATTERNS = [
    r"\bmu[oố]n ch[eế]t\b",
    r"\bt[ựu] t[ửu]\b",
    r"\bkh[oô]ng mu[oố]n s[oố]ng\b",
    r"\bk[eế]t th[uú]c cu[oộ]c [đd][oờ]i\b",
    r"\bt[ựu] l[aà]m h[aạ]i\b",
    r"\bnh[aả]y l[aầ]u\b",
    r"\bu[oố]ng thu[oố]c.*ch[eế]t\b",
]


def urgent_fallback_detected(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in URGENT_PATTERNS)


def urgent_support_message(pronoun_style: str, language: str = "vi") -> str:
    """Trả phản hồi an toàn mà không cần gọi model.

    `language` có giá trị mặc định để tương thích với code cũ, đồng thời khớp
    với app.py V20 đang truyền cả kiểu xưng hô và ngôn ngữ.
    """
    if language == "en":
        return (
            "I'm taking what you just said seriously. Right now, please don't stay alone and don't "
            "do anything that could hurt you. Move away from anything you could use to harm yourself, "
            "contact someone you trust, and say clearly: ‘I don't feel safe right now. Can you stay with me?’\n\n"
            "If the danger is immediate, call your local emergency service or go to the nearest emergency "
            "department now. I can stay with you here and help you focus on the next safe step, but I can't "
            "replace direct help. Are you alone right now, or is someone nearby?"
        )

    if language == "zh-Hans":
        return (
            "我会认真对待你刚才说的话。现在先不要独处，也不要做任何可能伤害自己的事。请把可能造成伤害的物品放远，"
            "联系一位你信任的人，并直接告诉对方：‘我现在觉得自己不安全，你能陪我一会儿吗？’\n\n"
            "如果危险就在眼前，请立刻联系当地紧急服务或前往最近的急诊。我可以继续陪你梳理下一步，但不能代替现场帮助。"
            "你现在是一个人吗，还是附近有人？"
        )

    if language == "zh-Hant":
        return (
            "我會認真看待你剛才說的話。現在先不要獨處，也不要做任何可能傷害自己的事。請把可能造成傷害的物品放遠，"
            "聯絡一位你信任的人，並直接告訴對方：『我現在覺得自己不安全，你能陪我一下嗎？』\n\n"
            "如果危險就在眼前，請立刻聯絡當地緊急服務或前往最近的急診。我可以繼續陪你整理下一步，但不能取代現場協助。"
            "你現在是一個人嗎，還是附近有人？"
        )

    if pronoun_style == "tao_may":
        return (
            "Tao đang coi điều mày vừa nói là nghiêm trọng. Ngay lúc này, đừng ở một mình và đừng "
            "làm gì có thể khiến mày bị thương. Hãy đặt xa những thứ có thể gây hại, gọi hoặc đi tới "
            "một người mày tin và nói thẳng: ‘Tao đang không an toàn, ở với tao một lúc được không?’\n\n"
            "Nếu nguy cơ đang ở ngay trước mắt, hãy gọi dịch vụ khẩn cấp tại nơi mày đang ở hoặc đi "
            "thẳng tới khoa cấp cứu gần nhất. Tao có thể tiếp tục ở đây để giúp mày tập trung vào bước "
            "an toàn tiếp theo, nhưng tao không thay thế được sự hỗ trợ trực tiếp. Mày đang ở một mình "
            "hay đang có ai ở gần?"
        )

    return (
        "Mình đang coi điều bạn vừa nói là nghiêm trọng. Ngay lúc này, đừng ở một mình và đừng làm "
        "gì có thể khiến bạn bị thương. Hãy đặt xa những thứ có thể gây hại, gọi hoặc đi tới một người "
        "bạn tin và nói thẳng: ‘Mình đang không an toàn, ở với mình một lúc được không?’\n\n"
        "Nếu nguy cơ đang ở ngay trước mắt, hãy gọi dịch vụ khẩn cấp tại nơi bạn đang ở hoặc đi thẳng "
        "tới khoa cấp cứu gần nhất. Mình có thể tiếp tục ở đây để giúp bạn tập trung vào bước an toàn "
        "tiếp theo, nhưng mình không thay thế được sự hỗ trợ trực tiếp. Bạn đang ở một mình hay đang "
        "có ai ở gần?"
    )
