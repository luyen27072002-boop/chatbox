from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, Flask, current_app, g, jsonify, redirect, render_template, request, session
from openai import OpenAI

from db import (
    finalize_message_quota,
    get_account,
    get_db,
    get_quota_status,
    refund_message_quota,
    reserve_message_quota,
)

bp = Blueprint("career", __name__)

MAX_TEXT = 8000
MAX_JOB_DESCRIPTION = 18000
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_CACHE_SECONDS = 6 * 60 * 60
REMOTIVE_FETCH_LIMIT = 250

JOOBLE_API_KEY_ENV = "JOOBLE_API_KEY"
JOOBLE_API_BASE = "https://jooble.org/api/{api_key}"
JOOBLE_RESULT_LIMIT = 30
JOOBLE_CACHE_SECONDS = 30 * 60
_jooble_cache_lock = threading.Lock()
_jooble_cache: dict[str, dict[str, Any]] = {}

BRAVE_SEARCH_API_KEY_ENV = "BRAVE_SEARCH_API_KEY"
BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BRAVE_CACHE_SECONDS = 30 * 60
_brave_cache_lock = threading.Lock()
_brave_cache: dict[str, dict[str, Any]] = {}

JOB_SOURCE_DOMAINS = {
    # Vietnam job boards
    "topcv.vn": ("TopCV", "job_board"),
    "vietnamworks.com": ("VietnamWorks", "job_board"),
    "careerviet.vn": ("CareerViet", "job_board"),
    "vieclam24h.vn": ("Việc Làm 24h", "job_board"),
    "jobsgo.vn": ("JobsGO", "job_board"),
    "vn.joboko.com": ("JobOKO", "job_board"),
    "joboko.com": ("JobOKO", "job_board"),
    "careerlink.vn": ("CareerLink", "job_board"),
    "glints.com": ("Glints", "job_board"),
    "vn.indeed.com": ("Indeed Việt Nam", "job_board"),
    "indeed.com": ("Indeed", "job_board"),
    "linkedin.com": ("LinkedIn", "professional_network"),
    "itviec.com": ("ITviec", "job_board"),
    "topdev.vn": ("TopDev", "job_board"),
    "jobstreet.vn": ("JobStreet", "job_board"),

    # Official / public employment services
    "vieclam.gov.vn": ("Sàn giao dịch việc làm quốc gia", "government"),
    "vieclamngoainuoc.dolab.gov.vn": ("DOLAB-JICA", "government"),

    # Recruitment agencies / headhunters
    "manpower.com.vn": ("Manpower Vietnam", "recruiter"),
    "adecco.com": ("Adecco Vietnam", "recruiter"),
    "rgf-hragent.asia": ("RGF HR Agent", "recruiter"),

    # Public ATS / company career systems
    "jobs.lever.co": ("Lever", "ats"),
    "api.lever.co": ("Lever", "ats"),
    "boards.greenhouse.io": ("Greenhouse", "ats"),
    "job-boards.greenhouse.io": ("Greenhouse", "ats"),
    "boards-api.greenhouse.io": ("Greenhouse", "ats"),
    "jobs.ashbyhq.com": ("Ashby", "ats"),
    "jobs.smartrecruiters.com": ("SmartRecruiters", "ats"),

    # Public social/community results - discovery only
    "facebook.com": ("Facebook public", "social"),
    "threads.net": ("Threads public", "social"),
}

BRAVE_SOURCE_GROUPS = {
    "core_job_boards": {
        "label": "Job boards Việt Nam",
        "domains": [
            "topcv.vn",
            "vietnamworks.com",
            "careerviet.vn",
            "vieclam24h.vn",
            "jobsgo.vn",
            "vn.joboko.com",
            "careerlink.vn",
            "glints.com",
            "vn.indeed.com",
            "linkedin.com",
            "itviec.com",
            "topdev.vn",
            "jobstreet.vn",
        ],
    },
    "official_ats_recruiters": {
        "label": "Nguồn chính thức, headhunter & ATS",
        "domains": [
            "vieclam.gov.vn",
            "vieclamngoainuoc.dolab.gov.vn",
            "manpower.com.vn",
            "adecco.com",
            "rgf-hragent.asia",
            "jobs.lever.co",
            "boards.greenhouse.io",
            "job-boards.greenhouse.io",
            "jobs.ashbyhq.com",
            "jobs.smartrecruiters.com",
        ],
    },
    "company_public": {
        "label": "Career pages & bài tuyển dụng công khai",
        "domains": [],
    },
}

_cache_lock = threading.Lock()
_remotive_cache: dict[str, Any] = {"fetched_at": 0.0, "jobs": [], "error": ""}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id() -> str | None:
    value = str(session.get("account_id", "") or "").strip()
    return value or None


def _error(message: str, status: int = 400, code: str = "bad_request"):
    return jsonify({"error": message, "code": code}), status


def _clean_text(value: Any, limit: int = MAX_TEXT) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit]


def _clean_line(value: Any, limit: int = 160) -> str:
    return " ".join(str(value or "").split()).strip()[:limit]


def _safe_url(value: Any) -> str:
    raw = str(value or "").strip()[:1200]
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw


def _json_list(value: Any, *, limit: int = 40) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;\n]", str(value or ""))
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = _clean_line(item, 80)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9+#.]+", " ", text.casefold()).strip()


def _tokens(value: str) -> set[str]:
    stop = {
        "and", "or", "the", "a", "an", "to", "of", "for", "with", "in", "on",
        "va", "hoac", "cua", "cho", "voi", "trong", "la", "mot", "cac", "co",
        "job", "work", "role", "position", "candidate", "team",
    }
    return {x for x in _normalize(value).split() if len(x) >= 2 and x not in stop}


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        data = " ".join(data.split())
        if data:
            self.parts.append(data)


def _strip_html(value: str) -> str:
    parser = _HTMLText()
    try:
        parser.feed(str(value or ""))
        return " ".join(parser.parts)
    except Exception:
        return re.sub(r"<[^>]+>", " ", str(value or ""))


def _profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "desired_role": _clean_line(payload.get("desired_role"), 120),
        "location": _clean_line(payload.get("location"), 120),
        "work_type": _clean_line(payload.get("work_type"), 40),
        "seniority": _clean_line(payload.get("seniority"), 50),
        "skills": _json_list(payload.get("skills"), limit=40),
        "summary": _clean_text(payload.get("summary"), 1800),
        "experience": _clean_text(payload.get("experience"), 6000),
        "education": _clean_text(payload.get("education"), 2400),
        "projects": _clean_text(payload.get("projects"), 4000),
        "languages": _clean_text(payload.get("languages"), 1200),
    }


def init_career_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS career_profiles (
            user_id TEXT PRIMARY KEY,
            desired_role TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            work_type TEXT NOT NULL DEFAULT '',
            seniority TEXT NOT NULL DEFAULT '',
            skills_json TEXT NOT NULL DEFAULT '[]',
            summary TEXT NOT NULL DEFAULT '',
            experience TEXT NOT NULL DEFAULT '',
            education TEXT NOT NULL DEFAULT '',
            projects TEXT NOT NULL DEFAULT '',
            languages TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS career_cv_versions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content_json TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_career_cv_user_created
        ON career_cv_versions(user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS career_interview_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            job_description TEXT NOT NULL DEFAULT '',
            questions_json TEXT NOT NULL,
            current_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_career_interview_user_updated
        ON career_interview_sessions(user_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS career_interview_answers (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            question_index INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES career_interview_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_career_answer_user_session
        ON career_interview_answers(user_id, session_id, question_index);

        CREATE TABLE IF NOT EXISTS career_saved_jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            company TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            job_type TEXT NOT NULL DEFAULT '',
            salary TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            match_score INTEGER NOT NULL DEFAULT 0,
            match_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_career_saved_jobs_user_created
        ON career_saved_jobs(user_id, created_at DESC);
        """
    )
    db.commit()


class CareerAI:
    def __init__(self, api_key: str, model: str) -> None:
        self.model = str(model or "gpt-5.6-luna").strip()
        self.client = OpenAI(api_key=api_key.strip()) if str(api_key or "").strip() else None

    @property
    def configured(self) -> bool:
        return self.client is not None

    @staticmethod
    def _text(response: Any) -> str:
        direct = str(getattr(response, "output_text", "") or "").strip()
        if direct:
            return direct
        chunks: list[str] = []
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "output_text":
                    value = str(getattr(part, "text", "") or "").strip()
                    if value:
                        chunks.append(value)
        return "\n".join(chunks).strip()

    @staticmethod
    def _json(text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except Exception:
            start, end = raw.find("{"), raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    value = json.loads(raw[start : end + 1])
                    return value if isinstance(value, dict) else {}
                except Exception:
                    pass
        return {}

    def _call_json(self, instructions: str, prompt: str, max_tokens: int = 2600) -> dict[str, Any]:
        if not self.client:
            return {}
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[{"role": "user", "content": prompt}],
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
            max_output_tokens=max_tokens,
            store=False,
        )
        return self._json(self._text(response))

    def improve_cv(self, profile: dict[str, Any], job_description: str) -> dict[str, Any]:
        instructions = """
You are a careful CV editor. Return ONLY valid JSON.
Never invent employers, dates, degrees, metrics, technologies, responsibilities, achievements, certifications, or skills.
You may reorganize and rewrite only facts supplied by the user. If a metric is missing, do not fabricate one.
Write in the same main language as the user's supplied profile.
JSON shape:
{
  "headline": "...",
  "summary": "...",
  "skills": ["..."],
  "experience_bullets": ["..."],
  "project_bullets": ["..."],
  "missing_for_target": ["..."],
  "warnings": ["..."]
}
""".strip()
        prompt = json.dumps(
            {"profile": profile, "target_job_description": job_description[:MAX_JOB_DESCRIPTION]},
            ensure_ascii=False,
        )
        return self._call_json(instructions, prompt)

    def review_answer(
        self,
        profile: dict[str, Any],
        role: str,
        job_description: str,
        question: str,
        answer: str,
    ) -> dict[str, Any]:
        instructions = """
You are an interview coach. Return ONLY valid JSON.
Evaluate the answer against the question and only the candidate facts supplied. Do not invent experience.
Do not judge protected characteristics. Do not make hiring decisions; this is practice feedback only.
Use a 0-100 practice score based on relevance, specificity, structure and evidence.
JSON shape:
{
  "score": 0,
  "what_worked": ["..."],
  "improve": ["..."],
  "better_structure": "...",
  "follow_up": "..."
}
""".strip()
        prompt = json.dumps(
            {
                "profile": profile,
                "target_role": role,
                "job_description": job_description[:MAX_JOB_DESCRIPTION],
                "question": question,
                "candidate_answer": answer,
            },
            ensure_ascii=False,
        )
        return self._call_json(instructions, prompt, max_tokens=1800)


def register_career(app: Flask) -> None:
    app.extensions["career_ai"] = CareerAI(
        api_key=app.config.get("OPENAI_API_KEY", ""),
        model=app.config.get("OPENAI_MODEL", "gpt-5.6-luna"),
    )
    with app.app_context():
        init_career_db()
    app.register_blueprint(bp)


def _ai() -> CareerAI:
    return current_app.extensions["career_ai"]


def _profile(user_id: str) -> dict[str, Any]:
    row = get_db().execute(
        """
        SELECT desired_role, location, work_type, seniority, skills_json, summary,
               experience, education, projects, languages, updated_at
        FROM career_profiles WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return {
            "desired_role": "", "location": "", "work_type": "", "seniority": "",
            "skills": [], "summary": "", "experience": "", "education": "",
            "projects": "", "languages": "", "updated_at": "",
        }
    item = dict(row)
    try:
        item["skills"] = json.loads(item.pop("skills_json") or "[]")
    except Exception:
        item["skills"] = []
        item.pop("skills_json", None)
    return item


def _save_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = _profile_payload(payload)
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO career_profiles(
            user_id, desired_role, location, work_type, seniority, skills_json,
            summary, experience, education, projects, languages, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            desired_role=excluded.desired_role, location=excluded.location,
            work_type=excluded.work_type, seniority=excluded.seniority,
            skills_json=excluded.skills_json, summary=excluded.summary,
            experience=excluded.experience, education=excluded.education,
            projects=excluded.projects, languages=excluded.languages,
            updated_at=excluded.updated_at
        """,
        (
            user_id, item["desired_role"], item["location"], item["work_type"],
            item["seniority"], json.dumps(item["skills"], ensure_ascii=False),
            item["summary"], item["experience"], item["education"], item["projects"],
            item["languages"], now, now,
        ),
    )
    db.commit()
    item["updated_at"] = now
    return item


def _latest_cv(user_id: str) -> dict[str, Any] | None:
    row = get_db().execute(
        "SELECT id, title, content_json, source, created_at FROM career_cv_versions "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    try:
        item["content"] = json.loads(item.pop("content_json") or "{}")
    except Exception:
        item["content"] = {}
        item.pop("content_json", None)
    return item


def _quota(user_id: str) -> dict[str, Any]:
    return get_quota_status(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )


def _reserve(user_id: str) -> dict[str, Any] | None:
    event = reserve_message_quota(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )
    if event:
        g.pending_quota_event_id = str(event["id"])
    return event


def _finish(event_id: str) -> None:
    finalize_message_quota(event_id)
    g.pending_quota_event_id = ""


def _fallback_cv(profile: dict[str, Any]) -> dict[str, Any]:
    exp = [x.strip(" -•\t") for x in profile.get("experience", "").splitlines() if x.strip()]
    projects = [x.strip(" -•\t") for x in profile.get("projects", "").splitlines() if x.strip()]
    return {
        "headline": profile.get("desired_role") or "Hồ sơ nghề nghiệp",
        "summary": profile.get("summary") or "",
        "skills": profile.get("skills") or [],
        "experience_bullets": exp[:12],
        "project_bullets": projects[:8],
        "missing_for_target": [],
        "warnings": ["Bản này được sắp xếp bằng code; bật OpenAI để dùng tính năng viết lại AI."],
    }


def _local_feedback(answer: str) -> dict[str, Any]:
    text = _clean_text(answer, 5000)
    words = len(text.split())
    has_example = bool(re.search(r"\b(ví dụ|example|project|dự án|khi đó|situation|task)\b", text, re.I))
    has_action = bool(re.search(r"\b(tôi đã|mình đã|i did|i built|i implemented|thực hiện|xử lý)\b", text, re.I))
    has_result = bool(re.search(r"\b(kết quả|result|improved|giảm|tăng|hoàn thành|đạt)\b", text, re.I))
    score = 45 + min(words, 120) // 6 + (10 if has_example else 0) + (10 if has_action else 0) + (10 if has_result else 0)
    score = max(30, min(90, score))
    improve = []
    if words < 45:
        improve.append("Câu trả lời còn ngắn; thêm một tình huống thật và việc bạn trực tiếp làm.")
    if not has_example:
        improve.append("Thêm ví dụ cụ thể thay vì chỉ mô tả chung.")
    if not has_action:
        improve.append("Nói rõ hành động của chính bạn.")
    if not has_result:
        improve.append("Kết thúc bằng kết quả hoặc điều bạn học được.")
    return {
        "score": score,
        "what_worked": ["Câu trả lời bám vào nội dung bạn đã cung cấp."] if text else [],
        "improve": improve or ["Có thể rút gọn và ưu tiên chi tiết có bằng chứng."],
        "better_structure": "Tình huống → nhiệm vụ → hành động của bạn → kết quả/bài học.",
        "follow_up": "",
    }


def _interview_questions(profile: dict[str, Any], role: str, job_description: str) -> list[str]:
    role = role or profile.get("desired_role") or "vị trí này"
    skills = profile.get("skills") or []
    skill = skills[0] if skills else "một kỹ năng quan trọng"
    second = skills[1] if len(skills) > 1 else skill
    questions = [
        f"Hãy giới thiệu ngắn gọn về bản thân và vì sao bạn phù hợp với vị trí {role}.",
        f"Kể về một dự án hoặc công việc mà bạn đã dùng {skill} để giải quyết một vấn đề cụ thể.",
        "Kể về một lần bạn gặp lỗi hoặc thất bại. Bạn đã xử lý thế nào và học được gì?",
        f"Nếu phải làm một nhiệm vụ liên quan đến {second} nhưng yêu cầu chưa rõ, bạn sẽ bắt đầu thế nào?",
        "Kể về một lần bạn phải phối hợp với người khác khi có bất đồng hoặc áp lực tiến độ.",
        f"Trong 6–12 tháng tới, bạn muốn phát triển điều gì để làm tốt hơn ở vị trí {role}?",
    ]
    if job_description.strip():
        questions.insert(
            2,
            "Trong mô tả công việc này, yêu cầu nào bạn tự tin nhất và yêu cầu nào bạn cần học thêm? Hãy giải thích bằng kinh nghiệm thật.",
        )
    return questions[:7]


def _match_job(profile: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    desired = _normalize(profile.get("desired_role", ""))
    title = _normalize(job.get("title", ""))
    desc = _normalize(job.get("description", ""))
    location = _normalize(job.get("location", ""))
    skills = [x for x in profile.get("skills", []) if _normalize(x)]

    title_tokens = _tokens(desired)
    job_title_tokens = _tokens(title)
    title_overlap = len(title_tokens & job_title_tokens) / max(len(title_tokens), 1) if title_tokens else 0

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    haystack = f"{title} {desc}"
    for skill in skills:
        key = _normalize(skill)
        if key and key in haystack:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)
    skill_ratio = len(matched_skills) / max(len(skills), 1) if skills else 0.35

    location_score = 0.5
    pref_loc = _normalize(profile.get("location", ""))
    if not pref_loc:
        location_score = 0.7
    elif pref_loc in location or "worldwide" in location or "anywhere" in location or "remote" in location:
        location_score = 1.0

    job_type = _normalize(job.get("job_type", ""))
    pref_type = _normalize(profile.get("work_type", ""))
    type_score = 1.0 if pref_type and pref_type in job_type else (0.7 if not pref_type else 0.4)

    score = round(35 * title_overlap + 45 * skill_ratio + 10 * location_score + 10 * type_score)
    score = max(0, min(100, score))
    return {
        "score": score,
        "matched_skills": matched_skills[:12],
        "missing_profile_skills": missing_skills[:12],
        "reason": (
            "Khớp tốt với vai trò và kỹ năng đã lưu."
            if score >= 75 else
            "Có nhiều điểm phù hợp nhưng vẫn cần đọc kỹ yêu cầu."
            if score >= 55 else
            "Độ khớp hiện tại chưa cao; kiểm tra lại vai trò, kỹ năng và yêu cầu."
        ),
    }




JOOBLE_ROLE_ALIASES = {
    "ke toan": "accountant accounting",
    "kiem toan": "auditor audit",
    "tai chinh": "finance financial",
    "ngan hang": "banking bank",
    "kinh doanh": "sales business development",
    "marketing": "marketing",
    "cham soc khach hang": "customer service customer support",
    "hanh chinh": "administration administrative",
    "nhan su": "human resources recruiter HR",
    "cong nghe thong tin": "information technology IT",
    "lap trinh vien": "software developer programmer",
    "data analyst": "data analyst",
    "ai engineer": "AI engineer machine learning",
    "ky su tu dong hoa": "automation engineer",
    "ky su robot": "robotics engineer",
    "ky su co khi": "mechanical engineer",
    "ky su dien": "electrical engineer electronics engineer",
    "san xuat": "manufacturing production",
    "qa qc": "QA QC quality assurance quality control",
    "logistics": "logistics",
    "supply chain": "supply chain",
    "xuat nhap khau": "import export",
    "thiet ke": "designer design",
    "giao vien": "teacher education",
    "y te": "healthcare medical",
    "duoc": "pharmaceutical pharmacy",
    "luat": "legal lawyer",
    "xay dung": "construction civil engineer",
    "bat dong san": "real estate",
    "du lich": "hospitality tourism hotel restaurant",
}


def _jooble_keyword_query(query: str) -> str:
    raw = _clean_line(query, 120)
    alias = JOOBLE_ROLE_ALIASES.get(_normalize(raw), "")
    return _clean_line(alias or raw, 120)


def _jooble_api_key() -> str:
    return str(os.getenv(JOOBLE_API_KEY_ENV, "") or "").strip()



def _parse_job_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _job_level_bucket(job: dict[str, Any]) -> str:
    haystack = _normalize(f"{job.get('title', '')} {job.get('description', '')}")
    if any(x in haystack for x in (
        "intern", "internship", "thuc tap", "fresher", "new graduate",
        "moi tot nghiep", "khong yeu cau kinh nghiem", "0 1 nam", "0-1 nam",
    )):
        return "entry"
    if any(x in haystack for x in (
        "senior", "lead", "principal", "manager", "truong phong", "truong nhom",
        "5 nam", "5+ nam", "5 years", "5+ years",
    )):
        return "senior"
    if any(x in haystack for x in (
        "middle", "mid level", "mid-level", "3 nam", "4 nam",
        "3 years", "4 years", "2 4 nam", "2-4 nam",
    )):
        return "mid"
    if any(x in haystack for x in (
        "junior", "1 nam", "2 nam", "1 year", "2 years", "1 2 nam", "1-2 nam",
    )):
        return "junior"
    return "unknown"


def _job_matches_filters(
    job: dict[str, Any],
    *,
    job_type: str = "",
    level: str = "",
    posted_days: int = 0,
    salary_only: bool = False,
) -> bool:
    if salary_only:
        salary_value = str(job.get("salary", "") or "").strip()
        if not salary_value:
            return False

    if job_type:
        actual = _normalize(job.get("job_type", ""))
        wanted = _normalize(job_type)
        aliases = {
            "full time": {"full time", "fulltime", "full-time"},
            "part time": {"part time", "parttime", "part-time"},
            "internship": {"intern", "internship", "thuc tap"},
            "contract": {"contract", "hop dong"},
            "freelance": {"freelance", "freelancer"},
        }
        checks = aliases.get(wanted, {wanted})
        if actual and not any(_normalize(x) in actual for x in checks):
            return False

    if level and _job_level_bucket(job) != level:
        return False

    if posted_days > 0:
        updated = _parse_job_datetime(job.get("publication_date", ""))
        if updated is not None:
            age_days = (datetime.now(timezone.utc) - updated).total_seconds() / 86400
            if age_days > posted_days:
                return False

    return True


def _sort_jobs(jobs: list[dict[str, Any]], sort_mode: str) -> list[dict[str, Any]]:
    if str(sort_mode or "").strip().lower() == "newest":
        def newest_key(job: dict[str, Any]) -> float:
            dt = _parse_job_datetime(job.get("publication_date", ""))
            return dt.timestamp() if dt else 0
        return sorted(jobs, key=newest_key, reverse=True)

    return sorted(
        jobs,
        key=lambda x: (
            int((x.get("match") or {}).get("score", 0) or 0),
            str(x.get("publication_date", "")),
        ),
        reverse=True,
    )



def _jooble_cache_key(query: str, location: str, radius: str = "") -> str:
    return json.dumps(
        {
            "q": _normalize(query),
            "location": _normalize(location or "Vietnam"),
            "radius": str(radius or "").strip(),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _jooble_cache_get(query: str, location: str, radius: str = "") -> list[dict[str, Any]] | None:
    key = _jooble_cache_key(query, location, radius)
    now = time.time()
    with _jooble_cache_lock:
        item = _jooble_cache.get(key)
        if not item:
            return None
        if now - float(item.get("created_at", 0.0)) > JOOBLE_CACHE_SECONDS:
            _jooble_cache.pop(key, None)
            return None
        return [dict(job) for job in (item.get("jobs") or [])]


def _jooble_cache_set(
    query: str,
    location: str,
    radius: str,
    jobs: list[dict[str, Any]],
) -> None:
    key = _jooble_cache_key(query, location, radius)
    with _jooble_cache_lock:
        _jooble_cache[key] = {
            "created_at": time.time(),
            "jobs": [dict(job) for job in jobs],
        }

        if len(_jooble_cache) > 250:
            oldest = sorted(
                _jooble_cache.items(),
                key=lambda pair: float(pair[1].get("created_at", 0.0)),
            )[:50]
            for old_key, _ in oldest:
                _jooble_cache.pop(old_key, None)



def _brave_api_key() -> str:
    return str(os.getenv(BRAVE_SEARCH_API_KEY_ENV, "") or "").strip()


def _source_info_for_url(url: str) -> tuple[str, str]:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return "", ""
    if host.startswith("www."):
        host = host[4:]
    for domain, info in JOB_SOURCE_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return info
    return "", ""


def _source_name_for_url(url: str) -> str:
    return _source_info_for_url(url)[0]


def _source_type_for_url(url: str) -> str:
    return _source_info_for_url(url)[1]


def _is_allowed_job_source_url(url: str) -> bool:
    return bool(_source_name_for_url(url))


def _looks_like_company_job_page(url: str, title: str, description: str) -> bool:
    """Allow public company career pages even if domain is not on our fixed list."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
    except Exception:
        return False

    # Never accept obvious search engines / aggregators through the generic branch.
    blocked = {
        "google.com", "bing.com", "yahoo.com", "brave.com",
        "youtube.com", "tiktok.com",
    }
    if any(host == d or host.endswith("." + d) for d in blocked):
        return False

    haystack = _normalize(f"{title} {description} {path}")
    job_signals = {
        "job", "jobs", "career", "careers", "vacancy", "vacancies",
        "recruitment", "recruiting", "tuyen dung", "viec lam",
        "join us", "opportunity", "opportunities",
    }
    return any(signal in haystack for signal in job_signals)


def _extract_salary_hint(text_value: str) -> str:
    """Rút mức lương chỉ khi snippet/title thực sự hiển thị con số + đơn vị."""
    raw = " ".join(str(text_value or "").split())
    if not raw:
        return ""

    patterns = [
        r"(?i)(?:lương|salary)\s*[:\-]?\s*((?:\d{1,3}(?:[.,]\d+)?)\s*(?:-|–|—|đến|to)\s*(?:\d{1,3}(?:[.,]\d+)?)\s*(?:triệu|tr|million)\b)",
        r"(?i)((?:\d{1,3}(?:[.,]\d+)?)\s*(?:-|–|—|đến|to)\s*(?:\d{1,3}(?:[.,]\d+)?)\s*(?:triệu|tr|million)\b)",
        r"(?i)((?:\d[\d.,]*\s*(?:VND|VNĐ|USD|US\$|\$|₫))\b)",
        r"(?i)((?:\$|₫)\s*\d[\d.,]*(?:\s*(?:-|–|—|to|đến)\s*(?:\$|₫)?\s*\d[\d.,]*)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            value = str(match.group(1) or match.group(0)).strip()
            return value[:140]
    return ""


def _brave_cache_key(query: str, location: str, group: str) -> str:
    return json.dumps(
        {
            "q": _normalize(query),
            "location": _normalize(location or "Vietnam"),
            "group": str(group or ""),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _brave_cache_get(query: str, location: str, group: str) -> list[dict[str, Any]] | None:
    key = _brave_cache_key(query, location, group)
    now = time.time()
    with _brave_cache_lock:
        item = _brave_cache.get(key)
        if not item:
            return None
        if now - float(item.get("created_at", 0.0)) > BRAVE_CACHE_SECONDS:
            _brave_cache.pop(key, None)
            return None
        return [dict(job) for job in (item.get("jobs") or [])]


def _brave_cache_set(
    query: str,
    location: str,
    group: str,
    jobs: list[dict[str, Any]],
) -> None:
    key = _brave_cache_key(query, location, group)
    with _brave_cache_lock:
        _brave_cache[key] = {
            "created_at": time.time(),
            "jobs": [dict(job) for job in jobs],
        }
        if len(_brave_cache) > 250:
            oldest = sorted(
                _brave_cache.items(),
                key=lambda pair: float(pair[1].get("created_at", 0.0)),
            )[:50]
            for old_key, _ in oldest:
                _brave_cache.pop(old_key, None)


def _brave_group_query(query: str, location: str, group: str) -> str:
    """Build a Brave query under the documented 400-char / 50-word limits."""
    config = BRAVE_SOURCE_GROUPS.get(group) or {}
    domains = list(config.get("domains") or [])
    q = " ".join(str(query or "").split()).strip()
    loc = " ".join(str(location or "Việt Nam").split()).strip()

    if group == "company_public":
        candidate = f"{q} {loc} tuyển dụng việc làm careers jobs recruitment Vietnam"
        return candidate[:360]

    prefix = f"{q} {loc}".strip()
    site_terms: list[str] = []
    for domain in domains:
        candidate_terms = site_terms + [f"site:{domain}"]
        candidate = f"{prefix} ({' OR '.join(candidate_terms)})"
        if len(candidate) > 360 or len(candidate.split()) > 45:
            break
        site_terms.append(f"site:{domain}")

    if not site_terms:
        return prefix[:360]
    return f"{prefix} ({' OR '.join(site_terms)})"[:360]



def _brave_search_group(
    *,
    query: str,
    location: str,
    group: str,
    count: int = 20,
) -> tuple[list[dict[str, Any]], str]:
    api_key = _brave_api_key()
    if not api_key:
        return [], "missing_api_key"

    cached = _brave_cache_get(query, location, group)
    if cached is not None:
        return cached[:count], "cache"

    search_query = _brave_group_query(query, location, group)
    params = {
        "q": search_query,
        "country": "ALL",
        "search_lang": "vi",
        "count": max(1, min(int(count), 20)),
        "safesearch": "moderate",
        "result_filter": "web",
        "operators": "true",
        "spellcheck": "false",
    }

    url = BRAVE_SEARCH_ENDPOINT + "?" + urlencode(params)
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            ),
        },
    )

    try:
        with urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except HTTPError as exc:
        code = int(getattr(exc, "code", 0) or 0)
        current_app.logger.warning(
            "brave_search_http_error group=%s status=%s query_chars=%s query_words=%s",
            group,
            code,
            len(search_query),
            len(search_query.split()),
        )
        if code in {401, 403}:
            return [], "auth_error"
        if code == 422:
            return [], "query_error"
        if code == 429:
            return [], "rate_limited"
        return [], f"http_{code or 'error'}"
    except (URLError, TimeoutError):
        current_app.logger.warning("brave_search_network_error group=%s", group)
        return [], "provider_unavailable"
    except Exception:
        current_app.logger.exception("brave_search_unexpected_error group=%s", group)
        return [], "provider_unavailable"

    results: list[dict[str, Any]] = []
    web_section = payload.get("web") if isinstance(payload, dict) else {}
    raw_results = web_section.get("results", []) if isinstance(web_section, dict) else []

    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        link = _safe_url(raw.get("url"))
        if not link:
            continue

        title = _clean_line(_strip_html(raw.get("title", "")), 220)
        description = _clean_text(_strip_html(raw.get("description", "")), 5000)
        if not title:
            continue

        known_source = _is_allowed_job_source_url(link)
        if group != "company_public" and not known_source:
            continue
        if group == "company_public" and not (
            known_source or _looks_like_company_job_page(link, title, description)
        ):
            continue

        source = _source_name_for_url(link)
        source_type = _source_type_for_url(link)
        if not source:
            source = _clean_line(urlparse(link).hostname, 100)
            source_type = "company_career"

        salary = _extract_salary_hint(f"{title} {description}")
        results.append(
            {
                "provider": "Brave Search",
                "source": source,
                "source_type": source_type,
                "source_group": group,
                "external_id": link[:400],
                "url": link,
                "title": title,
                "company": "",
                "location": _clean_line(location or "Việt Nam", 160),
                "job_type": "",
                "salary": salary,
                "description": description,
                "publication_date": "",
            }
        )

    results = _dedupe_jobs(results)
    _brave_cache_set(query, location, group, results)
    return results[:count], ""



def _fetch_brave_job_results(
    *,
    query: str,
    location: str,
    count_per_group: int = 20,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Search multiple source families. Fresh search = up to 4 Brave requests.

    Each group is cached independently for 30 minutes.
    """
    all_jobs: list[dict[str, Any]] = []
    states: dict[str, str] = {}

    for group in BRAVE_SOURCE_GROUPS:
        jobs, state = _brave_search_group(
            query=query,
            location=location,
            group=group,
            count=count_per_group,
        )
        states[group] = state or "ok"
        all_jobs.extend(jobs)

    return _dedupe_jobs(all_jobs), states


# ---------------- Public ATS enrichment ----------------

def _lever_parts(url: str) -> tuple[str, str] | None:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host != "jobs.lever.co":
            return None
        parts = [x for x in parsed.path.split("/") if x]
        if len(parts) < 2:
            return None
        return parts[0], parts[1]
    except Exception:
        return None


def _fetch_lever_job(url: str) -> dict[str, Any] | None:
    parts = _lever_parts(url)
    if not parts:
        return None
    site, posting_id = parts
    endpoint = f"https://api.lever.co/v0/postings/{site}/{posting_id}?mode=json"
    req = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "MoLoi/1.0"})
    try:
        with urlopen(req, timeout=8) as response:
            raw = json.loads(response.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None

    categories = raw.get("categories") if isinstance(raw.get("categories"), dict) else {}
    salary_range = raw.get("salaryRange") if isinstance(raw.get("salaryRange"), dict) else {}
    salary = ""
    if salary_range.get("min") is not None and salary_range.get("max") is not None:
        salary = (
            f"{salary_range.get('min')}–{salary_range.get('max')} "
            f"{salary_range.get('currency', '')}/{salary_range.get('interval', '')}"
        ).strip("/")

    return {
        "provider": "Lever Postings API",
        "source": "Lever",
        "source_type": "ats",
        "external_id": _clean_line(raw.get("id"), 120),
        "url": _safe_url(raw.get("hostedUrl")) or url,
        "title": _clean_line(raw.get("text"), 220),
        "company": site,
        "location": _clean_line(categories.get("location"), 160),
        "job_type": _clean_line(categories.get("commitment"), 80),
        "salary": _clean_line(salary, 140),
        "description": _clean_text(
            raw.get("descriptionPlain") or raw.get("openingPlain") or "",
            10000,
        ),
        "publication_date": "",
    }


def _greenhouse_parts(url: str) -> tuple[str, str] | None:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
            return None
        parts = [x for x in parsed.path.split("/") if x]
        # Current common pattern: /BOARD/jobs/JOB_ID
        if len(parts) >= 3 and parts[1] == "jobs":
            return parts[0], parts[2]
        return None
    except Exception:
        return None


def _fetch_greenhouse_job(url: str) -> dict[str, Any] | None:
    parts = _greenhouse_parts(url)
    if not parts:
        return None
    board, job_id = parts
    endpoint = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{board}/jobs/{job_id}?content=true"
    )
    req = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "MoLoi/1.0"})
    try:
        with urlopen(req, timeout=8) as response:
            raw = json.loads(response.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None

    location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    content = _clean_text(_strip_html(raw.get("content", "")), 10000)
    salary = _extract_salary_hint(content)

    return {
        "provider": "Greenhouse Job Board API",
        "source": "Greenhouse",
        "source_type": "ats",
        "external_id": _clean_line(raw.get("id"), 120),
        "url": url,
        "title": _clean_line(raw.get("title"), 220),
        "company": board,
        "location": _clean_line(location.get("name"), 160),
        "job_type": "",
        "salary": salary,
        "description": content,
        "publication_date": _clean_line(raw.get("updated_at"), 100),
    }


def _enrich_public_ats_jobs(
    jobs: list[dict[str, Any]],
    *,
    max_enrich: int = 10,
) -> list[dict[str, Any]]:
    """Upgrade Brave snippets to structured Lever/Greenhouse data when possible."""
    result: list[dict[str, Any]] = []
    used = 0

    for job in jobs:
        enriched = None
        if used < max_enrich:
            url = str(job.get("url", "") or "")
            if _lever_parts(url):
                enriched = _fetch_lever_job(url)
            elif _greenhouse_parts(url):
                enriched = _fetch_greenhouse_job(url)

        if enriched:
            used += 1
            # Preserve discovery group so UI/debug can still show where it came from.
            enriched["source_group"] = job.get("source_group", "public_ats")
            result.append(enriched)
        else:
            result.append(job)

    return result



def _fetch_jooble(
    *,
    query: str,
    location: str,
    page: int = 1,
    result_on_page: int = JOOBLE_RESULT_LIMIT,
    radius: str = "",
    salary: int = 0,
) -> tuple[list[dict[str, Any]], str]:
    """Lấy job thật qua Jooble REST API với cache ngắn hạn."""
    api_key = _jooble_api_key()
    if not api_key:
        return [], "missing_api_key"

    if int(page) == 1 and int(salary or 0) == 0:
        cached = _jooble_cache_get(query, location, radius)
        if cached is not None:
            return cached[: max(1, min(int(result_on_page), 50))], "cache"

    endpoint = JOOBLE_API_BASE.format(api_key=api_key)
    payload = {
        "keywords": _clean_line(query, 120),
        "location": _clean_line(location or "Vietnam", 120),
        "page": str(max(1, int(page))),
        "ResultOnPage": str(max(1, min(int(result_on_page), 50))),
        "companysearch": "false",
    }
    if str(radius or "").strip() in {"0", "4", "8", "16", "26", "40", "80"}:
        payload["radius"] = str(radius).strip()
    if int(salary or 0) > 0:
        payload["salary"] = int(salary)
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MoLoi/1.0 (+job-search)",
        },
    )

    try:
        with urlopen(req, timeout=12) as response:
            raw_payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception:
        return [], "provider_unavailable"

    raw_jobs = raw_payload.get("jobs", []) if isinstance(raw_payload, dict) else []
    jobs: list[dict[str, Any]] = []
    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue
        title = _clean_line(raw.get("title"), 180)
        link = _safe_url(raw.get("link"))
        if not title or not link:
            continue
        jobs.append(
            {
                "provider": "Jooble",
                "source": _clean_line(raw.get("source") or "Jooble", 100),
                "external_id": _clean_line(raw.get("id"), 100),
                "url": link,
                "title": title,
                "company": _clean_line(raw.get("company"), 160),
                "location": _clean_line(raw.get("location"), 160),
                "job_type": _clean_line(raw.get("type"), 80),
                "salary": _clean_line(raw.get("salary"), 140),
                "description": _clean_text(_strip_html(raw.get("snippet", "")), 5000),
                "publication_date": _clean_line(raw.get("updated"), 100),
            }
        )
    if int(page) == 1 and int(salary or 0) == 0:
        _jooble_cache_set(query, location, radius, jobs)
    return jobs[: max(1, min(int(result_on_page), 50))], ""


def _dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in jobs:
        url_key = _normalize(job.get("url", ""))
        title_key = _normalize(job.get("title", ""))
        company_key = _normalize(job.get("company", ""))
        key = url_key or f"{title_key}|{company_key}"
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result


def _fetch_remotive() -> tuple[list[dict[str, Any]], str]:
    now = time.time()
    with _cache_lock:
        if _remotive_cache["jobs"] and now - float(_remotive_cache["fetched_at"]) < REMOTIVE_CACHE_SECONDS:
            return list(_remotive_cache["jobs"]), str(_remotive_cache.get("error") or "")

    url = f"{REMOTIVE_URL}?{urlencode({'limit': REMOTIVE_FETCH_LIMIT})}"
    req = Request(url, headers={"User-Agent": "MoLoi/1.0 (+job-search; contact via website)"})
    jobs: list[dict[str, Any]] = []
    error = ""
    try:
        with urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        for raw in payload.get("jobs", []) if isinstance(payload, dict) else []:
            if not isinstance(raw, dict):
                continue
            jobs.append(
                {
                    "source": "Remotive",
                    "external_id": str(raw.get("id", ""))[:80],
                    "url": _safe_url(raw.get("url")),
                    "title": _clean_line(raw.get("title"), 180),
                    "company": _clean_line(raw.get("company_name"), 140),
                    "location": _clean_line(raw.get("candidate_required_location"), 160),
                    "job_type": _clean_line(raw.get("job_type"), 60),
                    "salary": _clean_line(raw.get("salary"), 120),
                    "description": _clean_text(_strip_html(raw.get("description", "")), 10000),
                    "publication_date": _clean_line(raw.get("publication_date"), 80),
                }
            )
    except Exception:
        error = "Nguồn việc làm tạm thời không phản hồi. Bạn vẫn có thể dán tin tuyển dụng để phân tích."

    with _cache_lock:
        if jobs:
            _remotive_cache.update({"fetched_at": now, "jobs": jobs, "error": ""})
        elif not _remotive_cache["jobs"]:
            _remotive_cache.update({"fetched_at": now, "error": error})
        cached = list(_remotive_cache["jobs"])
        cached_error = str(_remotive_cache.get("error") or error)
    return cached, cached_error


def _search_jobs(profile: dict[str, Any], query: str, limit: int) -> tuple[list[dict[str, Any]], str]:
    jobs, error = _fetch_remotive()
    q_tokens = _tokens(query)
    desired_tokens = _tokens(profile.get("desired_role", ""))
    needle = q_tokens or desired_tokens
    ranked = []
    for job in jobs:
        text_tokens = _tokens(f"{job.get('title','')} {job.get('description','')}")
        if needle and not (needle & text_tokens):
            continue
        match = _match_job(profile, job)
        item = dict(job)
        item["match"] = match
        ranked.append(item)
    ranked.sort(key=lambda x: (int(x["match"]["score"]), x.get("publication_date", "")), reverse=True)
    return ranked[:limit], error


def _saved_jobs(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, source, external_id, url, title, company, location, job_type, salary,
               description, match_score, match_json, created_at
        FROM career_saved_jobs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, max(1, min(int(limit), 100))),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["match"] = json.loads(item.pop("match_json") or "{}")
        except Exception:
            item["match"] = {"score": int(item.get("match_score") or 0)}
            item.pop("match_json", None)
        result.append(item)
    return result


def _interview_overview(user_id: str) -> dict[str, Any]:
    db = get_db()
    sessions = db.execute(
        "SELECT COUNT(*) AS n FROM career_interview_sessions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    answers = db.execute(
        "SELECT COUNT(*) AS n, AVG(CAST(json_extract(feedback_json, '$.score') AS REAL)) AS avg_score "
        "FROM career_interview_answers WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return {
        "sessions": int(sessions["n"] or 0) if sessions else 0,
        "answers": int(answers["n"] or 0) if answers else 0,
        "average_score": round(float(answers["avg_score"] or 0)) if answers else 0,
    }


@bp.get("/career/cv")
def career_cv_page():
    user_id = _user_id()
    if not user_id or not get_account(user_id):
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template("career/index.html", display_name=account.get("display_name", "Bạn"), initial_mode="cv")


@bp.get("/career/jobs")
def career_jobs_page():
    user_id = _user_id()
    if not user_id or not get_account(user_id):
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template("career/index.html", display_name=account.get("display_name", "Bạn"), initial_mode="jobs")


@bp.get("/api/career/overview")
def career_overview():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    profile = _profile(user_id)
    latest = _latest_cv(user_id)
    saved_count = get_db().execute(
        "SELECT COUNT(*) AS n FROM career_saved_jobs WHERE user_id = ?", (user_id,)
    ).fetchone()
    return jsonify(
        {
            "profile": profile,
            "profile_ready": bool(profile.get("desired_role") or profile.get("skills")),
            "latest_cv": latest,
            "interview": _interview_overview(user_id),
            "saved_jobs_count": int(saved_count["n"] or 0) if saved_count else 0,
            "ai_configured": _ai().configured,
            "quota": _quota(user_id),
        }
    )


@bp.post("/api/career/profile")
def career_save_profile():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return _error("Dữ liệu hồ sơ không hợp lệ.")
    profile = _save_profile(user_id, payload)
    return jsonify({"ok": True, "profile": profile})


@bp.post("/api/career/cv/improve")
def career_cv_improve():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    profile = _save_profile(user_id, payload.get("profile") or payload)
    job_description = _clean_text(payload.get("job_description"), MAX_JOB_DESCRIPTION)

    event = None
    if _ai().configured:
        event = _reserve(user_id)
        if not event:
            return _error("Bạn đã hết lượt hiện có.", 429, "quota_exhausted")

    try:
        content = _ai().improve_cv(profile, job_description) if _ai().configured else {}
        if not content:
            content = _fallback_cv(profile)
        content = {
            "headline": _clean_line(content.get("headline"), 180),
            "summary": _clean_text(content.get("summary"), 2200),
            "skills": _json_list(content.get("skills") or profile.get("skills"), limit=40),
            "experience_bullets": [_clean_text(x, 500) for x in (content.get("experience_bullets") or [])[:16]],
            "project_bullets": [_clean_text(x, 500) for x in (content.get("project_bullets") or [])[:12]],
            "missing_for_target": [_clean_text(x, 300) for x in (content.get("missing_for_target") or [])[:12]],
            "warnings": [_clean_text(x, 300) for x in (content.get("warnings") or [])[:8]],
            "education": profile.get("education", ""),
            "languages": profile.get("languages", ""),
        }
        cv_id = str(uuid.uuid4())
        now = _now()
        get_db().execute(
            "INSERT INTO career_cv_versions(id, user_id, title, content_json, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                cv_id, user_id, content.get("headline") or "CV",
                json.dumps(content, ensure_ascii=False),
                "ai" if _ai().configured else "local", now,
            ),
        )
        get_db().commit()
        if event:
            _finish(str(event["id"]))
        return jsonify({"id": cv_id, "content": content, "quota": _quota(user_id)}), 201
    except Exception:
        if event:
            refund_message_quota(str(event["id"]))
            g.pending_quota_event_id = ""
        current_app.logger.exception("career_cv_improve_failed")
        return _error("Chưa thể tạo bản CV lúc này. Hãy thử lại sau.", 502, "ai_unavailable")


@bp.post("/api/career/cv/analyze")
def career_cv_analyze():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    profile = _save_profile(user_id, payload.get("profile") or payload)
    jd = _clean_text(payload.get("job_description"), MAX_JOB_DESCRIPTION)
    fake_job = {
        "title": profile.get("desired_role", ""),
        "description": jd,
        "location": profile.get("location", ""),
        "job_type": profile.get("work_type", ""),
    }
    match = _match_job(profile, fake_job)
    jd_tokens = _tokens(jd)
    profile_tokens = _tokens(" ".join(profile.get("skills") or []))
    missing = sorted(jd_tokens - profile_tokens, key=len, reverse=True)[:15] if jd else []
    return jsonify({"match": match, "possible_missing_keywords": missing})


@bp.post("/api/career/interview/start")
def career_interview_start():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    profile = _profile(user_id)
    role = _clean_line(payload.get("role") or profile.get("desired_role"), 140)
    if not role:
        return _error("Hãy nhập vị trí muốn luyện phỏng vấn.")
    jd = _clean_text(payload.get("job_description"), MAX_JOB_DESCRIPTION)
    questions = _interview_questions(profile, role, jd)
    session_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO career_interview_sessions(
            id, user_id, role, job_description, questions_json, current_index, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (session_id, user_id, role, jd, json.dumps(questions, ensure_ascii=False), now, now),
    )
    db.commit()
    return jsonify({"id": session_id, "role": role, "questions": questions, "current_index": 0}), 201


def _owned_session(user_id: str, session_id: str):
    return get_db().execute(
        """
        SELECT id, role, job_description, questions_json, current_index, created_at, updated_at
        FROM career_interview_sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()


@bp.post("/api/career/interview/answer")
def career_interview_answer():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    session_id = _clean_line(payload.get("session_id"), 80)
    row = _owned_session(user_id, session_id)
    if not row:
        return _error("Không tìm thấy phiên phỏng vấn.", 404, "not_found")
    try:
        questions = json.loads(row["questions_json"] or "[]")
    except Exception:
        questions = []
    index = int(row["current_index"] or 0)
    if index < 0 or index >= len(questions):
        return _error("Phiên phỏng vấn này đã hoàn thành.", 409, "completed")
    answer = _clean_text(payload.get("answer"), 6000)
    if len(answer) < 10:
        return _error("Câu trả lời quá ngắn để đánh giá.")

    event = None
    if _ai().configured:
        event = _reserve(user_id)
        if not event:
            return _error("Bạn đã hết lượt hiện có.", 429, "quota_exhausted")
    try:
        feedback = (
            _ai().review_answer(
                _profile(user_id), str(row["role"]), str(row["job_description"]),
                str(questions[index]), answer,
            )
            if _ai().configured else {}
        )
        if not feedback:
            feedback = _local_feedback(answer)
        feedback["score"] = max(0, min(100, int(feedback.get("score", 0) or 0)))
        for key in ("what_worked", "improve"):
            feedback[key] = [_clean_text(x, 400) for x in (feedback.get(key) or [])[:8]]
        feedback["better_structure"] = _clean_text(feedback.get("better_structure"), 1200)
        feedback["follow_up"] = _clean_text(feedback.get("follow_up"), 500)

        answer_id = str(uuid.uuid4())
        next_index = index + 1
        now = _now()
        db = get_db()
        db.execute(
            """
            INSERT INTO career_interview_answers(
                id, session_id, user_id, question_index, question, answer, feedback_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                answer_id, session_id, user_id, index, str(questions[index]), answer,
                json.dumps(feedback, ensure_ascii=False), now,
            ),
        )
        db.execute(
            "UPDATE career_interview_sessions SET current_index = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (next_index, now, session_id, user_id),
        )
        db.commit()
        if event:
            _finish(str(event["id"]))
        return jsonify(
            {
                "feedback": feedback,
                "current_index": next_index,
                "completed": next_index >= len(questions),
                "next_question": questions[next_index] if next_index < len(questions) else "",
                "quota": _quota(user_id),
            }
        )
    except Exception:
        if event:
            refund_message_quota(str(event["id"]))
            g.pending_quota_event_id = ""
        current_app.logger.exception("career_interview_review_failed")
        return _error("Chưa thể đánh giá câu trả lời lúc này.", 502, "ai_unavailable")



VIETNAM_LOCATION_HINTS = {
    "", "vietnam", "viet nam", "việt nam",
    "hà nội", "ha noi",
    "tp. hồ chí minh", "tp ho chi minh", "hồ chí minh", "ho chi minh", "hcm", "tp.hcm",
    "đà nẵng", "da nang",
    "hải phòng", "hai phong",
    "cần thơ", "can tho",
    "bình dương", "binh duong",
    "đồng nai", "dong nai",
    "bắc ninh", "bac ninh",
    "hưng yên", "hung yen",
    "hải dương", "hai duong",
    "long an",
    "bà rịa - vũng tàu", "ba ria - vung tau", "vũng tàu", "vung tau",
    "nghệ an", "nghe an",
    "thanh hóa", "thanh hoa",
    "thái nguyên", "thai nguyen",
    "remote tại việt nam", "remote tai viet nam",
}


def _is_vietnam_search(location: str) -> bool:
    raw = str(location or "").strip()
    normalized = _normalize(raw)
    if not raw:
        return True
    if normalized in {_normalize(x) for x in VIETNAM_LOCATION_HINTS}:
        return True
    # Nếu user nhập một tỉnh/thành không nằm trong preset nhưng có hậu tố Việt Nam.
    return "viet nam" in normalized or "vietnam" in normalized


@bp.get("/api/career/jobs/search")
def career_jobs_search():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")

    query = _clean_line(request.args.get("q"), 120)
    location = _clean_line(request.args.get("location"), 120)
    job_type = _clean_line(request.args.get("job_type"), 40)
    level = _clean_line(request.args.get("level"), 20)
    radius = _clean_line(request.args.get("radius"), 8)
    sort_mode = _clean_line(request.args.get("sort"), 20) or "match"
    salary_only = str(request.args.get("salary_only", "")).lower() in {"1", "true", "yes"}

    try:
        posted_days = max(0, min(int(request.args.get("posted_days", 0) or 0), 365))
    except (TypeError, ValueError):
        posted_days = 0

    if not query:
        return _error("Hãy chọn công việc hoặc nhập từ khóa.")

    try:
        limit = max(1, min(int(request.args.get("limit", 30)), 40))
    except (TypeError, ValueError):
        limit = 30

    profile = _profile(user_id)
    vietnam_search = _is_vietnam_search(location)

    jooble_query = _jooble_keyword_query(query)
    jooble_location = location or "Vietnam"
    if _normalize(location) == _normalize("Remote tại Việt Nam"):
        jooble_query = f"{jooble_query} remote"
        jooble_location = "Vietnam"

    # Provider 1: Jooble structured job feed.
    jooble_jobs, jooble_state = _fetch_jooble(
        query=jooble_query,
        location=jooble_location,
        page=1,
        result_on_page=50,
        radius=radius,
        salary=0,
    )

    # Jooble can return 0 for Vietnamese city names even when country-level
    # Vietnam pages exist. Retry once at country level only when city search is empty.
    jooble_country_fallback = False
    if (
        not jooble_jobs
        and vietnam_search
        and str(location or "").strip()
        and _normalize(location) not in {_normalize("Vietnam"), _normalize("Việt Nam")}
        and jooble_state not in {"missing_api_key", "provider_unavailable"}
    ):
        fallback_jobs, fallback_state = _fetch_jooble(
            query=jooble_query,
            location="Vietnam",
            page=1,
            result_on_page=50,
            radius="",
            salary=0,
        )
        if fallback_jobs:
            jooble_jobs = fallback_jobs
            jooble_state = fallback_state
            jooble_country_fallback = True

    # Provider 2: Brave web index over selected job boards.
    # One Brave request covers all allowed domains; no direct scraping of those sites.
    brave_jobs, brave_states = _fetch_brave_job_results(
        query=query,
        location=location or "Việt Nam",
        count_per_group=20,
    )

    if not brave_jobs and _brave_api_key():
        fallback_jobs, fallback_state = _brave_search_group(
            query=f"{query} tuyển dụng",
            location=location or "Việt Nam",
            group="company_public",
            count=20,
        )
        brave_states["fallback"] = fallback_state or "ok"
        brave_jobs.extend(fallback_jobs)

    brave_jobs = _enrich_public_ats_jobs(brave_jobs, max_enrich=10)

    # Provider 3: Remotive only outside Vietnam scope.
    remotive_jobs: list[dict[str, Any]] = []
    remotive_error = ""
    if not vietnam_search:
        remotive_jobs, remotive_error = _search_jobs(profile, query, min(limit, 20))

    combined: list[dict[str, Any]] = []
    for job in jooble_jobs + brave_jobs + remotive_jobs:
        item = dict(job)
        if jooble_country_fallback and item.get("provider") == "Jooble":
            item["location_fallback"] = True
        item["match"] = _match_job(profile, item)
        if not _job_matches_filters(
            item,
            job_type=job_type,
            level=level,
            posted_days=posted_days,
            salary_only=salary_only,
        ):
            continue
        combined.append(item)

    combined = _dedupe_jobs(combined)
    combined = _sort_jobs(combined, sort_mode)[:limit]

    notices: list[str] = []
    if jooble_state == "cache":
        notices.append("Jooble: dùng cache.")
    elif jooble_state == "missing_api_key":
        notices.append("Jooble chưa kết nối.")
    elif jooble_state == "provider_unavailable":
        notices.append("Jooble tạm thời không phản hồi.")
    if jooble_country_fallback:
        notices.append("Jooble bổ sung kết quả toàn Việt Nam vì không có kết quả riêng cho tỉnh/thành đã chọn.")

    brave_state_values = list(brave_states.values())
    if brave_state_values and all(state == "cache" for state in brave_state_values):
        notices.append("Multi-source: dùng cache.")
    elif brave_state_values and all(state == "missing_api_key" for state in brave_state_values):
        notices.append("Brave Search chưa được kết nối.")
    else:
        if any(state == "auth_error" for state in brave_state_values):
            notices.append("Brave Search: API key hoặc gói Search chưa hợp lệ.")
        if any(state == "query_error" for state in brave_state_values):
            notices.append("Brave Search: một truy vấn bị từ chối.")
        if any(state == "rate_limited" for state in brave_state_values):
            notices.append("Brave Search đang giới hạn tốc độ; hãy thử lại sau ít giây.")
        if any(state == "provider_unavailable" for state in brave_state_values):
            notices.append("Một nhóm nguồn web tạm thời không phản hồi.")

    if remotive_error and not vietnam_search:
        notices.append(remotive_error)

    return jsonify(
        {
            "jobs": combined,
            "scope": "vietnam" if vietnam_search else "international",
            "filters": {
                "job_type": job_type,
                "level": level,
                "posted_days": posted_days,
                "radius": radius,
                "salary_only": salary_only,
                "sort": sort_mode,
            },
            "providers": {
                "jooble": {
                    "configured": bool(_jooble_api_key()),
                    "count_before_filters": len(jooble_jobs),
                    "state": jooble_state or "ok",
                    "cached": jooble_state == "cache",
                    "country_fallback_used": jooble_country_fallback,
                },
                "brave": {
                    "configured": bool(_brave_api_key()),
                    "count_before_filters": len(brave_jobs),
                    "groups": brave_states,
                    "cached": bool(brave_states) and all(
                        state == "cache" for state in brave_states.values()
                    ),
                    "source_groups": list(BRAVE_SOURCE_GROUPS.keys()),
                },
                "remotive": {
                    "enabled": not vietnam_search,
                    "count": len(remotive_jobs),
                    "state": "disabled_for_vietnam" if vietnam_search else (
                        "ok" if not remotive_error else "degraded"
                    ),
                },
            },
            "provider_notice": " ".join(notices),
            "attribution": (
                "Kết quả được hợp nhất từ provider được phép và chỉ mục web; "
                "mỗi tin giữ nguồn và link gốc."
            ),
        }
    )


@bp.post("/api/career/jobs/analyze")
def career_job_analyze():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    job = {
        "source": _clean_line(payload.get("source") or "Tin bạn nhập", 80),
        "external_id": "",
        "url": _safe_url(payload.get("url")),
        "title": _clean_line(payload.get("title"), 180),
        "company": _clean_line(payload.get("company"), 140),
        "location": _clean_line(payload.get("location"), 160),
        "job_type": _clean_line(payload.get("job_type"), 60),
        "salary": _clean_line(payload.get("salary"), 120),
        "description": _clean_text(payload.get("description"), MAX_JOB_DESCRIPTION),
    }
    if not job["title"] or len(job["description"]) < 20:
        return _error("Hãy nhập tên vị trí và mô tả tuyển dụng đủ chi tiết.")
    job["match"] = _match_job(_profile(user_id), job)
    return jsonify({"job": job})


@bp.get("/api/career/jobs/saved")
def career_jobs_saved():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    return jsonify({"jobs": _saved_jobs(user_id)})


@bp.post("/api/career/jobs/save")
def career_job_save():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
    normalized = {
        "source": _clean_line(job.get("source") or "Tin bạn lưu", 80),
        "external_id": _clean_line(job.get("external_id"), 80),
        "url": _safe_url(job.get("url")),
        "title": _clean_line(job.get("title"), 180),
        "company": _clean_line(job.get("company"), 140),
        "location": _clean_line(job.get("location"), 160),
        "job_type": _clean_line(job.get("job_type"), 60),
        "salary": _clean_line(job.get("salary"), 120),
        "description": _clean_text(job.get("description"), MAX_JOB_DESCRIPTION),
    }
    if not normalized["title"]:
        return _error("Tin tuyển dụng thiếu tên vị trí.")
    match = _match_job(_profile(user_id), normalized)
    job_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO career_saved_jobs(
            id, user_id, source, external_id, url, title, company, location, job_type,
            salary, description, match_score, match_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id, user_id, normalized["source"], normalized["external_id"], normalized["url"],
            normalized["title"], normalized["company"], normalized["location"],
            normalized["job_type"], normalized["salary"], normalized["description"],
            int(match["score"]), json.dumps(match, ensure_ascii=False), now,
        ),
    )
    db.commit()
    return jsonify({"id": job_id, "match": match}), 201


@bp.delete("/api/career/jobs/saved/<job_id>")
def career_job_delete(job_id: str):
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    db = get_db()
    row = db.execute(
        "SELECT id FROM career_saved_jobs WHERE id = ? AND user_id = ?",
        (job_id, user_id),
    ).fetchone()
    if not row:
        return _error("Không tìm thấy việc đã lưu.", 404, "not_found")
    db.execute("DELETE FROM career_saved_jobs WHERE id = ? AND user_id = ?", (job_id, user_id))
    db.commit()
    return jsonify({"ok": True})
