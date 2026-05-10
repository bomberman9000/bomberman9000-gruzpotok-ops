#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import os
import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GATEWAY_MODULES = [
    ROOT / "goutruckme-git/app/ai/gateway.py",
    ROOT / "goutruckme-api/src/core/services/ai_gateway.py",
    ROOT / "backend/app/services/ai/gateway_wrapper.py",
]

COMPILE_TARGETS = [
    *GATEWAY_MODULES,
    ROOT / "goutruckme-git/app/ai/ai_service.py",
    ROOT / "goutruckme-api/src/core/services/ai_service.py",
    ROOT / "backend/app/services/ai/gateway.py",
]


def _load_module(path: Path):
    name = "phase1a_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


async def _check_async_legacy(gateway) -> None:
    called: list[str] = []

    async def legacy_call() -> dict[str, str]:
        called.append("legacy")
        return {"path": "legacy"}

    result = await gateway.run_async("phase1a.smoke.async", legacy_call)
    assert result == {"path": "legacy"}
    assert called == ["legacy"]


def _check_sync_legacy(gateway) -> None:
    called: list[str] = []

    def legacy_call() -> dict[str, str]:
        called.append("legacy")
        return {"path": "legacy"}

    result = gateway.run_sync("phase1a.smoke.sync", legacy_call)
    assert result == {"path": "legacy"}
    assert called == ["legacy"]


async def main() -> None:
    os.environ["AI_GATEWAY_ENABLED"] = "false"
    os.environ["AI_GATEWAY_PROVIDER"] = "remote"
    os.environ["AI_GATEWAY_REMOTE_URL"] = "http://127.0.0.1:9/unused"
    os.environ["AI_GATEWAY_TIMEOUT_SEC"] = "0.1"

    for target in COMPILE_TARGETS:
        py_compile.compile(str(target), doraise=True)

    for module_path in GATEWAY_MODULES:
        module = _load_module(module_path)
        gateway = module.AIGateway()
        _check_sync_legacy(gateway)
        await _check_async_legacy(gateway)

    print("AI Gateway Phase 1A smoke check OK")


if __name__ == "__main__":
    asyncio.run(main())
