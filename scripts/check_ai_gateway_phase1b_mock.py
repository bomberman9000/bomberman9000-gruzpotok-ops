#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import os
import socket
import subprocess
import sys
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "phase1b_mock_token"
GATEWAY_ENV = [
    "AI_GATEWAY_ENABLED",
    "AI_GATEWAY_PROVIDER",
    "AI_GATEWAY_REMOTE_URL",
    "AI_GATEWAY_ALLOWED_REMOTE_PREFIXES",
    "AI_GATEWAY_INTERNAL_TOKEN",
    "AI_GATEWAY_TIMEOUT_SEC",
    "AI_GATEWAY_CONNECT_TIMEOUT_SEC",
    "AI_GATEWAY_READ_TIMEOUT_SEC",
    "AI_GATEWAY_TOTAL_TIMEOUT_SEC",
    "AI_GATEWAY_MAX_PAYLOAD_BYTES",
    "AI_GATEWAY_MAX_RESPONSE_BYTES",
]

WRAPPERS = [
    ROOT / "goutruckme-git/app/ai/gateway.py",
    ROOT / "goutruckme-api/src/core/services/ai_gateway.py",
    ROOT / "backend/app/services/ai/gateway_wrapper.py",
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _load_module(path: Path):
    name = "phase1b_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _clear_env() -> dict[str, str]:
    old = {key: os.environ[key] for key in GATEWAY_ENV if key in os.environ}
    for key in GATEWAY_ENV:
        os.environ.pop(key, None)
    return old


def _restore_env(old: dict[str, str]) -> None:
    for key in GATEWAY_ENV:
        os.environ.pop(key, None)
    os.environ.update(old)


def _set_remote_env(base_url: str, *, token: str | None = TOKEN, timeout: str = "0.4") -> None:
    os.environ["AI_GATEWAY_ENABLED"] = "true"
    os.environ["AI_GATEWAY_PROVIDER"] = "remote"
    os.environ["AI_GATEWAY_REMOTE_URL"] = base_url
    os.environ["AI_GATEWAY_ALLOWED_REMOTE_PREFIXES"] = "http://127.0.0.1:,http://localhost:"
    os.environ["AI_GATEWAY_TIMEOUT_SEC"] = timeout
    os.environ["AI_GATEWAY_CONNECT_TIMEOUT_SEC"] = "0.2"
    os.environ["AI_GATEWAY_READ_TIMEOUT_SEC"] = timeout
    os.environ["AI_GATEWAY_TOTAL_TIMEOUT_SEC"] = timeout
    os.environ["AI_GATEWAY_MAX_PAYLOAD_BYTES"] = "262144"
    os.environ["AI_GATEWAY_MAX_RESPONSE_BYTES"] = "1048576"
    if token is None:
        os.environ.pop("AI_GATEWAY_INTERNAL_TOKEN", None)
    else:
        os.environ["AI_GATEWAY_INTERNAL_TOKEN"] = token


def _start_mock_server(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["AI_GATEWAY_INTERNAL_TOKEN"] = TOKEN
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "tools/ai_gateway_mock_server.py"), "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1)
            raise RuntimeError(f"mock server exited early\nstdout={out}\nstderr={err}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return proc
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("mock server did not start")


def _expect_remote_error(module, code: str, func) -> None:
    try:
        func()
    except module.AIGatewayRemoteError as exc:
        assert exc.code == code, (exc.code, code)
        assert exc.fallback_allowed is False, exc.code
        return
    raise AssertionError(f"expected AIGatewayRemoteError({code})")


def _check_wrapper(module, base_url: str) -> None:
    gateway = module.AIGateway()
    calls: list[str] = []

    def legacy() -> dict[str, str]:
        calls.append("legacy")
        return {"path": "legacy"}

    def explode_remote() -> dict[str, str]:
        calls.append("remote")
        raise AssertionError("remote should not be called")

    os.environ["AI_GATEWAY_ENABLED"] = "false"
    os.environ["AI_GATEWAY_PROVIDER"] = "remote"
    assert gateway.run_sync("phase1b.disabled", legacy, remote_call=explode_remote) == {"path": "legacy"}
    assert calls == ["legacy"]

    calls.clear()
    os.environ["AI_GATEWAY_ENABLED"] = "true"
    os.environ["AI_GATEWAY_PROVIDER"] = "legacy"
    assert gateway.run_sync("phase1b.legacy_provider", legacy, remote_call=explode_remote) == {"path": "legacy"}
    assert calls == ["legacy"]

    _set_remote_env(base_url)
    health = gateway.health_sync()
    assert health["ok"] is True

    chat = gateway.chat_sync(
        messages=[{"role": "user", "content": "hello"}],
        model="mock-model",
        metadata={"case": "chat_ok"},
    )
    assert chat["ok"] is True
    assert chat["result"]["text"] == "mock chat response"

    def remote_chat(mode: str):
        return lambda: gateway.chat_sync(
            messages=[{"role": "user", "content": "hello"}],
            model="mock-model",
            metadata={"mock_mode": mode},
            operation=f"phase1b.{mode}",
        )

    assert gateway.run_sync("phase1b.timeout", legacy, remote_call=remote_chat("timeout")) == {"path": "legacy"}
    assert gateway.run_sync("phase1b.internal_error", legacy, remote_call=remote_chat("internal_error")) == {"path": "legacy"}
    assert gateway.run_sync(
        "phase1b.provider_unavailable",
        legacy,
        remote_call=remote_chat("provider_unavailable"),
    ) == {"path": "legacy"}

    _expect_remote_error(
        module,
        "invalid_request",
        lambda: gateway.run_sync("phase1b.invalid_request", legacy, remote_call=remote_chat("invalid_request")),
    )

    _set_remote_env(base_url, token="wrong")
    _expect_remote_error(
        module,
        "auth_failed",
        lambda: gateway.run_sync("phase1b.auth_failed", legacy, remote_call=remote_chat("chat_ok")),
    )

    _set_remote_env(base_url, token=None)
    _expect_remote_error(
        module,
        "auth_failed",
        lambda: gateway.run_sync("phase1b.missing_token", legacy, remote_call=remote_chat("chat_ok")),
    )

    _set_remote_env(base_url)
    os.environ["AI_GATEWAY_ALLOWED_REMOTE_PREFIXES"] = "http://example.invalid/"
    _expect_remote_error(
        module,
        "invalid_remote_url",
        lambda: gateway.run_sync("phase1b.invalid_remote_url", legacy, remote_call=remote_chat("chat_ok")),
    )


def _check_response_mapping(base_url: str) -> None:
    _set_remote_env(base_url)
    _install_optional_dependency_stubs()

    sys.path.insert(0, str(ROOT / "goutruckme-git"))
    from app.ai.ai_service import AIService as PublicAIService

    public_result = PublicAIService().ask(prompt="hello")
    assert set(["text", "model", "source"]).issubset(public_result.keys())
    assert public_result["text"] == "mock chat response"
    assert public_result["source"] == "mock-pc-ai"

    sys.path.insert(0, str(ROOT / "goutruckme-api"))
    from src.core.services.ai_service import AIService as BotAIService

    bot_result = BotAIService().ask(prompt="hello")
    assert set(bot_result.keys()) == {"text", "model", "source"}
    assert bot_result["text"] == "mock chat response"
    assert bot_result["source"] == "mock-pc-ai"


def _install_optional_dependency_stubs() -> None:
    if "httpx" not in sys.modules:
        try:
            __import__("httpx")
        except ModuleNotFoundError:
            httpx_stub = types.ModuleType("httpx")

            class _HTTPXError(Exception):
                pass

            class _Timeout:
                def __init__(self, *args, **kwargs):
                    pass

            class _Client:
                def __init__(self, *args, **kwargs):
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return None

            class _AsyncClient(_Client):
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    return None

            httpx_stub.Timeout = _Timeout
            httpx_stub.Client = _Client
            httpx_stub.AsyncClient = _AsyncClient
            httpx_stub.TimeoutException = _HTTPXError
            httpx_stub.RequestError = _HTTPXError
            httpx_stub.HTTPStatusError = _HTTPXError
            sys.modules["httpx"] = httpx_stub

    if "pydantic" not in sys.modules:
        try:
            __import__("pydantic")
        except ModuleNotFoundError:
            pydantic_stub = types.ModuleType("pydantic")

            def Field(default=None, **kwargs):
                if "default_factory" in kwargs:
                    return kwargs["default_factory"]()
                return default

            def field_validator(*args, **kwargs):
                def deco(fn):
                    return fn

                return deco

            class BaseModel:
                def __init__(self, **kwargs):
                    annotations = {}
                    for cls in reversed(self.__class__.mro()):
                        annotations.update(getattr(cls, "__annotations__", {}))
                    for name in annotations:
                        if name in kwargs:
                            value = kwargs[name]
                        else:
                            value = getattr(self.__class__, name, None)
                            if isinstance(value, list):
                                value = list(value)
                            elif isinstance(value, dict):
                                value = dict(value)
                        setattr(self, name, value)
                    for name, value in kwargs.items():
                        if not hasattr(self, name):
                            setattr(self, name, value)

                def model_dump(self, *args, **kwargs):
                    return dict(self.__dict__)

            pydantic_stub.BaseModel = BaseModel
            pydantic_stub.Field = Field
            pydantic_stub.field_validator = field_validator
            sys.modules["pydantic"] = pydantic_stub

    if "pydantic_settings" not in sys.modules:
        try:
            __import__("pydantic_settings")
        except ModuleNotFoundError:
            pydantic_settings_stub = types.ModuleType("pydantic_settings")
            BaseSettings = sys.modules["pydantic"].BaseModel
            pydantic_settings_stub.BaseSettings = BaseSettings
            pydantic_settings_stub.SettingsConfigDict = lambda **kwargs: dict(kwargs)
            sys.modules["pydantic_settings"] = pydantic_settings_stub


async def _check_rag(base_url: str) -> None:
    _set_remote_env(base_url)
    module = _load_module(ROOT / "backend/app/services/ai/gateway_wrapper.py")
    gateway = module.AIGateway()
    envelope = await gateway.rag_query_async(query="hello", metadata={"case": "rag_ok"})
    assert envelope["ok"] is True
    assert envelope["result"]["answer"] == "mock rag response"


async def _check_backend_ai_envelope(base_url: str) -> None:
    _set_remote_env(base_url)
    _install_optional_dependency_stubs()

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)
    ai_call_stub = types.ModuleType("app.services.ai.ai_call_service")
    ai_call_stub.record_ai_call = lambda **kwargs: None
    sys.modules["app.services.ai.ai_call_service"] = ai_call_stub
    sys.path.insert(0, str(ROOT / "backend"))
    from app.services.ai import gateway as backend_gateway

    backend_gateway.record_ai_call = lambda **kwargs: None

    async def legacy_call(_client):
        raise AssertionError("legacy RagApiClient call should not run when remote mock is enabled")

    envelope = await backend_gateway.run_ai_gateway(
        endpoint="query",
        rag_path="/query",
        request_id="phase1b-backend-envelope",
        user_input={"query": "hello"},
        call=legacy_call,
    )
    assert envelope.meta.request_id == "phase1b-backend-envelope"
    assert envelope.meta.endpoint == "query"
    assert envelope.data.status == "ok"
    assert envelope.data.answer == "mock rag response"
    assert isinstance(envelope.data.raw_response, dict)
    assert "ok" not in envelope.data.raw_response
    assert "result" not in envelope.data.raw_response
    assert "error" not in envelope.data.raw_response


def main() -> None:
    old_env = _clear_env()
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    proc = _start_mock_server(port)
    try:
        for wrapper in WRAPPERS:
            _check_wrapper(_load_module(wrapper), base_url)
        _check_response_mapping(base_url)
        asyncio.run(_check_rag(base_url))
        asyncio.run(_check_backend_ai_envelope(base_url))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        _restore_env(old_env)

    print("AI Gateway Phase 1B mock smoke OK")


if __name__ == "__main__":
    main()
