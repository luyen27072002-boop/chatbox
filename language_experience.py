from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_experiences(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise RuntimeError('language_experiences.json phải là object.')
    result: dict[str, list[dict[str, Any]]] = {}
    for language, items in raw.items():
        if not isinstance(items, list):
            continue
        clean = []
        for item in items:
            if not isinstance(item, dict) or not item.get('id'):
                continue
            obj = dict(item)
            obj['language'] = language
            clean.append(obj)
        result[str(language)] = clean
    return result


def build_experience_map(content: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for items in content.values():
        for item in items:
            result[str(item['id'])] = item
    return result


def init_experience_db(db) -> None:
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS language_experience_progress (
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            experience_id TEXT NOT NULL,
            views INTEGER NOT NULL DEFAULT 0,
            completions INTEGER NOT NULL DEFAULT 0,
            selected_terms_json TEXT NOT NULL DEFAULT '[]',
            first_seen_at TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(user_id, language, experience_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_experience_practice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            language TEXT NOT NULL,
            experience_id TEXT NOT NULL,
            term TEXT NOT NULL,
            mode TEXT NOT NULL,
            answer_text TEXT NOT NULL DEFAULT '',
            score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_language_experience_progress_user
        ON language_experience_progress(user_id, language, last_seen_at DESC);
        '''
    )
    db.commit()


def _level_rank(level: str) -> int:
    return {'A1-A2': 1, 'B1-B2': 2, 'C1-C2': 3}.get(str(level or 'A1-A2'), 1)


def _level_matches(item_level: str, selected_level: str) -> bool:
    return _level_rank(item_level) <= _level_rank(selected_level)


def _progress_map(db, user_id: str, language: str) -> dict[str, dict[str, Any]]:
    rows = db.execute(
        'SELECT * FROM language_experience_progress WHERE user_id = ? AND language = ?',
        (user_id, language),
    ).fetchall()
    return {str(row['experience_id']): dict(row) for row in rows}


def _public_term(term: dict[str, Any], *, reveal: bool = False) -> dict[str, Any]:
    base = {
        'term': str(term.get('term', '')),
        'importance': int(term.get('importance', 4) or 4),
    }
    if reveal:
        base.update({
            'meaning': str(term.get('meaning', '')),
            'contexts': list(term.get('contexts') or []),
            'read_check': dict(term.get('read_check') or {}),
            'speak_prompt': str(term.get('speak_prompt', '')),
            'write_prompt': str(term.get('write_prompt', '')),
        })
    return base


def public_experience(item: dict[str, Any], progress: dict[str, Any] | None = None) -> dict[str, Any]:
    selected: list[str] = []
    if progress:
        try:
            parsed = json.loads(str(progress.get('selected_terms_json') or '[]'))
            if isinstance(parsed, list):
                selected = [str(x) for x in parsed]
        except Exception:
            selected = []
    return {
        'id': str(item.get('id', '')),
        'language': str(item.get('language', '')),
        'level': str(item.get('level', 'A1-A2')),
        'format': str(item.get('format', 'video')),
        'title': str(item.get('title', '')),
        'hook': str(item.get('hook', '')),
        'setting': str(item.get('setting', 'street')),
        'duration': int(item.get('duration', 30) or 30),
        'lines': list(item.get('lines') or []),
        # Trước khi user chọn từ, chỉ gửi term chứ không hiện nghĩa.
        'terms': [_public_term(t, reveal=str(t.get('term')) in selected) for t in (item.get('terms') or [])],
        'selected_terms': selected,
        'views': int((progress or {}).get('views', 0) or 0),
        'completions': int((progress or {}).get('completions', 0) or 0),
    }


def feed_for_user(
    db,
    *,
    user_id: str,
    language: str,
    level: str,
    content: dict[str, list[dict[str, Any]]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    items = [dict(x) for x in (content.get(language) or []) if _level_matches(str(x.get('level', 'A1-A2')), level)]
    progress = _progress_map(db, user_id, language)

    format_order = {'video': 0, 'chat': 1, 'audio': 2, 'comic': 3, 'reply': 4}
    items.sort(key=lambda item: (
        1 if str(item.get('id')) in progress else 0,
        int((progress.get(str(item.get('id'))) or {}).get('views', 0) or 0),
        format_order.get(str(item.get('format', 'video')), 9),
        str(item.get('id')),
    ))
    return [public_experience(item, progress.get(str(item.get('id')))) for item in items[:max(1, min(30, int(limit)))]]


def mark_view(db, *, user_id: str, language: str, experience_id: str) -> None:
    now = now_iso()
    row = db.execute(
        'SELECT * FROM language_experience_progress WHERE user_id = ? AND language = ? AND experience_id = ?',
        (user_id, language, experience_id),
    ).fetchone()
    if row:
        db.execute(
            'UPDATE language_experience_progress SET views = views + 1, last_seen_at = ? WHERE user_id = ? AND language = ? AND experience_id = ?',
            (now, user_id, language, experience_id),
        )
    else:
        db.execute(
            '''INSERT INTO language_experience_progress(user_id, language, experience_id, views, completions, selected_terms_json, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, 1, 0, '[]', ?, ?)''',
            (user_id, language, experience_id, now, now),
        )


def save_selected_terms(
    db,
    *,
    user_id: str,
    language: str,
    experience_id: str,
    terms: list[str],
) -> list[str]:
    now = now_iso()
    clean: list[str] = []
    seen = set()
    for raw in terms:
        term = str(raw or '').strip()
        key = term.casefold()
        if term and key not in seen:
            seen.add(key)
            clean.append(term)
    row = db.execute(
        'SELECT * FROM language_experience_progress WHERE user_id = ? AND language = ? AND experience_id = ?',
        (user_id, language, experience_id),
    ).fetchone()
    if row:
        old: list[str] = []
        try:
            parsed = json.loads(str(row['selected_terms_json'] or '[]'))
            if isinstance(parsed, list): old = [str(x) for x in parsed]
        except Exception:
            old = []
        merged = old[:]
        keys = {x.casefold() for x in merged}
        for term in clean:
            if term.casefold() not in keys:
                keys.add(term.casefold())
                merged.append(term)
        db.execute(
            '''UPDATE language_experience_progress
               SET selected_terms_json = ?, completions = completions + 1, last_seen_at = ?
               WHERE user_id = ? AND language = ? AND experience_id = ?''',
            (json.dumps(merged, ensure_ascii=False), now, user_id, language, experience_id),
        )
        return merged
    db.execute(
        '''INSERT INTO language_experience_progress(user_id, language, experience_id, views, completions, selected_terms_json, first_seen_at, last_seen_at)
           VALUES (?, ?, ?, 1, 1, ?, ?, ?)''',
        (user_id, language, experience_id, json.dumps(clean, ensure_ascii=False), now, now),
    )
    return clean


def reveal_selected_experience(item: dict[str, Any], selected_terms: list[str]) -> dict[str, Any]:
    selected_keys = {str(x).casefold() for x in selected_terms}
    public = public_experience(item, {'selected_terms_json': json.dumps(selected_terms, ensure_ascii=False)})
    public['terms'] = [
        _public_term(t, reveal=str(t.get('term', '')).casefold() in selected_keys)
        for t in (item.get('terms') or [])
    ]
    return public


def find_term(item: dict[str, Any], term_text: str) -> dict[str, Any] | None:
    key = str(term_text or '').strip().casefold()
    for term in item.get('terms') or []:
        if str(term.get('term', '')).strip().casefold() == key:
            return dict(term)
    return None


def record_practice(db, *, user_id: str, language: str, experience_id: str, term: str, mode: str, answer: str, score: int) -> None:
    db.execute(
        '''INSERT INTO language_experience_practice(user_id, language, experience_id, term, mode, answer_text, score, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, language, experience_id, term, mode, str(answer or '')[:1200], max(0, min(100, int(score))), now_iso()),
    )
