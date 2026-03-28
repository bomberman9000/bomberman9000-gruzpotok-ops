from unittest.mock import MagicMock

from app.services.ingestion.runner import deactivate_excluded_source_documents


def test_deactivate_excluded_sums_rowcounts():
    cur = MagicMock()
    cur.rowcount = 1
    assert deactivate_excluded_source_documents(cur) == 1
    cur.execute.assert_called_once()
    args = cur.execute.call_args[0]
    assert "UPDATE documents" in args[0]
    assert args[1] == ("examples/freight/%",)
