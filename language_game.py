from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    Flask,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

from db import (
    finalize_message_quota,
    get_account,
    get_db,
    get_quota_status,
    get_usage_total,
    refund_message_quota,
    reserve_message_quota,
)
from language_service import LanguageGameService


BASE_DIR = Path(__file__).resolve().parent
bp = Blueprint("language_game", __name__)

VALID_LEVELS = {"A1-A2", "B1-B2", "C1-C2"}
VALID_HUMOR = {"chaotic-meme", "deadpan", "dramatic", "gentle"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id() -> str | None:
    value = str(session.get("account_id", "")).strip()
    return value or None


def _auth_error():
    return jsonify({"error": "Bạn cần đăng nhập trước.", "code": "auth_required"}), 401


def _error(message: str, status: int = 400, code: str = "bad_request", **extra):
    payload: dict[str, Any] = {"error": message, "code": code}
    payload.update(extra)
    return jsonify(payload), status


def _quota(user_id: str) -> dict[str, Any]:
    return get_quota_status(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )


def _scenes() -> list[dict[str, Any]]:
    return current_app.extensions["language_scenes"]


def _scene_map() -> dict[str, dict[str, Any]]:
    return current_app.extensions["language_scene_map"]


def _service() -> LanguageGameService:
    return current_app.extensions["language_game_service"]


def init_language_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS language_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            level TEXT NOT NULL,
            humor TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 50,
            progress INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'completed', 'abandoned')),
            turns_used INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('player', 'npc')),
            text TEXT NOT NULL,
            narrator TEXT NOT NULL DEFAULT '',
            feedback TEXT NOT NULL DEFAULT '',
            suggestion TEXT NOT NULL DEFAULT '',
            quality TEXT NOT NULL DEFAULT '',
            mood TEXT NOT NULL DEFAULT '',
            effect TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES language_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_language_sessions_user_updated
        ON language_sessions(user_id, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_language_messages_session_id
        ON language_messages(session_id, id ASC);
        """
    )
    db.commit()


def register_language_game(app: Flask) -> None:
    scenes_path = Path(app.config.get("LANGUAGE_SCENES_PATH") or BASE_DIR / "data" / "language_scenes.json")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    if not isinstance(scenes, list):
        raise RuntimeError("data/language_scenes.json phải là một danh sách cảnh.")
    scene_map = {str(item["id"]): item for item in scenes}

    service = app.config.get("LANGUAGE_GAME_SERVICE") or LanguageGameService(
        api_key=app.config.get("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_LANGUAGE_MODEL", app.config.get("OPENAI_MODEL", "gpt-5.6-luna")),
        reasoning_effort=os.getenv("OPENAI_LANGUAGE_REASONING_EFFORT", "low"),
        max_output_tokens=int(os.getenv("OPENAI_LANGUAGE_MAX_OUTPUT_TOKENS", "1400")),
    )
    app.extensions["language_scenes"] = scenes
    app.extensions["language_scene_map"] = scene_map
    app.extensions["language_game_service"] = service

    with app.app_context():
        init_language_db()
    app.register_blueprint(bp)


def _serialize_session(row: sqlite3.Row, *, include_scene: bool = True) -> dict[str, Any]:
    item = dict(row)
    if include_scene:
        scene = _scene_map().get(str(item.get("scene_id", "")), {})
        item["scene"] = {
            "id": scene.get("id", item.get("scene_id", "")),
            "title": scene.get("title", "Cảnh đã lưu"),
            "subtitle": scene.get("subtitle", ""),
            "language": scene.get("language", ""),
            "image": scene.get("image", ""),
            "npc_name": scene.get("npc_name", "NPC"),
        }
    item["completed"] = item.get("status") == "completed"
    return item


def _load_session(user_id: str, session_id: str) -> sqlite3.Row | None:
    return get_db().execute(
        """
        SELECT * FROM language_sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()


def _history(session_id: str, limit: int = 40) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT role, text, narrator, feedback, suggestion, quality, mood, effect, created_at
        FROM language_messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, max(1, min(int(limit), 200))),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


@bp.get("/language")
def language_page():
    user_id = _user_id()
    if not user_id:
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template(
        "language/index.html",
        scenes=_scenes(),
        display_name=account.get("display_name", "Bạn"),
        ai_configured=bool(_service().is_configured),
    )


@bp.get("/api/language/status")
def language_status():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    return jsonify(
        {
            "ok": True,
            "mode": "online-ai" if _service().is_configured else "offline-demo",
            "quota": _quota(user_id),
        }
    )


@bp.get("/api/language/overview")
def language_overview():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    rows = get_db().execute(
        """
        SELECT * FROM language_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()
    sessions = [_serialize_session(row) for row in rows]
    completed = sum(item["status"] == "completed" for item in sessions)
    active = next((item for item in sessions if item["status"] == "active"), None)
    return jsonify(
        {
            "sessions": sessions,
            "completed_count": completed,
            "active_session": active,
            "quota": _quota(user_id),
        }
    )


@bp.post("/api/language/start")
def language_start():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    scene_id = str(payload.get("scene_id", "")).strip()
    scene = _scene_map().get(scene_id)
    if not scene:
        return _error("Không tìm thấy cảnh.", 404, "scene_not_found")

    level = str(payload.get("level", "A1-A2")).strip()
    humor = str(payload.get("humor", "chaotic-meme")).strip()
    if level not in VALID_LEVELS:
        return _error("Trình độ không hợp lệ.")
    if humor not in VALID_HUMOR:
        return _error("Phong cách nhập vai không hợp lệ.")

    session_id = str(uuid.uuid4())
    now = _now()
    opening = str(scene.get("opening", "...")).strip()
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute(
            """
            INSERT INTO language_sessions(
                id, user_id, scene_id, level, humor, score, progress,
                status, turns_used, started_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 50, 0, 'active', 0, ?, ?)
            """,
            (session_id, user_id, scene_id, level, humor, now, now),
        )
        db.execute(
            """
            INSERT INTO language_messages(session_id, user_id, role, text, created_at)
            VALUES (?, ?, 'npc', ?, ?)
            """,
            (session_id, user_id, opening, now),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return jsonify(
        {
            "session_id": session_id,
            "scene": scene,
            "opening": opening,
            "score": 50,
            "progress": 0,
            "status": "active",
        }
    ), 201


@bp.get("/api/language/sessions/<session_id>")
def language_session_detail(session_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    row = _load_session(user_id, session_id)
    if not row:
        return _error("Không tìm thấy phiên chơi.", 404, "session_not_found")
    scene = _scene_map().get(str(row["scene_id"]))
    if not scene:
        return _error("Cảnh của phiên chơi không còn tồn tại.", 409, "scene_missing")
    return jsonify(
        {
            "session": _serialize_session(row),
            "scene": scene,
            "messages": _history(session_id, limit=100),
        }
    )


@bp.post("/api/language/respond")
def language_respond():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    message = str(payload.get("message", "")).strip()
    if not message:
        return _error("Nhập câu trả lời trước đã.")
    max_chars = int(current_app.config.get("LANGUAGE_MAX_MESSAGE_CHARS", 500))
    if len(message) > max_chars:
        return _error(f"Câu trả lời tối đa {max_chars} ký tự.")

    row = _load_session(user_id, session_id)
    if not row:
        return _error("Phiên chơi không tồn tại hoặc không thuộc tài khoản này.", 404, "session_not_found")
    if str(row["status"]) != "active":
        return _error("Cảnh này đã kết thúc. Hãy bắt đầu một lượt mới.", 409, "session_closed")
    scene = _scene_map().get(str(row["scene_id"]))
    if not scene:
        return _error("Cảnh của phiên chơi không còn tồn tại.", 409, "scene_missing")

    quota_event = reserve_message_quota(
        user_id,
        welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
        daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
    )
    if not quota_event:
        return _error(
            "Bạn đã dùng hết lượt hiện có. Hãy quay lại ngày mai hoặc mua thêm lượt.",
            429,
            "quota_exhausted",
            quota=_quota(user_id),
        )
    event_id = str(quota_event["id"])
    g.pending_quota_event_id = event_id

    state = {
        "level": str(row["level"]),
        "humor": str(row["humor"]),
        "score": int(row["score"]),
        "progress": int(row["progress"]),
    }
    history = [
        {"role": item["role"], "text": item["text"]}
        for item in _history(session_id, limit=12)
    ]

    try:
        result = _service().reply(
            scene=scene,
            state=state,
            message=message,
            history=history,
        )
        now = _now()
        status = "completed" if result.completed else "active"
        completed_at = now if result.completed else None
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                """
                INSERT INTO language_messages(session_id, user_id, role, text, created_at)
                VALUES (?, ?, 'player', ?, ?)
                """,
                (session_id, user_id, message, now),
            )
            db.execute(
                """
                INSERT INTO language_messages(
                    session_id, user_id, role, text, narrator, feedback,
                    suggestion, quality, mood, effect, created_at
                ) VALUES (?, ?, 'npc', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    result.reply,
                    result.narrator,
                    result.feedback,
                    result.suggestion,
                    result.quality,
                    result.mood,
                    result.effect,
                    now,
                ),
            )
            db.execute(
                """
                UPDATE language_sessions
                SET score = ?, progress = ?, status = ?, turns_used = turns_used + 1,
                    updated_at = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ? AND user_id = ?
                """,
                (
                    result.score,
                    result.progress,
                    status,
                    now,
                    completed_at,
                    session_id,
                    user_id,
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        if not finalize_message_quota(event_id):
            raise RuntimeError("Không thể chốt lượt vừa sử dụng.")
        g.pending_quota_event_id = ""

        return jsonify(
            {
                **result.as_dict(),
                "status": status,
                "quota": _quota(user_id),
                "quota_source": quota_event["source"],
                "used_total": get_usage_total(user_id),
            }
        )
    except Exception:
        try:
            refund_message_quota(event_id)
        finally:
            g.pending_quota_event_id = ""
        current_app.logger.exception("Language game response failed")
        return _error(
            "Không thể xử lý lượt nhập vai này. Lượt của bạn đã được hoàn lại.",
            503,
            "language_service_unavailable",
        )


@bp.post("/api/language/reset")
def language_reset():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    row = _load_session(user_id, session_id)
    if not row:
        return jsonify({"ok": True})
    if str(row["status"]) == "active":
        get_db().execute(
            """
            UPDATE language_sessions
            SET status = 'abandoned', updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (_now(), session_id, user_id),
        )
        get_db().commit()
    return jsonify({"ok": True})
