from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_NO_FALLBACK_ERROR_CODES = {"invalid_request", "auth_failed", "invalid_remote_url", "payload_too_large"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("ai_gateway.invalid_timeout env=%s value=%r fallback=%s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("ai_gateway.invalid_int env=%s value=%r fallback=%s", name, raw, default)
        return default


class AIGatewayRemoteError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        fallback_allowed: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.fallback_allowed = code not in _NO_FALLBACK_ERROR_CODES if fallback_allowed is None else fallback_allowed


@dataclass(frozen=True)
class AIGatewayConfig:
    enabled: bool
    provider: str
    remote_url: str
    internal_token: str
    timeout_sec: float
    connect_timeout_sec: float
    read_timeout_sec: float
    total_timeout_sec: float
    max_payload_bytes: int
    max_response_bytes: int
    allowed_remote_prefixes: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "AIGatewayConfig":
        timeout_sec = max(0.1, _env_float("AI_GATEWAY_TIMEOUT_SEC", 30.0))
        return cls(
            enabled=_env_bool("AI_GATEWAY_ENABLED", False),
            provider=(os.getenv("AI_GATEWAY_PROVIDER") or "legacy").strip().lower() or "legacy",
            remote_url=(os.getenv("AI_GATEWAY_REMOTE_URL") or "").strip(),
            internal_token=(os.getenv("AI_GATEWAY_INTERNAL_TOKEN") or "").strip(),
            timeout_sec=timeout_sec,
            connect_timeout_sec=max(0.1, _env_float("AI_GATEWAY_CONNECT_TIMEOUT_SEC", 3.0)),
            read_timeout_sec=max(0.1, _env_float("AI_GATEWAY_READ_TIMEOUT_SEC", timeout_sec)),
            total_timeout_sec=max(0.1, _env_float("AI_GATEWAY_TOTAL_TIMEOUT_SEC", timeout_sec)),
            max_payload_bytes=max(1, _env_int("AI_GATEWAY_MAX_PAYLOAD_BYTES", 262144)),
            max_response_bytes=max(1, _env_int("AI_GATEWAY_MAX_RESPONSE_BYTES", 1048576)),
            allowed_remote_prefixes=tuple(
                prefix.strip()
                for prefix in (os.getenv("AI_GATEWAY_ALLOWED_REMOTE_PREFIXES") or "").split(",")
                if prefix.strip()
            ),
        )


class AIGateway:
    """Preparation wrapper for future AI offload.

    Default path is intentionally legacy and does not alter responses.
    """

    def _log_selected(self, operation: str, cfg: AIGatewayConfig) -> None:
        selected = cfg.provider if cfg.enabled else "legacy"
        logger.info(
            "ai_gateway.selected operation=%s enabled=%s provider=%s remote_configured=%s timeout_sec=%s",
            operation,
            cfg.enabled,
            selected,
            bool(cfg.remote_url),
            cfg.timeout_sec,
        )

    def _run_sync_remote_with_timeout(
        self,
        operation: str,
        remote_call: Callable[[], T],
        timeout_sec: float,
    ) -> T:
        result_queue: queue.Queue[tuple[bool, T | BaseException]] = queue.Queue(maxsize=1)

        def target() -> None:
            try:
                result_queue.put_nowait((True, remote_call()))
            except BaseException as exc:
                result_queue.put_nowait((False, exc))

        thread = threading.Thread(
            target=target,
            name=f"ai-gateway-{operation[:40]}",
            daemon=True,
        )
        thread.start()
        try:
            ok, value = result_queue.get(timeout=timeout_sec)
        except queue.Empty as exc:
            raise TimeoutError(f"sync remote call timed out after {timeout_sec}s") from exc
        if ok:
            return value  # type: ignore[return-value]
        raise value

    def _remote_base_url(self, cfg: AIGatewayConfig) -> str:
        if not cfg.remote_url:
            raise AIGatewayRemoteError("provider_unavailable", "AI_GATEWAY_REMOTE_URL is not configured")
        base_url = cfg.remote_url.rstrip("/")
        if not cfg.allowed_remote_prefixes or not any(
            base_url.startswith(prefix) for prefix in cfg.allowed_remote_prefixes
        ):
            raise AIGatewayRemoteError("invalid_remote_url", "AI gateway remote URL is not allowed")
        return base_url

    def _remote_headers(self, cfg: AIGatewayConfig) -> dict[str, str]:
        if not cfg.internal_token:
            raise AIGatewayRemoteError("auth_failed", "AI gateway internal token is not configured")
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Internal-Token": cfg.internal_token,
        }

    def _json_bytes(self, payload: dict[str, Any], cfg: AIGatewayConfig) -> bytes:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(body) > cfg.max_payload_bytes:
            raise AIGatewayRemoteError("payload_too_large", "AI gateway payload is too large")
        return body

    def _classify_http_error(self, status_code: int, envelope: dict[str, Any] | None) -> AIGatewayRemoteError:
        code = ""
        message = f"remote status {status_code}"
        if isinstance(envelope, dict):
            error = envelope.get("error")
            if isinstance(error, dict):
                code = str(error.get("code") or "")
                message = str(error.get("message") or message)
        if not code:
            if status_code in (401, 403):
                code = "auth_failed"
            elif status_code == 413:
                code = "payload_too_large"
            elif status_code == 400:
                code = "invalid_request"
            elif status_code >= 500:
                code = "internal_error"
            else:
                code = "internal_error"
        return AIGatewayRemoteError(code, message, status_code=status_code)

    def _parse_remote_response(
        self,
        *,
        status_code: int,
        content: bytes,
        cfg: AIGatewayConfig,
    ) -> dict[str, Any]:
        if len(content) > cfg.max_response_bytes:
            raise AIGatewayRemoteError("payload_too_large", "AI gateway response is too large")
        envelope: dict[str, Any] | None = None
        try:
            parsed = json.loads(content.decode("utf-8"))
            if isinstance(parsed, dict):
                envelope = parsed
        except ValueError:
            envelope = None
        if status_code >= 400:
            raise self._classify_http_error(status_code, envelope)
        if not isinstance(envelope, dict):
            raise AIGatewayRemoteError("internal_error", "remote response is not a JSON object")
        if envelope.get("ok") is not True:
            error = envelope.get("error")
            code = "internal_error"
            message = "remote returned ok=false"
            if isinstance(error, dict):
                code = str(error.get("code") or code)
                message = str(error.get("message") or message)
            raise AIGatewayRemoteError(code, message, status_code=status_code)
        return envelope

    def _request_payload(
        self,
        *,
        task_type: str,
        timeout_sec: float,
        request_id: str | None,
        metadata: dict[str, Any] | None,
        **payload: Any,
    ) -> dict[str, Any]:
        data = {
            "request_id": request_id or str(uuid.uuid4()),
            "task_type": task_type,
            "timeout_sec": timeout_sec,
            "metadata": metadata or {},
        }
        data.update({key: value for key, value in payload.items() if value is not None})
        return data

    def _remote_post_sync(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        operation: str,
    ) -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        started = time.perf_counter()
        body = self._json_bytes(payload, cfg)
        url = f"{self._remote_base_url(cfg)}{path}"
        request = urllib.request.Request(
            url,
            data=body,
            headers=self._remote_headers(cfg),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=cfg.total_timeout_sec) as response:
                status_code = int(response.status)
                content = response.read(cfg.max_response_bytes + 1)
        except (TimeoutError, socket.timeout) as exc:
            raise AIGatewayRemoteError("timeout", "remote request timed out") from exc
        except urllib.error.HTTPError as exc:
            content = exc.read(cfg.max_response_bytes + 1)
            raise self._classify_http_error(int(exc.code), self._parse_error_envelope(content))
        except urllib.error.URLError as exc:
            raise AIGatewayRemoteError("network_error", "remote network error") from exc
        envelope = self._parse_remote_response(status_code=status_code, content=content, cfg=cfg)
        logger.info(
            "ai_gateway.remote_ok operation=%s status=%s duration_ms=%s provider=%s",
            operation,
            status_code,
            int((time.perf_counter() - started) * 1000),
            envelope.get("provider"),
        )
        return envelope

    def _parse_error_envelope(self, content: bytes) -> dict[str, Any] | None:
        try:
            parsed = json.loads(content.decode("utf-8"))
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _remote_post_async(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        operation: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._remote_post_sync,
            path,
            payload,
            operation=operation,
        )

    def health_sync(self, operation: str = "health") -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        url = f"{self._remote_base_url(cfg)}/health"
        request = urllib.request.Request(
            url,
            headers=self._remote_headers(cfg),
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=cfg.total_timeout_sec) as response:
                status_code = int(response.status)
                content = response.read(cfg.max_response_bytes + 1)
        except (TimeoutError, socket.timeout) as exc:
            raise AIGatewayRemoteError("timeout", "remote health timed out") from exc
        except urllib.error.HTTPError as exc:
            content = exc.read(cfg.max_response_bytes + 1)
            raise self._classify_http_error(int(exc.code), self._parse_error_envelope(content))
        except urllib.error.URLError as exc:
            raise AIGatewayRemoteError("network_error", "remote health network error") from exc
        return self._parse_remote_response(status_code=status_code, content=content, cfg=cfg)

    def chat_sync(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None,
        timeout_sec: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        operation: str = "chat",
    ) -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        payload = self._request_payload(
            task_type="chat",
            messages=messages,
            model=model,
            timeout_sec=timeout_sec or cfg.timeout_sec,
            request_id=request_id,
            metadata=metadata,
        )
        return self._remote_post_sync("/v1/ai/chat", payload, operation=operation)

    async def chat_async(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None,
        timeout_sec: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        operation: str = "chat",
    ) -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        payload = self._request_payload(
            task_type="chat",
            messages=messages,
            model=model,
            timeout_sec=timeout_sec or cfg.timeout_sec,
            request_id=request_id,
            metadata=metadata,
        )
        return await self._remote_post_async("/v1/ai/chat", payload, operation=operation)

    async def rag_query_async(
        self,
        *,
        query: str,
        task_type: str = "rag.query",
        timeout_sec: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        operation: str = "rag.query",
    ) -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        payload = self._request_payload(
            task_type=task_type,
            query=query,
            timeout_sec=timeout_sec or cfg.timeout_sec,
            request_id=request_id,
            metadata=metadata,
        )
        return await self._remote_post_async("/v1/ai/rag/query", payload, operation=operation)

    def embed_sync(
        self,
        *,
        input: str,
        model: str | None = None,
        timeout_sec: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        operation: str = "embed",
    ) -> dict[str, Any]:
        cfg = AIGatewayConfig.from_env()
        payload = self._request_payload(
            task_type="embed",
            input=input,
            model=model,
            timeout_sec=timeout_sec or cfg.timeout_sec,
            request_id=request_id,
            metadata=metadata,
        )
        return self._remote_post_sync("/v1/ai/embed", payload, operation=operation)

    def run_sync(
        self,
        operation: str,
        legacy_call: Callable[[], T],
        *,
        remote_call: Callable[[], T] | None = None,
    ) -> T:
        cfg = AIGatewayConfig.from_env()
        self._log_selected(operation, cfg)

        if not cfg.enabled or cfg.provider == "legacy":
            return legacy_call()

        if cfg.provider != "remote" or remote_call is None:
            logger.warning(
                "ai_gateway.fallback_legacy operation=%s provider=%s reason=unsupported_or_missing_remote",
                operation,
                cfg.provider,
            )
            return legacy_call()

        try:
            return self._run_sync_remote_with_timeout(operation, remote_call, cfg.timeout_sec)
        except AIGatewayRemoteError as exc:
            logger.warning(
                "ai_gateway.remote_error operation=%s provider=%s code=%s status=%s fallback_allowed=%s",
                operation,
                cfg.provider,
                exc.code,
                exc.status_code,
                exc.fallback_allowed,
            )
            if not exc.fallback_allowed:
                raise
        except TimeoutError as exc:
            logger.warning(
                "ai_gateway.timeout operation=%s provider=%s timeout_sec=%s error=%s",
                operation,
                cfg.provider,
                cfg.timeout_sec,
                str(exc)[:300],
            )
        except Exception as exc:
            logger.warning(
                "ai_gateway.error operation=%s provider=%s error=%s",
                operation,
                cfg.provider,
                str(exc)[:500],
            )

        logger.info("ai_gateway.fallback_legacy operation=%s provider=%s", operation, cfg.provider)
        return legacy_call()

    async def run_async(
        self,
        operation: str,
        legacy_call: Callable[[], Awaitable[T]],
        *,
        remote_call: Callable[[], Awaitable[T]] | None = None,
    ) -> T:
        cfg = AIGatewayConfig.from_env()
        self._log_selected(operation, cfg)

        if not cfg.enabled or cfg.provider == "legacy":
            return await legacy_call()

        if cfg.provider != "remote" or remote_call is None:
            logger.warning(
                "ai_gateway.fallback_legacy operation=%s provider=%s reason=unsupported_or_missing_remote",
                operation,
                cfg.provider,
            )
            return await legacy_call()

        try:
            return await asyncio.wait_for(remote_call(), timeout=cfg.timeout_sec)
        except AIGatewayRemoteError as exc:
            logger.warning(
                "ai_gateway.remote_error operation=%s provider=%s code=%s status=%s fallback_allowed=%s",
                operation,
                cfg.provider,
                exc.code,
                exc.status_code,
                exc.fallback_allowed,
            )
            if not exc.fallback_allowed:
                raise
        except TimeoutError as exc:
            logger.warning(
                "ai_gateway.timeout operation=%s provider=%s timeout_sec=%s error=%s",
                operation,
                cfg.provider,
                cfg.timeout_sec,
                str(exc)[:300],
            )
        except Exception as exc:
            logger.warning(
                "ai_gateway.error operation=%s provider=%s error=%s",
                operation,
                cfg.provider,
                str(exc)[:500],
            )

        logger.info("ai_gateway.fallback_legacy operation=%s provider=%s", operation, cfg.provider)
        return await legacy_call()


ai_gateway = AIGateway()
