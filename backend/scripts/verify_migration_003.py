#!/usr/bin/env python3
"""
Проверка миграции 003 на текущей DATABASE_URL:
- применить недостающие миграции дважды (второй проход без новых версий);
- убедиться в наличии колонок review_reason_codes / feedback_reason_codes.

Запуск из каталога backend:
  py scripts/verify_migration_003.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import psycopg2

from app.core.config import get_settings
from app.db.migrate import run_migrations


def main() -> int:
    s = get_settings()
    if not s.database_url:
        print("ERROR: DATABASE_URL не задан", file=sys.stderr)
        return 1
    conn = psycopg2.connect(s.database_url)
    try:
        applied1 = run_migrations(conn)
        applied2 = run_migrations(conn)
        print("first_apply:", applied1)
        print("second_apply:", applied2)
        if applied2:
            print("WARN: второй проход применил миграции — ожидалось []", file=sys.stderr)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('ai_reviews', 'ai_feedback')
              AND column_name IN ('review_reason_codes', 'feedback_reason_codes')
            ORDER BY table_name, column_name
            """
        )
        rows = cur.fetchall()
        cur.close()
        want = {("ai_feedback", "feedback_reason_codes"), ("ai_reviews", "review_reason_codes")}
        got = {(str(a), str(b)) for a, b in rows}
        if want != got:
            print("ERROR: колонки не совпадают с ожидаемым набором", file=sys.stderr)
            print("got:", sorted(got))
            print("want:", sorted(want))
            return 1
        print("OK: колонки на месте")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
