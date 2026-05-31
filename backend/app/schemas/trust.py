from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, StringConstraints, model_validator


class SubjectType(str, Enum):
    company = "company"
    carrier = "carrier"
    shipper = "shipper"
    user = "user"
    claim = "claim"
    freight = "freight"


class TrustLevel(str, Enum):
    excellent = "excellent"
    good = "good"
    caution = "caution"
    elevated = "elevated"
    high_risk = "high_risk"


class TrustStatus(str, Enum):
    fresh = "fresh"
    stale = "stale"
    empty = "empty"
    pending = "pending"
    failed = "failed"


class TrustProfilePublic(BaseModel):
    subject_type: str
    subject_id: str
    trust_score: Optional[int] = None
    trust_level: Optional[TrustLevel] = None
    status: TrustStatus = TrustStatus.empty
    verdict: Optional[str] = None
    positives: list[str] = []
    warnings: list[str] = []
    checked_at: Optional[str] = None
    expires_at: Optional[str] = None
    can_refresh: bool = False
    is_premium: bool = False
    full_report: Optional[str] = None


class TrustProfileInternal(TrustProfilePublic):
    source: Optional[str] = None
    report_version: Optional[str] = None
    internal_flags: list[str] = []
    agent_run_id: Optional[str] = None
    refresh_count_24h: int = 0


# Item-level constraint shared by all list fields on the write request.
_TrustListItem = Annotated[str, StringConstraints(max_length=240)]


class TrustProfileWriteRequest(BaseModel):
    """Internal AI write payload for a trust profile.

    Used only by the internal write path; never exposed on the public surface.
    """

    trust_score: int = Field(ge=0, le=100)
    trust_level: TrustLevel
    verdict: Annotated[str, StringConstraints(max_length=500)]
    positives: list[_TrustListItem] = Field(default_factory=list, max_length=10)
    warnings: list[_TrustListItem] = Field(default_factory=list, max_length=10)
    internal_flags: list[_TrustListItem] = Field(default_factory=list, max_length=10)
    source: Optional[Annotated[str, StringConstraints(max_length=80)]] = None
    report_version: Optional[Annotated[str, StringConstraints(max_length=32)]] = None
    agent_run_id: Optional[Annotated[str, StringConstraints(max_length=128)]] = None
    checked_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def _expires_after_checked(self) -> "TrustProfileWriteRequest":
        if self.expires_at <= self.checked_at:
            raise ValueError("expires_at must be after checked_at")
        return self


class TrustRefreshRequest(BaseModel):
    subject_type: SubjectType
    subject_id: str
    priority: str = "normal"


class TrustRefreshResponse(BaseModel):
    queued: bool = False
    estimated_seconds: Optional[int] = None
    run_id: Optional[str] = None
    status: str = "stub"
