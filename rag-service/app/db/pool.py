import os
from contextlib import contextmanager

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import pool

from app.core.config import settings

_connection_pool: pool.SimpleConnectionPool | None = None


def get_database_url() -> str:
    return settings.postgres_dsn


def get_pool() -> pool.SimpleConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.SimpleConnectionPool(
            1, 10, dsn=get_database_url()
        )
    return _connection_pool


@contextmanager
def get_conn():
    p = get_pool()
    conn = p.getconn()
    try:
        register_vector(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def reset_pool() -> None:
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
