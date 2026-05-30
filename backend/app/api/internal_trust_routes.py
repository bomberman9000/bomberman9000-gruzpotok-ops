from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.trust import (
    SubjectType,
    TrustProfileInternal,
    TrustRefreshRequest,
    TrustRefreshResponse,
)
from app.services.trust.profile_service import get_internal_profile

router = APIRouter(prefix="/api/v1/internal/ai/trust", tags=["trust-internal"])

_VALID_TYPES = {e.value for e in SubjectType}


@router.get("/profile/{subject_type}/{subject_id}", response_model=TrustProfileInternal)
async def trust_profile_internal(subject_type: str, subject_id: str) -> TrustProfileInternal:
    if subject_type not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid subject_type: {subject_type!r}")
    return get_internal_profile(subject_type, subject_id)


@router.post("/refresh", response_model=TrustRefreshResponse)
async def trust_refresh_stub(body: TrustRefreshRequest) -> TrustRefreshResponse:
    return TrustRefreshResponse(queued=False, estimated_seconds=None, run_id=None, status="stub")
