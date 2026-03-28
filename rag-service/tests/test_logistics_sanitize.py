from app.utils.logistics_sanitize import (
    is_ultra_general_pricing_query,
    sanitize_logistics_answer,
)


def test_ultra_general_detects_po_rossii():
    assert is_ultra_general_pricing_query("сколько стоит груз по россии") is True
    assert is_ultra_general_pricing_query("москва — спб 20 т") is False


def test_sanitize_strips_orientir_when_no_price():
    nq = "сколько стоит перевезти груз по россии"
    raw = "Ориентир: сведений мало. Уточните маршрут."
    out = sanitize_logistics_answer(raw, nq)
    assert out.startswith("Нужны уточнения:")
    assert "Ориентир:" not in out.split("\n")[0]


def test_sanitize_keeps_when_price_present():
    nq = "по россии"
    raw = "Ориентир: 10–20 тыс. руб. (условно)"
    assert sanitize_logistics_answer(raw, nq) == raw


def test_sanitize_noop_for_specific_route():
    nq = "самара — казань 3 т"
    raw = "Ориентир: 50–80 тыс."
    assert sanitize_logistics_answer(raw, nq) == raw
