-- Коды причин review / feedback (JSONB-массивы строк). Безопасно на существующей БД: IF NOT EXISTS.

ALTER TABLE ai_reviews ADD COLUMN IF NOT EXISTS review_reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE ai_feedback ADD COLUMN IF NOT EXISTS feedback_reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_ai_reviews_review_reason_codes_gin ON ai_reviews USING gin (review_reason_codes);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_feedback_reason_codes_gin ON ai_feedback USING gin (feedback_reason_codes);
