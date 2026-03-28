from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityPresentationContext:
    entity_type: str | None = None
    entity_id: str | None = None
    scenario: str | None = None
    screen_hint: str | None = None


def context_from_gateway(
    *,
    endpoint: str,
    user_input: dict | None,
    request_id: str,
) -> EntityPresentationContext:
    """Из user_input internal-эндпоинтов и kind публичных."""
    ui = user_input or {}
    if ui.get("product_claim_id"):
        kind = ui.get("kind") or ""
        if "draft" in kind:
            return EntityPresentationContext(
                entity_type="claim",
                entity_id=str(ui["product_claim_id"]),
                scenario="claim_draft",
                screen_hint="claim_draft_panel",
            )
        return EntityPresentationContext(
            entity_type="claim",
            entity_id=str(ui["product_claim_id"]),
            scenario="claim_review",
            screen_hint="claim_review_panel",
        )
    if ui.get("product_load_id"):
        return EntityPresentationContext(
            entity_type="freight_load",
            entity_id=str(ui["product_load_id"]),
            scenario="freight_risk",
            screen_hint="freight_risk_panel",
        )
    if ui.get("product_document_id"):
        return EntityPresentationContext(
            entity_type="document",
            entity_id=str(ui["product_document_id"]),
            scenario="document_check",
            screen_hint="document_check_panel",
        )

    # Публичные сценарии по kind / endpoint
    kind = str(ui.get("kind") or "")
    if kind.startswith("claim_review") or endpoint == "claim_review":
        return EntityPresentationContext(scenario="claim_review", screen_hint="claim_review_panel")
    if kind.startswith("claim_draft") or endpoint == "claim_draft":
        return EntityPresentationContext(scenario="claim_draft", screen_hint="claim_draft_panel")
    if kind.startswith("risk_check") or endpoint == "risk_check":
        return EntityPresentationContext(scenario="freight_risk", screen_hint="freight_risk_panel")
    if kind.startswith("route_advice") or endpoint == "route_advice":
        return EntityPresentationContext(scenario="route_advice", screen_hint="freight_route_panel")
    if kind.startswith("document_check") or endpoint == "document_check":
        return EntityPresentationContext(scenario="document_check", screen_hint="document_check_panel")
    if kind.startswith("transport_order_compose") or endpoint == "transport_order_compose":
        return EntityPresentationContext(
            scenario="transport_order_compose",
            screen_hint="transport_order_pdf_panel",
        )
    if endpoint == "query":
        return EntityPresentationContext(scenario="query", screen_hint="ai_query_panel")

    _ = request_id
    return EntityPresentationContext()
