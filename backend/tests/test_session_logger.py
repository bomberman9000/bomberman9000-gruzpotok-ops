from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.evals.session_logger import append_case, load_cases, save_cases


def test_load_save_roundtrip(tmp_path: Path):
    p = tmp_path / "log.json"
    save_cases([], path=p)
    assert load_cases(p) == []
    append_case(
        {
            "request_id": "r1",
            "endpoint": "e",
            "operator_action": "rejected",
            "reason_codes": ["too_generic"],
        },
        path=p,
    )
    cases = load_cases(p)
    assert len(cases) == 1
    assert cases[0]["request_id"] == "r1"
    assert cases[0]["reason_codes"] == ["too_generic"]
    assert "timestamp" in cases[0]


def test_load_legacy_list_format(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"request_id": "a", "reason_codes": ["x"]}]), encoding="utf-8")
    c = load_cases(p)
    assert len(c) == 1
    assert c[0]["request_id"] == "a"
