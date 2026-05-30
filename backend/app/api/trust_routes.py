from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.trust import SubjectType, TrustProfilePublic
from app.services.trust.profile_service import get_public_profile

router = APIRouter(prefix="/api/v1/trust", tags=["trust"])

_VALID_TYPES = {e.value for e in SubjectType}


@router.get("/profile/{subject_type}/{subject_id}", response_model=TrustProfilePublic)
async def trust_profile_public(subject_type: str, subject_id: str) -> TrustProfilePublic:
    if subject_type not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid subject_type: {subject_type!r}")
    return get_public_profile(subject_type, subject_id)
