"""One-time best-effort migration from local app.db to production Postgres.

Usage (PowerShell):
    $env:DATABASE_URL="postgresql://...external Render URL..."
    python scripts/migrate_sqlite_to_postgres.py app.db

Run this only after the production app has deployed once, so all target tables exist.
The script inserts missing rows and preserves existing target rows on primary/unique conflicts.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from collections import defaultdict, deque
from pathlib import Path


def source_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def dependency_order(conn: sqlite3.Connection, tables: list[str]) -> list[str]:
    table_set = set(tables)
    deps: dict[str, set[str]] = {t: set() for t in tables}
    children: dict[str, set[str]] = defaultdict(set)
    for table in tables:
        for row in conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall():
            parent = str(row[2])
            if parent in table_set and parent != table:
                deps[table].add(parent)
                children[parent].add(table)
    queue = deque(sorted(t for t in tables if not deps[t]))
    result: list[str] = []
    while queue:
        table = queue.popleft()
        result.append(table)
        for child in sorted(children[table]):
            deps[child].discard(table)
            if not deps[child] and child not in result and child not in queue:
                queue.append(child)
    # Cycles are unusual here; append any remainder deterministically.
    result.extend(sorted(set(tables) - set(result)))
    return result


def main() -> int:
    source_path = Path(sys.argv[1] if len(sys.argv) > 1 else "app.db").resolve()
    database_url = str(os.getenv("DATABASE_URL", "") or "").strip()
    if not source_path.is_file():
        print(f"Không tìm thấy SQLite: {source_path}")
        return 2
    if not database_url:
        print("Thiếu DATABASE_URL. Dùng External Database URL của Render cho lần migrate này.")
        return 2

    try:
        import psycopg
    except ImportError:
        print("Chưa cài psycopg. Chạy: pip install -r requirements.txt")
        return 2

    src = sqlite3.connect(str(source_path))
    src.row_factory = sqlite3.Row
    dst = psycopg.connect(database_url)
    try:
        tables = dependency_order(src, source_tables(src))
        total = 0
        for table in tables:
            target_cols = {
                str(row[0])
                for row in dst.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
                    (table,),
                ).fetchall()
            }
            if not target_cols:
                print(f"SKIP {table}: bảng chưa tồn tại ở Postgres")
                continue
            source_cols = [str(row[1]) for row in src.execute(f'PRAGMA table_info("{table}")').fetchall()]
            columns = [col for col in source_cols if col in target_cols]
            if not columns:
                continue
            rows = src.execute(
                f'SELECT {", ".join(chr(34)+c+chr(34) for c in columns)} FROM "{table}"'
            ).fetchall()
            if not rows:
                continue
            quoted = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            for row in rows:
                dst.execute(sql, tuple(row[col] for col in columns))
            dst.commit()
            total += len(rows)
            print(f"OK   {table}: {len(rows)} dòng")

            # Keep SERIAL ids ahead of imported explicit ids.
            if "id" in columns:
                seq_row = dst.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,)).fetchone()
                sequence = seq_row[0] if seq_row else None
                if sequence:
                    dst.execute(
                        f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{table}"), 1), '
                        f'(SELECT COUNT(*) > 0 FROM "{table}"))',
                        (sequence,),
                    )
                    dst.commit()
        print(f"Hoàn tất. Đã đọc/chèn tối đa {total} dòng từ {source_path.name}.")
        return 0
    except Exception:
        dst.rollback()
        raise
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    raise SystemExit(main())
