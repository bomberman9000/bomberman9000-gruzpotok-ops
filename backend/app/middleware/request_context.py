"""Логирование запросов и ошибок (operational visibility)."""
from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gruzpotok.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get("X-Request-ID") or request.headers.get("x-request-id") or "—"
        path = request.url.path
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
            ms = (time.perf_counter() - t0) * 1000
            if path.startswith("/api/") or path.startswith("/internal/"):
                logger.info(
                    "http %s %s -> %s in %.1fms request_id=%s",
                    request.method,
                    path,
                    response.status_code,
                    ms,
                    rid,
                )
            return response
        except Exception:
            ms = (time.perf_counter() - t0) * 1000
            logger.exception("http %s %s failed after %.1fms request_id=%s", request.method, path, ms, rid)
            raise
