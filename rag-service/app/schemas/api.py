from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


PersonaId = Literal["legal", "logistics", "antifraud"]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    mode: Literal["balanced", "strict", "draft"] | None = Field(
        default=None,
        description="Если не указан и задана persona — берётся default_mode персоны; иначе balanced.",
    )
    persona: PersonaId | None = Field(
        default=None,
        description="Роль ГрузПотока: правила фильтров, промпт и guardrails retrieval.",
    )
    category: Literal["legal", "freight", "general"] | None = Field(default=None)
    source_type: Literal["law", "contract", "template", "internal", "other"] | None = Field(
        default=None
    )
    top_k: int | None = Field(default=None, ge=1, le=100)
    final_k: int | None = Field(default=None, ge=1, le=50)
    debug: bool = Field(default=False)


class CitationItem(BaseModel):
    document_id: str
    file_name: str
    source_path: str
    section_title: str | None = None
    article_ref: str | None = None
    chunk_index: int
    chunk_id: int
    excerpt: str = Field(..., description="Short excerpt from chunk")


class RetrievalDebug(BaseModel):
    top_k: int
    final_k: int
    used_chunks: int
    normalized_query: str
    scores: list[dict[str, Any]] | None = None
    persona: PersonaId | str | None = None
    applied_filters: dict[str, Any] | None = None
    prompt_template_used: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    retrieval_debug: RetrievalDebug | None = None
    model: str
    mode: str
    persona: PersonaId | None = None
    llm_invoked: bool = Field(
        default=False,
        description="False если ответ сформирован без вызова LLM (строгий отказ или пустая база)",
    )


class SeedResponse(BaseModel):
    ingestion_run_id: int
    status: str
    files_seen: int
    files_indexed: int
    files_skipped: int
    documents_deactivated: int = Field(
        default=0,
        description="Число активных документов, помеченных неактивными (исключённые из индексации пути, например examples/freight/).",
    )
    errors: list[str]


class DocumentListItem(BaseModel):
    id: str
    source_path: str
    file_name: str
    category: str
    source_type: str
    title: str | None
    checksum: str
    imported_at: str | None
    is_active: bool
    chunk_count: int | None = None


class ChunkMetadata(BaseModel):
    id: int
    chunk_index: int
    token_count: int | None = None
    section_title: str | None = None
    article_ref: str | None = None
    page_ref: str | None = None
    excerpt: str = Field(..., description="Начало текста чанка (превью)")


class DocumentDetail(BaseModel):
    id: str
    source_path: str
    file_name: str
    category: str
    source_type: str
    title: str | None
    checksum: str
    last_updated_at: str | None
    imported_at: str | None
    version_tag: str | None
    is_active: bool
    metadata_json: dict[str, Any]
    chunks: list[ChunkMetadata] = Field(default_factory=list)


class StatsResponse(BaseModel):
    active_documents_count: int
    inactive_documents_count: int
    chunks_count: int
    documents_by_category: dict[str, int]
    documents_by_source_type: dict[str, int]
    last_ingestion_status: str | None
    last_ingestion_finished_at: str | None
    # Обратная совместимость (дублируют смысл новых полей)
    documents_total: int = Field(description="= active_documents_count")
    chunks_total: int = Field(description="= chunks_count")
    last_ingestion_runs: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool | None
    ollama_reachable: bool
    documents_active: int
    chunks_total: int
    ollama_base_url: str


class LegacyAskBody(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    category: str | None = None


# --- ГрузПоток: прикладные endpoints ---

RiskLevel = Literal["low", "medium", "high"]


class LegalClaimReviewRequest(BaseModel):
    claim_text: str = Field(..., min_length=1, max_length=16000)
    contract_context: str = Field(default="", max_length=32000)
    counterparty: str = Field(default="", max_length=2000)
    debug: bool = False


class LegalClaimReviewResponse(BaseModel):
    summary: str
    legal_risks: list[str]
    missing_information: list[str]
    recommended_position: str
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str
    retrieval_debug: RetrievalDebug | None = None


class LegalClaimDraftRequest(BaseModel):
    claim_text: str = Field(..., min_length=1, max_length=16000)
    company_name: str = Field(default="", max_length=500)
    signer: str = Field(default="", max_length=500)
    mode: Literal["draft"] = "draft"


class LegalClaimDraftResponse(BaseModel):
    draft_response_text: str
    tone: str
    legal_basis: list[str]
    disclaimers: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str


class LegalClaimComposeRequest(BaseModel):
    """Черновик исходящей претензии (от нашей стороны к контрагенту)."""

    facts: str = Field(..., min_length=1, max_length=32000)
    contract_context: str = Field(default="", max_length=32000)
    claimant_company: str = Field(default="", max_length=500)
    counterparty: str = Field(default="", max_length=2000)
    counterparty_address: str = Field(default="", max_length=2000)
    demands: str = Field(default="", max_length=8000)
    attachments_note: str = Field(default="", max_length=4000)


class LegalClaimComposeResponse(BaseModel):
    draft_claim_text: str
    missing_facts: list[str]
    disclaimers: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str


class FreightRiskCheckRequest(BaseModel):
    situation: str = Field(..., min_length=1, max_length=16000)
    counterparty_info: str = Field(default="", max_length=8000)
    route: str = Field(default="", max_length=4000)
    debug: bool = False


class FreightRiskCheckResponse(BaseModel):
    risk_level: RiskLevel
    red_flags: list[str]
    recommended_checks: list[str]
    suggested_next_steps: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str
    retrieval_debug: RetrievalDebug | None = None


class FreightRouteAdviceRequest(BaseModel):
    route_request: str = Field(default="", max_length=8000)
    vehicle: str = Field(default="", max_length=2000)
    cargo: str = Field(default="", max_length=4000)
    constraints: str = Field(default="", max_length=8000)


class FreightRouteAdviceResponse(BaseModel):
    summary: str
    operational_advice: list[str]
    missing_information: list[str]
    risks: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str
    retrieval_debug: RetrievalDebug | None = None


class FreightDocumentCheckRequest(BaseModel):
    document_text: str = Field(..., min_length=1, max_length=64000)
    document_type: str = Field(default="", max_length=500)
    debug: bool = False


class FreightDocumentCheckResponse(BaseModel):
    detected_issues: list[str]
    missing_fields: list[str]
    recommended_fixes: list[str]
    compliance_notes: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str
    retrieval_debug: RetrievalDebug | None = None


class FreightTransportOrderFields(BaseModel):
    """Поля заявки на перевозку / договора-заявки (текстовые строки для PDF)."""

    pdf_template: Literal["simple", "dogovor_zayavka"] = Field(
        default="dogovor_zayavka",
        description="dogovor_zayavka — макет как типовой договор-заявка на разовую перевозку; simple — короткая форма.",
    )
    document_title: str = Field(default="Заявка на перевозку груза", max_length=500)
    order_number: str = Field(default="", max_length=200)
    order_date: str = Field(default="", max_length=200)
    customer_name: str = Field(default="", max_length=1000)
    customer_representative_position: str = Field(
        default="",
        max_length=500,
        description="Должность подписанта заказчика, напр. «генерального директора»",
    )
    customer_representative_name: str = Field(
        default="",
        max_length=500,
        description="ФИО подписанта заказчика",
    )
    customer_inn_kpp: str = Field(default="", max_length=200)
    customer_inn: str = Field(default="", max_length=20)
    customer_kpp: str = Field(default="", max_length=20)
    customer_ogrn: str = Field(default="", max_length=20)
    customer_rs: str = Field(default="", max_length=50)
    customer_bank: str = Field(default="", max_length=500)
    customer_bik: str = Field(default="", max_length=20)
    customer_ks: str = Field(default="", max_length=50)
    customer_legal_city: str = Field(default="", max_length=200)
    customer_address: str = Field(default="", max_length=2000)
    customer_phone: str = Field(default="", max_length=200)
    customer_contact: str = Field(default="", max_length=500)
    carrier_name: str = Field(default="", max_length=1000)
    carrier_details: str = Field(default="", max_length=2000)
    carrier_legal_address: str = Field(default="", max_length=2000)
    carrier_inn: str = Field(default="", max_length=20)
    carrier_kpp: str = Field(default="", max_length=20)
    carrier_ogrn: str = Field(default="", max_length=20)
    carrier_rs: str = Field(default="", max_length=50)
    carrier_bank: str = Field(default="", max_length=500)
    carrier_bik: str = Field(default="", max_length=20)
    carrier_ks: str = Field(default="", max_length=50)
    route_description: str = Field(default="", max_length=2000)
    loading_unloading_method: str = Field(default="", max_length=500)
    shipper_contact: str = Field(default="", max_length=1000)
    consignee_contact: str = Field(default="", max_length=1000)
    loading_address: str = Field(default="", max_length=2000)
    loading_datetime: str = Field(default="", max_length=500)
    unloading_address: str = Field(default="", max_length=2000)
    unloading_datetime: str = Field(default="", max_length=500)
    delivery_deadline: str = Field(default="", max_length=500)
    cargo_name: str = Field(default="", max_length=4000)
    cargo_weight: str = Field(default="", max_length=200)
    cargo_volume: str = Field(default="", max_length=200)
    cargo_places: str = Field(default="", max_length=200)
    packaging: str = Field(default="", max_length=1000)
    vehicle_requirements: str = Field(default="", max_length=2000)
    vehicle_plate: str = Field(default="", max_length=100)
    driver_passport_phone: str = Field(default="", max_length=500)
    price_terms: str = Field(default="", max_length=2000)
    payment_deadline: str = Field(default="", max_length=500)
    ati_code: str = Field(default="", max_length=50)
    logist_name: str = Field(default="", max_length=300)
    additional_terms: str = Field(default="", max_length=8000)


class FreightTransportOrderPdfRequest(FreightTransportOrderFields):
    pdf_engine: Literal["fpdf", "libreoffice"] = Field(
        default="fpdf",
        description="fpdf — встроенная вёрстка; libreoffice — HTML→PDF через LibreOffice (soffice --headless) на сервере/ПК.",
    )

    @model_validator(mode="after")
    def _min_content_for_pdf(self) -> Self:
        blob = " ".join(
            [
                self.customer_name,
                self.loading_address,
                self.unloading_address,
                self.cargo_name,
                self.customer_address,
                self.route_description,
            ]
        ).strip()
        if len(blob) < 10:
            raise ValueError(
                "Недостаточно данных для PDF: укажите заказчика, маршрут (погрузка/выгрузка) "
                "и/или описание груза (не менее нескольких содержательных полей)."
            )
        return self


class FreightTransportOrderComposeRequest(BaseModel):
    request_text: str = Field(..., min_length=1, max_length=16000)
    debug: bool = False


class FreightTransportOrderComposeResponse(BaseModel):
    fields: FreightTransportOrderFields
    missing_information: list[str]
    citations: list[CitationItem]
    llm_invoked: bool
    persona: PersonaId
    mode: str
    retrieval_debug: RetrievalDebug | None = None
