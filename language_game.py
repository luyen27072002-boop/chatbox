from __future__ import annotations
from db_backend import column_names as backend_column_names

import copy
import json
import os
import re
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
from language_progress import (
    award_activity,
    ensure_profile,
    get_profile,
    leaderboard,
    record_skill_attempts,
    record_vocab_events,
    record_learning_term,
    save_profile,
    session_summary,
    skill_overview,
    update_mission_progress,
    vocabulary_overview,
)
from language_service import LanguageGameService
from language_learning import (
    MODULES,
    SKILL_FOR_MODULE,
    build_item_map,
    normalize as normalize_learning,
    dashboard as learning_dashboard,
    evaluate_fixed,
    init_learning_db,
    items_for_module,
    load_content,
    progress_summary as learning_progress_summary,
    record_attempt as record_learning_attempt,
    review_items as learning_review_items,
)
from language_experience import (
    build_experience_map,
    feed_for_user as experience_feed_for_user,
    find_term as experience_find_term,
    init_experience_db,
    load_experiences,
    mark_view as experience_mark_view,
    record_practice as experience_record_practice,
    reveal_selected_experience,
    save_selected_terms as experience_save_selected_terms,
)
from language_curriculum import (
    build_track_map as build_curriculum_track_map,
    checkpoint_definition as curriculum_checkpoint_definition,
    complete_activity as curriculum_complete_activity,
    get_selection as curriculum_get_selection,
    init_curriculum_db,
    load_curriculum,
    public_tracks as curriculum_public_tracks,
    roadmap as curriculum_roadmap,
    save_checkpoint_attempt as curriculum_save_checkpoint_attempt,
    score_fixed_questions as curriculum_score_fixed_questions,
    select_track as curriculum_select_track,
)


BASE_DIR = Path(__file__).resolve().parent
bp = Blueprint("language_game", __name__)

VALID_LEVELS = {"A1-A2", "B1-B2", "C1-C2"}
VALID_HUMOR = {"chaotic-meme", "deadpan", "dramatic", "gentle"}
VALID_GENDERS = {"male", "female"}
VALID_LANGUAGES = {"en", "zh"}
VALID_LIFE_ROLES = {"student", "worker"}
VALID_MODES = {"mission", "free_roam"}
VALID_SKIN_TONES = {"light", "tan", "brown", "deep"}
VALID_HAIR_STYLES = {"short", "bob", "long", "bun"}
VALID_HAIR_COLORS = {"black", "brown", "blonde", "pink"}
VALID_OUTFITS = {"casual", "student", "office", "sport"}
VALID_FACE_STYLES = {"smile", "calm", "cool", "cute"}


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


def _learning_content() -> dict[str, Any]:
    return current_app.extensions["language_learning_content"]


def _learning_item_map() -> dict[str, dict[str, Any]]:
    return current_app.extensions["language_learning_item_map"]


def _experience_content() -> dict[str, list[dict[str, Any]]]:
    return current_app.extensions["language_experience_content"]


def _experience_map() -> dict[str, dict[str, Any]]:
    return current_app.extensions["language_experience_map"]


def _curriculum_content() -> dict[str, Any]:
    return current_app.extensions["language_curriculum_content"]


def _curriculum_track_map() -> dict[str, dict[str, Any]]:
    return current_app.extensions["language_curriculum_track_map"]


def _known_vocabulary(user_id: str, language: str, limit: int = 80) -> list[str]:
    rows = get_db().execute(
        """
        SELECT term FROM language_vocab_stats
        WHERE user_id = ? AND language = ? AND (mastery >= 45 OR player_uses >= 1)
        ORDER BY player_uses DESC, mastery DESC, importance_score DESC, encounters DESC
        LIMIT ?
        """,
        (user_id, language, max(10, min(120, int(limit)))),
    ).fetchall()
    return [str(row["term"]) for row in rows]


def _public_scene(scene: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(scene)
    # Secret answers/clues are server-side game state. Never leak them to the browser.
    public.pop("secret_goal", None)
    public.pop("briefing_vi", None)
    return public




def _secret_clues(raw_scene: dict[str, Any], language: str) -> list[str]:
    goal = raw_scene.get("secret_goal") or {}
    localized = goal.get("clues_localized") or {}
    values = localized.get(language) if isinstance(localized, dict) else None
    if not isinstance(values, list):
        values = goal.get("clues") or []
    return [str(item).strip() for item in values if str(item).strip()]


def _public_challenge(raw_scene: dict[str, Any], language: str, revealed_count: int = 0) -> dict[str, Any]:
    goal = raw_scene.get("secret_goal") or {}
    answer = str(goal.get("answer", "")).strip()
    if not answer:
        return {"required": False}
    clues = _secret_clues(raw_scene, language)
    count = max(0, min(int(revealed_count or 0), len(clues)))
    goal_type = str(goal.get("type", "phrase")).strip().lower() or "phrase"
    return {
        "required": True,
        "label": str(goal.get("label", "đáp án cuối")).strip() or "đáp án cuối",
        "answer_type": goal_type,
        "placeholder": str(goal.get("answer_placeholder", "Nhập đáp án")).strip() or "Nhập đáp án",
        "clue_total": len(clues),
        "clues_revealed": count,
        "revealed_clues": clues[:count],
        "question_ideas": [str(item) for item in (goal.get("question_ideas") or []) if str(item).strip()][:4],
    }


def _secret_answer_matches(raw_scene: dict[str, Any], value: str) -> bool:
    goal = raw_scene.get("secret_goal") or {}
    answer = str(goal.get("answer", "")).strip()
    if not answer:
        return False
    goal_type = str(goal.get("type", "phrase")).strip().lower()
    raw = str(value or "").strip()
    if goal_type == "code":
        return re.sub(r"\D", "", raw) == re.sub(r"\D", "", answer)
    candidates = [answer] + [str(item) for item in (goal.get("aliases") or []) if str(item).strip()]
    normalized = re.sub(r"[^a-z0-9\u00c0-\u024f\u4e00-\u9fff]+", " ", raw.lower()).strip()
    return any(
        re.sub(r"[^a-z0-9\u00c0-\u024f\u4e00-\u9fff]+", " ", candidate.lower()).strip() == normalized
        for candidate in candidates
        if str(candidate).strip()
    )


def _question_earns_clue(raw_scene: dict[str, Any], message: str) -> bool:
    text = re.sub(r"\s+", " ", str(message or "").lower()).strip()
    if not text:
        return False
    meta_only = (
        "how can i do" in text
        or "what should i do" in text
        or "how do i play" in text
        or "làm sao chơi" in text
        or "tôi phải làm gì" in text
    )
    if meta_only:
        return False
    question_words = (
        "?", "who", "what", "where", "when", "why", "how", "which",
        "can you", "could you", "do you", "did you", "is there", "are there",
        "hint", "clue", "manh mối", "gợi ý", "誰", "什麼", "哪", "怎麼", "線索",
    )
    if not any(token in text for token in question_words):
        return False
    goal = raw_scene.get("secret_goal") or {}
    keywords = [str(item).lower() for item in (goal.get("clue_keywords") or []) if str(item).strip()]
    generic = any(token in text for token in ("hint", "clue", "manh mối", "gợi ý", "線索"))
    relevant = any(keyword in text for keyword in keywords) if keywords else True
    return generic or relevant

def _ensure_column(db, table: str, column: str, ddl: str) -> None:
    columns = backend_column_names(db, table)
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


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
            language_code TEXT NOT NULL DEFAULT 'en',
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

        CREATE TABLE IF NOT EXISTS language_player_profiles (
            user_id TEXT PRIMARY KEY,
            character_gender TEXT NOT NULL DEFAULT '',
            character_name TEXT NOT NULL DEFAULT '',
            target_language TEXT NOT NULL DEFAULT 'en',
            life_role TEXT NOT NULL DEFAULT '',
            skin_tone TEXT NOT NULL DEFAULT 'light',
            hair_style TEXT NOT NULL DEFAULT 'short',
            hair_color TEXT NOT NULL DEFAULT 'black',
            outfit_style TEXT NOT NULL DEFAULT 'casual',
            face_style TEXT NOT NULL DEFAULT 'smile',
            learning_goal TEXT NOT NULL DEFAULT 'comprehensive',
            daily_minutes INTEGER NOT NULL DEFAULT 20,
            cefr_level TEXT NOT NULL DEFAULT 'A1-A2',
            xp INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            best_streak INTEGER NOT NULL DEFAULT 0,
            last_active_date TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_vocab_stats (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            term TEXT NOT NULL,
            normalized_term TEXT NOT NULL,
            meaning TEXT NOT NULL DEFAULT '',
            encounters INTEGER NOT NULL DEFAULT 0,
            npc_encounters INTEGER NOT NULL DEFAULT 0,
            player_uses INTEGER NOT NULL DEFAULT 0,
            help_uses INTEGER NOT NULL DEFAULT 0,
            mastery REAL NOT NULL DEFAULT 0,
            importance_score INTEGER NOT NULL DEFAULT 0,
            contexts_json TEXT NOT NULL DEFAULT '[]',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            PRIMARY KEY(user_id, language, normalized_term),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_vocab_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            language TEXT NOT NULL,
            term TEXT NOT NULL,
            event_type TEXT NOT NULL,
            importance INTEGER NOT NULL DEFAULT 3,
            understood INTEGER NOT NULL DEFAULT 0,
            context TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES language_sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_skill_stats (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            skill TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            successes INTEGER NOT NULL DEFAULT 0,
            mastery REAL NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, language, skill),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_mission_progress (
            user_id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            best_score INTEGER NOT NULL DEFAULT 0,
            best_stars INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            completions INTEGER NOT NULL DEFAULT 0,
            last_played_at TEXT NOT NULL,
            PRIMARY KEY(user_id, scene_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_daily_activity (
            user_id TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            turns INTEGER NOT NULL DEFAULT 0,
            missions_completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, activity_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_language_sessions_user_updated
        ON language_sessions(user_id, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_language_messages_session_id
        ON language_messages(session_id, id ASC);

        CREATE INDEX IF NOT EXISTS idx_language_vocab_events_session
        ON language_vocab_events(session_id, id ASC);

        CREATE INDEX IF NOT EXISTS idx_language_vocab_user_importance
        ON language_vocab_stats(user_id, language, importance_score DESC, encounters DESC);
        """
    )

    # Migration an toàn: chép patch đè lên project cũ, không cần xóa app.db.
    _ensure_column(db, "language_sessions", "mode", "TEXT NOT NULL DEFAULT 'mission'")
    _ensure_column(db, "language_sessions", "language_code", "TEXT NOT NULL DEFAULT 'en'")
    _ensure_column(db, "language_sessions", "objectives_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(db, "language_sessions", "help_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "task_success", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "communication", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "language_quality", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "independence", "INTEGER NOT NULL DEFAULT 100")
    _ensure_column(db, "language_sessions", "stars", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "xp_earned", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "clues_revealed", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_sessions", "answer_attempts", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "language_player_profiles", "life_role", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(db, "language_player_profiles", "skin_tone", "TEXT NOT NULL DEFAULT 'light'")
    _ensure_column(db, "language_player_profiles", "hair_style", "TEXT NOT NULL DEFAULT 'short'")
    _ensure_column(db, "language_player_profiles", "hair_color", "TEXT NOT NULL DEFAULT 'black'")
    _ensure_column(db, "language_player_profiles", "outfit_style", "TEXT NOT NULL DEFAULT 'casual'")
    _ensure_column(db, "language_player_profiles", "face_style", "TEXT NOT NULL DEFAULT 'smile'")
    _ensure_column(db, "language_player_profiles", "learning_goal", "TEXT NOT NULL DEFAULT 'comprehensive'")
    _ensure_column(db, "language_player_profiles", "daily_minutes", "INTEGER NOT NULL DEFAULT 20")
    _ensure_column(db, "language_player_profiles", "cefr_level", "TEXT NOT NULL DEFAULT 'A1-A2'")
    init_learning_db(db)
    init_experience_db(db)
    init_curriculum_db(db)
    db.commit()


def register_language_game(app: Flask) -> None:
    scenes_path = Path(app.config.get("LANGUAGE_SCENES_PATH") or BASE_DIR / "data" / "language_scenes.json")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    if not isinstance(scenes, list):
        raise RuntimeError("data/language_scenes.json phải là một danh sách cảnh.")
    scene_map = {str(item["id"]): item for item in scenes}
    # Giữ các save V1 cũ không bị chết khi người dùng chép patch đè.
    legacy_aliases = {
        "coffee-chaos": "student-d1-store",
        "interview-disaster": "worker-d1-meeting",
        "convenience-store": "student-d1-store",
        "professor-meeting": "student-d2-project",
    }
    for legacy_id, canonical_id in legacy_aliases.items():
        if canonical_id in scene_map:
            scene_map[legacy_id] = scene_map[canonical_id]

    service = app.config.get("LANGUAGE_GAME_SERVICE") or LanguageGameService(
        api_key=app.config.get("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_LANGUAGE_MODEL", app.config.get("OPENAI_MODEL", "gpt-5.6-luna")),
        reasoning_effort=os.getenv("OPENAI_LANGUAGE_REASONING_EFFORT", "low"),
        max_output_tokens=int(os.getenv("OPENAI_LANGUAGE_MAX_OUTPUT_TOKENS", "1700")),
    )
    learning_path = Path(app.config.get("LANGUAGE_LEARNING_CONTENT_PATH") or BASE_DIR / "data" / "language_learning_content.json")
    learning_content = load_content(learning_path)
    learning_item_map = build_item_map(learning_content)
    experience_path = Path(app.config.get("LANGUAGE_EXPERIENCE_CONTENT_PATH") or BASE_DIR / "data" / "language_experiences.json")
    experience_content = load_experiences(experience_path)
    experience_map = build_experience_map(experience_content)
    curriculum_path = Path(app.config.get("LANGUAGE_CURRICULUM_PATH") or BASE_DIR / "data" / "language_curriculum.json")
    curriculum_content = load_curriculum(curriculum_path)
    curriculum_track_map = build_curriculum_track_map(curriculum_content)

    app.extensions["language_scenes"] = scenes
    app.extensions["language_scene_map"] = scene_map
    app.extensions["language_game_service"] = service
    app.extensions["language_learning_content"] = learning_content
    app.extensions["language_learning_item_map"] = learning_item_map
    app.extensions["language_experience_content"] = experience_content
    app.extensions["language_experience_map"] = experience_map
    app.extensions["language_curriculum_content"] = curriculum_content
    app.extensions["language_curriculum_track_map"] = curriculum_track_map

    with app.app_context():
        init_language_db()
    app.register_blueprint(bp)


def _resolve_scene(raw_scene: dict[str, Any], language: str) -> dict[str, Any]:
    """Gộp metadata chung với nội dung EN/ZH để một game dùng được cho cả hai ngôn ngữ."""
    language = language if language in VALID_LANGUAGES else "en"
    scene = copy.deepcopy(raw_scene)
    localized = scene.pop("localized", {}) or {}
    local = localized.get(language, {}) if isinstance(localized, dict) else {}
    if isinstance(local, dict):
        for key, value in local.items():
            scene[key] = copy.deepcopy(value)
    scene["language"] = language
    return scene


def _load_session(user_id: str, session_id: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM language_sessions WHERE id = ? AND user_id = ?",
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


def _mission_progress_map(user_id: str) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        "SELECT * FROM language_mission_progress WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {str(row["scene_id"]): dict(row) for row in rows}


def _completed(progress: dict[str, dict[str, Any]], scene_id: str) -> bool:
    return int(progress.get(scene_id, {}).get("completions", 0) or 0) > 0


def _life_catalog(role: str) -> list[dict[str, Any]]:
    items = []
    for scene in _scenes():
        if str(scene.get("game_group", "")) != "life":
            continue
        roles = [str(item) for item in scene.get("life_roles", [])]
        if role not in roles:
            continue
        items.append(scene)
    return sorted(items, key=lambda item: (int(item.get("day", 1)), int(item.get("step", 1))))


def _life_state(user_id: str, profile: dict[str, Any], language: str) -> dict[str, Any]:
    role = str(profile.get("life_role", ""))
    if role not in VALID_LIFE_ROLES:
        return {"ready": False, "role": role, "timeline": [], "current": None}

    catalog = _life_catalog(role)
    progress = _mission_progress_map(user_id)
    current_raw = next((scene for scene in catalog if not _completed(progress, str(scene["id"]))), None)
    all_done = current_raw is None and bool(catalog)
    if current_raw is None and catalog:
        current_raw = catalog[-1]

    current_day = int(current_raw.get("day", 1)) if current_raw else 1
    day_items = [scene for scene in catalog if int(scene.get("day", 1)) == current_day]
    timeline = []
    for scene in day_items:
        scene_id = str(scene["id"])
        saved = progress.get(scene_id, {})
        resolved = _resolve_scene(scene, language)
        timeline.append(
            {
                "id": scene_id,
                "time": scene.get("time", ""),
                "location": scene.get("location", ""),
                "title": scene.get("short_title", scene.get("title", "")),
                "completed": _completed(progress, scene_id),
                "current": bool(current_raw and scene_id == str(current_raw["id"]) and not all_done),
                "best_stars": int(saved.get("best_stars", 0) or 0),
                "travel_from": scene.get("travel_from", ""),
                "travel_to": scene.get("travel_to", scene.get("location", "")),
                "travel_theme": scene.get("travel_theme", "street"),
                "opening_preview": resolved.get("opening", ""),
            }
        )

    current = _resolve_scene(current_raw, language) if current_raw and not all_done else None
    if current:
        current["completed_before"] = _completed(progress, str(current_raw["id"]))

    done_count = sum(1 for scene in catalog if _completed(progress, str(scene["id"])))
    return {
        "ready": True,
        "role": role,
        "day": current_day,
        "timeline": timeline,
        "current": current,
        "all_done": all_done,
        "completed_steps": done_count,
        "total_steps": len(catalog),
        "day_complete": bool(day_items) and all(_completed(progress, str(item["id"])) for item in day_items),
    }


def _arcade_states(user_id: str, profile: dict[str, Any], language: str) -> list[dict[str, Any]]:
    progress = _mission_progress_map(user_id)
    player_level = int(profile.get("player_level", 1) or 1)
    items: list[dict[str, Any]] = []
    for raw in sorted(
        [scene for scene in _scenes() if str(scene.get("game_group", "")) == "arcade"],
        key=lambda item: int(item.get("arcade_order", 999)),
    ):
        resolved = _resolve_scene(raw, language)
        scene_id = str(raw["id"])
        saved = progress.get(scene_id, {})
        unlock_level = max(1, int(raw.get("unlock_level", 1) or 1))
        items.append(
            {
                "id": scene_id,
                "title": raw.get("title", "Mini game"),
                "hook": raw.get("hook", raw.get("mission", "")),
                "tag": raw.get("tag", "QUICK GAME"),
                "duration": raw.get("duration", "3–5 phút"),
                "unlock_level": unlock_level,
                "unlocked": player_level >= unlock_level,
                "completed": _completed(progress, scene_id),
                "best_score": int(saved.get("best_score", 0) or 0),
                "best_stars": int(saved.get("best_stars", 0) or 0),
                "attempts": int(saved.get("attempts", 0) or 0),
                "opening_preview": resolved.get("opening", ""),
                "visual": raw.get("visual", "chaos"),
            }
        )
    return items



def _scene_briefing(raw: dict[str, Any], language: str) -> dict[str, Any]:
    scene = _resolve_scene(raw, language)
    objectives = [str(item) for item in scene.get("objectives", []) if str(item).strip()]
    briefing_vi = raw.get("briefing_vi") or {}
    secret_goal = raw.get("secret_goal") or {}
    player_role = str(briefing_vi.get("player_role") or scene.get("player_role", "Người chơi")).strip()
    npc_name = str(scene.get("npc_name", "NPC")).strip()
    npc_role = str(briefing_vi.get("npc_role") or scene.get("npc_role", npc_name)).strip()
    mission = str(briefing_vi.get("goal") or secret_goal.get("goal") or scene.get("mission", raw.get("mission", "Hoàn thành tình huống."))).strip()
    hook = str(briefing_vi.get("situation") or scene.get("hook", raw.get("hook", mission))).strip()
    motivation = str(briefing_vi.get("motivation") or "").strip()
    opening = str(scene.get("opening", "")).strip()
    core_terms = [str(item) for item in scene.get("core_terms", []) if str(item).strip()]
    pass_rule = str(briefing_vi.get("pass_rule") or secret_goal.get("pass_rule") or scene.get("win_condition", "Hoàn thành mục tiêu thật của tình huống.")).strip()
    return {
        "title": str(scene.get("title", raw.get("title", "Tình huống"))),
        "situation": hook or mission,
        "player_role": player_role,
        "npc_name": npc_name,
        "npc_role": npc_role,
        "goal": mission,
        "motivation": motivation,
        "objectives": objectives,
        "first_clue": opening,
        "useful_terms": core_terms[:6],
        "pass_rule": pass_rule,
        "target_label": str(secret_goal.get("label", "")).strip(),
        "requires_final_answer": bool(secret_goal.get("answer")),
        "question_ideas": [str(item) for item in (secret_goal.get("question_ideas") or []) if str(item).strip()][:4],
    }

def _hub_cards(user_id: str, profile: dict[str, Any], language: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    life = _life_state(user_id, profile, language)
    current = life.get("current") or {}
    if life.get("ready"):
        cards.append({
            "id": str(current.get("id") or f"life-{profile.get('life_role','') or 'journey'}"),
            "scene_id": str(current.get("id", "")),
            "kind": "life",
            "title": f"Cuộc sống — {('Sinh viên' if profile.get('life_role') == 'student' else 'Người đi làm')}",
            "hook": str(current.get("mission", "Sống một ngày bình thường bằng ngoại ngữ.")),
            "subtitle": str(current.get("title", "Chặng tiếp theo")),
            "location": str(current.get("location", "")),
            "time": str(current.get("time", "")),
            "tag": "LIFE RPG",
            "duration": "liên tục",
            "unlocked": True,
            "completed": False,
            "best_stars": 0,
            "attempts": int(life.get("completed_steps", 0) or 0),
            "progress_text": f"{int(life.get('completed_steps',0) or 0)}/{int(life.get('total_steps',0) or 0)} chặng",
            "visual": "life",
            "briefing": _scene_briefing(_scene_map().get(str(current.get("id", "")), current), language),
        })
    for item in _arcade_states(user_id, profile, language):
        cards.append({
            "id": item["id"],
            "scene_id": item["id"],
            "kind": "arcade",
            "title": item.get("title", "Game"),
            "hook": item.get("hook", ""),
            "subtitle": item.get("tag", ""),
            "location": "",
            "time": "",
            "tag": item.get("tag", "QUICK GAME"),
            "duration": item.get("duration", "3–5 phút"),
            "unlocked": bool(item.get("unlocked")),
            "completed": bool(item.get("completed")),
            "best_stars": int(item.get("best_stars", 0) or 0),
            "attempts": int(item.get("attempts", 0) or 0),
            "progress_text": f"{int(item.get('attempts',0) or 0)} lượt",
            "visual": item.get("visual", "chaos"),
            "briefing": _scene_briefing(_scene_map().get(str(item.get("id", "")), {}), language),
        })
    return cards


def _scene_states(user_id: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    progress = _mission_progress_map(user_id)
    player_level = int(profile.get("player_level", 1) or 1)
    role = str(profile.get("life_role", ""))
    life = _life_state(user_id, profile, str(profile.get("target_language", "en")))
    current_life_id = str((life.get("current") or {}).get("id", ""))
    states: list[dict[str, Any]] = []
    for scene in _scenes():
        scene_id = str(scene["id"])
        saved = progress.get(scene_id, {})
        group = str(scene.get("game_group", "legacy"))
        if group == "life":
            roles = [str(item) for item in scene.get("life_roles", [])]
            unlocked = role in roles and (scene_id == current_life_id or _completed(progress, scene_id))
        elif group == "arcade":
            unlocked = player_level >= int(scene.get("unlock_level", 1) or 1)
        else:
            requires = [str(item) for item in scene.get("requires", []) if str(item).strip()]
            unlocked = all(_completed(progress, required) for required in requires)
        states.append(
            {
                "id": scene_id,
                "game_group": group,
                "unlocked": unlocked,
                "completed": _completed(progress, scene_id),
                "best_score": int(saved.get("best_score", 0) or 0),
                "best_stars": int(saved.get("best_stars", 0) or 0),
                "attempts": int(saved.get("attempts", 0) or 0),
            }
        )
    return states


def _parse_objectives(row: sqlite3.Row) -> list[str]:
    try:
        value = json.loads(str(row["objectives_json"] or "[]"))
        return [str(item) for item in value] if isinstance(value, list) else []
    except Exception:
        return []


def _serialize_session(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    try:
        item["objectives_completed"] = json.loads(str(item.get("objectives_json", "[]") or "[]"))
    except Exception:
        item["objectives_completed"] = []
    raw_scene = _scene_map().get(str(item.get("scene_id", "")), {})
    scene = _resolve_scene(raw_scene, str(item.get("language_code", "en"))) if raw_scene else {}
    item["scene"] = {
        "id": scene.get("id", item.get("scene_id", "")),
        "title": scene.get("title", "Cảnh đã lưu"),
        "short_title": scene.get("short_title", scene.get("title", "")),
        "language": scene.get("language", ""),
        "background": scene.get("background", ""),
        "npc_name": scene.get("npc_name", "NPC"),
        "location": scene.get("location", ""),
        "game_group": scene.get("game_group", "legacy"),
    }
    item["completed"] = item.get("status") == "completed"
    item["challenge"] = _public_challenge(raw_scene, str(item.get("language_code", "en")), int(item.get("clues_revealed", 0) or 0)) if raw_scene else {"required": False}
    return item


def _curriculum_payload(db, user_id: str, language: str) -> dict[str, Any]:
    tracks = curriculum_public_tracks(_curriculum_content()) if language == "en" else []
    selection = curriculum_get_selection(db, user_id, language)
    if not selection:
        return {"available": language == "en", "tracks": tracks, "selection": None, "roadmap": None}
    track = _curriculum_track_map().get(str(selection.get("track_id", "")))
    if not track:
        return {"available": language == "en", "tracks": tracks, "selection": None, "roadmap": None}
    road = curriculum_roadmap(
        db, user_id=user_id, language=language, track=track, target=str(selection.get("target", ""))
    )
    return {"available": language == "en", "tracks": tracks, "selection": selection, "roadmap": road}


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
    db = get_db()
    ensure_profile(db, user_id)
    db.commit()
    return jsonify(
        {
            "ok": True,
            "mode": "online-ai" if _service().is_configured else "offline-demo",
            "quota": _quota(user_id),
            "profile": get_profile(db, user_id),
        }
    )


@bp.get("/api/language/overview")
def language_overview():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    profile = get_profile(db, user_id)
    language = str(request.args.get("language", profile.get("target_language", "en"))).strip()
    if language not in VALID_LANGUAGES:
        language = str(profile.get("target_language", "en"))
    rows = db.execute(
        """
        SELECT * FROM language_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()
    sessions = [_serialize_session(row) for row in rows]
    db.commit()
    return jsonify(
        {
            "sessions": sessions,
            "active_session": next((item for item in sessions if item["status"] == "active"), None),
            "quota": _quota(user_id),
            "profile": profile,
            "life": _life_state(user_id, profile, language),
            "arcade": _arcade_states(user_id, profile, language),
            "cards": _hub_cards(user_id, profile, language),
            "scene_states": _scene_states(user_id, profile),
            "vocabulary": vocabulary_overview(db, user_id, language, limit=18),
            "skills": skill_overview(db, user_id, language, limit=12),
            "leaderboard": leaderboard(db, user_id, limit=8),
            "learning": {
                "dashboard": learning_dashboard(
                    db, user_id=user_id, language=language,
                    level=str(profile.get("cefr_level", "A1-A2")),
                    daily_minutes=int(profile.get("daily_minutes", 20) or 20),
                    content=_learning_content(),
                    learning_goal=str(profile.get("learning_goal", "comprehensive")),
                ),
                "progress": learning_progress_summary(
                    db, user_id=user_id, language=language, content=_learning_content()
                ),
            },
            "curriculum": _curriculum_payload(db, user_id, language),
        }
    )


@bp.get("/api/language/curriculum")
def language_curriculum_status():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    profile = get_profile(db, user_id)
    language = str(request.args.get("language", profile.get("target_language", "en"))).strip()
    if language not in VALID_LANGUAGES:
        language = "en"
    return jsonify(_curriculum_payload(db, user_id, language))


@bp.post("/api/language/curriculum/select")
def language_curriculum_select():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "en")).strip()
    track_id = str(payload.get("track_id", "")).strip()
    target = str(payload.get("target", "")).strip()
    if language != "en":
        return _error("V14 mới dựng roadmap tiếng Anh trước. Các ngôn ngữ khác sẽ dùng engine này sau.", 409, "curriculum_not_ready")
    track = _curriculum_track_map().get(track_id)
    if not track:
        return _error("Mục tiêu học không hợp lệ.")
    options = {str(item.get("value", "")) for item in (track.get("target_options") or [])}
    if target not in options:
        target = str((track.get("target_options") or [{}])[0].get("value", ""))
    db = get_db()
    selection = curriculum_select_track(db, user_id=user_id, language=language, track_id=track_id, target=target)
    # Đồng bộ learning_goal cũ để các module Train vẫn ưu tiên đúng kiểu nội dung.
    goal_map = {"daily": "daily", "work": "work", "ielts": "exam", "toeic": "exam"}
    try:
        db.execute(
            "UPDATE language_player_profiles SET learning_goal = ?, target_language = 'en', updated_at = ? WHERE user_id = ?",
            (goal_map.get(track_id, "comprehensive"), _now(), user_id),
        )
        db.commit()
    except Exception:
        db.rollback()
    return jsonify({"ok": True, "selection": selection, "curriculum": _curriculum_payload(db, user_id, language)})


@bp.post("/api/language/curriculum/activity/complete")
def language_curriculum_activity_complete():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "en")).strip()
    unit_id = str(payload.get("unit_id", "")).strip()
    activity_id = str(payload.get("activity_id", "")).strip()
    score = int(payload.get("score", 100) or 100)
    db = get_db()
    selection = curriculum_get_selection(db, user_id, language)
    if not selection:
        return _error("Hãy chọn lộ trình trước.", 409, "curriculum_required")
    track = _curriculum_track_map().get(str(selection.get("track_id", "")))
    if not track:
        return _error("Không tìm thấy lộ trình.", 404, "track_not_found")
    road = curriculum_roadmap(db, user_id=user_id, language=language, track=track, target=str(selection.get("target", "")))
    unit_state = next((u for st in road.get("stages", []) for u in st.get("units", []) if str(u.get("id")) == unit_id), None)
    if not unit_state or not unit_state.get("unlocked"):
        return _error("Unit này chưa được mở.", 409, "unit_locked")
    try:
        curriculum_complete_activity(
            db, user_id=user_id, language=language, track=track,
            unit_id=unit_id, activity_id=activity_id, score=score,
        )
    except ValueError as exc:
        return _error("Không tìm thấy hoạt động.", 404, str(exc))
    profile = award_activity(db, user_id, xp=8, turns=0, missions_completed=0)
    db.commit()
    return jsonify({"ok": True, "profile": profile, "curriculum": _curriculum_payload(db, user_id, language)})


@bp.post("/api/language/curriculum/checkpoint")
def language_curriculum_checkpoint():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "en")).strip()
    stage_id = str(payload.get("stage_id", "")).strip()
    answers = payload.get("answers") if isinstance(payload.get("answers"), dict) else {}
    db = get_db()
    selection = curriculum_get_selection(db, user_id, language)
    if not selection:
        return _error("Hãy chọn lộ trình trước.", 409, "curriculum_required")
    track_id = str(selection.get("track_id", ""))
    track = _curriculum_track_map().get(track_id)
    if not track:
        return _error("Không tìm thấy lộ trình.", 404, "track_not_found")
    road = curriculum_roadmap(db, user_id=user_id, language=language, track=track, target=str(selection.get("target", "")))
    stage_state = next((st for st in road.get("stages", []) if str(st.get("id")) == stage_id), None)
    if not stage_state:
        return _error("Không tìm thấy stage.", 404, "stage_not_found")
    if not (stage_state.get("checkpoint") or {}).get("available"):
        return _error("Hoàn thành các unit của stage trước khi làm bài test.", 409, "checkpoint_locked")
    checkpoint = curriculum_checkpoint_definition(track, stage_id)
    if not checkpoint:
        return _error("Không tìm thấy bài test.", 404, "checkpoint_not_found")
    fixed_score, _, fixed_feedback = curriculum_score_fixed_questions(checkpoint, answers)
    speaking_q = next((q for q in checkpoint.get("questions", []) if str(q.get("type")) == "speaking"), {})
    writing_q = next((q for q in checkpoint.get("questions", []) if str(q.get("type")) == "writing"), {})
    speaking_answer = str(answers.get(str(speaking_q.get("id", "")), "")).strip() if speaking_q else ""
    writing_answer = str(answers.get(str(writing_q.get("id", "")), "")).strip() if writing_q else ""
    if speaking_q and not speaking_answer:
        return _error("Checkpoint cần hoàn thành phần Speaking.")
    if writing_q and not writing_answer:
        return _error("Checkpoint cần hoàn thành phần Writing.")
    profile = get_profile(db, user_id)
    speaking_score = 0
    writing_score = 0
    free = {"feedback": ""}
    if speaking_q or writing_q:
        if _service().is_configured:
            quota_event = reserve_message_quota(
                user_id,
                welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
                daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
            )
            if not quota_event:
                return _error("Bạn đã dùng hết lượt AI hiện có. Checkpoint có phần tự do cần một lượt AI để chấm.", 429, "quota_exhausted", quota=_quota(user_id))
            event_id = str(quota_event["id"])
            g.pending_quota_event_id = event_id
        else:
            event_id = ""
        try:
            free = _service().checkpoint_feedback(
                language=language,
                level=str(stage_state.get("level", profile.get("cefr_level", "A1-A2"))),
                speaking_prompt=str(speaking_q.get("prompt", "")), speaking_answer=speaking_answer,
                writing_prompt=str(writing_q.get("prompt", "")), writing_answer=writing_answer,
            )
            if event_id:
                if not finalize_message_quota(event_id):
                    raise RuntimeError("Không thể chốt lượt AI.")
                g.pending_quota_event_id = ""
        except Exception:
            if event_id:
                try:
                    refund_message_quota(event_id)
                finally:
                    g.pending_quota_event_id = ""
            current_app.logger.exception("Curriculum checkpoint feedback failed")
            return _error("Chưa chấm được checkpoint lúc này.", 502, "checkpoint_feedback_failed")
        speaking_score = int(free.get("speaking_score", 0) or 0) if speaking_q else 0
        writing_score = int(free.get("writing_score", 0) or 0) if writing_q else 0
    weights = checkpoint.get("weights") if isinstance(checkpoint.get("weights"), dict) else {}
    fixed_weight = int(weights.get("fixed", 60 if (speaking_q or writing_q) else 100) or 0)
    speaking_weight = int(weights.get("speaking", 20 if speaking_q else 0) or 0)
    writing_weight = int(weights.get("writing", 20 if writing_q else 0) or 0)
    total_weight = max(1, fixed_weight + speaking_weight + writing_weight)
    overall = round((fixed_score * fixed_weight + speaking_score * speaking_weight + writing_score * writing_weight) / total_weight)
    pass_score = int(checkpoint.get("pass_score", 70) or 70)
    minimum_free = int(checkpoint.get("minimum_free_score", 50) or 50)
    passed = overall >= pass_score and (not speaking_q or speaking_score >= minimum_free) and (not writing_q or writing_score >= minimum_free)
    feedback_parts = []
    if fixed_feedback:
        feedback_parts.append(" ".join(fixed_feedback[:2]))
    if str(free.get("feedback", "")).strip():
        feedback_parts.append(str(free.get("feedback", "")).strip())
    feedback = " ".join(feedback_parts).strip() or ("Đạt checkpoint." if passed else "Chưa đạt checkpoint.")
    result = curriculum_save_checkpoint_attempt(
        db, user_id=user_id, language=language, track_id=track_id, stage_id=stage_id,
        score=overall, speaking_score=speaking_score, writing_score=writing_score,
        passed=passed, answers=answers, feedback=feedback,
    )
    if passed:
        profile = award_activity(db, user_id, xp=220, turns=0, missions_completed=1)
        # Đồng bộ level của Train theo stage kế tiếp để nội dung nền tăng dần cùng roadmap.
        stages = track.get("stages") or []
        stage_index = next((i for i, st in enumerate(stages) if str(st.get("id", "")) == stage_id), -1)
        next_stage = stages[stage_index + 1] if 0 <= stage_index < len(stages) - 1 else None
        next_label = str((next_stage or {}).get("level", ""))
        if next_label in {"A1", "A2", "Foundation", "350–450"}:
            grouped_level = "A1-A2"
        elif next_label in {"B1", "B2", "5.5–6.0", "6.5", "500–600", "650–750"}:
            grouped_level = "B1-B2"
        elif next_label:
            grouped_level = "C1-C2"
        else:
            grouped_level = str(profile.get("cefr_level", "A1-A2"))
        db.execute(
            "UPDATE language_player_profiles SET cefr_level = ?, updated_at = ? WHERE user_id = ?",
            (grouped_level, _now(), user_id),
        )
        db.commit()
        profile = get_profile(db, user_id)
    return jsonify({
        **result,
        "fixed_score": fixed_score,
        "pass_score": pass_score,
        "profile": profile,
        "quota": _quota(user_id),
        "curriculum": _curriculum_payload(db, user_id, language),
    })


@bp.get("/api/language/learning/feed")
def language_learning_feed():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    profile = get_profile(db, user_id)
    language = str(request.args.get("language", profile.get("target_language", "en"))).strip()
    if language not in VALID_LANGUAGES:
        language = str(profile.get("target_language", "en"))
    level = str(request.args.get("level", profile.get("cefr_level", "A1-A2"))).strip()
    if level not in VALID_LEVELS:
        level = str(profile.get("cefr_level", "A1-A2"))
    limit = max(1, min(20, int(request.args.get("limit", 8) or 8)))
    items = experience_feed_for_user(
        db, user_id=user_id, language=language, level=level,
        content=_experience_content(), limit=limit,
    )
    return jsonify({"items": items, "language": language, "level": level})


@bp.post("/api/language/learning/experience/view")
def language_experience_view():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    experience_id = str(payload.get("experience_id", "")).strip()
    item = _experience_map().get(experience_id)
    if not item:
        return _error("Không tìm thấy trải nghiệm.", 404, "experience_not_found")
    db = get_db()
    experience_mark_view(db, user_id=user_id, language=str(item.get("language", "en")), experience_id=experience_id)
    db.commit()
    return jsonify({"ok": True})


@bp.post("/api/language/learning/experience/select-words")
def language_experience_select_words():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    experience_id = str(payload.get("experience_id", "")).strip()
    requested = payload.get("terms") if isinstance(payload.get("terms"), list) else []
    item = _experience_map().get(experience_id)
    if not item:
        return _error("Không tìm thấy trải nghiệm.", 404, "experience_not_found")
    allowed = {str(t.get("term", "")).casefold(): dict(t) for t in (item.get("terms") or []) if str(t.get("term", "")).strip()}
    chosen: list[str] = []
    for raw in requested:
        text = str(raw or "").strip()
        if text.casefold() in allowed and text not in chosen:
            chosen.append(text)
    if not chosen:
        return _error("Chọn ít nhất một từ/cụm mày chưa biết.")
    language = str(item.get("language", "en"))
    db = get_db()
    merged = experience_save_selected_terms(
        db, user_id=user_id, language=language, experience_id=experience_id, terms=chosen,
    )
    for term_text in chosen:
        term = allowed.get(term_text.casefold()) or {}
        contexts = term.get("contexts") or []
        first_context = str((contexts[0] or {}).get("text", "")) if contexts and isinstance(contexts[0], dict) else "experience discovery"
        record_learning_term(
            db, user_id=user_id, language=language, term=term_text,
            meaning=str(term.get("meaning", "")), score=20,
            importance=int(term.get("importance", 5) or 5), active_use=False,
            context=first_context or "experience discovery",
        )
    profile = award_activity(db, user_id, xp=min(18, 4 + len(chosen) * 3), turns=0, missions_completed=0)
    db.commit()
    return jsonify({
        "ok": True, "experience": reveal_selected_experience(item, merged),
        "profile": profile, "quota": _quota(user_id),
    })


@bp.post("/api/language/learning/experience/practice")
def language_experience_practice():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    experience_id = str(payload.get("experience_id", "")).strip()
    term_text = str(payload.get("term", "")).strip()
    mode = str(payload.get("mode", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    item = _experience_map().get(experience_id)
    if not item:
        return _error("Không tìm thấy trải nghiệm.", 404, "experience_not_found")
    term = experience_find_term(item, term_text)
    if not term:
        return _error("Không tìm thấy từ này trong trải nghiệm.", 404, "term_not_found")
    if mode not in {"listening", "reading", "speaking", "writing"}:
        return _error("Chế độ luyện không hợp lệ.")
    language = str(item.get("language", "en"))
    db = get_db()
    profile = get_profile(db, user_id)
    db.commit()
    correction = ""
    if mode == "reading":
        check = term.get("read_check") if isinstance(term.get("read_check"), dict) else {}
        expected = str(check.get("answer", ""))
        ok = normalize_learning(answer) == normalize_learning(expected)
        score = 100 if ok else 35
        feedback = "Đúng. Mày đã hiểu từ này trong ngữ cảnh mới." if ok else f"Chưa đúng. Đáp án phù hợp hơn: {expected}"
        correction = expected
    elif mode == "listening":
        # Listening ở Word Lab là exposure chủ động: nghe các context rồi tự xác nhận đã bắt được từ.
        score = 72
        feedback = "Đã ghi nhận một lượt nghe chủ động. Từ này sẽ quay lại ở context khác sau."
    else:
        if not answer:
            return _error("Hãy nói hoặc viết một câu trước.")
        quota_event = reserve_message_quota(
            user_id, welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
            daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
        )
        if not quota_event:
            return _error("Bạn đã dùng hết lượt AI hiện có.", 429, "quota_exhausted", quota=_quota(user_id))
        event_id = str(quota_event["id"])
        g.pending_quota_event_id = event_id
        prompt = str(term.get("speak_prompt" if mode == "speaking" else "write_prompt", ""))
        try:
            result = _service().learning_feedback(
                module=mode, prompt=prompt, answer=answer, language=language,
                level=str(profile.get("cefr_level", "A1-A2")),
                model_answer=f"Use '{term_text}' naturally and keep the intended meaning.",
                focus=[term_text, "natural meaning in context"],
            )
            if not finalize_message_quota(event_id):
                raise RuntimeError("Không thể chốt lượt AI.")
            g.pending_quota_event_id = ""
        except Exception:
            try:
                refund_message_quota(event_id)
            finally:
                g.pending_quota_event_id = ""
            current_app.logger.exception("Experience practice feedback failed")
            return _error("Chưa chấm được lượt này. Thử lại sau.", 502, "learning_feedback_failed")
        score = int(result.get("score", 0) or 0)
        feedback = str(result.get("feedback", ""))
        correction = str(result.get("correction", ""))
    experience_record_practice(
        db, user_id=user_id, language=language, experience_id=experience_id,
        term=term_text, mode=mode, answer=answer, score=score,
    )
    contexts = term.get("contexts") or []
    context = str((contexts[-1] or {}).get("text", "")) if contexts and isinstance(contexts[-1], dict) else "experience practice"
    tracked = record_learning_term(
        db, user_id=user_id, language=language, term=term_text,
        meaning=str(term.get("meaning", "")), score=score,
        importance=int(term.get("importance", 5) or 5),
        active_use=mode in {"speaking", "writing"} and score >= 65, context=context,
    )
    record_skill_attempts(db, user_id=user_id, language=language, skills=[mode], score=score)
    xp = 10 if score >= 85 else 7 if score >= 65 else 3
    profile = award_activity(db, user_id, xp=xp, turns=0, missions_completed=0)
    db.commit()
    return jsonify({
        "score": score, "feedback": feedback, "correction": correction,
        "tracked_term": tracked, "profile": profile, "xp_earned": xp, "quota": _quota(user_id),
    })


@bp.get("/api/language/learning/items")
def language_learning_items():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    db = get_db()
    profile = get_profile(db, user_id)
    language = str(request.args.get("language", profile.get("target_language", "en"))).strip()
    if language not in VALID_LANGUAGES:
        language = str(profile.get("target_language", "en"))
    level = str(request.args.get("level", profile.get("cefr_level", "A1-A2"))).strip()
    if level not in VALID_LEVELS:
        level = str(profile.get("cefr_level", "A1-A2"))
    module = str(request.args.get("module", "vocabulary")).strip()
    mode = str(request.args.get("mode", "new")).strip()
    limit = int(request.args.get("limit", 8) or 8)
    if module == "review":
        items = learning_review_items(
            db, user_id=user_id, language=language, level=level,
            content=_learning_content(), limit=limit,
        )
    elif module in MODULES:
        items = items_for_module(
            db, user_id=user_id, language=language, level=level, module=module,
            content=_learning_content(), mode="review" if mode == "review" else "new", limit=limit,
        )
    else:
        return _error("Module học không hợp lệ.")
    return jsonify({
        "items": items, "module": module, "mode": mode,
        "language": language, "level": level,
    })


@bp.post("/api/language/learning/submit")
def language_learning_submit():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    item_id = str(payload.get("item_id", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    if not item_id or not answer:
        return _error("Thiếu bài hoặc câu trả lời.")
    item = _learning_item_map().get(item_id)
    if not item:
        return _error("Không tìm thấy bài học.", 404, "learning_item_not_found")
    language = str(item.get("language", "en"))
    module = str(item.get("module", ""))
    db = get_db()
    profile = get_profile(db, user_id)
    db.commit()
    level = str(profile.get("cefr_level", "A1-A2"))

    ai_modules = {"writing", "speaking", "pronunciation"}
    if module in ai_modules:
        quota_event = reserve_message_quota(
            user_id,
            welcome_limit=int(current_app.config["FREE_WELCOME_LIMIT"]),
            daily_limit=int(current_app.config["FREE_DAILY_LIMIT"]),
        )
        if not quota_event:
            return _error(
                "Bạn đã dùng hết lượt AI hiện có. Các bài trắc nghiệm và ôn từ vẫn dùng được.",
                429, "quota_exhausted", quota=_quota(user_id),
            )
        event_id = str(quota_event["id"])
        g.pending_quota_event_id = event_id
        try:
            result = _service().learning_feedback(
                module=module,
                prompt=str(item.get("prompt", item.get("tip", ""))),
                answer=answer, language=language, level=level,
                model_answer=str(item.get("model", item.get("target", ""))),
                focus=[str(x) for x in (item.get("focus") or [])],
            )
            if not finalize_message_quota(event_id):
                raise RuntimeError("Không thể chốt lượt AI.")
            g.pending_quota_event_id = ""
        except Exception:
            try:
                refund_message_quota(event_id)
            finally:
                g.pending_quota_event_id = ""
            current_app.logger.exception("Language learning feedback failed")
            return _error("Chưa chấm được bài này. Thử lại sau.", 502, "learning_feedback_failed")
        score = int(result.get("score", 0) or 0)
        feedback = str(result.get("feedback", ""))
        correction = str(result.get("correction", ""))
    else:
        score, _, feedback = evaluate_fixed(item, answer)
        correction = str(item.get("answer", ""))

    recorded = record_learning_attempt(
        db, user_id=user_id, language=language, item=item, answer=answer,
        score=score, feedback=feedback,
    )
    record_skill_attempts(
        db, user_id=user_id, language=language,
        skills=[SKILL_FOR_MODULE.get(module, module)], score=score,
    )
    tracked_term = {}
    if module == "vocabulary":
        tracked_term = record_learning_term(
            db, user_id=user_id, language=language,
            term=str(item.get("term", "")), meaning=str(item.get("meaning", "")),
            score=score, importance=int(item.get("importance", 5) or 5),
            active_use=False, context=str(item.get("example", "learning module")),
        )
    elif module == "phrases":
        tracked_term = record_learning_term(
            db, user_id=user_id, language=language,
            term=str(item.get("phrase", "")), meaning=str(item.get("meaning", "")),
            score=score, importance=5, active_use=score >= 65,
            context=str(item.get("use", "communication phrase")),
        )
    xp_award = 14 if score >= 85 else 10 if score >= 65 else 5
    profile = award_activity(db, user_id, xp=xp_award, turns=0, missions_completed=0)
    db.commit()
    return jsonify({
        **recorded,
        "feedback": feedback,
        "correction": correction,
        "xp_earned": xp_award,
        "profile": profile,
        "tracked_term": tracked_term,
        "quota": _quota(user_id),
        "learning": {
            "dashboard": learning_dashboard(
                db, user_id=user_id, language=language, level=level,
                daily_minutes=int(profile.get("daily_minutes", 20) or 20),
                content=_learning_content(),
                learning_goal=str(profile.get("learning_goal", "comprehensive")),
            ),
            "progress": learning_progress_summary(
                db, user_id=user_id, language=language, content=_learning_content()
            ),
        },
    })


@bp.post("/api/language/profile")
def language_profile_save():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    gender = str(payload.get("character_gender", "")).strip()
    name = str(payload.get("character_name", "")).strip()
    target_language = str(payload.get("target_language", "en")).strip()
    life_role = str(payload.get("life_role", "")).strip()
    skin_tone = str(payload.get("skin_tone", "light")).strip() or "light"
    hair_style = str(payload.get("hair_style", "short")).strip() or "short"
    hair_color = str(payload.get("hair_color", "black")).strip() or "black"
    outfit_style = str(payload.get("outfit_style", "casual")).strip() or "casual"
    face_style = str(payload.get("face_style", "smile")).strip() or "smile"
    learning_goal = str(payload.get("learning_goal", "comprehensive")).strip() or "comprehensive"
    daily_minutes = int(payload.get("daily_minutes", 20) or 20)
    cefr_level = str(payload.get("cefr_level", "A1-A2")).strip() or "A1-A2"
    if gender not in VALID_GENDERS:
        return _error("Hãy chọn nhân vật nam hoặc nữ.")
    if life_role not in VALID_LIFE_ROLES:
        return _error("Hãy chọn cuộc sống sinh viên hoặc người đi làm.")
    if target_language not in VALID_LANGUAGES:
        return _error("Ngôn ngữ mục tiêu không hợp lệ.")
    if skin_tone not in VALID_SKIN_TONES or hair_style not in VALID_HAIR_STYLES or hair_color not in VALID_HAIR_COLORS or outfit_style not in VALID_OUTFITS or face_style not in VALID_FACE_STYLES:
        return _error("Tùy chọn tạo hình nhân vật không hợp lệ.")
    if len(name) > 40:
        return _error("Tên nhân vật tối đa 40 ký tự.")
    if cefr_level not in VALID_LEVELS:
        return _error("Trình độ CEFR không hợp lệ.")
    daily_minutes = max(5, min(60, daily_minutes))
    profile = save_profile(
        get_db(), user_id,
        character_gender=gender, character_name=name, target_language=target_language, life_role=life_role,
        skin_tone=skin_tone, hair_style=hair_style, hair_color=hair_color, outfit_style=outfit_style, face_style=face_style,
        learning_goal=learning_goal, daily_minutes=daily_minutes, cefr_level=cefr_level,
    )
    return jsonify({"ok": True, "profile": profile})


def _can_start_scene(user_id: str, profile: dict[str, Any], raw_scene: dict[str, Any], mode: str) -> tuple[bool, str]:
    group = str(raw_scene.get("game_group", "legacy"))
    progress = _mission_progress_map(user_id)
    scene_id = str(raw_scene.get("id", ""))
    if group == "life":
        role = str(profile.get("life_role", ""))
        if role not in [str(item) for item in raw_scene.get("life_roles", [])]:
            return False, "Cảnh này không thuộc cuộc sống nhân vật đã chọn."
        life = _life_state(user_id, profile, str(profile.get("target_language", "en")))
        current_id = str((life.get("current") or {}).get("id", ""))
        if scene_id != current_id and not _completed(progress, scene_id):
            return False, "Hãy đi theo nhịp sống hiện tại trước."
        return True, ""
    if group == "arcade":
        required_level = int(raw_scene.get("unlock_level", 1) or 1)
        if int(profile.get("player_level", 1) or 1) < required_level:
            return False, f"Game này mở ở Lv.{required_level}."
        return True, ""
    requires = [str(item) for item in raw_scene.get("requires", []) if str(item).strip()]
    if mode == "free_roam" or all(_completed(progress, scene) for scene in requires):
        return True, ""
    return False, "Nhiệm vụ này chưa được mở khóa."


@bp.post("/api/language/start")
def language_start():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    scene_id = str(payload.get("scene_id", "")).strip()
    raw_scene = _scene_map().get(scene_id)
    if not raw_scene:
        return _error("Không tìm thấy cảnh.", 404, "scene_not_found")

    level = str(payload.get("level", "A1-A2")).strip()
    humor = str(payload.get("humor", "chaotic-meme")).strip()
    mode = str(payload.get("mode", "mission")).strip()
    if level not in VALID_LEVELS:
        return _error("Trình độ không hợp lệ.")
    if humor not in VALID_HUMOR:
        return _error("Phong cách nhập vai không hợp lệ.")
    if mode not in VALID_MODES:
        return _error("Chế độ chơi không hợp lệ.")

    db = get_db()
    ensure_profile(db, user_id)
    db.commit()
    profile = get_profile(db, user_id)
    if not profile.get("profile_ready"):
        return _error("Hãy tạo nhân vật và chọn cuộc sống trước.", 409, "profile_required")
    allowed, reason = _can_start_scene(user_id, profile, raw_scene, mode)
    if not allowed:
        return _error(reason, 409, "mission_locked")

    language = str(profile.get("target_language", "en"))
    scene = _resolve_scene(raw_scene, language)
    session_id = str(uuid.uuid4())
    now = _now()
    opening = str(
        scene.get("free_roam_opening", scene.get("opening", "..."))
        if mode == "free_roam"
        else scene.get("opening", "...")
    ).strip()
    objectives = [] if mode == "free_roam" else [str(item) for item in scene.get("objectives", [])]

    # get_profile() internally ensures the profile row exists. SQLite may therefore
    # already have an implicit transaction open here. Starting another explicit
    # BEGIN IMMEDIATE raises: "cannot start a transaction within a transaction".
    # Continue in the current transaction and commit/rollback atomically below.
    try:
        db.execute(
            """
            INSERT INTO language_sessions(
                id, user_id, scene_id, level, humor, language_code, mode, score, progress,
                status, turns_used, objectives_json, help_count,
                task_success, communication, language_quality, independence,
                stars, xp_earned, started_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 50, 0, 'active', 0, '[]', 0, 0, 0, 0, 100, 0, 0, ?, ?)
            """,
            (session_id, user_id, scene_id, level, humor, language, mode, now, now),
        )
        db.execute(
            """
            INSERT INTO language_messages(session_id, user_id, role, text, created_at)
            VALUES (?, ?, 'npc', ?, ?)
            """,
            (session_id, user_id, opening, now),
        )
        if mode == "mission":
            update_mission_progress(
                db,
                user_id=user_id,
                scene_id=scene_id,
                score=0,
                stars=0,
                completed=False,
                new_attempt=True,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return jsonify(
        {
            "session_id": session_id,
            "scene": _public_scene(scene),
            "opening": opening,
            "score": 50,
            "progress": 0,
            "status": "active",
            "mode": mode,
            "objectives": objectives,
            "profile": get_profile(db, user_id),
            "briefing": _scene_briefing(raw_scene, language),
            "challenge": _public_challenge(raw_scene, language, 0),
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
    raw_scene = _scene_map().get(str(row["scene_id"])) or {}
    scene = _resolve_scene(raw_scene, str(row["language_code"] or "en"))
    return jsonify(
        {
            "session": _serialize_session(row),
            "scene": _public_scene(scene),
            "messages": _history(session_id, limit=80),
            "briefing": _scene_briefing(raw_scene, str(row["language_code"] or "en")),
            "challenge": _public_challenge(raw_scene, str(row["language_code"] or "en"), int(row["clues_revealed"] or 0)),
        }
    )


@bp.get("/api/language/sessions/<session_id>/summary")
def language_session_summary(session_id: str):
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    summary = session_summary(get_db(), user_id, session_id)
    if not summary:
        return _error("Không tìm thấy phiên chơi.", 404, "session_not_found")
    return jsonify(summary)


@bp.post("/api/language/hint")
def language_hint():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    row = _load_session(user_id, session_id)
    if not row or str(row["status"]) != "active":
        return _error("Phiên chơi không còn hoạt động.", 409, "session_closed")
    raw_scene = _scene_map().get(str(row["scene_id"])) or {}
    scene = _resolve_scene(raw_scene, str(row["language_code"] or "en"))
    next_level = min(4, int(row["help_count"] or 0) + 1)
    hints = scene.get("hints") or {}
    hint = str(hints.get(str(next_level), "")).strip()
    if not hint:
        suggestions = scene.get("suggestions") or []
        if next_level <= 1:
            remaining = [item for item in scene.get("objectives", []) if item not in _parse_objectives(row)]
            hint = str(remaining[0] if remaining else scene.get("mission", "Hãy làm rõ mục tiêu của mày."))
        elif next_level == 2:
            hint = " / ".join(str(item) for item in (scene.get("core_terms") or [])[:4])
        elif suggestions:
            hint = str(suggestions[min(len(suggestions) - 1, next_level - 3)])
        else:
            hint = "Hãy nói điều mày thực sự muốn NPC hiểu."

    db = get_db()
    db.execute(
        "UPDATE language_sessions SET help_count = help_count + 1, updated_at = ? WHERE id = ? AND user_id = ?",
        (_now(), session_id, user_id),
    )
    core_terms = scene.get("core_terms") or []
    if next_level >= 2 and core_terms:
        record_vocab_events(
            db,
            user_id=user_id,
            session_id=session_id,
            language=str(scene.get("language", "en")),
            events=[
                {
                    "term": str(core_terms[0]),
                    "source": "hint",
                    "importance": 4,
                    "understood": False,
                    "context": hint,
                }
            ],
        )
    db.commit()
    return jsonify({"hint": hint, "hint_level": next_level, "help_count": int(row["help_count"] or 0) + 1})


@bp.post("/api/language/respond")
def language_respond():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    message = str(payload.get("message", "")).strip()
    input_mode = str(payload.get("input_mode", "text")).strip()
    if input_mode not in {"text", "voice"}:
        input_mode = "text"
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
    raw_scene = _scene_map().get(str(row["scene_id"]))
    if not raw_scene:
        return _error("Cảnh của phiên chơi không còn tồn tại.", 409, "scene_missing")
    scene = _resolve_scene(raw_scene, str(row["language_code"] or "en"))

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
        "mode": str(row["mode"] or "mission"),
        "score": int(row["score"]),
        "progress": int(row["progress"]),
        "help_count": int(row["help_count"] or 0),
        "clues_revealed": int(row["clues_revealed"] or 0),
        "objectives_completed": _parse_objectives(row),
        "known_vocabulary": _known_vocabulary(user_id, str(row["language_code"] or "en"), limit=80),
    }
    history = [{"role": item["role"], "text": item["text"]} for item in _history(session_id, limit=12)]

    try:
        result = _service().reply(scene=scene, state=state, message=message, history=history)
        challenge_before = _public_challenge(raw_scene, str(row["language_code"] or "en"), int(row["clues_revealed"] or 0))
        clue_count_before = int(row["clues_revealed"] or 0)
        clue_count_after = clue_count_before
        new_clue = ""
        if challenge_before.get("required") and _question_earns_clue(raw_scene, message):
            all_clues = _secret_clues(raw_scene, str(row["language_code"] or "en"))
            if clue_count_before < len(all_clues):
                new_clue = all_clues[clue_count_before]
                clue_count_after = clue_count_before + 1
        npc_reply = result.reply
        if new_clue:
            clue_prefix = "Clue" if str(row["language_code"] or "en") == "en" else "線索"
            npc_reply = f"{npc_reply}\n\n{clue_prefix}: {new_clue}"
        merged_objectives = list(state["objectives_completed"])
        for objective in result.objectives_completed:
            if objective not in merged_objectives:
                merged_objectives.append(objective)

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
                    npc_reply,
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
                    objectives_json = ?, task_success = ?, communication = ?,
                    language_quality = ?, independence = ?, stars = MAX(stars, ?),
                    xp_earned = xp_earned + ?, clues_revealed = ?, updated_at = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE id = ? AND user_id = ?
                """,
                (
                    result.score,
                    result.progress,
                    status,
                    json.dumps(merged_objectives, ensure_ascii=False),
                    result.task_success,
                    result.communication,
                    result.language_quality,
                    result.independence,
                    result.stars,
                    result.xp_earned,
                    clue_count_after,
                    now,
                    completed_at,
                    session_id,
                    user_id,
                ),
            )

            tracked_terms = record_vocab_events(
                db,
                user_id=user_id,
                session_id=session_id,
                language=str(scene.get("language", "en")),
                events=result.vocab_events,
            )
            skill_names = list(result.skills_practiced)
            skill_names.append("speaking" if input_mode == "voice" else "writing")
            skill_names.append("listening" if input_mode == "voice" else "reading")
            record_skill_attempts(
                db,
                user_id=user_id,
                language=str(scene.get("language", "en")),
                skills=skill_names,
                score=result.communication,
            )
            profile = award_activity(
                db,
                user_id,
                xp=result.xp_earned,
                turns=1,
                missions_completed=1 if result.completed else 0,
            )
            if str(row["mode"] or "mission") == "mission":
                update_mission_progress(
                    db,
                    user_id=user_id,
                    scene_id=str(row["scene_id"]),
                    score=result.score,
                    stars=result.stars,
                    completed=result.completed,
                    new_attempt=False,
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
                "reply": npc_reply,
                "status": status,
                "new_clue": new_clue,
                "challenge": _public_challenge(raw_scene, str(row["language_code"] or "en"), clue_count_after),
                "quota": _quota(user_id),
                "quota_source": quota_event["source"],
                "used_total": get_usage_total(user_id),
                "objectives_completed_all": merged_objectives,
                "tracked_terms": tracked_terms,
                "profile": profile,
                "life": _life_state(user_id, profile, str(profile.get("target_language", "en"))) if result.completed else None,
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


@bp.post("/api/language/answer")
def language_answer():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    if not answer:
        return _error("Nhập đáp án trước đã.")
    row = _load_session(user_id, session_id)
    if not row:
        return _error("Phiên chơi không tồn tại.", 404, "session_not_found")
    if str(row["status"]) != "active":
        return _error("Cảnh này đã kết thúc.", 409, "session_closed")
    raw_scene = _scene_map().get(str(row["scene_id"])) or {}
    goal = raw_scene.get("secret_goal") or {}
    if not str(goal.get("answer", "")).strip():
        return _error("Game này không có đáp án riêng.", 409, "answer_not_required")

    db = get_db()
    now = _now()
    correct = _secret_answer_matches(raw_scene, answer)
    attempts = int(row["answer_attempts"] or 0) + 1
    if not correct:
        db.execute(
            "UPDATE language_sessions SET answer_attempts = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (attempts, now, session_id, user_id),
        )
        db.commit()
        return jsonify({
            "correct": False,
            "message": "Chưa đúng. Tiếp tục hỏi để lấy thêm manh mối rồi thử lại.",
            "answer_attempts": attempts,
            "challenge": _public_challenge(raw_scene, str(row["language_code"] or "en"), int(row["clues_revealed"] or 0)),
        })

    score = max(80, int(row["score"] or 0))
    communication = max(70, int(row["communication"] or 0))
    clues_used = int(row["clues_revealed"] or 0)
    turns_used = int(row["turns_used"] or 0)
    speed_bonus = max(0, 18 - max(0, turns_used - 2) * 2)
    clue_bonus = max(0, 12 - clues_used * 3)
    xp_award = 45 + speed_bonus + clue_bonus
    stars = 3 if score >= 85 and attempts == 1 else 2 if score >= 70 else 1

    try:
        db.execute(
            """
            UPDATE language_sessions
            SET status = 'completed', progress = 100, task_success = 100, score = ?,
                stars = MAX(stars, ?), xp_earned = xp_earned + ?, answer_attempts = ?,
                updated_at = ?, completed_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (score, stars, xp_award, attempts, now, now, session_id, user_id),
        )
        profile = award_activity(db, user_id, xp=xp_award, turns=0, missions_completed=1)
        if str(row["mode"] or "mission") == "mission":
            update_mission_progress(
                db, user_id=user_id, scene_id=str(row["scene_id"]), score=score,
                stars=stars, completed=True, new_attempt=False,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return jsonify({
        "correct": True,
        "completed": True,
        "message": "Đúng đáp án. Qua màn.",
        "score": score,
        "progress": 100,
        "stars": stars,
        "xp_earned": xp_award,
        "profile": profile,
        "life": _life_state(user_id, profile, str(profile.get("target_language", "en"))),
        "challenge": _public_challenge(raw_scene, str(row["language_code"] or "en"), clues_used),
    })


@bp.post("/api/language/learning/save-term")
def language_learning_save_term():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    term = str(payload.get("term", "")).strip()[:120]
    language = str(payload.get("language", "en")).strip()
    if language not in VALID_LANGUAGES:
        language = "en"
    if not term:
        return _error("Thiếu từ/cụm cần lưu.")
    db = get_db()
    tracked = record_learning_term(
        db, user_id=user_id, language=language, term=term, meaning="",
        score=15, importance=5, active_use=False, context="dictionary lookup",
    )
    db.commit()
    return jsonify({"ok": True, "tracked_term": tracked})


@bp.post("/api/language/dictionary")
def language_dictionary():
    user_id = _user_id()
    if not user_id:
        return _auth_error()
    payload = request.get_json(silent=True) or {}
    term = str(payload.get("term", "")).strip()
    language = str(payload.get("language", "en")).strip()
    if not term:
        return _error("Gõ từ hoặc cụm từ cần tra.", 400, "missing_term")
    if len(term) > 80:
        return _error("Từ/cụm cần tra tối đa 80 ký tự.", 400, "term_too_long")
    if language not in VALID_LANGUAGES:
        return _error("Ngôn ngữ tra cứu không hợp lệ.", 400, "invalid_language")
    try:
        answer = _service().dictionary_lookup(term=term, language=language)
        return jsonify({"answer": answer, "term": term, "language": language})
    except Exception:
        current_app.logger.exception("Language dictionary lookup failed")
        return _error(
            "Từ điển trực tuyến đang lỗi tạm thời.",
            503,
            "dictionary_unavailable",
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
