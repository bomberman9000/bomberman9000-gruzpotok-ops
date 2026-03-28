from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection

from app.core.config import get_settings


@contextmanager
def get_conn() -> Generator[PgConnection, None, None]:
    s = get_settings()
    if not s.database_url:
        raise RuntimeError("database_url is not configured")
    conn = psycopg2.connect(s.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
