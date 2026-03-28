"""Опциональная защита internal API токеном (X-Internal-Token или Bearer)."""
from __future__ import annotations

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Пути без проверки токена (health, docs, публичный AI, статика оператора)
_EXEMPT_PREFIXES = (
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/ai",  # публичный контур AI (не internal)
)


def _exempt(path: str) -> bool:
    if path in ("/", "/favicon.ico"):
        return True
    for p in _EXEMPT_PREFIXES:
        if path == p or path.startswith(p + "/") or path.startswith(p + "?"):
            return True
    if path.startswith("/operator"):
        return True
    return False


def _requires_internal_auth(path: str) -> bool:
    if path.startswith("/api/v1/internal"):
        return True
    if path.startswith("/internal/ops"):
        return True
    return False


def _token_ok(request: Request, expected: str | None) -> bool:
    if not expected:
        return False
    h = request.headers.get("X-Internal-Token") or request.headers.get("x-internal-token")
    if h and h.strip() == expected:
        return True
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() == expected
    return False


class InternalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        s = get_settings()
        path = request.url.path
        if not _requires_internal_auth(path):
            return await call_next(request)
        if not s.internal_auth_enabled:
            return await call_next(request)
        if not (s.internal_auth_token or "").strip():
            logger.warning("INTERNAL_AUTH_ENABLED but INTERNAL_AUTH_TOKEN empty — auth not enforced")
            return await call_next(request)
        if _exempt(path):
            return await call_next(request)
        if not _token_ok(request, s.internal_auth_token):
            logger.warning("internal auth denied path=%s", path)
            return JSONResponse({"detail": "Unauthorized internal API"}, status_code=401)
        return await call_next(request)
