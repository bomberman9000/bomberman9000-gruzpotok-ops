#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


PROVIDER = "mock-pc-ai"
MODEL = "mock-model"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _envelope(
    *,
    ok: bool,
    result: dict | list | None,
    error: dict | None,
    duration_ms: int = 1,
    fallback_reason: str | None = None,
) -> dict:
    return {
        "ok": ok,
        "result": result,
        "error": error,
        "provider": PROVIDER,
        "model": MODEL if ok else None,
        "duration_ms": duration_ms,
        "fallback_reason": fallback_reason,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AIGatewayMock/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    @property
    def expected_token(self) -> str:
        return os.getenv("AI_GATEWAY_INTERNAL_TOKEN", "")

    def _check_auth(self) -> bool:
        token = self.headers.get("X-Internal-Token", "")
        if not token:
            _json_response(
                self,
                HTTPStatus.UNAUTHORIZED,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "auth_failed", "message": "missing token", "retryable": False},
                ),
            )
            return False
        if not self.expected_token or token != self.expected_token:
            _json_response(
                self,
                HTTPStatus.FORBIDDEN,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "auth_failed", "message": "invalid token", "retryable": False},
                ),
            )
            return False
        return True

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        if not raw:
            return {}
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}

    def _mode(self, payload: dict | None = None) -> str:
        query = parse_qs(urlparse(self.path).query)
        if query.get("mode"):
            return str(query["mode"][0])
        metadata = (payload or {}).get("metadata")
        if isinstance(metadata, dict):
            return str(metadata.get("mock_mode") or metadata.get("mode") or "")
        return ""

    def _maybe_error(self, mode: str) -> bool:
        if mode == "timeout":
            time.sleep(2.0)
            return False
        if mode == "internal_error":
            _json_response(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "internal_error", "message": "mock internal error", "retryable": True},
                    fallback_reason="mock_internal_error",
                ),
            )
            return True
        if mode == "invalid_request":
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "invalid_request", "message": "mock invalid request", "retryable": False},
                ),
            )
            return True
        if mode == "provider_unavailable":
            _json_response(
                self,
                HTTPStatus.SERVICE_UNAVAILABLE,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "provider_unavailable", "message": "mock provider unavailable", "retryable": True},
                    fallback_reason="mock_provider_unavailable",
                ),
            )
            return True
        return False

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/health":
            _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": {"code": "not_found"}})
            return
        if not self._check_auth():
            return
        if self._maybe_error(self._mode()):
            return
        _json_response(
            self,
            HTTPStatus.OK,
            _envelope(
                ok=True,
                result={"ollama": True, "rag": True, "workers": True, "mock": True},
                error=None,
            ),
        )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/v1/ai/chat", "/v1/ai/rag/query", "/v1/ai/embed"}:
            _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": {"code": "not_found"}})
            return
        if not self._check_auth():
            return
        try:
            payload = self._read_json()
        except Exception:
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _envelope(
                    ok=False,
                    result=None,
                    error={"code": "invalid_request", "message": "invalid json", "retryable": False},
                ),
            )
            return
        if self._maybe_error(self._mode(payload)):
            return
        if path == "/v1/ai/chat":
            result: dict | list | None = {
                "text": "mock chat response",
                "model": payload.get("model") or MODEL,
            }
        elif path == "/v1/ai/rag/query":
            result = {
                "answer": "mock rag response",
                "summary": "mock rag response",
                "citations": [],
                "llm_invoked": False,
                "model": payload.get("model") or MODEL,
            }
        else:
            result = {
                "embedding": [0.01, 0.02, 0.03],
                "dimensions": 3,
                "model": payload.get("model") or MODEL,
            }
        _json_response(self, HTTPStatus.OK, _envelope(ok=True, result=result, error=None))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock PC AI Gateway server")
    parser.add_argument("--host", default=os.getenv("AI_GATEWAY_MOCK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AI_GATEWAY_MOCK_PORT", "18081")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"AI Gateway mock listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
