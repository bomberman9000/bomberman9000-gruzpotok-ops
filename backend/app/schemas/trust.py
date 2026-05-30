from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


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


class TrustRefreshRequest(BaseModel):
    subject_type: SubjectType
    subject_id: str
    priority: str = "normal"


class TrustRefreshResponse(BaseModel):
    queued: bool = False
    estimated_seconds: Optional[int] = None
    run_id: Optional[str] = None
    status: str = "stub"
