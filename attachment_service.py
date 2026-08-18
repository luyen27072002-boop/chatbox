from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import mimetypes
import os
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from db import create_attachment, delete_pending_attachment, update_attachment_openai_file_id
from storage_backend import storage_from_env


class AttachmentError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_attachment", status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/octet-stream"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".json": {"application/json", "text/json", "text/plain", "application/octet-stream"},
    ".py": {"text/x-python", "text/plain", "application/octet-stream"},
    ".js": {"text/javascript", "application/javascript", "text/plain", "application/octet-stream"},
    ".ts": {"text/typescript", "application/typescript", "text/plain", "application/octet-stream"},
    ".html": {"text/html", "text/plain", "application/octet-stream"},
    ".css": {"text/css", "text/plain", "application/octet-stream"},
    ".xml": {"application/xml", "text/xml", "text/plain", "application/octet-stream"},
    ".yaml": {"application/yaml", "text/yaml", "text/plain", "application/octet-stream"},
    ".yml": {"application/yaml", "text/yaml", "text/plain", "application/octet-stream"},
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def public_attachment(metadata: dict[str, Any]) -> dict[str, Any]:
    data = dict(metadata)
    data.pop("local_path", None)
    data.pop("stored_name", None)
    data.pop("openai_file_id", None)
    data.pop("user_id", None)
    return data


@dataclass
class AttachmentService:
    base_dir: Path
    max_file_bytes: int
    max_total_bytes: int
    max_image_bytes: int | None = None
    max_files: int = 10
    storage: Any | None = None

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir).resolve()
        self.max_image_bytes = int(self.max_image_bytes or self.max_file_bytes)
        self.storage = self.storage or storage_from_env(self.base_dir)

    def _size_limit_for(self, ext: str, mime_type: str) -> int:
        if ext in IMAGE_EXTENSIONS or str(mime_type or "").startswith("image/"):
            return int(self.max_image_bytes or self.max_file_bytes)
        return int(self.max_file_bytes)

    def _validate_filename(self, file_storage: FileStorage) -> tuple[str, str, str]:
        original = str(file_storage.filename or "").strip()
        if not original:
            raise AttachmentError("Tệp chưa có tên.")
        safe = secure_filename(original) or "attachment"
        ext = Path(safe).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise AttachmentError(
                f"Định dạng {ext or '(không có đuôi)'} chưa được hỗ trợ.",
                code="unsupported_attachment",
            )
        reported = str(file_storage.mimetype or "").lower().split(";", 1)[0].strip()
        guessed = mimetypes.guess_type(safe)[0] or "application/octet-stream"
        accepted = ALLOWED_EXTENSIONS[ext]
        if reported and reported not in accepted and reported != "application/octet-stream":
            # Browser MIME can vary for text/code; accept text/* for text-oriented extensions.
            if not (ext in {".txt", ".md", ".json", ".py", ".js", ".ts", ".html", ".css", ".xml", ".yaml", ".yml", ".csv"} and reported.startswith("text/")):
                raise AttachmentError("Loại tệp không khớp với phần mở rộng.", code="attachment_mime_mismatch")
        mime_type = reported if reported and reported != "application/octet-stream" else guessed
        return original, ext, mime_type

    def save_uploads(self, user_id: str, files: Iterable[FileStorage]) -> list[dict[str, Any]]:
        file_list = [item for item in files if item and item.filename]
        if not file_list:
            raise AttachmentError("Chưa chọn tệp nào.")
        if len(file_list) > self.max_files:
            raise AttachmentError(
                f"Mỗi tin nhắn tối đa {self.max_files} tệp.",
                code="too_many_attachments",
            )
        staged: list[tuple[FileStorage, str, str, str, bytes]] = []
        total = 0
        for item in file_list:
            original, ext, mime_type = self._validate_filename(item)
            size_limit = self._size_limit_for(ext, mime_type)
            data = item.stream.read(size_limit + 1)
            if len(data) > size_limit:
                limit_mb = max(1, round(size_limit / (1024 * 1024)))
                raise AttachmentError(
                    f"Tệp {original} vượt quá giới hạn {limit_mb} MB.",
                    code="attachment_too_large",
                    status=413,
                )
            total += len(data)
            if total > self.max_total_bytes:
                raise AttachmentError(
                    "Tổng dung lượng tệp vượt quá giới hạn cho một tin nhắn.",
                    code="attachments_total_too_large",
                    status=413,
                )
            staged.append((item, original, ext, mime_type, data))

        created: list[dict[str, Any]] = []
        try:
            for _item, original, ext, mime_type, data in staged:
                stored_name = f"{uuid.uuid4().hex}{ext}"
                key = f"uploads/{user_id}/{stored_name}"
                locator = self.storage.put_bytes(key, data, mime_type)
                metadata = create_attachment(
                    user_id=str(user_id),
                    kind="upload",
                    original_name=original,
                    stored_name=stored_name,
                    mime_type=mime_type,
                    size_bytes=len(data),
                    local_path=locator,
                )
                created.append(metadata)
        except Exception:
            for item in created:
                self.delete_local_attachment(item)
                delete_pending_attachment(str(user_id), str(item["id"]))
            raise
        return created

    def delete_local_attachment(self, metadata: dict[str, Any]) -> None:
        locator = str(metadata.get("local_path") or "")
        if not locator:
            return
        try:
            self.storage.delete(locator)
        except Exception:
            pass

    def read_attachment_bytes(self, metadata: dict[str, Any]) -> bytes:
        locator = str(metadata.get("local_path") or "")
        if not locator or not self.storage.exists(locator):
            raise AttachmentError("Tệp không còn trên máy chủ.", code="attachment_missing", status=410)
        return self.storage.read_bytes(locator)

    def signed_download_url(self, metadata: dict[str, Any], *, as_attachment: bool = True) -> str | None:
        locator = str(metadata.get("local_path") or "")
        if not locator or not self.storage.exists(locator):
            return None
        return self.storage.signed_download_url(
            locator,
            filename=str(metadata.get("original_name") or "download"),
            as_attachment=as_attachment,
        )

    def save_generated_bytes(
        self,
        *,
        user_id: str,
        content: bytes,
        original_name: str,
        mime_type: str,
        kind: str,
        suffix: str,
    ) -> dict[str, Any]:
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        key = f"generated/{user_id}/{stored_name}"
        locator = self.storage.put_bytes(key, content, mime_type)
        return create_attachment(
            user_id=str(user_id),
            kind=kind,
            original_name=original_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size_bytes=len(content),
            local_path=locator,
        )

    def ensure_openai_file_id(self, ai_client: Any, user_id: str, attachment: dict[str, Any]) -> str:
        cached = str(attachment.get("openai_file_id") or "").strip()
        if cached:
            return cached
        locator = str(attachment.get("local_path") or "")
        if not locator or not self.storage.exists(locator):
            raise AttachmentError("Tệp đính kèm không còn trên máy chủ.", code="attachment_missing", status=410)
        suffix = Path(str(attachment.get("original_name") or "")).suffix
        try:
            with self.storage.materialize(locator, suffix=suffix) as path:
                with path.open("rb") as handle:
                    uploaded = ai_client.files.create(file=handle, purpose="user_data")
            file_id = str(getattr(uploaded, "id", "") or "").strip()
            if not file_id:
                raise RuntimeError("OpenAI không trả về file id.")
        except Exception as exc:
            raise AttachmentError(
                "Chưa thể gửi tệp lên dịch vụ AI. Hãy thử lại.",
                code="openai_file_upload_failed",
                status=503,
            ) from exc
        update_attachment_openai_file_id(str(user_id), str(attachment["id"]), file_id)
        attachment["openai_file_id"] = file_id
        return file_id


def is_image_attachment(metadata: dict[str, Any]) -> bool:
    mime = str(metadata.get("mime_type") or "").lower()
    if mime.startswith("image/"):
        return True
    return Path(str(metadata.get("original_name") or "")).suffix.lower() in IMAGE_EXTENSIONS
