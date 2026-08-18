from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import unicodedata


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
    folded = folded.replace("đ", "d")
    return " ".join(folded.split())


def _attachment_ext(item: dict[str, Any]) -> str:
    return Path(str(item.get("original_name") or "")).suffix.lower()


def _is_image(item: dict[str, Any]) -> bool:
    mime = str(item.get("mime_type") or "").lower()
    return mime.startswith("image/") or _attachment_ext(item) in {".png", ".jpg", ".jpeg", ".webp"}


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase = str(phrase or "").strip()
    if not phrase:
        return False
    # Space-normalized text: boundaries prevent e.g. "hinh" matching "chinh".
    return re.search(r"(?<![\w])" + re.escape(phrase) + r"(?![\w])", text) is not None


@dataclass(frozen=True)
class ActionDecision:
    kind: str  # text | image | artifact
    format: str | None = None
    scope: str = "reply"
    reason: str = "text-default"


@dataclass(frozen=True)
class ActionResolution:
    decision: ActionDecision
    effective_message: str
    attachments: list[dict[str, Any]]
    continued: bool = False
    original_message: str = ""


CONTINUATION_MARKERS = (
    "lam lai", "gui lai", "tra lai", "sua tiep", "chinh tiep", "lam tiep",
    "doi sang", "doi thanh", "them vao", "bo di", "xoa di", "dep hon",
    "ok lam", "oke lam", "lam di", "gui t", "gui tao", "gui minh",
    "redo", "do it again", "send it again", "edit it", "change it to",
)
STATUS_ONLY_MARKERS = (
    "dang lam chua", "dang lam khong", "lam toi dau", "xong chua", "con dang lam",
    "are you working", "is it done", "still working",
)


def is_background_status_question(message: str) -> bool:
    text = _fold(message)
    return bool(text) and any(marker in text for marker in STATUS_ONLY_MARKERS)


def _looks_like_continuation(message: str) -> bool:
    text = _fold(message)
    if not text or any(marker in text for marker in STATUS_ONLY_MARKERS):
        return False
    if any(marker in text for marker in CONTINUATION_MARKERS):
        return True
    # Very short imperative follow-ups often omit the object because the previous task supplies it.
    imperative = ("sua", "chinh", "doi", "them", "xoa", "lam", "gui", "ve", "render")
    return len(text) <= 72 and any(text.startswith(word + " ") for word in imperative)


def resolve_action(
    message: str,
    attachments: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> ActionResolution:
    current_attachments = list(attachments or [])
    current = infer_action(message, current_attachments)
    if current.kind != "text" or current_attachments:
        return ActionResolution(current, str(message or ""), current_attachments, False, str(message or ""))
    if not _looks_like_continuation(message):
        return ActionResolution(current, str(message or ""), current_attachments, False, str(message or ""))

    rows = list(history or [])
    for row in reversed(rows):
        if str(row.get("role") or "") != "user":
            continue
        prior_message = str(row.get("content") or "").strip()
        prior_attachments = list(row.get("attachments") or [])
        prior = infer_action(prior_message, prior_attachments)
        if prior.kind not in {"artifact", "image"}:
            continue
        effective = (
            "TÁC VỤ GỐC ĐÃ ĐƯỢC NGƯỜI DÙNG YÊU CẦU TRƯỚC ĐÓ:\n"
            f"{prior_message}\n\n"
            "YÊU CẦU TIẾP NỐI HIỆN TẠI:\n"
            f"{str(message or '').strip()}"
        )
        return ActionResolution(
            decision=prior,
            effective_message=effective,
            attachments=prior_attachments,
            continued=True,
            original_message=prior_message,
        )
    return ActionResolution(current, str(message or ""), current_attachments, False, str(message or ""))


FORMAT_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("docx", ("word", "docx", "file word")),
    ("pdf", ("pdf",)),
    ("xlsx", ("excel", "xlsx", "spreadsheet", "bang tinh")),
    ("pptx", ("powerpoint", "pptx", "ppt", "slide deck", "slide")),
    ("csv", ("csv",)),
    ("json", ("json",)),
    ("md", ("markdown", "md")),
    ("py", ("python file", ".py")),
    ("js", ("javascript file", ".js")),
    ("ts", ("typescript file", ".ts")),
    ("html", ("html",)),
    ("css", ("css",)),
    ("txt", ("txt", "text file", "file text")),
)

EXTENSION_TO_FORMAT = {
    ".docx": "docx",
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
    ".pptx": "pptx",
    ".txt": "txt",
    ".md": "md",
    ".json": "json",
    ".py": "py",
    ".js": "js",
    ".ts": "ts",
    ".html": "html",
    ".css": "css",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yml",
}

IMAGE_NOUNS = (
    "hinh", "hinh anh", "minh hoa", "poster", "banner", "avatar",
    "thumbnail", "cover", "wallpaper", "photo", "image", "picture",
)
IMAGE_CREATE_MARKERS = (
    "tao anh", "tao hinh", "ve ", "ve cho", "thiet ke anh", "thiet ke poster",
    "render ", "generate image", "create image", "make an image", "draw ",
    "illustrate", "show me an image", "cho tao hinh", "cho minh hinh", "lam hinh",
)
IMAGE_EDIT_MARKERS = (
    "chinh anh", "sua anh", "edit image", "retouch", "xoa", "remove", "them",
    "add", "doi nen", "thay nen", "background", "crop", "replace",
)

FILE_OUTPUT_MARKERS = (
    "tao file", "lam file", "xuat file", "gui lai file", "tra lai file", "save file",
    "create file", "make a file", "export file", "send back the file", "download file",
    "luu thanh", "xuat thanh", "lam thanh", "tao ban", "gui lai", "tra lai",
)
FILE_TRANSFORM_MARKERS = (
    "dich", "translate", "sua", "chinh", "viet lai", "rewrite", "cap nhat", "update",
    "dien", "fill", "format", "dinh dang", "chuyen", "convert", "thay", "replace",
    "them", "bo sung", "xoa", "remove", "rut gon", "lam song ngu", "song ngu",
)
CONVERSATION_MARKERS = (
    "toan bo cuoc tro chuyen", "cuoc tro chuyen nay", "doan chat nay", "toan bo chat",
    "chat nay", "whole conversation", "entire conversation", "whole chat", "entire chat",
)


def _explicit_format(text: str) -> str | None:
    for fmt, markers in FORMAT_MARKERS:
        if any(marker in text for marker in markers):
            return fmt
    return None


def _source_format(attachments: list[dict[str, Any]] | None) -> str | None:
    non_images = [item for item in (attachments or []) if not _is_image(item)]
    if not non_images:
        return None
    formats = [EXTENSION_TO_FORMAT.get(_attachment_ext(item)) for item in non_images]
    formats = [fmt for fmt in formats if fmt]
    if not formats:
        return None
    # If all source files share a format, preserve it by default. Otherwise use DOCX as a safe document container.
    if len(set(formats)) == 1:
        return formats[0]
    return "docx"


def infer_action(message: str, attachments: list[dict[str, Any]] | None = None) -> ActionDecision:
    raw_text = " ".join(str(message or "").lower().split())
    text = _fold(message)
    items = attachments or []
    has_image = any(_is_image(item) for item in items)
    source_fmt = _source_format(items)

    # Image creation/editing takes precedence over file export because the result itself is an image.
    raw_image_markers = ("tạo ảnh", "cho tao ảnh", "cho mình ảnh", "làm ảnh", "sửa ảnh", "chỉnh ảnh", "ảnh minh họa")
    if any(marker in raw_text for marker in raw_image_markers) or any(marker in text for marker in IMAGE_CREATE_MARKERS):
        return ActionDecision(kind="image", reason="explicit-image-request")
    if has_image and any(marker in text for marker in IMAGE_EDIT_MARKERS):
        return ActionDecision(kind="image", reason="image-edit")
    ask_verbs = ("cho", "gui", "lam", "tao", "ve", "thiet ke", "render", "generate", "create", "make", "show")
    if any(_contains_phrase(text, noun) for noun in IMAGE_NOUNS) and any(_contains_phrase(text, verb) for verb in ask_verbs):
        return ActionDecision(kind="image", reason="natural-image-request")

    explicit_fmt = _explicit_format(text)
    scope = "conversation" if any(marker in text for marker in CONVERSATION_MARKERS) else "reply"

    # Explicit format + creation/export wording always means a generated artifact.
    if explicit_fmt:
        output_context = (
            "tao", "lam", "xuat", "luu", "gui", "tra", "download", "export", "create", "make", "save",
        )
        if any(marker in text for marker in FILE_OUTPUT_MARKERS) or any(word in text for word in output_context):
            return ActionDecision(kind="artifact", format=explicit_fmt, scope=scope, reason="explicit-output-format")

    # With an attached document/spreadsheet/deck, natural transform + send-back language should preserve source type.
    if source_fmt:
        has_output_marker = any(marker in text for marker in FILE_OUTPUT_MARKERS)
        has_transform = any(marker in text for marker in FILE_TRANSFORM_MARKERS)
        send_back = any(marker in text for marker in ("gui lai", "tra lai", "cho tao file", "cho minh file"))
        # "dịch ... làm file" / "sửa ... gửi lại" / "điền ... rồi gửi lại" etc.
        if has_output_marker or has_transform or send_back:
            return ActionDecision(kind="artifact", format=explicit_fmt or source_fmt, scope=scope, reason="attachment-transform-output")
        # Generic "làm file" with an attachment should still preserve the attachment format.
        if re.search(r"\b(?:lam|tao|xuat)\b.{0,24}\bfile\b", text):
            return ActionDecision(kind="artifact", format=explicit_fmt or source_fmt, scope=scope, reason="generic-file-output")

    return ActionDecision(kind="text", reason="text-default")


def build_artifact_instruction(
    decision: ActionDecision,
    attachments: list[dict[str, Any]] | None,
    message: str,
) -> str:
    if decision.kind != "artifact" or not decision.format:
        return ""
    names = [str(item.get("original_name") or "").strip() for item in (attachments or [])]
    names = [name for name in names if name]
    source_note = ", ".join(names) if names else "không có tệp nguồn"
    folded = _fold(message)
    bilingual = any(marker in folded for marker in ("song ngu", "bilingual", "hai ngon ngu", "2 ngon ngu"))
    translation = any(marker in folded for marker in ("dich", "translate", "translation"))

    lines = [
        "GHI CHÚ KHẢ NĂNG HỆ THỐNG:",
        f"Ứng dụng chủ sẽ tạo và đính kèm tệp .{decision.format} sau khi mày trả lời.",
        "Không được nói rằng mày không thể tạo, xuất, tải xuống hoặc đính kèm file.",
        "Hãy trả ra NỘI DUNG HOÀN CHỈNH cuối cùng để hệ thống đặt vào file, không viết lời xin lỗi hay hướng dẫn người dùng tự copy.",
        f"Tệp nguồn: {source_note}.",
    ]
    if translation:
        lines.append("Nếu đây là dịch thuật, dịch đầy đủ theo yêu cầu và không bỏ sót tiêu đề, mục, số liệu hoặc đoạn văn có nghĩa.")
    if bilingual:
        lines.append(
            "Người dùng yêu cầu bản song ngữ: giữ đủ cả hai ngôn ngữ theo thứ tự song song, rõ ràng và nhất quán; không bỏ sót nội dung của một bên."
        )
    if decision.format == "xlsx":
        lines.append("Nếu dữ liệu phù hợp dạng bảng, ưu tiên trả bảng Markdown sạch để hệ thống đưa vào Excel thành các ô riêng.")
    elif decision.format == "pptx":
        lines.append("Nếu là PowerPoint, chia nội dung thành các slide rõ ràng với tiêu đề và bullet ngắn gọn cho từng slide.")
    return "\n".join(lines)
