import json

import pytest

from app.services.json_extract import (
    parse_claim_review_model_output,
    parse_json_object,
)


def test_parse_json_object_raw_decode_with_trailing_junk():
    payload = '{"summary":"ok","legal_risks":[]}'
    text = payload + "\n\n(конец)"
    out = parse_json_object(text)
    assert out["summary"] == "ok"


def test_parse_claim_review_unwraps_json_string_in_summary():
    inner = {
        "summary": "Краткое резюме по претензии.",
        "legal_risks": ["Риск один"],
        "missing_information": ["Нужен расчёт"],
        "recommended_position": "Запросить документы",
    }
    outer = {"summary": json.dumps(inner, ensure_ascii=False)}
    text = json.dumps(outer, ensure_ascii=False)
    out = parse_claim_review_model_output(text)
    assert out["summary"] == "Краткое резюме по претензии."
    assert out["legal_risks"] == ["Риск один"]


def test_parse_json_object_rejects_non_object():
    with pytest.raises(ValueError):
        parse_json_object("[1,2,3]")


def test_parse_json_object_repairs_missing_closing_brace():
    truncated = (
        '{"summary":"x","legal_risks":[],"missing_information":[],"recommended_position":"y"'
    )
    out = parse_json_object(truncated)
    assert out["summary"] == "x"
    assert out["recommended_position"] == "y"
