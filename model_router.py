from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import unicodedata


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
    folded = folded.replace("đ", "d")
    return " ".join(folded.split())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


@dataclass(frozen=True)
class RoutingDecision:
    tier: str
    model: str
    reasoning_effort: str
    reason: str


@dataclass
class ModelRouter:
    fast_model: str = "gpt-5.6-luna"
    smart_model: str = "gpt-5.6-terra"
    heavy_model: str = "gpt-5.6-sol"
    image_model: str = "gpt-5.6-terra"
    image_heavy_model: str = "gpt-5.6-sol"

    def _attachment_stats(self, attachments: list[dict[str, Any]] | None) -> tuple[int, int, int]:
        items = attachments or []
        total_bytes = sum(int(item.get("size_bytes") or 0) for item in items)
        image_count = sum(
            1 for item in items
            if str(item.get("mime_type") or "").lower().startswith("image/")
        )
        return len(items), total_bytes, image_count

    def route_text(
        self,
        message: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> RoutingDecision:
        text = _fold(message)
        file_count, total_bytes, _image_count = self._attachment_stats(attachments)

        explicit_xhigh = (
            "nghi that ky", "suy nghi that ky", "phan tich sau", "deep reasoning",
            "think deeply", "nghi ca chuc phut", "reasoning max", "suy luan sau",
        )
        explicit_heavy = (
            "nghien cuu", "research", "paper", "luan van", "thuat toan", "algorithm",
            "kien truc", "architecture", "race condition", "deadlock", "debug ca project",
            "doc ca project", "toi uu he thong", "proof", "chung minh", "root cause",
            "phuc tap", "complex", "chuyen sau", "ky thuat kho",
        )
        translation = (
            "dich", "translate", "translation", "phien dich", "bien dich",
        )
        professional = (
            "chuyen nganh", "technical", "ky thuat", "phap ly", "legal", "hop dong",
            "hoc thuat", "academic", "ieee", "bao cao", "report", "ho so", "tai lieu",
            "giup tao giu format", "giu nguyen bo cuc", "giu dinh dang",
        )
        coding = (
            "code", "python", "javascript", "typescript", "c#", "c++", "bug", "debug",
            "api", "database", "sql", "backend", "frontend", "refactor", "test", "loi code",
        )
        analysis = (
            "phan tich", "so sanh", "danh gia", "tom tat file", "doc file", "doc tai lieu",
            "trich xuat", "tong hop", "lap ke hoach", "viet bao cao",
        )

        heavy_score = 0
        smart_score = 0
        reasons: list[str] = []

        if _contains_any(text, explicit_xhigh):
            heavy_score += 4
            reasons.append("explicit-deep-reasoning")
        if _contains_any(text, explicit_heavy):
            heavy_score += 2
            smart_score += 1
            reasons.append("complex-professional-task")
        if _contains_any(text, translation):
            smart_score += 2
            reasons.append("translation")
        if _contains_any(text, professional):
            smart_score += 1
            reasons.append("professional-context")
        if _contains_any(text, coding):
            smart_score += 2
            reasons.append("coding")
        if _contains_any(text, analysis):
            smart_score += 1
            reasons.append("analysis")

        if file_count:
            smart_score += 2
            reasons.append(f"attachments:{file_count}")
        if file_count >= 4:
            heavy_score += 2
            reasons.append("many-attachments")
        if total_bytes >= 12 * 1024 * 1024:
            heavy_score += 1
            reasons.append("large-input")
        if total_bytes >= 25 * 1024 * 1024:
            heavy_score += 1
            reasons.append("very-large-input")

        # Large/specialized translations and large code bases deserve Sol.
        if _contains_any(text, translation) and _contains_any(text, professional) and total_bytes >= 5 * 1024 * 1024:
            heavy_score += 2
            reasons.append("large-specialized-translation")
        if _contains_any(text, coding) and file_count >= 3:
            heavy_score += 2
            reasons.append("multi-file-coding")

        if heavy_score >= 3:
            effort = "xhigh" if _contains_any(text, explicit_xhigh) else "high"
            return RoutingDecision(
                tier="heavy",
                model=self.heavy_model,
                reasoning_effort=effort,
                reason=",".join(reasons) or "heavy-score",
            )
        if smart_score >= 2:
            return RoutingDecision(
                tier="smart",
                model=self.smart_model,
                reasoning_effort="medium",
                reason=",".join(reasons) or "smart-score",
            )
        return RoutingDecision(
            tier="fast",
            model=self.fast_model,
            reasoning_effort="low",
            reason="casual-or-simple",
        )

    def route_image(
        self,
        message: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> RoutingDecision:
        text = _fold(message)
        file_count, _total_bytes, image_count = self._attachment_stats(attachments)

        edit_markers = (
            "chinh", "sua", "xoa", "them", "doi", "thay", "edit", "retouch", "remove",
            "replace", "crop", "background", "nen", "mask",
        )
        precision_markers = (
            "giu nguyen", "chinh xac", "logo", "chu tren anh", "text", "phoi canh",
            "perspective", "anh sang", "lighting", "san pham", "product", "brand",
            "nhan vat giong", "consistent", "khong thay doi", "high fidelity",
        )
        complex_markers = (
            "poster chuyen nghiep", "quang cao", "commercial", "photorealistic", "realistic",
            "nhieu vat the", "multi-object", "composite", "ghep anh",
        )

        heavy_score = 0
        reasons: list[str] = []
        if image_count and _contains_any(text, edit_markers):
            heavy_score += 2
            reasons.append("image-edit")
        if _contains_any(text, precision_markers):
            heavy_score += 2
            reasons.append("precision")
        if _contains_any(text, complex_markers):
            heavy_score += 1
            reasons.append("complex-image")
        if image_count >= 2 or file_count >= 3:
            heavy_score += 1
            reasons.append("multiple-references")

        if heavy_score >= 3:
            return RoutingDecision(
                tier="image-heavy",
                model=self.image_heavy_model,
                reasoning_effort="high",
                reason=",".join(reasons) or "complex-image-edit",
            )
        return RoutingDecision(
            tier="image-smart",
            model=self.image_model,
            reasoning_effort="medium",
            reason=",".join(reasons) or "image-generation",
        )
