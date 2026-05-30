from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.db.pool import get_conn
from app.schemas.trust import TrustLevel, TrustProfileInternal, TrustStatus

logger = logging.getLogger(__name__)


def normalize_subject_id(subject_id: str) -> str:
    return subject_id.strip().lower()


def _resolve_status(status: str, expires_at: Optional[datetime]) -> TrustStatus:
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(tz=timezone.utc):
            return TrustStatus.stale
    try:
        return TrustStatus(status)
    except ValueError:
        return TrustStatus.empty


def get_profile(subject_type: str, subject_id: str) -> Optional[TrustProfileInternal]:
    sid = normalize_subject_id(subject_id)
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT subject_type, subject_id, trust_score, trust_level, status,
                       verdict, positives, warnings, internal_flags, source,
                       report_version, agent_run_id, checked_at, expires_at
                FROM trust_profiles
                WHERE subject_type = %s AND subject_id = %s
                """,
                (subject_type, sid),
            )
            row = cur.fetchone()
            cur.close()
    except Exception as exc:
        logger.warning("trust DB get_profile error subject=%s/%s: %s", subject_type, sid, exc)
        return None

    if row is None:
        return None

    (
        st, si, score, level, status, verdict,
        positives, warnings, internal_flags, source,
        report_version, agent_run_id, checked_at, expires_at,
    ) = row

    return TrustProfileInternal(
        subject_type=st,
        subject_id=si,
        trust_score=score,
        trust_level=TrustLevel(level) if level else None,
        status=_resolve_status(status, expires_at),
        verdict=verdict,
        positives=positives if isinstance(positives, list) else (json.loads(positives) if positives else []),
        warnings=warnings if isinstance(warnings, list) else (json.loads(warnings) if warnings else []),
        internal_flags=internal_flags if isinstance(internal_flags, list) else (json.loads(internal_flags) if internal_flags else []),
        source=source,
        report_version=report_version,
        agent_run_id=agent_run_id,
        checked_at=checked_at.isoformat() if checked_at else None,
        expires_at=expires_at.isoformat() if expires_at else None,
        can_refresh=False,
        is_premium=False,
        full_report=None,
        refresh_count_24h=0,
    )


def upsert_profile(profile: TrustProfileInternal) -> None:
    sid = normalize_subject_id(profile.subject_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO trust_profiles (
                subject_type, subject_id, trust_score, trust_level, status,
                verdict, positives, warnings, internal_flags, source,
                report_version, agent_run_id, checked_at, expires_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                      %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (subject_type, subject_id) DO UPDATE SET
                trust_score    = EXCLUDED.trust_score,
                trust_level    = EXCLUDED.trust_level,
                status         = EXCLUDED.status,
                verdict        = EXCLUDED.verdict,
                positives      = EXCLUDED.positives,
                warnings       = EXCLUDED.warnings,
                internal_flags = EXCLUDED.internal_flags,
                source         = EXCLUDED.source,
                report_version = EXCLUDED.report_version,
                agent_run_id   = EXCLUDED.agent_run_id,
                checked_at     = EXCLUDED.checked_at,
                expires_at     = EXCLUDED.expires_at,
                updated_at     = NOW()
            """,
            (
                profile.subject_type,
                sid,
                profile.trust_score,
                profile.trust_level.value if profile.trust_level else None,
                profile.status.value,
                profile.verdict,
                json.dumps(profile.positives),
                json.dumps(profile.warnings),
                json.dumps(profile.internal_flags),
                profile.source,
                profile.report_version,
                profile.agent_run_id,
                profile.checked_at,
                profile.expires_at,
            ),
        )
        cur.close()
