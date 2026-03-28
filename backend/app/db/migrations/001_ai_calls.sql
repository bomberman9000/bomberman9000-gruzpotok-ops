-- Базовые таблицы истории AI-вызовов и feedback (backend ГрузПотока).
-- Идемпотентность: CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS ai_calls (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id TEXT NOT NULL,
    endpoint TEXT,
    persona TEXT,
    mode TEXT,
    user_input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    normalized_status TEXT,
    llm_invoked BOOLEAN,
    citations_count INTEGER DEFAULT 0,
    response_summary TEXT,
    raw_meta_json JSONB,
    raw_data_json JSONB,
    latency_ms INTEGER,
    is_error BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_ai_calls_request_id ON ai_calls (request_id);
CREATE INDEX IF NOT EXISTS idx_ai_calls_created_at ON ai_calls (created_at DESC);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id TEXT NOT NULL,
    ai_call_id BIGINT REFERENCES ai_calls (id) ON DELETE SET NULL,
    useful BOOLEAN NOT NULL,
    correct BOOLEAN,
    comment TEXT,
    user_role TEXT,
    source_screen TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_request_id ON ai_feedback (request_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_ai_call_id ON ai_feedback (ai_call_id);
