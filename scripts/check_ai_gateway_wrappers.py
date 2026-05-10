#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WRAPPERS = [
    ROOT / "goutruckme-git/app/ai/gateway.py",
    ROOT / "goutruckme-api/src/core/services/ai_gateway.py",
    ROOT / "backend/app/services/ai/gateway_wrapper.py",
]

GATEWAY_ENV = [
    "AI_GATEWAY_ENABLED",
    "AI_GATEWAY_PROVIDER",
    "AI_GATEWAY_REMOTE_URL",
    "AI_GATEWAY_TIMEOUT_SEC",
]


def _clear_gateway_env() -> dict[str, str]:
    old = {key: os.environ[key] for key in GATEWAY_ENV if key in os.environ}
    for key in GATEWAY_ENV:
        os.environ.pop(key, None)
    return old


def _restore_gateway_env(old: dict[str, str]) -> None:
    for key in GATEWAY_ENV:
        os.environ.pop(key, None)
    os.environ.update(old)


def _load_module(path: Path):
    name = "gateway_conformance_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    before_env = {key: os.environ.get(key) for key in GATEWAY_ENV}
    sys.modules[name] = module
    spec.loader.exec_module(module)
    after_env = {key: os.environ.get(key) for key in GATEWAY_ENV}
    assert before_env == after_env, f"import mutated gateway env: {path}"
    return module


async def _assert_async_legacy(gateway, expected_label: str) -> None:
    calls: list[str] = []

    async def legacy_call() -> dict[str, str]:
        calls.append(expected_label)
        return {"path": expected_label}

    result = await gateway.run_async(f"conformance.{expected_label}.async", legacy_call)
    assert result == {"path": expected_label}
    assert calls == [expected_label]


def _assert_sync_legacy(gateway, expected_label: str) -> None:
    calls: list[str] = []

    def legacy_call() -> dict[str, str]:
        calls.append(expected_label)
        return {"path": expected_label}

    result = gateway.run_sync(f"conformance.{expected_label}.sync", legacy_call)
    assert result == {"path": expected_label}
    assert calls == [expected_label]


async def _assert_remote_timeout_fallback(gateway) -> None:
    sync_calls: list[str] = []
    async_calls: list[str] = []

    def sync_legacy() -> dict[str, str]:
        sync_calls.append("legacy")
        return {"path": "legacy"}

    def sync_remote() -> dict[str, str]:
        sync_calls.append("remote")
        time.sleep(0.2)
        return {"path": "remote"}

    async def async_legacy() -> dict[str, str]:
        async_calls.append("legacy")
        return {"path": "legacy"}

    async def async_remote() -> dict[str, str]:
        async_calls.append("remote")
        await asyncio.sleep(0.2)
        return {"path": "remote"}

    os.environ["AI_GATEWAY_ENABLED"] = "true"
    os.environ["AI_GATEWAY_PROVIDER"] = "remote"
    os.environ["AI_GATEWAY_TIMEOUT_SEC"] = "0.01"

    assert gateway.run_sync("conformance.remote.sync_timeout", sync_legacy, remote_call=sync_remote) == {"path": "legacy"}
    assert await gateway.run_async(
        "conformance.remote.async_timeout",
        async_legacy,
        remote_call=async_remote,
    ) == {"path": "legacy"}
    assert sync_calls[:2] == ["remote", "legacy"]
    assert async_calls == ["remote", "legacy"]


async def _check_wrapper(path: Path) -> None:
    old_env = _clear_gateway_env()
    try:
        module = _load_module(path)
        gateway = module.AIGateway()

        _assert_sync_legacy(gateway, "disabled")
        await _assert_async_legacy(gateway, "disabled")

        os.environ["AI_GATEWAY_ENABLED"] = "true"
        os.environ["AI_GATEWAY_PROVIDER"] = "legacy"
        _assert_sync_legacy(gateway, "enabled_legacy")
        await _assert_async_legacy(gateway, "enabled_legacy")

        os.environ["AI_GATEWAY_PROVIDER"] = "unknown"
        _assert_sync_legacy(gateway, "unknown_provider")
        await _assert_async_legacy(gateway, "unknown_provider")

        await _assert_remote_timeout_fallback(gateway)
    finally:
        _restore_gateway_env(old_env)


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    for wrapper in WRAPPERS:
        await _check_wrapper(wrapper)
    print("AI Gateway wrapper conformance OK")


if __name__ == "__main__":
    asyncio.run(main())
