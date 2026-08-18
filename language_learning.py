from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MODULES = {
    "vocabulary",
    "phrases",
    "grammar",
    "listening",
    "speaking",
    "reading",
    "writing",
    "pronunciation",
}

MODULE_LABELS = {
    "vocabulary": "Từ vựng",
    "phrases": "Câu giao tiếp",
    "grammar": "Ngữ pháp",
    "listening": "Listening",
    "speaking": "Speaking",
    "reading": "Reading",
    "writing": "Writing",
    "pronunciation": "Phát âm",
}

SKILL_FOR_MODULE = {
    "vocabulary": "vocabulary",
    "phrases": "communication_phrases",
    "grammar": "grammar",
    "listening": "listening",
    "speaking": "speaking",
    "reading": "reading",
    "writing": "writing",
    "pronunciation": "pronunciation",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> date:
    return date.today()


def normalize(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
    text = text.strip(" \t\r\n.,!?;:'\"()[]{}<>，。！？；：、")
    return text


def load_content(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("language_learning_content.json phải là object.")
    return raw


def build_item_map(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for language, modules in content.items():
        if not isinstance(modules, dict):
            continue
        for module, items in modules.items():
            if module not in MODULES or not isinstance(items, list):
                continue
            for raw in items:
                if not isinstance(raw, dict) or not raw.get("id"):
                    continue
                item = dict(raw)
                item["language"] = language
                item["module"] = module
                result[str(item["id"])] = item
    return result


def init_learning_db(db) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS language_learning_progress (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            item_id TEXT NOT NULL,
            module TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            mastery REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'new',
            due_date TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(user_id, language, item_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_learning_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            item_id TEXT NOT NULL,
            module TEXT NOT NULL,
            answer_text TEXT NOT NULL DEFAULT '',
            score INTEGER NOT NULL DEFAULT 0,
            correct INTEGER NOT NULL DEFAULT 0,
            feedback TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_language_learning_due
        ON language_learning_progress(user_id, language, due_date, mastery);

        CREATE INDEX IF NOT EXISTS idx_language_learning_attempts_user_date
        ON language_learning_attempts(user_id, created_at DESC);
        """
    )
    db.commit()


def _level_matches(item_level: str, selected_level: str) -> bool:
    item_level = str(item_level or "A1-A2")
    selected_level = str(selected_level or "A1-A2")
    if selected_level == "C1-C2":
        return item_level in {"A1-A2", "B1-B2", "C1-C2"}
    if selected_level == "B1-B2":
        return item_level in {"A1-A2", "B1-B2"}
    return item_level == "A1-A2"


def _public_item(item: dict[str, Any], progress: dict[str, Any] | None = None) -> dict[str, Any]:
    blocked = {"answer", "acceptable", "model"}
    out = {k: v for k, v in item.items() if k not in blocked}
    if progress:
        out["mastery"] = float(progress.get("mastery", 0) or 0)
        out["attempts"] = int(progress.get("attempts", 0) or 0)
        out["due_date"] = str(progress.get("due_date", "") or "")
        out["status"] = str(progress.get("status", "new") or "new")
    else:
        out.update({"mastery": 0.0, "attempts": 0, "due_date": "", "status": "new"})
    return out


def _progress_map(db, user_id: str, language: str) -> dict[str, dict[str, Any]]:
    rows = db.execute(
        "SELECT * FROM language_learning_progress WHERE user_id = ? AND language = ?",
        (user_id, language),
    ).fetchall()
    return {str(row["item_id"]): dict(row) for row in rows}


def items_for_module(
    db,
    *,
    user_id: str,
    language: str,
    level: str,
    module: str,
    content: dict[str, Any],
    mode: str = "new",
    limit: int = 8,
) -> list[dict[str, Any]]:
    if module not in MODULES:
        return []
    candidates = []
    for raw in ((content.get(language) or {}).get(module) or []):
        if not isinstance(raw, dict) or not _level_matches(str(raw.get("level", "A1-A2")), level):
            continue
        item = dict(raw)
        item["language"] = language
        item["module"] = module
        candidates.append(item)
    progress = _progress_map(db, user_id, language)
    today_text = _today().isoformat()

    def key_new(item: dict[str, Any]):
        p = progress.get(str(item.get("id")))
        level_priority = 0 if str(item.get("level", "")) == level else 1
        return (1 if p else 0, level_priority, float((p or {}).get("mastery", 0) or 0), str(item.get("id")))

    def key_review(item: dict[str, Any]):
        p = progress.get(str(item.get("id")), {})
        due = str(p.get("due_date", "") or "")
        is_due = bool(p) and (not due or due <= today_text)
        return (0 if is_due else 1, float(p.get("mastery", 0) or 0), str(p.get("last_seen_at", "")))

    if mode == "review":
        candidates = [
            item for item in candidates
            if str(item.get("id")) in progress
            and (
                not str(progress[str(item["id"])].get("due_date", "") or "")
                or str(progress[str(item["id"])].get("due_date", "")) <= today_text
                or float(progress[str(item["id"])].get("mastery", 0) or 0) < 70
            )
        ]
        candidates.sort(key=key_review)
    else:
        candidates.sort(key=key_new)

    return [_public_item(item, progress.get(str(item.get("id")))) for item in candidates[: max(1, min(30, int(limit)))]]


def _interval_days(mastery: float, correct: bool) -> int:
    if not correct:
        return 1
    if mastery < 35:
        return 1
    if mastery < 60:
        return 3
    if mastery < 80:
        return 7
    if mastery < 92:
        return 14
    return 30


def _next_mastery(old: float, score: int, attempts: int) -> float:
    score = max(0, min(100, int(score)))
    if attempts <= 1:
        return round(max(old, score * 0.55), 1)
    alpha = 0.34 if attempts < 5 else 0.24
    result = old * (1 - alpha) + score * alpha
    if score >= 85:
        result += 4
    elif score < 50:
        result -= 6
    return round(max(0.0, min(100.0, result)), 1)


def evaluate_fixed(item: dict[str, Any], answer: str) -> tuple[int, bool, str]:
    expected = item.get("answer")
    acceptable = item.get("acceptable") if isinstance(item.get("acceptable"), list) else []
    candidates = [expected, *acceptable]
    user = normalize(answer)
    ok = any(user == normalize(candidate) for candidate in candidates if candidate is not None)
    if not ok and expected and user:
        # Lenient fill-in matching for short language answers.
        exp = normalize(expected)
        if len(user) >= 4 and (user in exp or exp in user):
            ok = True
    return (100 if ok else 30, ok, "Đúng rồi." if ok else f"Đáp án phù hợp hơn: {expected}")


def record_attempt(
    db,
    *,
    user_id: str,
    language: str,
    item: dict[str, Any],
    answer: str,
    score: int,
    feedback: str,
) -> dict[str, Any]:
    module = str(item.get("module", ""))
    item_id = str(item.get("id", ""))
    score = max(0, min(100, int(score)))
    correct = score >= 65
    now = now_iso()
    row = db.execute(
        """
        SELECT * FROM language_learning_progress
        WHERE user_id = ? AND language = ? AND item_id = ?
        """,
        (user_id, language, item_id),
    ).fetchone()
    old = dict(row) if row else {}
    attempts = int(old.get("attempts", 0) or 0) + 1
    mastery = _next_mastery(float(old.get("mastery", 0) or 0), score, attempts)
    due = (_today() + timedelta(days=_interval_days(mastery, correct))).isoformat()
    status = "mastered" if mastery >= 85 and attempts >= 2 else "learning"

    if row:
        db.execute(
            """
            UPDATE language_learning_progress
            SET attempts = ?, correct_count = correct_count + ?, mastery = ?, status = ?,
                due_date = ?, last_seen_at = ?
            WHERE user_id = ? AND language = ? AND item_id = ?
            """,
            (attempts, 1 if correct else 0, mastery, status, due, now, user_id, language, item_id),
        )
    else:
        db.execute(
            """
            INSERT INTO language_learning_progress(
                user_id, language, item_id, module, attempts, correct_count,
                mastery, status, due_date, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, language, item_id, module, 1 if correct else 0, mastery, status, due, now, now),
        )

    db.execute(
        """
        INSERT INTO language_learning_attempts(
            user_id, language, item_id, module, answer_text, score, correct, feedback, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, language, item_id, module, str(answer or "")[:1600], score, 1 if correct else 0, str(feedback or "")[:1200], now),
    )
    return {
        "item_id": item_id,
        "module": module,
        "score": score,
        "correct": correct,
        "mastery": mastery,
        "due_date": due,
        "status": status,
    }


def _counts_by_module(db, user_id: str, language: str) -> dict[str, dict[str, int]]:
    rows = db.execute(
        """
        SELECT module,
               COUNT(*) AS seen,
               SUM(CASE WHEN mastery >= 85 THEN 1 ELSE 0 END) AS mastered,
               SUM(CASE WHEN due_date <> '' AND due_date <= ? THEN 1 ELSE 0 END) AS due
        FROM language_learning_progress
        WHERE user_id = ? AND language = ?
        GROUP BY module
        """,
        (_today().isoformat(), user_id, language),
    ).fetchall()
    result = {module: {"seen": 0, "mastered": 0, "due": 0} for module in MODULES}
    for row in rows:
        module = str(row["module"])
        if module in result:
            result[module] = {
                "seen": int(row["seen"] or 0),
                "mastered": int(row["mastered"] or 0),
                "due": int(row["due"] or 0),
            }
    return result


def _today_attempts(db, user_id: str) -> int:
    start = f"{_today().isoformat()}T00:00:00"
    row = db.execute(
        "SELECT COUNT(*) AS n FROM language_learning_attempts WHERE user_id = ? AND created_at >= ?",
        (user_id, start),
    ).fetchone()
    return int(row["n"] or 0) if row else 0




def _today_game_steps(db, user_id: str) -> int:
    try:
        row = db.execute(
            "SELECT missions_completed, turns FROM language_daily_activity WHERE user_id = ? AND activity_date = ?",
            (user_id, _today().isoformat()),
        ).fetchone()
    except Exception:
        return 0
    if not row:
        return 0
    missions = int(row["missions_completed"] or 0)
    turns = int(row["turns"] or 0)
    return missions + (1 if turns >= 3 else 0)

def dashboard(
    db,
    *,
    user_id: str,
    language: str,
    level: str,
    daily_minutes: int,
    content: dict[str, Any],
    learning_goal: str = "comprehensive",
) -> dict[str, Any]:
    counts = _counts_by_module(db, user_id, language)
    attempts_today = _today_attempts(db, user_id) + _today_game_steps(db, user_id)
    minutes = max(5, min(60, int(daily_minutes or 20)))
    target_steps = max(3, round(minutes / 3.5))

    due_total = sum(v["due"] for v in counts.values())
    base = {
        "review": {"id": "review", "module": "review", "title": "Ôn thứ sắp quên", "subtitle": f"{due_total} mục đang đến hạn", "minutes": 3, "action": "review"},
        "vocabulary": {"id": "vocabulary", "module": "vocabulary", "title": "Từ vựng cốt lõi", "subtitle": "Từ đời sống, ưu tiên từ hữu dụng", "minutes": 4, "action": "new"},
        "phrases": {"id": "phrases", "module": "phrases", "title": "Câu giao tiếp", "subtitle": "Cụm nói được ngay trong đời sống", "minutes": 4, "action": "new"},
        "grammar": {"id": "grammar", "module": "grammar", "title": "Ngữ pháp để dùng", "subtitle": "Một cấu trúc ngắn rồi áp dụng", "minutes": 4, "action": "new"},
        "listening": {"id": "listening", "module": "listening", "title": "Nghe nhanh", "subtitle": "Một tình huống đời thường", "minutes": 4, "action": "new"},
        "reading": {"id": "reading", "module": "reading", "title": "Đọc nhanh", "subtitle": "Tin nhắn, thông báo hoặc email ngắn", "minutes": 4, "action": "new"},
        "writing": {"id": "writing", "module": "writing", "title": "Viết thực tế", "subtitle": "Một tin nhắn hoặc email ngắn", "minutes": 5, "action": "new"},
        "games": {"id": "games", "module": "games", "title": "Áp dụng bằng game", "subtitle": "Dùng thứ đã học vào tình huống", "minutes": 5, "action": "games"},
    }
    goal_orders = {
        "work": ["review", "phrases", "listening", "writing", "games"],
        "study": ["review", "vocabulary", "grammar", "reading", "writing"],
        "exam": ["review", "vocabulary", "grammar", "reading", "listening"],
        "travel": ["review", "phrases", "vocabulary", "listening", "games"],
        "daily": ["review", "phrases", "vocabulary", "listening", "games"],
        "comprehensive": ["review", "vocabulary", "phrases", "listening", "games"],
    }
    plan = [base[key] for key in goal_orders.get(str(learning_goal), goal_orders["comprehensive"])]
    if minutes <= 10:
        plan = [plan[0], plan[1], plan[4]]
    elif minutes <= 15:
        plan = [plan[0], plan[1], plan[2], plan[4]]

    today_progress = min(100, round(attempts_today / max(1, target_steps) * 100))
    return {
        "date": _today().isoformat(),
        "daily_minutes": minutes,
        "target_steps": target_steps,
        "attempts_today": attempts_today,
        "today_progress": today_progress,
        "plan": plan,
        "module_counts": counts,
    }


def review_items(
    db,
    *,
    user_id: str,
    language: str,
    level: str,
    content: dict[str, Any],
    limit: int = 12,
) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for module in ("vocabulary", "phrases", "grammar", "listening", "reading", "pronunciation"):
        all_items.extend(items_for_module(
            db, user_id=user_id, language=language, level=level,
            module=module, content=content, mode="review", limit=4,
        ))
    all_items.sort(key=lambda item: (float(item.get("mastery", 0) or 0), str(item.get("due_date", ""))))
    return all_items[: max(1, min(30, int(limit)))]


def progress_summary(db, *, user_id: str, language: str, content: dict[str, Any]) -> dict[str, Any]:
    counts = _counts_by_module(db, user_id, language)
    rows = db.execute(
        """
        SELECT module, AVG(mastery) AS mastery, SUM(attempts) AS attempts
        FROM language_learning_progress
        WHERE user_id = ? AND language = ?
        GROUP BY module
        """,
        (user_id, language),
    ).fetchall()
    mastery = {module: 0 for module in MODULES}
    attempts = {module: 0 for module in MODULES}
    for row in rows:
        module = str(row["module"])
        if module in mastery:
            mastery[module] = round(float(row["mastery"] or 0), 1)
            attempts[module] = int(row["attempts"] or 0)
    total_items = sum(len(items) for module, items in (content.get(language) or {}).items() if module in MODULES and isinstance(items, list))
    seen = sum(v["seen"] for v in counts.values())
    mastered = sum(v["mastered"] for v in counts.values())
    return {
        "modules": [
            {
                "module": module,
                "label": MODULE_LABELS[module],
                "mastery": mastery[module],
                "attempts": attempts[module],
                "seen": counts[module]["seen"],
                "mastered": counts[module]["mastered"],
                "due": counts[module]["due"],
            }
            for module in ("vocabulary", "phrases", "grammar", "listening", "speaking", "reading", "writing", "pronunciation")
        ],
        "content_total": total_items,
        "seen_total": seen,
        "mastered_total": mastered,
        "coverage": round((seen / total_items * 100), 1) if total_items else 0,
    }
