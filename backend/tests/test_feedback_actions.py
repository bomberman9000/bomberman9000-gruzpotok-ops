from app.services.presentation.feedback_actions import quick_feedback_actions, standard_actions


def test_quick_actions_types():
    acts = quick_feedback_actions(request_id="rid-1")
    types = {a.type for a in acts}
    assert "mark_useful" in types
    assert "mark_not_useful" in types


def test_standard_has_open_citations():
    acts = standard_actions(
        request_id="rid-2",
        citations_count=2,
        retryable=True,
        status="unavailable",
    )
    types = [a.type for a in acts]
    assert "open_citations" in types
    assert "ask_more" in types
