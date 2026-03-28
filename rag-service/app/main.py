from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI

from app.api.gruzpotok_routes import router as gruzpotok_router
from app.api.routes import router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.migrate import run_migrations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting RAG API, DSN host parsed from config")
    conn = psycopg2.connect(settings.postgres_dsn)
    try:
        applied = run_migrations(conn)
        if applied:
            logger.info("Migrations applied: %s", applied)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Offline RAG API",
    description="Локальный RAG: PostgreSQL/pgvector + Ollama",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(gruzpotok_router)


@app.get("/")
def root():
    return {
        "service": "rag-api",
        "docs": "/docs",
        "health": "/health",
        "query": "POST /query",
        "seed": "POST /seed",
        "gruzpotok": [
            "POST /legal/claim-review",
            "POST /legal/claim-draft",
            "POST /legal/claim-compose",
            "POST /freight/risk-check",
            "POST /freight/route-advice",
            "POST /freight/document-check",
            "POST /freight/transport-order-compose",
            "POST /freight/transport-order-pdf",
        ],
    }
