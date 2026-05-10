from __future__ import annotations

import logging
from pathlib import Path
import shutil
import uuid

import pytest

from app.services.document_input_policy import (
    DOCUMENT_CAPABLE_INPUTS,
    INTENTIONALLY_PLAIN_TEXT_ONLY_ROUTES,
    DocumentInputRouteError,
    resolve_document_capable_input,
)


@pytest.fixture
def work_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / "_pytest_document_input_policy"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_document_capable_policy_allowlist_contract():
    assert {k: v.field_name for k, v in DOCUMENT_CAPABLE_INPUTS.items()} == {
        "legal_claim_review": "claim_text",
        "legal_claim_draft": "claim_text",
        "legal_claim_compose": "facts",
        "freight_document_check": "document_text",
        "freight_transport_order_compose": "request_text",
    }


def test_plain_text_only_routes_contract():
    assert INTENTIONALLY_PLAIN_TEXT_ONLY_ROUTES == (
        "freight_risk_check",
        "freight_route_advice",
        "query",
    )


def test_resolve_document_capable_input_rejects_unknown_route():
    with pytest.raises(ValueError, match="not document-capable"):
        resolve_document_capable_input("text", route_label="freight_risk_check", logger=logging.getLogger("test"))


def test_resolve_document_capable_input_plain_text_logs_standard_shape(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="document-policy-test")
    logger = logging.getLogger("document-policy-test")
    sensitive_text = "Контрагент просрочил оплату по договору поставки."

    text, info = resolve_document_capable_input(
        sensitive_text,
        route_label="legal_claim_review",
        logger=logger,
    )

    assert text == sensitive_text
    assert info["route_mode"] == "plain_text_direct"
    assert info["field_name"] == "claim_text"
    assert info["preview"] is None
    assert "document_input route=legal_claim_review field=claim_text mode=plain_text" in caplog.text
    assert sensitive_text not in caplog.text


def test_resolve_document_capable_input_document_logs_standard_shape(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    caplog.set_level(logging.INFO, logger="document-policy-test")
    logger = logging.getLogger("document-policy-test")
    txt_path = work_dir / "claim.txt"
    sensitive_text = "Претензия: сумма 100 000 руб., срок оплаты нарушен."
    txt_path.write_text(sensitive_text, encoding="utf-8")

    text, info = resolve_document_capable_input(
        str(txt_path),
        route_label="legal_claim_review",
        logger=logger,
    )

    assert "100 000 руб." in text
    assert info["route_mode"] == "document_pipeline_extract_then_rag"
    assert info["document_type"] == "txt"
    assert info["field_name"] == "claim_text"
    assert info["preview"] is None
    assert info["source_file_name"] == "claim.txt"
    assert "document_input route=legal_claim_review field=claim_text mode=document_pipeline" in caplog.text
    assert sensitive_text not in caplog.text


def test_document_path_outside_configured_root_is_rejected(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    allowed_root = work_dir / "allowed"
    allowed_root.mkdir()
    outside = work_dir / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(allowed_root))

    with pytest.raises(DocumentInputRouteError) as exc_info:
        resolve_document_capable_input(
            str(outside),
            route_label="legal_claim_review",
            logger=logging.getLogger("test"),
        )

    assert exc_info.value.code == "document_path_outside_root"


def test_relative_path_traversal_outside_root_is_rejected(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    allowed_root = work_dir / "allowed"
    allowed_root.mkdir()
    outside = work_dir / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(allowed_root))

    with pytest.raises(DocumentInputRouteError) as exc_info:
        resolve_document_capable_input(
            "../outside.txt",
            route_label="legal_claim_review",
            logger=logging.getLogger("test"),
        )

    assert exc_info.value.code == "document_path_outside_root"


def test_symlink_escape_outside_root_is_rejected(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    allowed_root = work_dir / "allowed"
    allowed_root.mkdir()
    outside = work_dir / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = allowed_root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink not available")
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(allowed_root))

    with pytest.raises(DocumentInputRouteError) as exc_info:
        resolve_document_capable_input(
            str(link),
            route_label="legal_claim_review",
            logger=logging.getLogger("test"),
        )

    assert exc_info.value.code == "document_path_outside_root"


def test_tilde_input_is_not_expanded(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))

    with pytest.raises(DocumentInputRouteError) as exc_info:
        resolve_document_capable_input(
            "~/.ssh/id_rsa.txt",
            route_label="legal_claim_review",
            logger=logging.getLogger("test"),
        )

    assert exc_info.value.code == "file_not_found"


@pytest.mark.parametrize("raw_input", ["../../etc/passwd", "/etc/passwd", "~/.ssh/id_rsa"])
def test_unsupported_suffix_path_like_input_is_plain_text_not_file_read(
    raw_input: str,
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))

    text, info = resolve_document_capable_input(
        raw_input,
        route_label="legal_claim_review",
        logger=logging.getLogger("test"),
    )

    assert text == raw_input
    assert info["route_mode"] == "plain_text_direct"
