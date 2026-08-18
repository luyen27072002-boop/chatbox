from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, session

from db import get_account, get_db

bp = Blueprint("self_discovery", __name__)

TEST_TYPES = {"big5", "eq", "reasoning"}
BIG5_ORDER = ["extraversion", "agreeableness", "conscientiousness", "emotional_stability", "openness"]
EQ_ORDER = ["self_awareness", "self_regulation", "empathy", "social_skills"]
REASONING_ORDER = ["pattern", "logic", "numerical", "spatial"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id() -> str | None:
    value = str(session.get("account_id", "")).strip()
    return value or None


def _error(message: str, status: int = 400, code: str = "bad_request"):
    return jsonify({"error": message, "code": code}), status


def _data_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "self_discovery_tests.json"


def _load_bank() -> dict[str, Any]:
    with _data_path().open("r", encoding="utf-8") as fh:
        return json.load(fh)


def init_self_discovery_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS self_discovery_results (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            test_type TEXT NOT NULL CHECK(test_type IN ('big5','eq','reasoning')),
            answers_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_self_discovery_user_type_created
        ON self_discovery_results(user_id, test_type, created_at DESC);
        """
    )
    db.commit()


def register_self_discovery(app: Flask) -> None:
    with app.app_context():
        init_self_discovery_db()
    app.register_blueprint(bp)


def _localized_question(item: dict[str, Any], language: str) -> dict[str, Any]:
    lang = language if language in {"vi", "en", "zh"} else "vi"
    out = {
        "id": item["id"],
        "dimension": item["dimension"],
        "text": item.get("text", {}).get(lang) or item.get("text", {}).get("vi", ""),
    }
    if "options" in item:
        options = item.get("options") or {}
        out["options"] = options.get(lang) or options.get("vi") or []
    return out


def _normalize_answers(raw: Any, question_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Câu trả lời không hợp lệ.")
    answers = {str(k): v for k, v in raw.items() if str(k) in question_ids}
    if set(answers) != question_ids:
        raise ValueError("Bạn cần trả lời đủ tất cả câu hỏi.")
    return answers


def _score_likert(test_type: str, questions: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    by_dim: dict[str, list[int]] = {}
    for q in questions:
        try:
            value = int(answers[q["id"]])
        except (TypeError, ValueError) as exc:
            raise ValueError("Mỗi câu cần chọn mức từ 1 đến 5.") from exc
        if value < 1 or value > 5:
            raise ValueError("Mỗi câu cần chọn mức từ 1 đến 5.")
        if q.get("reverse"):
            value = 6 - value
        by_dim.setdefault(q["dimension"], []).append(value)

    order = BIG5_ORDER if test_type == "big5" else EQ_ORDER
    scores = {}
    for dim in order:
        values = by_dim.get(dim, [])
        avg = sum(values) / len(values) if values else 3.0
        scores[dim] = round((avg - 1) / 4 * 100)

    result: dict[str, Any] = {"scores": scores}
    if test_type == "eq":
        result["overall"] = round(sum(scores.values()) / max(len(scores), 1))
    else:
        # Big Five không có một “điểm tính cách tổng” có ý nghĩa; lưu hai nét nổi nhất.
        result["strongest"] = [key for key, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:2]]
    return result


def _score_reasoning(questions: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    correct = 0
    by_dim: dict[str, list[int]] = {}
    for q in questions:
        try:
            value = int(answers[q["id"]])
        except (TypeError, ValueError) as exc:
            raise ValueError("Câu trả lời tư duy không hợp lệ.") from exc
        options = q.get("options", {}).get("vi") or []
        if value < 0 or value >= len(options):
            raise ValueError("Câu trả lời tư duy không hợp lệ.")
        hit = 1 if value == int(q["answer"]) else 0
        correct += hit
        by_dim.setdefault(q["dimension"], []).append(hit)

    scores = {}
    for dim in REASONING_ORDER:
        values = by_dim.get(dim, [])
        scores[dim] = round(sum(values) / len(values) * 100) if values else 0
    return {
        "scores": scores,
        "correct": correct,
        "total": len(questions),
        "overall": round(correct / max(len(questions), 1) * 100),
        "note": "Đây là bài tư duy ngắn để tự khám phá, không phải bài IQ chuẩn hóa hay chẩn đoán tâm lý.",
    }


def _latest_results(user_id: str) -> dict[str, Any]:
    rows = get_db().execute(
        """
        SELECT id, test_type, result_json, created_at
        FROM self_discovery_results
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()
    latest: dict[str, Any] = {}
    attempts = {key: 0 for key in TEST_TYPES}
    for row in rows:
        test_type = str(row["test_type"])
        attempts[test_type] = attempts.get(test_type, 0) + 1
        if test_type in latest:
            continue
        try:
            result = json.loads(row["result_json"] or "{}")
        except Exception:
            result = {}
        latest[test_type] = {
            "id": row["id"],
            "test_type": test_type,
            "result": result,
            "created_at": row["created_at"],
        }
    return {"latest": latest, "attempts": attempts, "completed_count": len(latest)}


@bp.get("/self-discovery")
def self_discovery_page():
    user_id = _user_id()
    if not user_id or not get_account(user_id):
        return redirect("/")
    account = get_account(user_id) or {}
    return render_template("self_discovery/index.html", display_name=account.get("display_name", "Bạn"))


@bp.get("/api/self-discovery/overview")
def self_discovery_overview():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    return jsonify(_latest_results(user_id))


@bp.get("/api/self-discovery/schema")
def self_discovery_schema():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    test_type = str(request.args.get("type", "")).strip()
    if test_type not in TEST_TYPES:
        return _error("Loại bài kiểm tra không hợp lệ.")
    language = str(request.args.get("lang", "vi")).strip()
    bank = _load_bank()
    test = bank[test_type]
    return jsonify({
        "test_type": test_type,
        "kind": test["type"],
        "title": test.get("title", {}).get(language) or test.get("title", {}).get("vi", ""),
        "questions": [_localized_question(item, language) for item in test["questions"]],
        "scale": [1, 2, 3, 4, 5] if test["type"] == "likert" else None,
    })


@bp.post("/api/self-discovery/submit")
def self_discovery_submit():
    user_id = _user_id()
    if not user_id:
        return _error("Bạn cần đăng nhập trước.", 401, "auth_required")
    payload = request.get_json(silent=True) or {}
    test_type = str(payload.get("test_type", "")).strip()
    if test_type not in TEST_TYPES:
        return _error("Loại bài kiểm tra không hợp lệ.")
    bank = _load_bank()
    questions = bank[test_type]["questions"]
    try:
        answers = _normalize_answers(payload.get("answers"), {q["id"] for q in questions})
        result = _score_reasoning(questions, answers) if test_type == "reasoning" else _score_likert(test_type, questions, answers)
    except ValueError as exc:
        return _error(str(exc))

    result_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO self_discovery_results(id, user_id, test_type, answers_json, result_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            result_id,
            user_id,
            test_type,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            now,
        ),
    )
    db.commit()
    return jsonify({"id": result_id, "test_type": test_type, "result": result, "overview": _latest_results(user_id)}), 201
