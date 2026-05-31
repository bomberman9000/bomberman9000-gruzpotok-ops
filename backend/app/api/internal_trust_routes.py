from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.trust import (
    SubjectType,
    TrustProfileInternal,
    TrustProfileWriteRequest,
    TrustRefreshRequest,
    TrustRefreshResponse,
)
from app.services.trust.profile_service import (
    get_internal_profile,
    invalidate_cache,
    write_profile,
)

router = APIRouter(prefix="/api/v1/internal/ai/trust", tags=["trust-internal"])

_VALID_TYPES = {e.value for e in SubjectType}


@router.get("/profile/{subject_type}/{subject_id}", response_model=TrustProfileInternal)
async def trust_profile_internal(subject_type: str, subject_id: str) -> TrustProfileInternal:
    if subject_type not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid subject_type: {subject_type!r}")
    return get_internal_profile(subject_type, subject_id)


@router.post("/profile/{subject_type}/{subject_id}", response_model=TrustProfileInternal)
async def trust_profile_write(
    subject_type: str, subject_id: str, body: TrustProfileWriteRequest
) -> TrustProfileInternal:
    if subject_type not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid subject_type: {subject_type!r}")
    return write_profile(subject_type, subject_id, body)


@router.post("/refresh", response_model=TrustRefreshResponse)
async def trust_refresh_stub(body: TrustRefreshRequest) -> TrustRefreshResponse:
    invalidate_cache(body.subject_type.value, body.subject_id)
    return TrustRefreshResponse(queued=False, estimated_seconds=None, run_id=None, status="stub")
