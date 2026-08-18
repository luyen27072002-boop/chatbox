from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_curriculum(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("tracks"), list):
        raise RuntimeError("language_curriculum.json không đúng định dạng.")
    return raw


def build_track_map(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in content.get("tracks") or []:
        if not isinstance(raw, dict) or not str(raw.get("id", "")).strip():
            continue
        track = dict(raw)
        result[str(track["id"])] = track
    return result


def init_curriculum_db(db) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS language_curriculum_profiles (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            track_id TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            selected_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, language),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_curriculum_activity_progress (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            track_id TEXT NOT NULL,
            stage_id TEXT NOT NULL,
            unit_id TEXT NOT NULL,
            activity_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 100,
            completed_at TEXT NOT NULL,
            PRIMARY KEY(user_id, language, track_id, unit_id, activity_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_curriculum_checkpoint_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            track_id TEXT NOT NULL,
            stage_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            speaking_score INTEGER NOT NULL DEFAULT 0,
            writing_score INTEGER NOT NULL DEFAULT 0,
            passed INTEGER NOT NULL DEFAULT 0,
            answers_json TEXT NOT NULL DEFAULT '{}',
            feedback TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_language_curriculum_activity
        ON language_curriculum_activity_progress(user_id, language, track_id, stage_id, unit_id);

        CREATE INDEX IF NOT EXISTS idx_language_curriculum_checkpoint
        ON language_curriculum_checkpoint_attempts(user_id, language, track_id, stage_id, passed, created_at DESC);
        """
    )
    db.commit()


def public_tracks(content: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for track in content.get("tracks") or []:
        result.append({
            "id": str(track.get("id", "")),
            "title": str(track.get("title", "")),
            "short_title": str(track.get("short_title", track.get("title", ""))),
            "description": str(track.get("description", "")),
            "best_for": [str(x) for x in (track.get("best_for") or [])],
            "target_options": [dict(x) for x in (track.get("target_options") or []) if isinstance(x, dict)],
            "stage_count": len(track.get("stages") or []),
            "accent": str(track.get("accent", "green")),
        })
    return result


def get_selection(db, user_id: str, language: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT * FROM language_curriculum_profiles WHERE user_id = ? AND language = ?",
        (user_id, language),
    ).fetchone()
    return dict(row) if row else None


def select_track(db, *, user_id: str, language: str, track_id: str, target: str) -> dict[str, Any]:
    now = now_iso()
    existing = get_selection(db, user_id, language)
    if existing:
        db.execute(
            """
            UPDATE language_curriculum_profiles
            SET track_id = ?, target = ?, updated_at = ?
            WHERE user_id = ? AND language = ?
            """,
            (track_id, target, now, user_id, language),
        )
    else:
        db.execute(
            """
            INSERT INTO language_curriculum_profiles(user_id, language, track_id, target, selected_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, language, track_id, target, now, now),
        )
    db.commit()
    return get_selection(db, user_id, language) or {}


def _activity_rows(db, user_id: str, language: str, track_id: str) -> set[tuple[str, str]]:
    rows = db.execute(
        """
        SELECT unit_id, activity_id FROM language_curriculum_activity_progress
        WHERE user_id = ? AND language = ? AND track_id = ?
        """,
        (user_id, language, track_id),
    ).fetchall()
    return {(str(row["unit_id"]), str(row["activity_id"])) for row in rows}


def _passed_stages(db, user_id: str, language: str, track_id: str) -> set[str]:
    rows = db.execute(
        """
        SELECT DISTINCT stage_id FROM language_curriculum_checkpoint_attempts
        WHERE user_id = ? AND language = ? AND track_id = ? AND passed = 1
        """,
        (user_id, language, track_id),
    ).fetchall()
    return {str(row["stage_id"]) for row in rows}


def _checkpoint_best(db, user_id: str, language: str, track_id: str, stage_id: str) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT * FROM language_curriculum_checkpoint_attempts
        WHERE user_id = ? AND language = ? AND track_id = ? AND stage_id = ?
        ORDER BY score DESC, created_at DESC LIMIT 1
        """,
        (user_id, language, track_id, stage_id),
    ).fetchone()
    return dict(row) if row else None


def _target_stage_id(track: dict[str, Any], target: str) -> str:
    for option in track.get("target_options") or []:
        if str(option.get("value", "")) == str(target):
            return str(option.get("stage_id", ""))
    stages = track.get("stages") or []
    return str(stages[-1].get("id", "")) if stages else ""


def _public_checkpoint(checkpoint: dict[str, Any], *, available: bool, best: dict[str, Any] | None, stage_complete: bool) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    for question in checkpoint.get("questions") or []:
        if not isinstance(question, dict):
            continue
        public = {k: v for k, v in question.items() if k not in {"answer", "acceptable", "keywords", "model_answer"}}
        questions.append(public)
    return {
        "id": str(checkpoint.get("id", "")),
        "title": str(checkpoint.get("title", "Checkpoint")),
        "description": str(checkpoint.get("description", "")),
        "pass_score": int(checkpoint.get("pass_score", 70) or 70),
        "available": bool(available),
        "stage_complete": bool(stage_complete),
        "passed": bool(best and int(best.get("passed", 0) or 0)),
        "best_score": int((best or {}).get("score", 0) or 0),
        "questions": questions if available else [],
    }


def roadmap(db, *, user_id: str, language: str, track: dict[str, Any], target: str = "") -> dict[str, Any]:
    track_id = str(track.get("id", ""))
    completed_activities = _activity_rows(db, user_id, language, track_id)
    passed_stages = _passed_stages(db, user_id, language, track_id)
    target_stage_id = _target_stage_id(track, target)
    stages_out: list[dict[str, Any]] = []
    previous_stage_passed = True
    current_stage_id = ""
    total_required = 0
    total_done = 0

    for stage_index, stage in enumerate(track.get("stages") or []):
        stage_id = str(stage.get("id", ""))
        stage_unlocked = previous_stage_passed
        units_out: list[dict[str, Any]] = []
        previous_unit_done = True
        stage_units_done = True
        for unit_index, unit in enumerate(stage.get("units") or []):
            unit_id = str(unit.get("id", ""))
            activities_out: list[dict[str, Any]] = []
            required_ids: list[str] = []
            for activity in unit.get("activities") or []:
                activity_id = str(activity.get("id", ""))
                required = bool(activity.get("required", True))
                done = (unit_id, activity_id) in completed_activities
                if required:
                    required_ids.append(activity_id)
                    total_required += 1
                    if done:
                        total_done += 1
                activities_out.append({
                    **{k: v for k, v in activity.items() if k not in {"internal"}},
                    "completed": done,
                })
            unit_done = bool(required_ids) and all((unit_id, aid) in completed_activities for aid in required_ids)
            unit_unlocked = stage_unlocked and previous_unit_done
            if not unit_done:
                stage_units_done = False
            units_out.append({
                "id": unit_id,
                "title": str(unit.get("title", "")),
                "outcome": str(unit.get("outcome", "")),
                "description": str(unit.get("description", "")),
                "minutes": int(unit.get("minutes", 15) or 15),
                "unlocked": unit_unlocked,
                "completed": unit_done,
                "activities": activities_out,
                "required_done": sum(1 for aid in required_ids if (unit_id, aid) in completed_activities),
                "required_total": len(required_ids),
            })
            previous_unit_done = unit_done
        checkpoint = stage.get("checkpoint") or {}
        best = _checkpoint_best(db, user_id, language, track_id, stage_id)
        passed = stage_id in passed_stages
        checkpoint_available = stage_unlocked and stage_units_done
        if stage_unlocked and not passed and not current_stage_id:
            current_stage_id = stage_id
        stages_out.append({
            "id": stage_id,
            "label": str(stage.get("label", "")),
            "level": str(stage.get("level", "")),
            "title": str(stage.get("title", "")),
            "outcome": str(stage.get("outcome", "")),
            "description": str(stage.get("description", "")),
            "unlocked": stage_unlocked,
            "passed": passed,
            "is_target": stage_id == target_stage_id,
            "units": units_out,
            "checkpoint": _public_checkpoint(checkpoint, available=checkpoint_available, best=best, stage_complete=stage_units_done),
        })
        previous_stage_passed = passed

    if not current_stage_id and stages_out:
        current_stage_id = stages_out[-1]["id"]
    return {
        "track_id": track_id,
        "track_title": str(track.get("title", "")),
        "target": target,
        "target_stage_id": target_stage_id,
        "current_stage_id": current_stage_id,
        "activity_progress": round(total_done / max(1, total_required) * 100),
        "activity_done": total_done,
        "activity_total": total_required,
        "stages": stages_out,
    }


def find_stage(track: dict[str, Any], stage_id: str) -> dict[str, Any] | None:
    for stage in track.get("stages") or []:
        if str(stage.get("id", "")) == str(stage_id):
            return stage
    return None


def find_unit(track: dict[str, Any], unit_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for stage in track.get("stages") or []:
        for unit in stage.get("units") or []:
            if str(unit.get("id", "")) == str(unit_id):
                return stage, unit
    return None, None


def complete_activity(
    db,
    *,
    user_id: str,
    language: str,
    track: dict[str, Any],
    unit_id: str,
    activity_id: str,
    score: int = 100,
) -> dict[str, Any]:
    stage, unit = find_unit(track, unit_id)
    if not stage or not unit:
        raise ValueError("unit_not_found")
    activity = next((a for a in unit.get("activities") or [] if str(a.get("id", "")) == str(activity_id)), None)
    if not activity:
        raise ValueError("activity_not_found")
    now = now_iso()
    db.execute(
        """
        INSERT INTO language_curriculum_activity_progress(
            user_id, language, track_id, stage_id, unit_id, activity_id, score, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, language, track_id, unit_id, activity_id)
        DO UPDATE SET score = MAX(score, excluded.score), completed_at = excluded.completed_at
        """,
        (
            user_id, language, str(track.get("id", "")), str(stage.get("id", "")),
            unit_id, activity_id, max(0, min(100, int(score))), now,
        ),
    )
    db.commit()
    return {"ok": True, "unit_id": unit_id, "activity_id": activity_id}


def checkpoint_definition(track: dict[str, Any], stage_id: str) -> dict[str, Any] | None:
    stage = find_stage(track, stage_id)
    if not stage:
        return None
    checkpoint = dict(stage.get("checkpoint") or {})
    checkpoint["stage_id"] = stage_id
    return checkpoint


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split()).strip(" .,!?:;\"'()[]{}")


def score_fixed_questions(checkpoint: dict[str, Any], answers: dict[str, Any]) -> tuple[int, int, list[str]]:
    fixed = [q for q in (checkpoint.get("questions") or []) if str(q.get("type", "")) in {"mcq", "listening", "reading"}]
    if not fixed:
        return 0, 0, []
    points = 0
    feedback: list[str] = []
    for question in fixed:
        qid = str(question.get("id", ""))
        answer = _normalize(answers.get(qid, ""))
        expected = _normalize(question.get("answer", ""))
        ok = answer == expected
        points += 1 if ok else 0
        if not ok:
            feedback.append(str(question.get("feedback", "Ôn lại mục này.")))
    return round(points / len(fixed) * 100), len(fixed), feedback[:3]


def save_checkpoint_attempt(
    db,
    *,
    user_id: str,
    language: str,
    track_id: str,
    stage_id: str,
    score: int,
    speaking_score: int,
    writing_score: int,
    passed: bool,
    answers: dict[str, Any],
    feedback: str,
) -> dict[str, Any]:
    now = now_iso()
    db.execute(
        """
        INSERT INTO language_curriculum_checkpoint_attempts(
            user_id, language, track_id, stage_id, score, speaking_score, writing_score,
            passed, answers_json, feedback, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, language, track_id, stage_id, int(score), int(speaking_score), int(writing_score),
            1 if passed else 0, json.dumps(answers, ensure_ascii=False), str(feedback or "")[:2000], now,
        ),
    )
    db.commit()
    return {
        "score": int(score),
        "speaking_score": int(speaking_score),
        "writing_score": int(writing_score),
        "passed": bool(passed),
        "feedback": feedback,
    }
