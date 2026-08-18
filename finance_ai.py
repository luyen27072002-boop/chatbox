from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import re
import unicodedata
from typing import Any


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
    return " ".join(folded.replace("đ", "d").split())


@dataclass
class FinanceIntent:
    action: str = "add"  # add | edit_last | delete_last | query | export | unknown
    kind: str = "expense"
    amount: int | None = None
    category: str | None = None
    occurred_on: str | None = None
    month: str | None = None
    note: str = ""
    vendor: str = ""
    department: str = ""
    project: str = ""
    client: str = ""
    payment_method: str = ""
    currency: str = "VND"
    output_format: str = "xlsx"
    confidence: float = 0.0
    needs_ai: bool = False
    needs_clarification: bool = False
    clarification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("client_entertainment", ("tiep khach", "gap khach", "gap doi tac", "moi khach", "khach hang an", "doi tac an")),
    ("office", ("van phong pham", "muc may in", "giay in", "giay a4", "but ", "but bi", "kep giay", "photo tai lieu")),
    ("transport", ("grab", "taxi", "xang", "gui xe", "parking", "xe buyt", "di lai", "phi cau duong")),
    ("travel", ("cong tac", "khach san", "hotel", "ve may bay", "airbnb", "luu tru")),
    ("equipment", ("thiet bi", "may moc", "laptop", "may tinh", "man hinh", "camera", "cong cu", "dung cu")),
    ("software", ("phan mem", "software", "license", "ban quyen", "cloud", "server", "hosting", "domain")),
    ("telecom", ("internet", "wifi", "dien thoai", "sim ", "vnpt", "viettel", "mobifone")),
    ("rent", ("tien thue", "thue van phong", "thue xuong", "mat bang")),
    ("utilities", ("tien dien", "tien nuoc", "dien nuoc", "hoa don dien", "hoa don nuoc")),
    ("marketing", ("quang cao", "marketing", "facebook ads", "google ads", "in banner", "in poster")),
    ("shipping", ("van chuyen", "giao hang", "ship hang", "shipper", "buu dien", "logistics")),
    ("maintenance", ("bao tri", "bao duong", "sua may", "sua chua")),
    ("payroll", ("tra luong", "tien luong nhan vien", "luong nhan vien")),
    ("tax", ("thue gtgt", "thue vat", "nop thue", "le phi", "phi nha nuoc")),
    ("training", ("dao tao", "khoa hoc", "hoc phi", "training")),
    ("health", ("thuoc", "benh vien", "kham benh", "y te", "bao hiem suc khoe")),
    ("food", ("tien an", "an com", "com ", "do an", "cafe", "ca phe", "bua sang", "bua trua", "bua toi", "nha hang")),
    ("shopping", ("mua sam", "shopee", "lazada")),
    ("bills", ("hoa don", "phi dich vu")),
)

INCOME_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("salary", ("luong", "salary")),
    ("bonus", ("thuong", "bonus")),
    ("freelance", ("freelance", "tien cong", "phi dich vu nhan")),
    ("sale", ("tien khach", "khach thanh toan", "ban hang", "doanh thu", "thu tien hang")),
)

DEPARTMENT_RULES = {
    "ke toan": "Kế toán",
    "ky thuat": "Kỹ thuật",
    "san xuat": "Sản xuất",
    "kinh doanh": "Kinh doanh",
    "sales": "Sales",
    "marketing": "Marketing",
    "nhan su": "Nhân sự",
    "hanh chinh": "Hành chính",
    "mua hang": "Mua hàng",
    "kho": "Kho",
}


def _parse_amount(text: str) -> int | None:
    folded = fold_text(text)
    folded = re.sub(r"(?<!\d)\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?!\d)", " ", folded)
    # 2tr4 / 2tr45 / 2 tr 450
    match = re.search(r"(?<!\d)(\d{1,9})\s*(?:tr|trieu)\s*(\d{1,3})?(?!\d)", folded)
    if match:
        whole = int(match.group(1)) * 1_000_000
        tail = match.group(2) or ""
        if tail:
            whole += int(tail) * (10 ** max(0, 6 - len(tail)))
        return whole
    match = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan)(?!\w)", folded)
    if match:
        return int(round(float(match.group(1).replace(",", ".")) * 1_000))
    match = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:m|million)(?!\w)", folded)
    if match:
        return int(round(float(match.group(1).replace(",", ".")) * 1_000_000))
    # Explicit large raw number, e.g. 100000 or 2,400,000. Avoid dates.
    candidates = re.findall(r"(?<!\d)(\d[\d.,]{3,})(?!\d)", folded)
    for raw in candidates:
        if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", raw):
            continue
        digits = re.sub(r"\D", "", raw)
        if digits and int(digits) >= 1_000:
            return int(digits)
    return None


def _parse_date(text: str, today: date) -> tuple[str | None, bool]:
    folded = fold_text(text)
    explicit = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?!\d)", folded)
    if explicit:
        day, month, year = map(int, explicit.groups())
        if year < 100:
            year += 2000
        try:
            return date(year, month, day).isoformat(), False
        except ValueError:
            return None, True
    iso = re.search(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)", folded)
    if iso:
        year, month, day = map(int, iso.groups())
        try:
            return date(year, month, day).isoformat(), False
        except ValueError:
            return None, True
    # dd/mm or dd-mm without a year: use the current calendar year.
    # Example on 2026-08-18: 21/09 -> 2026-09-21.
    partial = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})(?![/-]\d)(?!\d)", folded)
    if partial:
        day, month = map(int, partial.groups())
        try:
            return date(today.year, month, day).isoformat(), False
        except ValueError:
            return None, True
    if "hom nay" in folded or "today" in folded:
        return today.isoformat(), False
    if "hom qua" in folded or "yesterday" in folded:
        return (today - timedelta(days=1)).isoformat(), False
    if "hom kia" in folded:
        return (today - timedelta(days=2)).isoformat(), False
    if "hom truoc" in folded or "may hom truoc" in folded:
        return None, True
    return today.isoformat(), False


def parse_month(text: str, today: date) -> str | None:
    folded = fold_text(text)
    if "thang nay" in folded or "this month" in folded:
        return today.strftime("%Y-%m")
    if "thang truoc" in folded or "last month" in folded:
        first = today.replace(day=1)
        previous = first - timedelta(days=1)
        return previous.strftime("%Y-%m")
    match = re.search(r"thang\s+(\d{1,2})(?:[/-](\d{4}))?", folded)
    if match:
        month = int(match.group(1))
        year = int(match.group(2) or today.year)
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
    return None


def _category(text: str, *, income: bool = False) -> tuple[str | None, float]:
    folded = fold_text(text)
    rules = INCOME_CATEGORY_RULES if income else CATEGORY_RULES
    for category, markers in rules:
        if any(marker in folded for marker in markers):
            return category, 0.99
    return None, 0.0


def _department(text: str) -> str:
    folded = fold_text(text)
    for marker, label in DEPARTMENT_RULES.items():
        if f"phong {marker}" in folded or f"bo phan {marker}" in folded or marker in folded:
            return label
    return ""


def _payment_method(text: str) -> str:
    folded = fold_text(text)
    if "chuyen khoan" in folded or re.search(r"\bck\b", folded):
        return "bank_transfer"
    if "tien mat" in folded or "cash" in folded:
        return "cash"
    if "the tin dung" in folded or "credit card" in folded:
        return "credit_card"
    return ""


def _detect_action(text: str) -> str:
    folded = fold_text(text)
    if any(x in folded for x in ("xoa khoan vua", "xoa giao dich vua", "xoa cai vua", "delete last")):
        return "delete_last"
    if any(x in folded for x in ("doi khoan vua", "sua khoan vua", "cap nhat khoan vua", "edit last")):
        return "edit_last"
    if any(x in folded for x in ("xuat", "export", "tai excel", "download excel")):
        return "export"
    if any(x in folded for x in ("bao nhieu", "tong chi", "tong thu", "da chi", "chi bao nhieu", "thu bao nhieu", "how much")):
        return "query"
    return "add"


def parse_finance_message(message: str, *, today: date | None = None) -> FinanceIntent:
    today = today or date.today()
    raw = " ".join(str(message or "").split()).strip()
    folded = fold_text(raw)
    action = _detect_action(raw)
    month = parse_month(raw, today)
    income = any(marker in folded for marker in ("thu vao", "tong thu", "thu bao nhieu", "nhan tien", "nhan ", "doanh thu", "luong", "khach thanh toan", "tien khach"))
    kind = "income" if income else "expense"
    category, cat_conf = _category(raw, income=income)

    if action in {"query", "export"}:
        # Generic month summary/export should include both income and expense.
        # Only narrow to one side when the user explicitly asks for it.
        both_sides = any(marker in folded for marker in ("thu chi", "thu/chi", "tong thu chi"))
        explicit_income = any(marker in folded for marker in ("chi thu", "tong thu", "thu vao", "doanh thu", "chi rieng thu", "chi moi thu"))
        explicit_expense = any(marker in folded for marker in ("tong chi", "chi bao nhieu", "chi rieng chi", "chi moi chi"))
        if action == "export" and not explicit_income and not explicit_expense:
            report_kind = ""
        elif both_sides:
            report_kind = ""
        elif explicit_income and not explicit_expense:
            report_kind = "income"
        elif explicit_expense and not explicit_income:
            report_kind = "expense"
        else:
            report_kind = kind
        return FinanceIntent(
            action=action,
            kind=report_kind,
            category=category,
            month=month,
            output_format="xlsx",
            note=raw,
            confidence=1.0,
        )

    if action == "delete_last":
        return FinanceIntent(action=action, note=raw, confidence=1.0)

    amount = _parse_amount(raw)
    occurred_on, ambiguous_date = _parse_date(raw, today)
    result = FinanceIntent(
        action=action,
        kind=kind,
        amount=amount,
        category=category,
        occurred_on=occurred_on,
        note=raw[:500],
        department=_department(raw),
        payment_method=_payment_method(raw),
        confidence=cat_conf,
    )
    if amount is None:
        result.needs_clarification = True
        result.clarification = "Khoản này bao nhiêu tiền?"
        return result
    if ambiguous_date:
        result.needs_clarification = True
        result.clarification = "Khoản này chính xác là ngày nào?"
        return result
    if category is None:
        result.needs_ai = True
        result.confidence = 0.0
    return result
