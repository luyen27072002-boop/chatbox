from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    return date.today().isoformat()


def normalize_term(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    text = text.strip(" \t\r\n.,!?;:'\"()[]{}<>，。！？；：、")
    return text[:120]


def _json_list(value: Any, limit: int = 8) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
            items = parsed if isinstance(parsed, list) else []
        except Exception:
            items = []
    else:
        items = []
    out: list[str] = []
    for item in items:
        text = normalize_term(item)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def ensure_profile(db, user_id: str) -> None:
    now = now_iso()
    db.execute(
        """
        INSERT INTO language_player_profiles(
            user_id, character_gender, character_name, target_language, life_role,
            skin_tone, hair_style, hair_color, outfit_style, face_style,
            xp, streak, best_streak, last_active_date, created_at, updated_at
        ) VALUES (?, '', '', 'en', '', 'light', 'short', 'black', 'casual', 'smile', 0, 0, 0, '', ?, ?)
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, now, now),
    )


def get_profile(db, user_id: str) -> dict[str, Any]:
    ensure_profile(db, user_id)
    row = db.execute(
        "SELECT * FROM language_player_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    profile = dict(row) if row else {}
    xp = int(profile.get("xp", 0) or 0)
    profile["player_level"] = max(1, xp // 500 + 1)
    profile["xp_into_level"] = xp % 500
    profile["xp_to_next_level"] = 500
    profile["profile_ready"] = bool(str(profile.get("character_gender", "")).strip() and str(profile.get("life_role", "")).strip())
    profile["appearance"] = {
        "skin_tone": str(profile.get("skin_tone", "light") or "light"),
        "hair_style": str(profile.get("hair_style", "short") or "short"),
        "hair_color": str(profile.get("hair_color", "black") or "black"),
        "outfit_style": str(profile.get("outfit_style", "casual") or "casual"),
        "face_style": str(profile.get("face_style", "smile") or "smile"),
    }
    return profile


def save_profile(
    db,
    user_id: str,
    *,
    character_gender: str,
    character_name: str,
    target_language: str,
    life_role: str = "student",
    skin_tone: str = "light",
    hair_style: str = "short",
    hair_color: str = "black",
    outfit_style: str = "casual",
    face_style: str = "smile",
    learning_goal: str = "comprehensive",
    daily_minutes: int = 20,
    cefr_level: str = "A1-A2",
) -> dict[str, Any]:
    ensure_profile(db, user_id)
    now = now_iso()
    db.execute(
        """
        UPDATE language_player_profiles
        SET character_gender = ?, character_name = ?, target_language = ?, life_role = ?,
            skin_tone = ?, hair_style = ?, hair_color = ?, outfit_style = ?, face_style = ?,
            learning_goal = ?, daily_minutes = ?, cefr_level = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (
            character_gender, normalize_term(character_name)[:40], target_language, life_role,
            skin_tone, hair_style, hair_color, outfit_style, face_style,
            learning_goal, max(5, min(60, int(daily_minutes or 20))), cefr_level, now, user_id,
        ),
    )
    db.commit()
    return get_profile(db, user_id)


def award_activity(
    db,
    user_id: str,
    *,
    xp: int,
    turns: int = 0,
    missions_completed: int = 0,
) -> dict[str, Any]:
    ensure_profile(db, user_id)
    xp = max(0, int(xp))
    today = date.today()
    today_text = today.isoformat()
    row = db.execute(
        "SELECT streak, best_streak, last_active_date FROM language_player_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    streak = int(row["streak"] or 0) if row else 0
    best = int(row["best_streak"] or 0) if row else 0
    last_text = str(row["last_active_date"] or "") if row else ""

    if last_text != today_text:
        try:
            last = date.fromisoformat(last_text) if last_text else None
        except ValueError:
            last = None
        if last == today - timedelta(days=1):
            streak += 1
        else:
            streak = 1
        best = max(best, streak)

    now = now_iso()
    db.execute(
        """
        UPDATE language_player_profiles
        SET xp = xp + ?, streak = ?, best_streak = ?, last_active_date = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (xp, streak, best, today_text, now, user_id),
    )
    db.execute(
        """
        INSERT INTO language_daily_activity(user_id, activity_date, xp, turns, missions_completed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, activity_date)
        DO UPDATE SET
            xp = xp + excluded.xp,
            turns = turns + excluded.turns,
            missions_completed = missions_completed + excluded.missions_completed
        """,
        (user_id, today_text, xp, max(0, int(turns)), max(0, int(missions_completed))),
    )
    return get_profile(db, user_id)


def _importance_score(old_score: int, raw_importance: int, encounters: int, player_uses: int) -> int:
    raw = max(1, min(5, int(raw_importance or 3)))
    base = raw * 16
    frequency = min(18, int(math.log2(max(1, encounters) + 1) * 4))
    active = min(12, player_uses * 2)
    return max(int(old_score or 0), min(100, base + frequency + active))


def record_vocab_events(
    db,
    *,
    user_id: str,
    session_id: str,
    language: str,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    now = now_iso()
    changed: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for raw in events[:12]:
        if not isinstance(raw, dict):
            continue
        term = normalize_term(raw.get("term", ""))
        if not term or len(term) < 2:
            continue
        source = str(raw.get("source", "npc")).strip().lower()
        if source not in {"npc", "player", "hint"}:
            source = "npc"
        key = (term.casefold(), source)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        importance = max(1, min(5, int(raw.get("importance", 3) or 3)))
        understood = bool(raw.get("understood", source == "player"))
        context = normalize_term(raw.get("context", ""))[:240]
        meaning = normalize_term(raw.get("meaning", ""))[:160]
        event_type = {
            "npc": "encountered",
            "player": "used",
            "hint": "helped",
        }[source]

        db.execute(
            """
            INSERT INTO language_vocab_events(
                user_id, session_id, language, term, event_type, importance,
                understood, context, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                session_id,
                language,
                term,
                event_type,
                importance,
                1 if understood else 0,
                context,
                now,
            ),
        )

        row = db.execute(
            """
            SELECT * FROM language_vocab_stats
            WHERE user_id = ? AND language = ? AND normalized_term = ?
            """,
            (user_id, language, term.casefold()),
        ).fetchone()

        old = dict(row) if row else {}
        encounters = int(old.get("encounters", 0) or 0) + 1
        npc_count = int(old.get("npc_encounters", 0) or 0) + (1 if source == "npc" else 0)
        player_uses = int(old.get("player_uses", 0) or 0) + (1 if source == "player" else 0)
        help_uses = int(old.get("help_uses", 0) or 0) + (1 if source == "hint" else 0)
        mastery = float(old.get("mastery", 0) or 0)

        if source == "player":
            mastery += 9.0
        elif source == "npc" and understood:
            mastery += 4.0
        elif source == "npc":
            mastery += 1.5
        else:
            mastery += 0.5
        if encounters >= 3:
            mastery += 0.5
        mastery = round(min(100.0, mastery), 1)

        importance_score = _importance_score(
            int(old.get("importance_score", 0) or 0), importance, encounters, player_uses
        )
        contexts = _json_list(old.get("contexts_json", "[]"), limit=6)
        if context and context not in contexts:
            contexts.append(context)
            contexts = contexts[-6:]

        if row:
            db.execute(
                """
                UPDATE language_vocab_stats
                SET term = ?, meaning = CASE WHEN ? <> '' THEN ? ELSE meaning END,
                    encounters = ?, npc_encounters = ?, player_uses = ?, help_uses = ?,
                    mastery = ?, importance_score = ?, contexts_json = ?, last_seen_at = ?
                WHERE user_id = ? AND language = ? AND normalized_term = ?
                """,
                (
                    term,
                    meaning,
                    meaning,
                    encounters,
                    npc_count,
                    player_uses,
                    help_uses,
                    mastery,
                    importance_score,
                    json.dumps(contexts, ensure_ascii=False),
                    now,
                    user_id,
                    language,
                    term.casefold(),
                ),
            )
        else:
            db.execute(
                """
                INSERT INTO language_vocab_stats(
                    user_id, language, term, normalized_term, meaning,
                    encounters, npc_encounters, player_uses, help_uses,
                    mastery, importance_score, contexts_json, first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    language,
                    term,
                    term.casefold(),
                    meaning,
                    encounters,
                    npc_count,
                    player_uses,
                    help_uses,
                    mastery,
                    importance_score,
                    json.dumps(contexts, ensure_ascii=False),
                    now,
                    now,
                ),
            )

        changed.append(
            {
                "term": term,
                "source": source,
                "encounters": encounters,
                "player_uses": player_uses,
                "mastery": mastery,
                "importance_score": importance_score,
            }
        )
    return changed


def record_skill_attempts(
    db,
    *,
    user_id: str,
    language: str,
    skills: list[str],
    score: int,
) -> None:
    now = now_iso()
    score = max(0, min(100, int(score)))
    for raw in skills[:10]:
        skill = normalize_term(raw).lower().replace(" ", "_")
        if not skill:
            continue
        row = db.execute(
            """
            SELECT attempts, mastery FROM language_skill_stats
            WHERE user_id = ? AND language = ? AND skill = ?
            """,
            (user_id, language, skill),
        ).fetchone()
        if row:
            attempts = int(row["attempts"] or 0) + 1
            old = float(row["mastery"] or 0)
            alpha = 0.35 if attempts < 5 else 0.22
            mastery = round(old * (1 - alpha) + score * alpha, 1)
            db.execute(
                """
                UPDATE language_skill_stats
                SET attempts = ?, successes = successes + ?, mastery = ?, updated_at = ?
                WHERE user_id = ? AND language = ? AND skill = ?
                """,
                (attempts, 1 if score >= 65 else 0, mastery, now, user_id, language, skill),
            )
        else:
            db.execute(
                """
                INSERT INTO language_skill_stats(
                    user_id, language, skill, attempts, successes, mastery, updated_at
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (user_id, language, skill, 1 if score >= 65 else 0, float(score), now),
            )


def update_mission_progress(
    db,
    *,
    user_id: str,
    scene_id: str,
    score: int,
    stars: int,
    completed: bool,
    new_attempt: bool = False,
) -> None:
    now = now_iso()
    row = db.execute(
        "SELECT * FROM language_mission_progress WHERE user_id = ? AND scene_id = ?",
        (user_id, scene_id),
    ).fetchone()
    if row:
        db.execute(
            """
            UPDATE language_mission_progress
            SET best_score = MAX(best_score, ?), best_stars = MAX(best_stars, ?),
                attempts = attempts + ?,
                completions = completions + ?,
                last_played_at = ?
            WHERE user_id = ? AND scene_id = ?
            """,
            (score, stars, 1 if new_attempt else 0, 1 if completed else 0, now, user_id, scene_id),
        )
    else:
        db.execute(
            """
            INSERT INTO language_mission_progress(
                user_id, scene_id, best_score, best_stars, attempts, completions, last_played_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, scene_id, score, stars, 1 if new_attempt else 0, 1 if completed else 0, now),
        )


def vocabulary_overview(db, user_id: str, language: str, limit: int = 12) -> dict[str, Any]:
    where = "user_id = ?"
    args: list[Any] = [user_id]
    if language in {"en", "zh"}:
        where += " AND language = ?"
        args.append(language)

    totals = db.execute(
        f"""
        SELECT COUNT(*) AS discovered,
               SUM(CASE WHEN player_uses >= 2 THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN mastery >= 80 AND encounters >= 4 THEN 1 ELSE 0 END) AS mastered,
               COALESCE(SUM(encounters), 0) AS total_encounters
        FROM language_vocab_stats
        WHERE {where}
        """,
        tuple(args),
    ).fetchone()

    rows = db.execute(
        f"""
        SELECT term, meaning, encounters, npc_encounters, player_uses, help_uses,
               mastery, importance_score, contexts_json, last_seen_at
        FROM language_vocab_stats
        WHERE {where}
        ORDER BY importance_score DESC, encounters DESC, player_uses DESC
        LIMIT ?
        """,
        (*args, max(1, min(50, int(limit)))),
    ).fetchall()
    terms = []
    for row in rows:
        item = dict(row)
        item["contexts"] = _json_list(item.pop("contexts_json", "[]"), limit=6)
        terms.append(item)

    return {
        "discovered": int(totals["discovered"] or 0) if totals else 0,
        "active": int(totals["active"] or 0) if totals else 0,
        "mastered": int(totals["mastered"] or 0) if totals else 0,
        "total_encounters": int(totals["total_encounters"] or 0) if totals else 0,
        "terms": terms,
    }


def skill_overview(db, user_id: str, language: str, limit: int = 12) -> list[dict[str, Any]]:
    args: list[Any] = [user_id]
    where = "user_id = ?"
    if language in {"en", "zh"}:
        where += " AND language = ?"
        args.append(language)
    rows = db.execute(
        f"""
        SELECT skill, attempts, successes, mastery
        FROM language_skill_stats
        WHERE {where}
        ORDER BY mastery DESC, attempts DESC
        LIMIT ?
        """,
        (*args, max(1, min(30, int(limit)))),
    ).fetchall()
    return [dict(row) for row in rows]


def session_summary(db, user_id: str, session_id: str) -> dict[str, Any]:
    session = db.execute(
        "SELECT * FROM language_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not session:
        return {}
    vocab_rows = db.execute(
        """
        SELECT term,
               COUNT(*) AS encounters,
               SUM(CASE WHEN event_type = 'used' THEN 1 ELSE 0 END) AS used,
               MAX(importance) AS importance
        FROM language_vocab_events
        WHERE user_id = ? AND session_id = ?
        GROUP BY lower(term)
        ORDER BY used DESC, importance DESC, encounters DESC
        LIMIT 12
        """,
        (user_id, session_id),
    ).fetchall()
    player_count = db.execute(
        """
        SELECT COUNT(*) AS n FROM language_messages
        WHERE session_id = ? AND user_id = ? AND role = 'player'
        """,
        (session_id, user_id),
    ).fetchone()
    return {
        "session": dict(session),
        "turns": int(player_count["n"] or 0) if player_count else 0,
        "terms": [dict(row) for row in vocab_rows],
    }


def leaderboard(db, user_id: str, limit: int = 10) -> dict[str, Any]:
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    rows = db.execute(
        """
        SELECT p.user_id,
               COALESCE(NULLIF(p.character_name, ''), u.display_name, 'Người chơi') AS name,
               COALESCE(SUM(a.xp), 0) AS weekly_xp,
               p.xp AS total_xp,
               p.streak
        FROM language_player_profiles p
        JOIN accounts u ON u.id = p.user_id
        LEFT JOIN language_daily_activity a
          ON a.user_id = p.user_id AND a.activity_date >= ?
        GROUP BY p.user_id, name, p.xp, p.streak
        ORDER BY weekly_xp DESC, p.xp DESC
        LIMIT ?
        """,
        (monday, max(3, min(30, int(limit)))),
    ).fetchall()
    items = [{**dict(row), "is_me": str(row["user_id"]) == str(user_id)} for row in rows]
    my_rank = None
    all_rows = db.execute(
        """
        SELECT p.user_id, COALESCE(SUM(a.xp), 0) AS weekly_xp, p.xp AS total_xp
        FROM language_player_profiles p
        LEFT JOIN language_daily_activity a
          ON a.user_id = p.user_id AND a.activity_date >= ?
        GROUP BY p.user_id, p.xp
        ORDER BY weekly_xp DESC, p.xp DESC
        """,
        (monday,),
    ).fetchall()
    for index, row in enumerate(all_rows, start=1):
        if str(row["user_id"]) == str(user_id):
            my_rank = index
            break
    return {"week_start": monday, "items": items, "my_rank": my_rank}


def record_learning_term(
    db,
    *,
    user_id: str,
    language: str,
    term: str,
    meaning: str = "",
    score: int = 70,
    importance: int = 5,
    active_use: bool = False,
    context: str = "learning module",
) -> dict[str, Any]:
    """Ghi nhận từ/cụm học trong lesson vào cùng Language Life Record với game."""
    now = now_iso()
    term = normalize_term(term)
    if not term:
        return {}
    normalized = term.casefold()
    row = db.execute(
        """
        SELECT * FROM language_vocab_stats
        WHERE user_id = ? AND language = ? AND normalized_term = ?
        """,
        (user_id, language, normalized),
    ).fetchone()
    old = dict(row) if row else {}
    encounters = int(old.get("encounters", 0) or 0) + 1
    npc_count = int(old.get("npc_encounters", 0) or 0)
    player_uses = int(old.get("player_uses", 0) or 0) + (1 if active_use else 0)
    help_uses = int(old.get("help_uses", 0) or 0)
    mastery = float(old.get("mastery", 0) or 0)
    score = max(0, min(100, int(score)))
    gain = 2.5 + (score / 100.0) * (8.0 if active_use else 5.0)
    mastery = round(min(100.0, mastery + gain), 1)
    importance_score = _importance_score(int(old.get("importance_score", 0) or 0), importance, encounters, player_uses)
    contexts = _json_list(old.get("contexts_json", "[]"), limit=6)
    clean_context = normalize_term(context)[:240]
    if clean_context and clean_context not in contexts:
        contexts.append(clean_context)
        contexts = contexts[-6:]
    clean_meaning = normalize_term(meaning)[:160]

    if row:
        db.execute(
            """
            UPDATE language_vocab_stats
            SET term = ?, meaning = CASE WHEN ? <> '' THEN ? ELSE meaning END,
                encounters = ?, npc_encounters = ?, player_uses = ?, help_uses = ?,
                mastery = ?, importance_score = ?, contexts_json = ?, last_seen_at = ?
            WHERE user_id = ? AND language = ? AND normalized_term = ?
            """,
            (
                term, clean_meaning, clean_meaning, encounters, npc_count, player_uses, help_uses,
                mastery, importance_score, json.dumps(contexts, ensure_ascii=False), now,
                user_id, language, normalized,
            ),
        )
    else:
        db.execute(
            """
            INSERT INTO language_vocab_stats(
                user_id, language, term, normalized_term, meaning,
                encounters, npc_encounters, player_uses, help_uses,
                mastery, importance_score, contexts_json, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, language, term, normalized, clean_meaning,
                encounters, npc_count, player_uses, help_uses,
                mastery, importance_score, json.dumps(contexts, ensure_ascii=False), now, now,
            ),
        )
    return {
        "term": term,
        "encounters": encounters,
        "player_uses": player_uses,
        "mastery": mastery,
        "importance_score": importance_score,
    }
