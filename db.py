from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from flask import current_app, g

from profile_engine import default_profile, normalize_profile


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA busy_timeout=10000")
    return g.db


def close_db(_: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _column_names(db: sqlite3.Connection, table: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT,
            permanent_test INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            pronoun_style TEXT NOT NULL DEFAULT 'minh_ban',
            response_style TEXT NOT NULL DEFAULT 'luyen',
            tone_style TEXT NOT NULL DEFAULT 'gentle',
            memory_summary TEXT NOT NULL DEFAULT '',
            profile_json TEXT NOT NULL DEFAULT '{}',
            profile_completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            preview TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id TEXT,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'listen',
            category TEXT NOT NULL DEFAULT 'other',
            response_style TEXT NOT NULL DEFAULT 'luyen',
            tone_style TEXT NOT NULL DEFAULT 'gentle',
            profile_archetype TEXT NOT NULL DEFAULT 'balanced_companion',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS usage_daily (
            user_id TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, usage_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_wallets (
            user_id TEXT PRIMARY KEY,
            welcome_used INTEGER NOT NULL DEFAULT 0,
            purchased_credits INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS free_daily_usage (
            user_id TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, usage_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payment_orders (
            id TEXT PRIMARY KEY,
            order_code INTEGER NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            plan_type TEXT NOT NULL CHECK(plan_type IN ('topup', 'monthly')),
            plan_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            credits INTEGER NOT NULL DEFAULT 0,
            monthly_messages INTEGER NOT NULL DEFAULT 0,
            unlimited INTEGER NOT NULL DEFAULT 0,
            daily_fair_limit INTEGER NOT NULL DEFAULT 0,
            duration_days INTEGER NOT NULL DEFAULT 30,
            status TEXT NOT NULL DEFAULT 'pending',
            provider TEXT NOT NULL DEFAULT 'payos',
            checkout_url TEXT NOT NULL DEFAULT '',
            payment_link_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            paid_at TEXT,
            raw_webhook_json TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            payment_order_id TEXT NOT NULL UNIQUE,
            message_limit INTEGER NOT NULL DEFAULT 0,
            messages_used INTEGER NOT NULL DEFAULT 0,
            unlimited INTEGER NOT NULL DEFAULT 0,
            daily_fair_limit INTEGER NOT NULL DEFAULT 0,
            starts_at TEXT NOT NULL,
            ends_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(payment_order_id) REFERENCES payment_orders(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS subscription_daily_usage (
            subscription_id TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(subscription_id, usage_date),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quota_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'reserved',
            created_at TEXT NOT NULL,
            finalized_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    # Các migration nhẹ khi chép bản mới đè lên dự án cũ.
    account_columns = _column_names(db, "accounts")
    if "permanent_test" not in account_columns:
        db.execute(
            "ALTER TABLE accounts ADD COLUMN permanent_test INTEGER NOT NULL DEFAULT 0"
        )

    user_columns = _column_names(db, "users")
    if "response_style" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN response_style TEXT NOT NULL DEFAULT 'luyen'"
        )
    if "tone_style" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN tone_style TEXT NOT NULL DEFAULT 'gentle'"
        )
    if "profile_json" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN profile_json TEXT NOT NULL DEFAULT '{}'")
    if "profile_completed" not in user_columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN profile_completed INTEGER NOT NULL DEFAULT 0"
        )

    message_columns = _column_names(db, "messages")
    if "response_style" not in message_columns:
        db.execute(
            "ALTER TABLE messages ADD COLUMN response_style TEXT NOT NULL DEFAULT 'luyen'"
        )
    if "tone_style" not in message_columns:
        db.execute(
            "ALTER TABLE messages ADD COLUMN tone_style TEXT NOT NULL DEFAULT 'gentle'"
        )
    if "profile_archetype" not in message_columns:
        db.execute(
            "ALTER TABLE messages ADD COLUMN profile_archetype TEXT NOT NULL DEFAULT 'balanced_companion'"
        )
    if "conversation_id" not in message_columns:
        db.execute("ALTER TABLE messages ADD COLUMN conversation_id TEXT")

    # Không ghi đè persona đã lưu. Chỉ sửa giá trị rỗng về mặc định Luyện.
    db.execute(
        "UPDATE users SET response_style = 'luyen' "
        "WHERE response_style IS NULL OR response_style = ''"
    )
    db.execute(
        "UPDATE messages SET response_style = 'luyen' "
        "WHERE response_style IS NULL OR response_style = ''"
    )

    db.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_user_created
        ON messages(user_id, id DESC);

        CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
        ON messages(conversation_id, id ASC);

        CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
        ON conversations(user_id, updated_at DESC);


        CREATE INDEX IF NOT EXISTS idx_payment_orders_user_created
        ON payment_orders(user_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_ends
        ON subscriptions(user_id, ends_at ASC);

        CREATE INDEX IF NOT EXISTS idx_quota_events_user_created
        ON quota_events(user_id, created_at DESC);
        """
    )
    _migrate_legacy_messages(db)
    db.commit()


def _migrate_legacy_messages(db: sqlite3.Connection) -> None:
    """Gom tin nhắn bản cũ của mỗi tài khoản vào một cuộc trò chuyện cũ."""
    user_rows = db.execute(
        """
        SELECT DISTINCT user_id
        FROM messages
        WHERE conversation_id IS NULL OR conversation_id = ''
        """
    ).fetchall()
    for user_row in user_rows:
        user_id = str(user_row["user_id"])
        first = db.execute(
            """
            SELECT created_at FROM messages
            WHERE user_id = ? AND (conversation_id IS NULL OR conversation_id = '')
            ORDER BY id ASC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        last = db.execute(
            """
            SELECT content, created_at FROM messages
            WHERE user_id = ? AND (conversation_id IS NULL OR conversation_id = '')
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if not first or not last:
            continue
        conversation_id = str(uuid.uuid4())
        preview = _preview_text(str(last["content"]))
        db.execute(
            """
            INSERT INTO conversations(
                id, user_id, title, preview, summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, '', ?, ?)
            """,
            (
                conversation_id,
                user_id,
                "Cuộc trò chuyện trước đây",
                preview,
                str(first["created_at"]),
                str(last["created_at"]),
            ),
        )
        db.execute(
            """
            UPDATE messages SET conversation_id = ?
            WHERE user_id = ? AND (conversation_id IS NULL OR conversation_id = '')
            """,
            (conversation_id, user_id),
        )


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def _serialize_account(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data.pop("password_hash", None)
    data["user_id"] = data["id"]
    data["permanent_test"] = bool(data.get("permanent_test", 0))
    return data


def create_account(
    *, display_name: str, username: str, email: str, password_hash: str
) -> dict[str, Any]:
    db = get_db()
    account_id = str(uuid.uuid4())
    now = _now()
    try:
        db.execute(
            """
            INSERT INTO accounts(
                id, display_name, username, email, password_hash,
                created_at, updated_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                display_name.strip(),
                username.strip().lower(),
                email.strip().lower(),
                password_hash,
                now,
                now,
                now,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        text = str(exc).lower()
        if "username" in text:
            raise ValueError("Tên đăng nhập này đã có người dùng.") from exc
        if "email" in text:
            raise ValueError("Email này đã được đăng ký.") from exc
        raise ValueError("Không thể tạo tài khoản với thông tin này.") from exc

    get_or_create_user(account_id)
    return get_account(account_id) or {}


def get_account(account_id: str) -> dict[str, Any] | None:
    row = get_db().execute(
        "SELECT * FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    return _serialize_account(row)


def get_account_for_login(identifier: str) -> dict[str, Any] | None:
    normalized = identifier.strip().lower()
    row = get_db().execute(
        """
        SELECT * FROM accounts
        WHERE lower(username) = ? OR lower(email) = ?
        LIMIT 1
        """,
        (normalized, normalized),
    ).fetchone()
    return dict(row) if row is not None else None


def mark_account_login(account_id: str) -> None:
    now = _now()
    db = get_db()
    db.execute(
        "UPDATE accounts SET last_login_at = ?, updated_at = ? WHERE id = ?",
        (now, now, account_id),
    )
    db.commit()


def is_permanent_test_account(user_id: str) -> bool:
    row = get_db().execute(
        "SELECT permanent_test FROM accounts WHERE id = ?",
        (user_id,),
    ).fetchone()
    return bool(row and int(row["permanent_test"] or 0))


def set_permanent_test_account(identifier: str, enabled: bool = True) -> dict[str, Any]:
    normalized = str(identifier or "").strip().lower()
    if not normalized:
        raise ValueError("Cần nhập tên đăng nhập hoặc email của tài khoản.")

    db = get_db()
    row = db.execute(
        """
        SELECT id FROM accounts
        WHERE lower(username) = ? OR lower(email) = ?
        LIMIT 1
        """,
        (normalized, normalized),
    ).fetchone()
    if row is None:
        raise ValueError("Không tìm thấy tài khoản này. Hãy tạo tài khoản trên web trước.")

    account_id = str(row["id"])
    now = _now()
    db.execute(
        "UPDATE accounts SET permanent_test = ?, updated_at = ? WHERE id = ?",
        (1 if enabled else 0, now, account_id),
    )
    db.commit()
    return get_account(account_id) or {}


def _serialize_user(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    raw_profile = data.pop("profile_json", "{}")
    try:
        profile_payload = json.loads(raw_profile or "{}")
        if not isinstance(profile_payload, dict):
            profile_payload = {}
    except (TypeError, json.JSONDecodeError):
        profile_payload = {}
    try:
        profile = normalize_profile(profile_payload)
    except ValueError:
        profile = default_profile()
    data["profile"] = profile
    data["profile_completed"] = bool(data.get("profile_completed", 0))
    return data


def get_or_create_user(user_id: str) -> dict[str, Any]:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        now = _now()
        default_json = json.dumps(default_profile(), ensure_ascii=False)
        db.execute(
            """
            INSERT INTO users(id, profile_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, default_json, now, now),
        )
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _serialize_user(row)


def update_user_settings(
    user_id: str,
    pronoun_style: str,
    response_style: str = "luyen",
    tone_style: str = "gentle",
) -> None:
    get_or_create_user(user_id)
    db = get_db()
    db.execute(
        """
        UPDATE users
        SET pronoun_style = ?, response_style = ?, tone_style = ?, updated_at = ?
        WHERE id = ?
        """,
        (pronoun_style, response_style, tone_style, _now(), user_id),
    )
    db.commit()


def update_user_profile(user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    get_or_create_user(user_id)
    normalized = normalize_profile(profile)
    db = get_db()
    db.execute(
        """
        UPDATE users
        SET profile_json = ?, profile_completed = 1, updated_at = ?
        WHERE id = ?
        """,
        (json.dumps(normalized, ensure_ascii=False), _now(), user_id),
    )
    db.commit()
    return normalized


def update_user_memory(user_id: str, memory_summary: str) -> None:
    """Giữ để tương thích dữ liệu cũ; V8 dùng summary riêng cho từng cuộc trò chuyện."""
    get_or_create_user(user_id)
    db = get_db()
    db.execute(
        "UPDATE users SET memory_summary = ?, updated_at = ? WHERE id = ?",
        (memory_summary[:2000], _now(), user_id),
    )
    db.commit()


def _serialize_conversation(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def create_conversation(
    user_id: str,
    *,
    title: str = "Cuộc trò chuyện mới",
    preview: str = "",
) -> dict[str, Any]:
    get_or_create_user(user_id)
    conversation_id = str(uuid.uuid4())
    now = _now()
    db = get_db()
    db.execute(
        """
        INSERT INTO conversations(
            id, user_id, title, preview, summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, '', ?, ?)
        """,
        (
            conversation_id,
            user_id,
            _clean_title(title),
            _preview_text(preview),
            now,
            now,
        ),
    )
    db.commit()
    return get_conversation(user_id, conversation_id) or {}


def get_conversation(user_id: str, conversation_id: str) -> dict[str, Any] | None:
    row = get_db().execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        WHERE c.id = ? AND c.user_id = ?
        """,
        (conversation_id, user_id),
    ).fetchone()
    return _serialize_conversation(row)


def list_conversations(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT c.id, c.user_id, c.title, c.preview, c.created_at, c.updated_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        WHERE c.user_id = ?
        ORDER BY c.updated_at DESC
        LIMIT ?
        """,
        (user_id, max(1, min(limit, 300))),
    ).fetchall()
    return [dict(row) for row in rows]


def rename_conversation(
    user_id: str, conversation_id: str, title: str
) -> dict[str, Any] | None:
    cleaned = _clean_title(title)
    db = get_db()
    cursor = db.execute(
        """
        UPDATE conversations
        SET title = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (cleaned, _now(), conversation_id, user_id),
    )
    db.commit()
    if cursor.rowcount == 0:
        return None
    return get_conversation(user_id, conversation_id)


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    db = get_db()
    owned = db.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    ).fetchone()
    if not owned:
        return False
    db.execute(
        "DELETE FROM messages WHERE conversation_id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    db.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    db.commit()
    return True


def get_conversation_summary(user_id: str, conversation_id: str) -> str:
    row = get_db().execute(
        "SELECT summary FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    ).fetchone()
    return str(row["summary"]) if row else ""


def update_conversation_summary(
    user_id: str, conversation_id: str, summary: str
) -> None:
    db = get_db()
    db.execute(
        """
        UPDATE conversations
        SET summary = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (summary[:3000], _now(), conversation_id, user_id),
    )
    db.commit()


def save_message(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    mode: str = "listen",
    category: str = "other",
    response_style: str = "luyen",
    tone_style: str = "gentle",
    profile_archetype: str = "balanced_companion",
) -> int:
    get_or_create_user(user_id)
    if not get_conversation(user_id, conversation_id):
        raise ValueError("Cuộc trò chuyện không tồn tại.")
    now = _now()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO messages(
            user_id, conversation_id, role, content, mode, category,
            response_style, tone_style, profile_archetype, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            conversation_id,
            role,
            content,
            mode,
            category,
            response_style,
            tone_style,
            profile_archetype,
            now,
        ),
    )
    if role == "user":
        db.execute(
            """
            UPDATE conversations
            SET preview = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (_preview_text(content), now, conversation_id, user_id),
        )
    else:
        db.execute(
            """
            UPDATE conversations SET updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now, conversation_id, user_id),
        )
    db.commit()
    return int(cursor.lastrowid)


def get_history(
    user_id: str,
    conversation_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    db = get_db()
    safe_limit = max(1, min(int(limit), 10000))
    if conversation_id:
        rows = db.execute(
            """
            SELECT id, conversation_id, role, content, mode, category,
                   response_style, tone_style, profile_archetype, created_at
            FROM messages
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, conversation_id, safe_limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, conversation_id, role, content, mode, category,
                   response_style, tone_style, profile_archetype, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def count_user_messages(user_id: str, conversation_id: str | None = None) -> int:
    if conversation_id:
        row = get_db().execute(
            """
            SELECT COUNT(*) AS n FROM messages
            WHERE user_id = ? AND conversation_id = ? AND role = 'user'
            """,
            (user_id, conversation_id),
        ).fetchone()
    else:
        row = get_db().execute(
            "SELECT COUNT(*) AS n FROM messages WHERE user_id = ? AND role = 'user'",
            (user_id,),
        ).fetchone()
    return int(row["n"])


def get_usage_today(user_id: str) -> int:
    """Giữ lại cho tương thích với code cũ; giới hạn mới dùng tổng lượt theo tài khoản."""
    row = get_db().execute(
        "SELECT message_count FROM usage_daily WHERE user_id = ? AND usage_date = ?",
        (user_id, date.today().isoformat()),
    ).fetchone()
    return int(row["message_count"]) if row else 0


def get_usage_total(user_id: str) -> int:
    """Tổng số phản hồi AI đã cấp cho tài khoản, không tự đặt lại theo ngày."""
    row = get_db().execute(
        "SELECT COALESCE(SUM(message_count), 0) AS n FROM usage_daily WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["n"]) if row else 0


def increment_usage(user_id: str) -> None:
    get_or_create_user(user_id)
    db = get_db()
    today = date.today().isoformat()
    db.execute(
        """
        INSERT INTO usage_daily(user_id, usage_date, message_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, usage_date)
        DO UPDATE SET message_count = message_count + 1
        """,
        (user_id, today),
    )
    db.commit()


def clear_user_data(user_id: str) -> None:
    """Xóa nội dung cá nhân ở mọi module nhưng giữ tài khoản và lịch sử thanh toán."""
    db = get_db()
    db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))

    # Các bảng module được tạo sau init_db, vì vậy phải kiểm tra trước để bản cũ
    # vẫn nâng cấp an toàn khi người dùng chép file đè lên dự án hiện tại.
    if _table_exists(db, "language_messages"):
        db.execute("DELETE FROM language_messages WHERE user_id = ?", (user_id,))
    if _table_exists(db, "language_sessions"):
        db.execute("DELETE FROM language_sessions WHERE user_id = ?", (user_id,))
    if _table_exists(db, "rehearsal_messages") and _table_exists(db, "rehearsal_sessions"):
        db.execute(
            "DELETE FROM rehearsal_messages WHERE session_id IN "
            "(SELECT id FROM rehearsal_sessions WHERE user_id = ?)",
            (user_id,),
        )
    if _table_exists(db, "rehearsal_sessions"):
        db.execute("DELETE FROM rehearsal_sessions WHERE user_id = ?", (user_id,))
    if _table_exists(db, "life_threads"):
        db.execute("DELETE FROM life_threads WHERE user_id = ?", (user_id,))
    if _table_exists(db, "life_entries"):
        db.execute("DELETE FROM life_entries WHERE user_id = ?", (user_id,))

    # Không xóa usage/quota/payment: xóa lịch sử không được làm mới lượt miễn phí.
    now = _now()
    default_json = json.dumps(default_profile(), ensure_ascii=False)
    db.execute(
        """
        UPDATE users
        SET pronoun_style = 'minh_ban', response_style = 'luyen',
            tone_style = 'gentle', memory_summary = '', profile_json = ?, profile_completed = 0,
            updated_at = ?
        WHERE id = ?
        """,
        (default_json, now, user_id),
    )
    db.commit()


def export_user_data(user_id: str) -> dict[str, Any]:
    db = get_db()
    conversations = list_conversations(user_id, limit=300)
    for conversation in conversations:
        conversation["messages"] = get_history(
            user_id, str(conversation["id"]), limit=10000
        )

    language_sessions: list[dict[str, Any]] = []
    if _table_exists(db, "language_sessions"):
        rows = db.execute(
            "SELECT * FROM language_sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        for row in rows:
            item = dict(row)
            if _table_exists(db, "language_messages"):
                item["messages"] = [
                    dict(message)
                    for message in db.execute(
                        "SELECT * FROM language_messages WHERE session_id = ? ORDER BY id ASC",
                        (item["id"],),
                    ).fetchall()
                ]
            language_sessions.append(item)

    life_data: dict[str, list[dict[str, Any]]] = {}
    for table in ("life_entries", "life_threads", "rehearsal_sessions"):
        if _table_exists(db, table):
            life_data[table] = [
                dict(row)
                for row in db.execute(
                    f"SELECT * FROM {table} WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
            ]

    return {
        "account": get_account(user_id),
        "user": get_or_create_user(user_id),
        "conversations": conversations,
        "language_sessions": language_sessions,
        "life": life_data,
    }


def _clean_title(value: str) -> str:
    title = " ".join(str(value).replace("\n", " ").split()).strip()
    return (title or "Cuộc trò chuyện mới")[:80]


def _preview_text(value: str) -> str:
    text = " ".join(str(value).replace("\n", " ").split()).strip()
    return text[:160]

# ---------------------------------------------------------------------------
# Billing, quota and payment helpers (V20)
# ---------------------------------------------------------------------------


def _billing_today() -> str:
    timezone_name = str(current_app.config.get("BILLING_TIMEZONE", "Asia/Ho_Chi_Minh"))
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = timezone.utc
    return datetime.now(zone).date().isoformat()


def _ensure_wallet(db: sqlite3.Connection, user_id: str) -> None:
    now = _now()
    db.execute(
        """
        INSERT INTO billing_wallets(user_id, welcome_used, purchased_credits, created_at, updated_at)
        VALUES (?, 0, 0, ?, ?)
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, now, now),
    )


def _expire_subscriptions(db: sqlite3.Connection) -> None:
    now = _now()
    db.execute(
        """
        UPDATE subscriptions
        SET status = 'expired', updated_at = ?
        WHERE status = 'active' AND ends_at <= ?
        """,
        (now, now),
    )


def get_quota_status(
    user_id: str,
    *,
    welcome_limit: int,
    daily_limit: int,
) -> dict[str, Any]:
    get_or_create_user(user_id)
    db = get_db()
    if is_permanent_test_account(user_id):
        return {
            "welcome_limit": int(welcome_limit),
            "welcome_used": 0,
            "welcome_remaining": 0,
            "daily_limit": int(daily_limit),
            "daily_used": 0,
            "daily_remaining": 0,
            "daily_date": _billing_today(),
            "purchased_credits": 0,
            "subscription_remaining": 0,
            "unlimited_active": True,
            "unlimited_daily_remaining": 0,
            "finite_remaining": 0,
            "can_chat": True,
            "subscriptions": [],
            "used_total": get_usage_total(user_id),
            "permanent_test": True,
        }
    _ensure_wallet(db, user_id)
    _expire_subscriptions(db)
    # Hai helper trên có thể INSERT/UPDATE. Commit trước khi trả trạng thái để
    # request chat tiếp theo không gặp "cannot start a transaction within a transaction".
    db.commit()
    today = _billing_today()

    wallet = db.execute(
        "SELECT welcome_used, purchased_credits FROM billing_wallets WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    daily = db.execute(
        "SELECT message_count FROM free_daily_usage WHERE user_id = ? AND usage_date = ?",
        (user_id, today),
    ).fetchone()
    subscriptions = db.execute(
        """
        SELECT id, plan_id, plan_name, message_limit, messages_used, unlimited,
               daily_fair_limit, starts_at, ends_at
        FROM subscriptions
        WHERE user_id = ? AND status = 'active' AND starts_at <= ? AND ends_at > ?
        ORDER BY ends_at ASC, created_at ASC
        """,
        (user_id, _now(), _now()),
    ).fetchall()

    welcome_used = int(wallet["welcome_used"]) if wallet else 0
    purchased = int(wallet["purchased_credits"]) if wallet else 0
    daily_used = int(daily["message_count"]) if daily else 0
    serialized_subscriptions: list[dict[str, Any]] = []
    subscription_remaining = 0
    unlimited_active = False
    unlimited_daily_remaining = 0

    for row in subscriptions:
        item = dict(row)
        if int(item["unlimited"]):
            unlimited_active = True
            daily_row = db.execute(
                """
                SELECT message_count FROM subscription_daily_usage
                WHERE subscription_id = ? AND usage_date = ?
                """,
                (item["id"], today),
            ).fetchone()
            unlimited_used_today = int(daily_row["message_count"]) if daily_row else 0
            item["used_today"] = unlimited_used_today
            item["remaining_today"] = max(
                0, int(item["daily_fair_limit"]) - unlimited_used_today
            )
            unlimited_daily_remaining += item["remaining_today"]
            item["remaining"] = None
        else:
            item["remaining"] = max(
                0, int(item["message_limit"]) - int(item["messages_used"])
            )
            subscription_remaining += int(item["remaining"])
        item["unlimited"] = bool(item["unlimited"])
        serialized_subscriptions.append(item)

    welcome_remaining = max(0, int(welcome_limit) - welcome_used)
    daily_remaining = max(0, int(daily_limit) - daily_used)
    finite_remaining = (
        welcome_remaining + daily_remaining + purchased + subscription_remaining
    )
    can_chat = finite_remaining > 0 or unlimited_daily_remaining > 0

    return {
        "welcome_limit": int(welcome_limit),
        "welcome_used": welcome_used,
        "welcome_remaining": welcome_remaining,
        "daily_limit": int(daily_limit),
        "daily_used": daily_used,
        "daily_remaining": daily_remaining,
        "daily_date": today,
        "purchased_credits": purchased,
        "subscription_remaining": subscription_remaining,
        "unlimited_active": unlimited_active,
        "unlimited_daily_remaining": unlimited_daily_remaining,
        "finite_remaining": finite_remaining,
        "can_chat": can_chat,
        "subscriptions": serialized_subscriptions,
        "used_total": get_usage_total(user_id),
        "permanent_test": False,
    }


def reserve_message_quota(
    user_id: str,
    *,
    welcome_limit: int,
    daily_limit: int,
) -> dict[str, Any] | None:
    """Atomically reserve one reply allowance.

    Priority: daily free -> welcome -> expiring monthly plan -> purchased credits.
    The caller must finalize on success or refund when the AI request fails.
    """
    get_or_create_user(user_id)
    db = get_db()
    today = _billing_today()
    now = _now()
    event_id = str(uuid.uuid4())

    if is_permanent_test_account(user_id):
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                """
                INSERT INTO quota_events(id, user_id, source, source_ref, status, created_at)
                VALUES (?, ?, 'permanent_test', ?, 'reserved', ?)
                """,
                (event_id, user_id, user_id, now),
            )
            db.commit()
            return {
                "id": event_id,
                "source": "permanent_test",
                "source_ref": user_id,
            }
        except Exception:
            db.rollback()
            raise

    db.execute("BEGIN IMMEDIATE")
    try:
        _ensure_wallet(db, user_id)
        _expire_subscriptions(db)

        daily_row = db.execute(
            "SELECT message_count FROM free_daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today),
        ).fetchone()
        daily_used = int(daily_row["message_count"]) if daily_row else 0
        if daily_used < int(daily_limit):
            db.execute(
                """
                INSERT INTO free_daily_usage(user_id, usage_date, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, usage_date)
                DO UPDATE SET message_count = message_count + 1
                """,
                (user_id, today),
            )
            source, source_ref = "daily_free", today
        else:
            wallet = db.execute(
                "SELECT welcome_used, purchased_credits FROM billing_wallets WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            welcome_used = int(wallet["welcome_used"])
            purchased = int(wallet["purchased_credits"])
            if welcome_used < int(welcome_limit):
                db.execute(
                    """
                    UPDATE billing_wallets
                    SET welcome_used = welcome_used + 1, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (now, user_id),
                )
                source, source_ref = "welcome", ""
            else:
                subs = db.execute(
                    """
                    SELECT id, message_limit, messages_used, unlimited, daily_fair_limit
                    FROM subscriptions
                    WHERE user_id = ? AND status = 'active' AND starts_at <= ? AND ends_at > ?
                    ORDER BY ends_at ASC, created_at ASC
                    """,
                    (user_id, now, now),
                ).fetchall()
                source = ""
                source_ref = ""
                for sub in subs:
                    sub_id = str(sub["id"])
                    if int(sub["unlimited"]):
                        daily_sub = db.execute(
                            """
                            SELECT message_count FROM subscription_daily_usage
                            WHERE subscription_id = ? AND usage_date = ?
                            """,
                            (sub_id, today),
                        ).fetchone()
                        used_today = int(daily_sub["message_count"]) if daily_sub else 0
                        if used_today < int(sub["daily_fair_limit"]):
                            db.execute(
                                """
                                INSERT INTO subscription_daily_usage(subscription_id, usage_date, message_count)
                                VALUES (?, ?, 1)
                                ON CONFLICT(subscription_id, usage_date)
                                DO UPDATE SET message_count = message_count + 1
                                """,
                                (sub_id, today),
                            )
                            source, source_ref = "subscription_unlimited", sub_id
                            break
                    elif int(sub["messages_used"]) < int(sub["message_limit"]):
                        db.execute(
                            """
                            UPDATE subscriptions
                            SET messages_used = messages_used + 1, updated_at = ?
                            WHERE id = ?
                            """,
                            (now, sub_id),
                        )
                        source, source_ref = "subscription", sub_id
                        break

                if not source and purchased > 0:
                    db.execute(
                        """
                        UPDATE billing_wallets
                        SET purchased_credits = purchased_credits - 1, updated_at = ?
                        WHERE user_id = ? AND purchased_credits > 0
                        """,
                        (now, user_id),
                    )
                    source, source_ref = "purchased", ""

                if not source:
                    db.rollback()
                    return None

        db.execute(
            """
            INSERT INTO quota_events(id, user_id, source, source_ref, status, created_at)
            VALUES (?, ?, ?, ?, 'reserved', ?)
            """,
            (event_id, user_id, source, source_ref, now),
        )
        db.commit()
        return {"id": event_id, "source": source, "source_ref": source_ref}
    except Exception:
        db.rollback()
        raise


def finalize_message_quota(event_id: str) -> bool:
    db = get_db()
    now = _now()
    db.execute("BEGIN IMMEDIATE")
    try:
        event = db.execute(
            "SELECT user_id, status FROM quota_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if not event or str(event["status"]) != "reserved":
            db.rollback()
            return False
        user_id = str(event["user_id"])
        today = _billing_today()
        db.execute(
            """
            INSERT INTO usage_daily(user_id, usage_date, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date)
            DO UPDATE SET message_count = message_count + 1
            """,
            (user_id, today),
        )
        db.execute(
            """
            UPDATE quota_events SET status = 'consumed', finalized_at = ?
            WHERE id = ? AND status = 'reserved'
            """,
            (now, event_id),
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def refund_message_quota(event_id: str) -> bool:
    db = get_db()
    now = _now()
    db.execute("BEGIN IMMEDIATE")
    try:
        event = db.execute(
            """
            SELECT user_id, source, source_ref, status
            FROM quota_events WHERE id = ?
            """,
            (event_id,),
        ).fetchone()
        if not event or str(event["status"]) != "reserved":
            db.rollback()
            return False
        user_id = str(event["user_id"])
        source = str(event["source"])
        source_ref = str(event["source_ref"])
        if source == "daily_free":
            db.execute(
                """
                UPDATE free_daily_usage
                SET message_count = MAX(0, message_count - 1)
                WHERE user_id = ? AND usage_date = ?
                """,
                (user_id, source_ref),
            )
        elif source == "welcome":
            db.execute(
                """
                UPDATE billing_wallets
                SET welcome_used = MAX(0, welcome_used - 1), updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
        elif source == "purchased":
            db.execute(
                """
                UPDATE billing_wallets
                SET purchased_credits = purchased_credits + 1, updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
        elif source == "subscription":
            db.execute(
                """
                UPDATE subscriptions
                SET messages_used = MAX(0, messages_used - 1), updated_at = ?
                WHERE id = ?
                """,
                (now, source_ref),
            )
        elif source == "subscription_unlimited":
            db.execute(
                """
                UPDATE subscription_daily_usage
                SET message_count = MAX(0, message_count - 1)
                WHERE subscription_id = ? AND usage_date = ?
                """,
                (source_ref, _billing_today()),
            )
        db.execute(
            """
            UPDATE quota_events SET status = 'refunded', finalized_at = ?
            WHERE id = ? AND status = 'reserved'
            """,
            (now, event_id),
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def create_payment_order(user_id: str, plan: dict[str, Any]) -> dict[str, Any]:
    get_or_create_user(user_id)
    db = get_db()
    now = _now()
    order_id = str(uuid.uuid4())
    # Millisecond timestamp plus a UUID fragment: integer, stable and collision resistant.
    order_code = int(datetime.now(timezone.utc).timestamp() * 1000) * 100 + (
        int(uuid.uuid4().hex[:4], 16) % 100
    )
    db.execute(
        """
        INSERT INTO payment_orders(
            id, order_code, user_id, plan_id, plan_type, plan_name, amount,
            credits, monthly_messages, unlimited, daily_fair_limit, duration_days,
            status, provider, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'payos', ?, ?)
        """,
        (
            order_id,
            order_code,
            user_id,
            str(plan["id"]),
            str(plan["kind"]),
            str(plan["name"]),
            int(plan["price_vnd"]),
            int(plan.get("credits", 0)),
            int(plan.get("messages", 0)),
            1 if plan.get("unlimited") else 0,
            int(plan.get("daily_fair_limit", 0)),
            int(plan.get("duration_days", 30)),
            now,
            now,
        ),
    )
    db.commit()
    return get_payment_order(user_id, order_id) or {}


def update_payment_checkout(
    order_id: str, *, checkout_url: str, payment_link_id: str
) -> None:
    db = get_db()
    db.execute(
        """
        UPDATE payment_orders
        SET checkout_url = ?, payment_link_id = ?, updated_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (checkout_url, payment_link_id, _now(), order_id),
    )
    db.commit()


def mark_payment_failed(order_id: str, reason: str = "") -> None:
    db = get_db()
    db.execute(
        """
        UPDATE payment_orders
        SET status = 'failed', raw_webhook_json = ?, updated_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (str(reason)[:4000], _now(), order_id),
    )
    db.commit()


def get_payment_order(user_id: str, order_id: str) -> dict[str, Any] | None:
    row = get_db().execute(
        """
        SELECT id, order_code, user_id, plan_id, plan_type, plan_name, amount,
               credits, monthly_messages, unlimited, daily_fair_limit,
               duration_days, status, provider, checkout_url, payment_link_id,
               created_at, updated_at, paid_at
        FROM payment_orders WHERE id = ? AND user_id = ?
        """,
        (order_id, user_id),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["unlimited"] = bool(data["unlimited"])
    return data


def get_payment_order_by_code(order_code: int) -> dict[str, Any] | None:
    row = get_db().execute(
        "SELECT * FROM payment_orders WHERE order_code = ?",
        (int(order_code),),
    ).fetchone()
    return dict(row) if row else None


def list_payment_orders(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, order_code, plan_id, plan_type, plan_name, amount, status,
               checkout_url, created_at, paid_at
        FROM payment_orders WHERE user_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (user_id, max(1, min(int(limit), 100))),
    ).fetchall()
    return [dict(row) for row in rows]


def apply_paid_order(
    *, order_code: int, amount: int, raw_webhook_json: str = ""
) -> tuple[dict[str, Any] | None, bool]:
    """Apply a verified payment exactly once.

    Returns (order, newly_applied). Amount must match the server-side catalog
    snapshot stored when the order was created.
    """
    db = get_db()
    now = _now()
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute(
            "SELECT * FROM payment_orders WHERE order_code = ?",
            (int(order_code),),
        ).fetchone()
        if not row:
            db.rollback()
            return None, False
        order = dict(row)
        if int(order["amount"]) != int(amount):
            db.rollback()
            raise ValueError("Số tiền webhook không khớp đơn hàng.")
        if str(order["status"]) == "paid":
            db.rollback()
            return order, False
        if str(order["status"]) not in {"pending", "failed"}:
            db.rollback()
            return order, False

        user_id = str(order["user_id"])
        _ensure_wallet(db, user_id)
        if str(order["plan_type"]) == "topup":
            db.execute(
                """
                UPDATE billing_wallets
                SET purchased_credits = purchased_credits + ?, updated_at = ?
                WHERE user_id = ?
                """,
                (int(order["credits"]), now, user_id),
            )
        else:
            starts = datetime.now(timezone.utc)
            ends = starts + timedelta(days=max(1, int(order["duration_days"])))
            subscription_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO subscriptions(
                    id, user_id, plan_id, plan_name, payment_order_id,
                    message_limit, messages_used, unlimited, daily_fair_limit,
                    starts_at, ends_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    subscription_id,
                    user_id,
                    str(order["plan_id"]),
                    str(order["plan_name"]),
                    str(order["id"]),
                    int(order["monthly_messages"]),
                    int(order["unlimited"]),
                    int(order["daily_fair_limit"]),
                    starts.isoformat(),
                    ends.isoformat(),
                    now,
                    now,
                ),
            )

        db.execute(
            """
            UPDATE payment_orders
            SET status = 'paid', paid_at = ?, updated_at = ?, raw_webhook_json = ?
            WHERE id = ?
            """,
            (now, now, raw_webhook_json[:20000], str(order["id"])),
        )
        db.commit()
        updated = get_payment_order(user_id, str(order["id"]))
        return updated, True
    except Exception:
        db.rollback()
        raise
