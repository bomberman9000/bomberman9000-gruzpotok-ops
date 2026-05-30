from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.schemas.trust import TrustLevel, TrustProfileInternal, TrustProfilePublic, TrustStatus

_PROFILES = [
    {
        "trust_score": 85,
        "trust_level": TrustLevel.excellent,
        "verdict": "Можно работать",
        "positives": ["Работает 7+ лет", "Нет судебных исков", "Официальный сайт подтверждён"],
        "warnings": [],
        "internal_flags": [],
    },
    {
        "trust_score": 68,
        "trust_level": TrustLevel.good,
        "verdict": "Надёжный контрагент",
        "positives": ["Работает 3 года", "Чистая кредитная история"],
        "warnings": ["Небольшой уставный капитал"],
        "internal_flags": ["low_capital"],
    },
    {
        "trust_score": 52,
        "trust_level": TrustLevel.caution,
        "verdict": "Нужна осторожность",
        "positives": ["Работает 2 года"],
        "warnings": ["Минимальный уставный капитал", "Официальный сайт не найден"],
        "internal_flags": ["low_capital", "no_website"],
    },
    {
        "trust_score": 35,
        "trust_level": TrustLevel.elevated,
        "verdict": "Повышенный риск",
        "positives": [],
        "warnings": ["Зарегистрирована менее 1 года", "Адрес массовой регистрации"],
        "internal_flags": ["new_company", "mass_address"],
    },
    {
        "trust_score": 18,
        "trust_level": TrustLevel.high_risk,
        "verdict": "Высокий риск",
        "positives": [],
        "warnings": ["Зарегистрирована менее 1 года", "Массовый адрес", "Иски в арбитраже"],
        "internal_flags": ["new_company", "mass_address", "arbitrage_claims"],
    },
]


def _bucket(subject_id: str) -> int:
    digest = hashlib.md5(subject_id.encode(), usedforsecurity=False).digest()
    return int.from_bytes(digest[:4], "big") % len(_PROFILES)


def get_public_profile(subject_type: str, subject_id: str) -> TrustProfilePublic:
    p = _PROFILES[_bucket(subject_id)]
    now = datetime.now(tz=timezone.utc)
    return TrustProfilePublic(
        subject_type=subject_type,
        subject_id=subject_id,
        trust_score=p["trust_score"],
        trust_level=p["trust_level"],
        status=TrustStatus.fresh,
        verdict=p["verdict"],
        positives=p["positives"],
        warnings=p["warnings"],
        checked_at=now.isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat(),
        can_refresh=False,
        is_premium=False,
        full_report=None,
    )


def get_internal_profile(subject_type: str, subject_id: str) -> TrustProfileInternal:
    p = _PROFILES[_bucket(subject_id)]
    now = datetime.now(tz=timezone.utc)
    return TrustProfileInternal(
        subject_type=subject_type,
        subject_id=subject_id,
        trust_score=p["trust_score"],
        trust_level=p["trust_level"],
        status=TrustStatus.fresh,
        verdict=p["verdict"],
        positives=p["positives"],
        warnings=p["warnings"],
        checked_at=now.isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat(),
        can_refresh=False,
        is_premium=False,
        full_report=None,
        source="p1_deterministic_stub",
        report_version="0.1",
        internal_flags=p["internal_flags"],
        agent_run_id=None,
        refresh_count_24h=0,
    )
