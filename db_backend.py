from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable


class DatabaseIntegrityError(Exception):
    pass


def database_target(sqlite_path: str) -> tuple[str, str]:
    url = str(os.getenv("DATABASE_URL", "") or "").strip()
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return "postgres", url
    if str(os.getenv("REQUIRE_POSTGRES", "false")).lower() in {"1", "true", "yes"}:
        raise RuntimeError("Production yêu cầu PostgreSQL nhưng DATABASE_URL đang trống.")
    return "sqlite", str(sqlite_path)


def translate_postgres_sql(sql: str) -> str:
    """Translate the small SQLite dialect subset used by this project to Postgres."""
    out = str(sql)
    out = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", out, flags=re.I)
    out = re.sub(r"\s+COLLATE\s+NOCASE\b", "", out, flags=re.I)
    # One legacy query uses SQLite's json_extract. The column stores JSON text.
    out = re.sub(
        r"json_extract\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*'\$\.([A-Za-z0-9_]+)'\s*\)",
        r"(CAST(\1 AS jsonb) ->> '\2')",
        out,
        flags=re.I,
    )
    # Project SQL uses qmark placeholders and does not use literal question marks in SQL strings.
    out = out.replace("?", "%s")
    return out


def _split_script(script: str) -> list[str]:
    # DDL in this project does not contain semicolons inside quoted strings.
    return [part.strip() for part in str(script).split(";") if part.strip()]


class CursorProxy:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return int(getattr(self._cursor, "rowcount", -1) or 0)

    @property
    def lastrowid(self) -> int | None:
        value = getattr(self._cursor, "lastrowid", None)
        return int(value) if value is not None else None

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)


class SQLiteConnection:
    backend = "sqlite"

    def __init__(self, path: str):
        self.raw = sqlite3.connect(
            path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        self.raw.row_factory = sqlite3.Row
        self.raw.execute("PRAGMA journal_mode=WAL")
        self.raw.execute("PRAGMA foreign_keys=ON")
        self.raw.execute("PRAGMA busy_timeout=10000")

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> CursorProxy:
        try:
            return CursorProxy(self.raw.execute(sql, tuple(params or ())))
        except sqlite3.IntegrityError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        self.raw.executescript(script)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


class PostgresConnection:
    backend = "postgres"

    def __init__(self, url: str):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - only occurs on incomplete production install
            raise RuntimeError("DATABASE_URL đã được cấu hình nhưng chưa cài psycopg[binary].") from exc
        self._psycopg = psycopg
        self.raw = psycopg.connect(url, row_factory=dict_row)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> CursorProxy:
        translated = translate_postgres_sql(sql)
        try:
            cursor = self.raw.execute(translated, tuple(params or ()))
            return CursorProxy(cursor)
        except self._psycopg.IntegrityError as exc:
            self.raw.rollback()
            raise DatabaseIntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        for statement in _split_script(script):
            self.raw.execute(translate_postgres_sql(statement))

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


def connect_database(sqlite_path: str):
    backend, target = database_target(sqlite_path)
    if backend == "postgres":
        return PostgresConnection(target)
    return SQLiteConnection(target)


def column_names(db: Any, table: str) -> set[str]:
    if getattr(db, "backend", "sqlite") == "postgres":
        rows = db.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table,),
        ).fetchall()
        return {str(row["name"]) for row in rows}
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def table_exists(db: Any, table: str) -> bool:
    if getattr(db, "backend", "sqlite") == "postgres":
        row = db.execute(
            """
            SELECT 1 AS ok
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            LIMIT 1
            """,
            (table,),
        ).fetchone()
        return row is not None
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None
