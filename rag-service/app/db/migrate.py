"""Apply SQL migrations from app/db/migrations once per version."""
from pathlib import Path

import sqlparse
from psycopg2.extensions import connection as PgConnection

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _sql_without_line_comments(stmt: str) -> str:
    """Убирает строки, целиком являющиеся `--` комментариями (после sqlparse.split)."""
    lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
    return "\n".join(lines).strip()


def _ensure_migrations_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )


def run_migrations(conn: PgConnection) -> list[str]:
    """Returns list of applied migration versions."""
    cur = conn.cursor()
    _ensure_migrations_table(cur)
    conn.commit()
    cur.close()

    applied: list[str] = []
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for path in sql_files:
        version = path.name
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
        if cur.fetchone():
            cur.close()
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            for stmt in sqlparse.split(sql):
                s = _sql_without_line_comments(stmt)
                if not s:
                    continue
                cur.execute(s)
            cur.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
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
