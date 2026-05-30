from __future__ import annotations

import logging
from typing import Optional

from app.schemas.trust import TrustProfileInternal, TrustProfilePublic, TrustStatus
from app.services.trust import cache as trust_cache
from app.services.trust import db_repository

logger = logging.getLogger(__name__)

_CACHE_TTL = 60.0


def _empty_public(subject_type: str, subject_id: str) -> TrustProfilePublic:
    return TrustProfilePublic(subject_type=subject_type, subject_id=subject_id, status=TrustStatus.empty)


def _empty_internal(subject_type: str, subject_id: str) -> TrustProfileInternal:
    return TrustProfileInternal(subject_type=subject_type, subject_id=subject_id, status=TrustStatus.empty)


def _failed_public(subject_type: str, subject_id: str) -> TrustProfilePublic:
    return TrustProfilePublic(subject_type=subject_type, subject_id=subject_id, status=TrustStatus.failed)


def _failed_internal(subject_type: str, subject_id: str) -> TrustProfileInternal:
    return TrustProfileInternal(subject_type=subject_type, subject_id=subject_id, status=TrustStatus.failed)


def _load(subject_type: str, subject_id: str) -> Optional[TrustProfileInternal]:
    key = trust_cache.cache_key(subject_type, subject_id)
    cached = trust_cache.get(key)
    if cached is not None:
        return cached
    profile = db_repository.get_profile(subject_type, subject_id)
    if profile is not None:
        trust_cache.set(key, profile, ttl_seconds=_CACHE_TTL)
    return profile


def get_public_profile(subject_type: str, subject_id: str) -> TrustProfilePublic:
    try:
        profile = _load(subject_type, subject_id)
    except Exception as exc:
        logger.warning("trust get_public_profile error %s/%s: %s", subject_type, subject_id, exc)
        return _failed_public(subject_type, subject_id)
    if profile is None:
        return _empty_public(subject_type, subject_id)
    return TrustProfilePublic(
        subject_type=profile.subject_type,
        subject_id=profile.subject_id,
        trust_score=profile.trust_score,
        trust_level=profile.trust_level,
        status=profile.status,
        verdict=profile.verdict,
        positives=profile.positives,
        warnings=profile.warnings,
        checked_at=profile.checked_at,
        expires_at=profile.expires_at,
        can_refresh=profile.can_refresh,
        is_premium=profile.is_premium,
        full_report=profile.full_report,
    )


def get_internal_profile(subject_type: str, subject_id: str) -> TrustProfileInternal:
    try:
        profile = _load(subject_type, subject_id)
    except Exception as exc:
        logger.warning("trust get_internal_profile error %s/%s: %s", subject_type, subject_id, exc)
        return _failed_internal(subject_type, subject_id)
    if profile is None:
        return _empty_internal(subject_type, subject_id)
    return profile


def invalidate_cache(subject_type: str, subject_id: str) -> None:
    trust_cache.delete(trust_cache.cache_key(subject_type, subject_id))
