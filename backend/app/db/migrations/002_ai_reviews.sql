-- Таблица review оператора по вызовам (одна строка на ai_call_id).

CREATE TABLE IF NOT EXISTS ai_reviews (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ai_call_id BIGINT NOT NULL REFERENCES ai_calls (id) ON DELETE CASCADE,
    request_id TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    scenario TEXT,
    operator_action TEXT NOT NULL,
    operator_comment TEXT,
    final_text TEXT,
    final_status TEXT,
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_reviews_ai_call_id_key UNIQUE (ai_call_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_reviews_updated_at ON ai_reviews (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_reviews_operator_action ON ai_reviews (operator_action);
