import type { TrustLevel, TrustProfile, TrustStatus } from "./types";

interface RawTrustProfile {
  subject_type: string;
  subject_id: string;
  trust_score: number | null;
  trust_level: string | null;
  status: string;
  verdict: string | null;
  positives: string[];
  warnings: string[];
  checked_at: string | null;
  expires_at: string | null;
  can_refresh: boolean;
  is_premium: boolean;
  full_report: string | null;
}

export function mapTrustProfile(raw: RawTrustProfile): TrustProfile {
  return {
    subjectType: raw.subject_type,
    subjectId: raw.subject_id,
    trustScore: raw.trust_score,
    trustLevel: (raw.trust_level as TrustLevel) ?? null,
    status: raw.status as TrustStatus,
    verdict: raw.verdict,
    positives: raw.positives ?? [],
    warnings: raw.warnings ?? [],
    checkedAt: raw.checked_at,
    expiresAt: raw.expires_at,
    canRefresh: raw.can_refresh ?? false,
    isPremium: raw.is_premium ?? false,
    fullReport: raw.full_report,
  };
}
