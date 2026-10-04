CREATE TABLE IF NOT EXISTS ai_requests (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    purpose TEXT NOT NULL,
    task_type TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    privacy_class TEXT NOT NULL CHECK (privacy_class IN ('public','internal')),
    prompt_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_responses (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success','unavailable','timeout','provider_error','invalid_output','cancelled','disabled')),
    error_category TEXT,
    candidate_id TEXT,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES ai_requests(id)
);

CREATE TABLE IF NOT EXISTS ai_candidates (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL,
    response_id TEXT NOT NULL UNIQUE,
    review_state TEXT NOT NULL CHECK (review_state IN ('pending_review','rejected')),
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES ai_requests(id),
    FOREIGN KEY (response_id) REFERENCES ai_responses(id)
);

CREATE INDEX IF NOT EXISTS idx_ai_request_provider ON ai_requests(provider_id, model_id);
CREATE INDEX IF NOT EXISTS idx_ai_response_status ON ai_responses(status);
CREATE INDEX IF NOT EXISTS idx_ai_candidate_review ON ai_candidates(review_state);
