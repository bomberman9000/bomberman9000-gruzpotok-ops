from app.services.notifications.high_priority import render_high_priority_alert


def test_render_empty():
    t = render_high_priority_alert([])
    assert "нет элементов" in t.lower() or "queue" in t.lower()


def test_render_lines():
    items = [
        {
            "call_id": 1,
            "persona": "legal",
            "normalized_status": "ok",
            "priority_score": 90.0,
            "priority_reasons": ["persona=legal", "risk=high"],
        }
    ]
    t = render_high_priority_alert(items)
    assert "1" in t
    assert "legal" in t
