from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Any

from flask import Blueprint, Flask, current_app, jsonify, redirect, render_template, request, session

from db import (
    finalize_message_quota,
    get_account,
    get_db,
    get_or_create_user,
    refund_message_quota,
    reserve_message_quota,
)
from safety import urgent_fallback_detected, urgent_support_message
from story_service import LifeStoryService, LifeStoryServiceError


bp = Blueprint("life", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id() -> str | None:
    value = str(session.get("account_id", "") or "").strip()
    return value if value and get_account(value) else None


def _auth_error():
    response = jsonify({"error": "Bạn cần đăng nhập trước.", "code": "auth_required"})
    response.status_code = 401
    return response


def _error(message: str, status: int = 400, code: str = "bad_request"):
    response = jsonify({"error": message, "code": code})
    response.status_code = status
    return response


def _json_dict(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _serialize_entry(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = _json_dict(data.pop("metadata_json", "{}"))
    return data


def _serialize_thread(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _serialize_session(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def init_life_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS life_entries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_type TEXT NOT NULL CHECK(entry_type IN ('autobiography', 'unsent')),
            title TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            rewritten_text TEXT NOT NULL,
            style TEXT NOT NULL DEFAULT 'honest',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS life_threads (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            source_entry_id TEXT,
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'unsaid'
                CHECK(status IN ('unsaid', 'waiting', 'deciding', 'letting_go', 'closed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(source_entry_id) REFERENCES life_entries(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS rehearsal_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            other_person TEXT NOT NULL,
            situation TEXT NOT NULL,
            goal TEXT NOT NULL DEFAULT '',
            progress TEXT NOT NULL DEFAULT 'opening',
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'closed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rehearsal_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'counterpart', 'coach', 'suggestion')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES rehearsal_sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_life_entries_user_date
        ON life_entries(user_id, entry_date DESC, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_life_threads_user_status
        ON life_threads(user_id, status, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_rehearsal_sessions_user_updated
        ON rehearsal_sessions(user_id, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_rehearsal_messages_session
        ON rehearsal_messages(session_id, id ASC);
        """
    )
    db.commit()


def register_life_features(app: Flask) -> None:
    service = LifeStoryService(
        api_key=app.config.get("OPENAI_API_KEY", ""),
        model=app.config.get("OPENAI_MODEL", "gpt-5.6-luna"),
    )
    app.extensions["life_story_service"] = service
    with app.app_context():
        init_life_db()
    app.register_blueprint(bp)


def _service() -> LifeStoryService:
    service = current_app.extensions.get("life_story_service")
    if not isinstance(service, LifeStoryService):
        raise LifeStoryServiceError("Tính năng Cuốn đời tôi chưa được khởi tạo.")
    return service


def _reserve(user_id: str) -> dict[str, Any] | None:
    return reserve_message_quota(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )


def _run_ai(user_id: str, callback):
    quota_event = _reserve(user_id)
    if not quota_event:
        raise PermissionError("Bạn đã dùng hết lượt hiện có.")
    event_id = str(quota_event["id"])
    try:
        result = callback()
        if not finalize_message_quota(event_id):
            raise LifeStoryServiceError("Không thể chốt lượt vừa sử dụng.")
        return result
    except Exception:
        refund_message_quota(event_id)
        raise


LIFE_PAGE_ROUTES = {
    "overview": "/timeline",
    "timeline": "/timeline",
    "autobiography": "/story",
    "story": "/story",
    "unsent": "/unsent",
    "rehearsal": "/rehearsal",
    "threads": "/threads",
}


def _render_life_page(template_name: str, page_name: str):
    user_id = _user_id()
    if not user_id:
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template(
        template_name,
        life_page=page_name,
        display_name=account.get("display_name", "Bạn"),
    )


@bp.get("/life")
def life_home():
    # Tương thích link V21/V22 cũ nhưng đưa mỗi chức năng sang một trang riêng.
    requested = str(request.args.get("tab", "timeline")).strip().lower()
    return redirect(LIFE_PAGE_ROUTES.get(requested, "/timeline"))


@bp.get("/story")
def story_page():
    return _render_life_page("story.html", "story")


@bp.get("/unsent")
def unsent_page():
    return _render_life_page("unsent.html", "unsent")


@bp.get("/rehearsal")
def rehearsal_page():
    return _render_life_page("rehearsal.html", "rehearsal")


@bp.get("/threads")
def threads_page():
    return _render_life_page("threads.html", "threads")


@bp.get("/timeline")
def timeline_page():
    return _render_life_page("timeline.html", "timeline")


@bp.get("/api/life/overview")
def overview():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    entries = db.execute(
        """
        SELECT * FROM life_entries
        WHERE user_id = ?
        ORDER BY entry_date DESC, created_at DESC
        LIMIT 100
        """,
        (user_id,),
    ).fetchall()
    threads = db.execute(
        """
        SELECT * FROM life_threads
        WHERE user_id = ?
        ORDER BY CASE status WHEN 'closed' THEN 1 ELSE 0 END, updated_at DESC
        LIMIT 100
        """,
        (user_id,),
    ).fetchall()
    sessions = db.execute(
        """
        SELECT * FROM rehearsal_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()
    return jsonify(
        {
            "entries": [_serialize_entry(row) for row in entries],
            "threads": [_serialize_thread(row) for row in threads],
            "sessions": [_serialize_session(row) for row in sessions],
        }
    )


@bp.post("/api/life/autobiography")
def create_autobiography():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    raw_text = str(payload.get("raw_text", "")).strip()
    style = str(payload.get("style", "honest")).strip()
    entry_date = str(payload.get("entry_date", date.today().isoformat())).strip()
    if len(raw_text) < 20:
        return _error("Kể thêm một chút để câu chuyện có đủ chất liệu.")
    if len(raw_text) > 12000:
        return _error("Bản ghi tối đa 12.000 ký tự.")
    if urgent_fallback_detected(raw_text):
        return jsonify(
            {
                "urgent": True,
                "message": urgent_support_message("minh_ban", "vi"),
            }
        )

    try:
        result = _run_ai(
            user_id,
            lambda: _service().create_autobiography(
                raw_text=raw_text,
                style=style,
                entry_date=entry_date,
            ),
        )
    except PermissionError as exc:
        return _error(str(exc), 429, "quota_exhausted")
    except LifeStoryServiceError as exc:
        return _error(str(exc), 503, "story_service_error")

    title = str(result.get("title", "Một ngày của tôi")).strip()[:120]
    narrative = str(result.get("narrative", "")).strip()
    closing_line = str(result.get("closing_line", "")).strip()
    rewritten = narrative
    if closing_line and closing_line not in rewritten:
        rewritten = f"{rewritten}\n\n{closing_line}".strip()
    entry_id = str(uuid.uuid4())
    now = _now()
    metadata = {
        "closing_line": closing_line,
        "tags": result.get("tags", []),
        "open_threads": result.get("open_threads", []),
    }
    db = get_db()
    db.execute(
        """
        INSERT INTO life_entries(
            id, user_id, entry_date, entry_type, title, raw_text,
            rewritten_text, style, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, 'autobiography', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_id,
            user_id,
            entry_date,
            title,
            raw_text,
            rewritten,
            style,
            json.dumps(metadata, ensure_ascii=False),
            now,
            now,
        ),
    )
    created_threads: list[dict[str, Any]] = []
    for item in result.get("open_threads", [])[:3]:
        if not isinstance(item, dict):
            continue
        thread_title = str(item.get("title", "")).strip()[:120]
        if not thread_title:
            continue
        status = str(item.get("status", "unsaid"))
        if status not in {"unsaid", "waiting", "deciding", "letting_go", "closed"}:
            status = "unsaid"
        thread_id = str(uuid.uuid4())
        detail = str(item.get("detail", "")).strip()[:1000]
        db.execute(
            """
            INSERT INTO life_threads(
                id, user_id, source_entry_id, title, detail, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (thread_id, user_id, entry_id, thread_title, detail, status, now, now),
        )
        created_threads.append(
            {
                "id": thread_id,
                "user_id": user_id,
                "source_entry_id": entry_id,
                "title": thread_title,
                "detail": detail,
                "status": status,
                "created_at": now,
                "updated_at": now,
            }
        )
    db.commit()
    row = db.execute("SELECT * FROM life_entries WHERE id = ?", (entry_id,)).fetchone()
    return jsonify(
        {
            "ok": True,
            "entry": _serialize_entry(row),
            "threads": created_threads,
        }
    ), 201


@bp.post("/api/life/unsent")
def create_unsent():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    raw_text = str(payload.get("raw_text", "")).strip()
    relation = str(payload.get("relation", "")).strip()[:120]
    output_type = str(payload.get("output_type", "unsent_letter")).strip()
    if len(raw_text) < 10:
        return _error("Viết thêm một chút về điều bạn đang muốn nói.")
    if len(raw_text) > 8000:
        return _error("Nội dung tối đa 8.000 ký tự.")
    if urgent_fallback_detected(raw_text):
        return jsonify(
            {
                "urgent": True,
                "message": urgent_support_message("minh_ban", "vi"),
            }
        )
    try:
        result = _run_ai(
            user_id,
            lambda: _service().create_unsent_piece(
                raw_text=raw_text,
                relation=relation,
                output_type=output_type,
            ),
        )
    except PermissionError as exc:
        return _error(str(exc), 429, "quota_exhausted")
    except LifeStoryServiceError as exc:
        return _error(str(exc), 503, "story_service_error")

    entry_id = str(uuid.uuid4())
    now = _now()
    title = str(result.get("title", "Điều chưa từng nói")).strip()[:120]
    rewritten = str(result.get("rewritten", "")).strip()
    metadata = {
        "relation": relation,
        "output_type": output_type,
        "sendable_version": str(result.get("sendable_version", "")).strip(),
        "core_feeling": str(result.get("core_feeling", "")).strip(),
        "caution": str(result.get("caution", "")).strip(),
    }
    db = get_db()
    db.execute(
        """
        INSERT INTO life_entries(
            id, user_id, entry_date, entry_type, title, raw_text,
            rewritten_text, style, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, 'unsent', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_id,
            user_id,
            date.today().isoformat(),
            title,
            raw_text,
            rewritten,
            output_type,
            json.dumps(metadata, ensure_ascii=False),
            now,
            now,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM life_entries WHERE id = ?", (entry_id,)).fetchone()
    return jsonify({"ok": True, "entry": _serialize_entry(row)}), 201


@bp.patch("/api/life/entries/<entry_id>")
def update_entry(entry_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()[:120]
    rewritten_text = str(payload.get("rewritten_text", "")).strip()[:20000]
    if not title or not rewritten_text:
        return _error("Tiêu đề và nội dung không được để trống.")
    db = get_db()
    cursor = db.execute(
        """
        UPDATE life_entries
        SET title = ?, rewritten_text = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (title, rewritten_text, _now(), entry_id, user_id),
    )
    db.commit()
    if cursor.rowcount <= 0:
        return _error("Không tìm thấy bản ghi.", 404, "not_found")
    row = db.execute("SELECT * FROM life_entries WHERE id = ?", (entry_id,)).fetchone()
    return jsonify({"ok": True, "entry": _serialize_entry(row)})


@bp.delete("/api/life/entries/<entry_id>")
def delete_entry(entry_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    cursor = db.execute(
        "DELETE FROM life_entries WHERE id = ? AND user_id = ?",
        (entry_id, user_id),
    )
    db.commit()
    if cursor.rowcount <= 0:
        return _error("Không tìm thấy bản ghi.", 404, "not_found")
    return jsonify({"ok": True})


@bp.post("/api/life/threads")
def create_thread():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()[:120]
    detail = str(payload.get("detail", "")).strip()[:1000]
    status = str(payload.get("status", "unsaid")).strip()
    if not title:
        return _error("Tên chuyện đang trống.")
    if status not in {"unsaid", "waiting", "deciding", "letting_go", "closed"}:
        status = "unsaid"
    thread_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO life_threads(
            id, user_id, source_entry_id, title, detail, status, created_at, updated_at
        ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
        """,
        (thread_id, user_id, title, detail, status, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM life_threads WHERE id = ?", (thread_id,)).fetchone()
    return jsonify({"ok": True, "thread": _serialize_thread(row)}), 201


@bp.patch("/api/life/threads/<thread_id>")
def update_thread(thread_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "")).strip()
    title = str(payload.get("title", "")).strip()[:120]
    detail = str(payload.get("detail", "")).strip()[:1000]
    if status not in {"unsaid", "waiting", "deciding", "letting_go", "closed"}:
        return _error("Trạng thái không hợp lệ.")
    db = get_db()
    current = db.execute(
        "SELECT * FROM life_threads WHERE id = ? AND user_id = ?",
        (thread_id, user_id),
    ).fetchone()
    if not current:
        return _error("Không tìm thấy chuyện này.", 404, "not_found")
    cursor = db.execute(
        """
        UPDATE life_threads
        SET title = ?, detail = ?, status = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title or str(current["title"]),
            detail if "detail" in payload else str(current["detail"]),
            status,
            _now(),
            thread_id,
            user_id,
        ),
    )
    db.commit()
    if cursor.rowcount <= 0:
        return _error("Không thể cập nhật.", 400)
    row = db.execute("SELECT * FROM life_threads WHERE id = ?", (thread_id,)).fetchone()
    return jsonify({"ok": True, "thread": _serialize_thread(row)})


@bp.delete("/api/life/threads/<thread_id>")
def delete_thread(thread_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    cursor = db.execute(
        "DELETE FROM life_threads WHERE id = ? AND user_id = ?",
        (thread_id, user_id),
    )
    db.commit()
    if cursor.rowcount <= 0:
        return _error("Không tìm thấy chuyện này.", 404, "not_found")
    return jsonify({"ok": True})


@bp.post("/api/life/rehearsal/start")
def start_rehearsal():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    other_person = str(payload.get("other_person", "")).strip()[:120]
    situation = str(payload.get("situation", "")).strip()[:2000]
    goal = str(payload.get("goal", "")).strip()[:1000]
    opening = str(payload.get("opening", "")).strip()[:2000]
    if not other_person or not situation or not opening:
        return _error("Cần có người đối diện, tình huống và câu mở đầu.")
    if urgent_fallback_detected(opening + " " + situation):
        return jsonify(
            {
                "urgent": True,
                "message": urgent_support_message("minh_ban", "vi"),
            }
        )
    try:
        result = _run_ai(
            user_id,
            lambda: _service().start_rehearsal(
                other_person=other_person,
                situation=situation,
                goal=goal,
                opening=opening,
            ),
        )
    except PermissionError as exc:
        return _error(str(exc), 429, "quota_exhausted")
    except LifeStoryServiceError as exc:
        return _error(str(exc), 503, "story_service_error")

    session_id = str(uuid.uuid4())
    now = _now()
    progress = str(result.get("progress", "opening"))
    db = get_db()
    db.execute(
        """
        INSERT INTO rehearsal_sessions(
            id, user_id, other_person, situation, goal, progress, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (session_id, user_id, other_person, situation, goal, progress, now, now),
    )
    messages = [
        ("user", opening),
        ("counterpart", str(result.get("counterpart_reply", "")).strip()),
        ("coach", str(result.get("coach_note", "")).strip()),
        ("suggestion", str(result.get("suggested_reply", "")).strip()),
    ]
    for role, content in messages:
        if content:
            db.execute(
                "INSERT INTO rehearsal_messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
    db.commit()
    return jsonify({"ok": True, "session_id": session_id, "result": result}), 201


@bp.get("/api/life/rehearsal/<session_id>")
def get_rehearsal(session_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    session_row = db.execute(
        "SELECT * FROM rehearsal_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not session_row:
        return _error("Không tìm thấy buổi luyện nói.", 404, "not_found")
    messages = db.execute(
        "SELECT role, content, created_at FROM rehearsal_messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    return jsonify(
        {
            "session": _serialize_session(session_row),
            "messages": [dict(row) for row in messages],
        }
    )


@bp.post("/api/life/rehearsal/<session_id>/reply")
def reply_rehearsal(session_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    user_message = str(payload.get("message", "")).strip()[:2000]
    if not user_message:
        return _error("Câu trả lời đang trống.")
    db = get_db()
    session_row = db.execute(
        "SELECT * FROM rehearsal_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not session_row:
        return _error("Không tìm thấy buổi luyện nói.", 404, "not_found")
    transcript_rows = db.execute(
        """
        SELECT role, content FROM rehearsal_messages
        WHERE session_id = ? AND role IN ('user', 'counterpart')
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()
    transcript = [dict(row) for row in transcript_rows]
    try:
        result = _run_ai(
            user_id,
            lambda: _service().continue_rehearsal(
                other_person=str(session_row["other_person"]),
                situation=str(session_row["situation"]),
                goal=str(session_row["goal"]),
                transcript=transcript,
                user_message=user_message,
            ),
        )
    except PermissionError as exc:
        return _error(str(exc), 429, "quota_exhausted")
    except LifeStoryServiceError as exc:
        return _error(str(exc), 503, "story_service_error")

    now = _now()
    messages = [
        ("user", user_message),
        ("counterpart", str(result.get("counterpart_reply", "")).strip()),
        ("coach", str(result.get("coach_note", "")).strip()),
        ("suggestion", str(result.get("suggested_reply", "")).strip()),
    ]
    for role, content in messages:
        if content:
            db.execute(
                "INSERT INTO rehearsal_messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
    progress = str(result.get("progress", session_row["progress"]))
    db.execute(
        "UPDATE rehearsal_sessions SET progress = ?, updated_at = ? WHERE id = ?",
        (progress, now, session_id),
    )
    db.commit()
    return jsonify({"ok": True, "result": result})


@bp.post("/api/life/rehearsal/<session_id>/close")
def close_rehearsal(session_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    cursor = db.execute(
        """
        UPDATE rehearsal_sessions
        SET status = 'closed', progress = 'closing', updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (_now(), session_id, user_id),
    )
    db.commit()
    if cursor.rowcount <= 0:
        return _error("Không tìm thấy buổi luyện nói.", 404, "not_found")
    return jsonify({"ok": True})
