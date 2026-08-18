from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, Flask, current_app, g, jsonify, redirect, render_template, request, send_file, session

from astrology_service import AstrologyService, AstrologyServiceError, calculate_birth_profile, normalize_ui_language
from tuvi_engine import TuViEngineError, render_full_tuvi_chart_image
from db import (
    finalize_message_quota,
    get_account,
    get_db,
    get_quota_status,
    refund_message_quota,
    reserve_message_quota,
)

bp = Blueprint("astrology", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id() -> str | None:
    value = str(session.get("account_id", "")).strip()
    return value or None


def _service() -> AstrologyService:
    return current_app.extensions["astrology_service"]


def _quota(user_id: str) -> dict[str, Any]:
    return get_quota_status(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )


def _error(message: str, status: int = 400, code: str = "bad_request", **extra):
    payload: dict[str, Any] = {"error": message, "code": code}
    payload.update(extra)
    return jsonify(payload), status


def _auth_error():
    return _error("Bạn cần đăng nhập trước.", 401, "auth_required")


def _reserve(user_id: str) -> dict[str, Any] | None:
    event = reserve_message_quota(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )
    if event:
        g.pending_quota_event_id = str(event["id"])
    return event


def _finish_quota(event_id: str) -> None:
    finalize_message_quota(event_id)
    g.pending_quota_event_id = ""


def init_astrology_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS astrology_profiles (
            user_id TEXT PRIMARY KEY,
            birth_date TEXT NOT NULL,
            birth_time TEXT NOT NULL DEFAULT '',
            birth_place TEXT NOT NULL DEFAULT '',
            gender TEXT NOT NULL DEFAULT '',
            profile_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS astrology_readings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            reading_json TEXT NOT NULL,
            ui_language TEXT NOT NULL DEFAULT 'vi',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS astrology_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            meta_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(reading_id) REFERENCES astrology_readings(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_astrology_readings_user_created
        ON astrology_readings(user_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_astrology_messages_reading
        ON astrology_messages(reading_id, id ASC);
        """
    )
    db.commit()


def register_astrology(app: Flask) -> None:
    service = app.config.get("ASTROLOGY_SERVICE") or AstrologyService(
        api_key=app.config.get("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_ASTROLOGY_MODEL", app.config.get("OPENAI_MODEL", "gpt-5.6-luna")),
        reasoning_effort=os.getenv("OPENAI_ASTROLOGY_REASONING_EFFORT", "low"),
        max_output_tokens=int(os.getenv("OPENAI_ASTROLOGY_MAX_OUTPUT_TOKENS", "2200")),
    )
    app.extensions["astrology_service"] = service
    with app.app_context():
        init_astrology_db()
    app.register_blueprint(bp)


def _latest_reading(user_id: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM astrology_readings WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()


def _serialize_reading(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    try:
        item["profile"] = json.loads(item.pop("profile_json"))
    except Exception:
        item["profile"] = {}
        item.pop("profile_json", None)
    try:
        item["reading"] = json.loads(item.pop("reading_json"))
    except Exception:
        item["reading"] = {}
        item.pop("reading_json", None)
    return item


def _profile_has_star_data(profile: dict[str, Any] | None) -> bool:
    """True khi lá số đã parse được dữ liệu sao thực sự."""
    chart = (profile or {}).get("tuvi_chart") or {}
    if chart.get("engine") == "tuvi-mcp-server" and isinstance(chart.get("raw_chart"), dict):
        return True
    palaces = chart.get("palaces") or []
    return sum(len((p or {}).get("stars") or []) for p in palaces if isinstance(p, dict)) > 0


def _repair_saved_chart_if_needed(
    user_id: str,
    row: sqlite3.Row | None,
    serialized: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Tự sửa lá số cũ bị parser rỗng, không trừ quota.

    Chỉ rebuild phần birth profile / tuvi_chart. Không gọi AI lại ở đây.
    """
    if not row or not serialized:
        return serialized

    profile = serialized.get("profile") or {}
    if _profile_has_star_data(profile):
        return serialized

    birth_date = str(profile.get("birth_date", "")).strip()
    birth_time = str(profile.get("birth_time", "")).strip()
    gender = str(profile.get("gender", "")).strip()
    if not birth_date or not birth_time or gender not in {"male", "female"}:
        return serialized

    account = get_account(user_id) or {}
    try:
        repaired_profile = calculate_birth_profile(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=str(profile.get("birth_place", "")).strip(),
            gender=gender,
            display_name=str(
                profile.get("display_name")
                or account.get("display_name")
                or "Bạn"
            ),
        )
    except AstrologyServiceError:
        return serialized

    if not _profile_has_star_data(repaired_profile):
        return serialized

    now = _now()
    payload = json.dumps(repaired_profile, ensure_ascii=False)
    db = get_db()
    try:
        db.execute(
            """
            UPDATE astrology_readings
            SET profile_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (payload, now, str(row["id"]), user_id),
        )
        db.execute(
            """
            UPDATE astrology_profiles
            SET profile_json = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (payload, now, user_id),
        )
        db.commit()
        serialized["profile"] = repaired_profile
        serialized["chart_repaired"] = True
    except Exception:
        db.rollback()

    return serialized


def _messages(user_id: str, reading_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT role, content, meta_json, created_at
        FROM astrology_messages
        WHERE user_id = ? AND reading_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (user_id, reading_id, max(1, min(int(limit), 100))),
    ).fetchall()
    result = []
    for row in reversed(rows):
        item = dict(row)
        try:
            item["meta"] = json.loads(item.pop("meta_json") or "{}")
        except Exception:
            item["meta"] = {}
            item.pop("meta_json", None)
        result.append(item)
    return result


@bp.get("/astrology")
def astrology_page():
    user_id = _user_id()
    if not user_id:
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template(
        "astrology/index.html",
        display_name=account.get("display_name", "Bạn"),
        ai_configured=bool(_service().is_configured),
    )


@bp.get("/api/astrology/overview")
def astrology_overview():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    row = _latest_reading(user_id)
    serialized = _serialize_reading(row)
    serialized = _repair_saved_chart_if_needed(user_id, row, serialized)
    return jsonify({
        "reading": serialized,
        "messages": _messages(user_id, str(row["id"]), 40) if row else [],
        "quota": _quota(user_id),
        "mode": "online-ai" if _service().is_configured else "offline-demo",
    })


@bp.get("/api/astrology/chart-image/<reading_id>.png")
def astrology_chart_image(reading_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    row = get_db().execute(
        "SELECT profile_json FROM astrology_readings WHERE id = ? AND user_id = ? LIMIT 1",
        (str(reading_id), user_id),
    ).fetchone()
    if not row:
        return _error("Không tìm thấy lá số này.", 404, "reading_not_found")
    try:
        profile = json.loads(row["profile_json"] or "{}")
    except Exception:
        profile = {}
    try:
        image_path = render_full_tuvi_chart_image(
            birth_date=str(profile.get("birth_date", "")),
            birth_time=str(profile.get("birth_time", "")),
            gender=str(profile.get("gender", "")),
            display_name=str(profile.get("display_name", "") or "Khách"),
            current_year=datetime.now().year,
            time_zone=7,
        )
        data = Path(image_path).read_bytes()
    except (TuViEngineError, OSError) as exc:
        return _error(str(exc), 500, "chart_render_error")
    return send_file(io.BytesIO(data), mimetype="image/png", download_name="la-so-tu-vi.png", max_age=0)


@bp.post("/api/astrology/chart")
def astrology_chart():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    account = get_account(user_id) or {}
    try:
        profile = calculate_birth_profile(
            birth_date=str(payload.get("birth_date", "")).strip(),
            birth_time=str(payload.get("birth_time", "")).strip(),
            birth_place=str(payload.get("birth_place", "")).strip(),
            gender=str(payload.get("gender", "")).strip(),
            display_name=str(account.get("display_name", "Bạn")),
        )
    except AstrologyServiceError as exc:
        return _error(str(exc), 400, "chart_input_error")

    event = _reserve(user_id)
    if not event:
        return _error("Bạn đã hết lượt hiện có.", 429, "quota_exhausted", quota=_quota(user_id))

    ui_language = normalize_ui_language(str(payload.get("ui_language", "vi")))
    reading = _service().generate_reading(profile=profile, ui_language=ui_language)
    reading_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """
            INSERT INTO astrology_profiles(
                user_id, birth_date, birth_time, birth_place, gender,
                profile_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                birth_date = excluded.birth_date,
                birth_time = excluded.birth_time,
                birth_place = excluded.birth_place,
                gender = excluded.gender,
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                profile["birth_date"],
                profile.get("birth_time", ""),
                profile.get("birth_place", ""),
                profile.get("gender", ""),
                json.dumps(profile, ensure_ascii=False),
                now,
                now,
            ),
        )
        db.execute(
            """
            INSERT INTO astrology_readings(
                id, user_id, profile_json, reading_json, ui_language, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading_id,
                user_id,
                json.dumps(profile, ensure_ascii=False),
                json.dumps(reading, ensure_ascii=False),
                ui_language,
                now,
                now,
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        refund_message_quota(str(event["id"]))
        g.pending_quota_event_id = ""
        raise

    _finish_quota(str(event["id"]))
    return jsonify({
        "reading": {
            "id": reading_id,
            "profile": profile,
            "reading": reading,
            "ui_language": ui_language,
            "created_at": now,
        },
        "quota": _quota(user_id),
        "quota_source": event.get("source", ""),
    }), 201


@bp.post("/api/astrology/ask")
def astrology_ask():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question:
        return _error("Nhập câu bạn muốn hỏi trước đã.")
    if len(question) > 1200:
        return _error("Câu hỏi tối đa 1200 ký tự.")

    reading_id = str(payload.get("reading_id", "")).strip()
    if reading_id:
        row = get_db().execute(
            "SELECT * FROM astrology_readings WHERE id = ? AND user_id = ?",
            (reading_id, user_id),
        ).fetchone()
    else:
        row = _latest_reading(user_id)
    if not row:
        return _error("Bạn cần tạo lá số trước.", 409, "reading_required")

    serialized = _serialize_reading(row) or {}
    history_rows = _messages(user_id, str(row["id"]), 16)
    history = [{"role": item["role"], "content": item["content"]} for item in history_rows]
    ui_language = normalize_ui_language(str(payload.get("ui_language") or row["ui_language"] or "vi"))

    event = _reserve(user_id)
    if not event:
        return _error("Bạn đã hết lượt hiện có.", 429, "quota_exhausted", quota=_quota(user_id))

    answer = _service().answer_question(
        profile=serialized.get("profile") or {},
        reading=serialized.get("reading") or {},
        question=question,
        history=history,
        ui_language=ui_language,
    )
    now = _now()
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO astrology_messages(reading_id, user_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
            (row["id"], user_id, question, now),
        )
        db.execute(
            """
            INSERT INTO astrology_messages(reading_id, user_id, role, content, meta_json, created_at)
            VALUES (?, ?, 'assistant', ?, ?, ?)
            """,
            (
                row["id"],
                user_id,
                str(answer.get("answer", "")),
                json.dumps({
                    "takeaways": answer.get("takeaways", []),
                    "caution": answer.get("caution", ""),
                    "used_demo": bool(answer.get("used_demo", False)),
                }, ensure_ascii=False),
                now,
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        refund_message_quota(str(event["id"]))
        g.pending_quota_event_id = ""
        raise

    _finish_quota(str(event["id"]))
    return jsonify({
        "answer": answer,
        "reading_id": str(row["id"]),
        "quota": _quota(user_id),
        "quota_source": event.get("source", ""),
    })
