from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.ai_history_routes import router as ai_history_router
from app.api.ai_ops_hardening_routes import router as ai_ops_hardening_router
from app.api.ai_operator_dashboard_routes import router as ai_operator_dashboard_router
from app.api.ai_review_routes import router as ai_review_router
from app.api.ai_routes import router as ai_router
from app.api.internal_routes import router as internal_router
from app.core.config import get_settings
from app.db.migrate import run_migrations
from app.middleware.internal_auth import InternalAuthMiddleware
from app.middleware.request_context import RequestLoggingMiddleware
from app.services import observability
from app.services.ops.go_live_check import build_go_live_check
from app.services.ops_status import build_ops_status, ping_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.database_url:
        conn = psycopg2.connect(s.database_url)
        try:
            applied = run_migrations(conn)
            if applied:
                logger.info("backend migrations applied: %s", applied)
        finally:
            conn.close()
    yield


logging.basicConfig(level=get_settings().log_level)

app = FastAPI(
    title="ГрузПоток Backend (AI)",
    description="Интеграционный слой к rag-api: претензии, логистика, документы.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(InternalAuthMiddleware)

_s0 = get_settings()
if _s0.cors_origins:
    _origins = [o.strip() for o in str(_s0.cors_origins).split(",") if o.strip()]
else:
    _origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(internal_router)
app.include_router(ai_history_router)
app.include_router(ai_review_router)
app.include_router(ai_operator_dashboard_router)
app.include_router(ai_ops_hardening_router)


@app.get("/health")
def health() -> dict:
    from app.services.ai.ai_call_service import count_ai_calls

    s = get_settings()
    snap = observability.snapshot()
    out: dict = {
        "status": "ok",
        "service": "gruzpotok-backend",
        "database_configured": bool(s.database_url),
        "internal_auth_enabled": bool(s.internal_auth_enabled),
    }
    out.update(snap)
    out["ai_calls_in_db"] = count_ai_calls()
    out["ready_endpoint"] = "/ready"
    out["ops_status_endpoint"] = "/internal/ops/status"
    out["go_live_check_endpoint"] = "/internal/ops/go-live-check"
    return out


@app.get("/ready")
def ready() -> dict:
    """Readiness: БД доступна, если DATABASE_URL задан."""
    s = get_settings()
    if not s.database_url:
        return {"ready": True, "database": "not_configured", "note": "DATABASE_URL empty — dev mode"}
    ok = ping_database()
    return {"ready": ok, "database": "ok" if ok else "unreachable"}


@app.get("/internal/ops/status")
def internal_ops_status() -> dict:
    return build_ops_status()


@app.get("/internal/ops/go-live-check")
def internal_go_live_check() -> dict:
    """Чеклист перед internal rollout (см. docs/AI_LAUNCH_READINESS.md)."""
    return build_go_live_check()


@app.get("/")
def root() -> dict:
    return {
        "service": "gruzpotok-backend",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "ops_status": "/internal/ops/status",
        "go_live_check": "/internal/ops/go-live-check",
        "ai": "/api/v1/ai",
        "internal": "/api/v1/internal",
        "internal_ai_history": "/api/v1/internal/ai/calls",
        "operator_ui": "/operator" if get_settings().operator_ui_dist else None,
    }


_s1 = get_settings()
if _s1.operator_ui_dist:
    _dist = Path(_s1.operator_ui_dist)
    if _dist.is_dir() and (_dist / "index.html").is_file():
        app.mount("/operator", StaticFiles(directory=str(_dist), html=True), name="operator_ui")
        logger.info("Serving operator UI from %s at /operator", _dist)
    else:
        logger.warning("OPERATOR_UI_DIST set but index.html missing: %s", _dist)
