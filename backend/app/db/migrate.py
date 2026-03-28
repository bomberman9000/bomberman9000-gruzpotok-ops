"""Применение SQL-миграций (как в rag-service)."""
from pathlib import Path

import sqlparse
from psycopg2.extensions import connection as PgConnection

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# Отдельно от rag-service: там своя таблица schema_migrations, иначе риск коллизии имён файлов миграций.
MIGRATIONS_TABLE = "schema_migrations_gruzpotok"


def _ensure_migrations_table(cur) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )


def run_migrations(conn: PgConnection) -> list[str]:
    cur = conn.cursor()
    _ensure_migrations_table(cur)
    conn.commit()
    cur.close()

    applied: list[str] = []
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for path in sql_files:
        version = path.name
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {MIGRATIONS_TABLE} WHERE version = %s", (version,))
        if cur.fetchone():
            cur.close()
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            for stmt in sqlparse.split(sql):
                s = stmt.strip()
                if not s or s.startswith("--"):
                    continue
                cur.execute(s)
            cur.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (version) VALUES (%s)",
                (version,),
            )
            cur.close()
            conn.commit()
            applied.append(version)
        except Exception:
            conn.rollback()
            cur.close()
            raise
    return applied


if __name__ == "__main__":
    import os
    import sys

    import psycopg2

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("DATABASE_URL не задан", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(url)
    try:
        applied = run_migrations(conn)
        print("Применено:" if applied else "Новых миграций нет.", applied or [])
    finally:
        conn.close()
