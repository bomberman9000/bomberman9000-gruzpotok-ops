-- Trust profiles storage (P2).
-- Idempotent: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS trust_profiles (
    id              BIGSERIAL PRIMARY KEY,
    subject_type    TEXT NOT NULL,
    subject_id      TEXT NOT NULL,
    trust_score     INTEGER,
    trust_level     TEXT,
    status          TEXT NOT NULL DEFAULT 'empty',
    verdict         TEXT,
    positives       JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings        JSONB NOT NULL DEFAULT '[]'::jsonb,
    internal_flags  JSONB NOT NULL DEFAULT '[]'::jsonb,
    source          TEXT,
    report_version  TEXT,
    agent_run_id    TEXT,
    checked_at      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trust_profiles_subject UNIQUE (subject_type, subject_id),
    CONSTRAINT chk_trust_subject_type CHECK (subject_type IN ('company','carrier','shipper','user','claim','freight')),
    CONSTRAINT chk_trust_level CHECK (trust_level IS NULL OR trust_level IN ('excellent','good','caution','elevated','high_risk')),
    CONSTRAINT chk_trust_status CHECK (status IN ('fresh','stale','empty','pending','failed')),
    CONSTRAINT chk_trust_score CHECK (trust_score IS NULL OR trust_score BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS trust_profiles_subject_idx ON trust_profiles (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS trust_profiles_expires_idx ON trust_profiles (expires_at);
CREATE INDEX IF NOT EXISTS trust_profiles_level_idx   ON trust_profiles (trust_level);
