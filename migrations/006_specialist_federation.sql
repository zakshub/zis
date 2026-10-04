CREATE TABLE IF NOT EXISTS specialist_requests (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    specialist_id TEXT NOT NULL,
    action TEXT NOT NULL,
    requested_capability TEXT NOT NULL,
    privacy_class TEXT NOT NULL CHECK (privacy_class IN ('public','internal')),
    input_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (specialist_id) REFERENCES specialist_registry(id)
);

CREATE TABLE IF NOT EXISTS specialist_responses (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    specialist_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success','unavailable','incompatible','timeout','specialist_error','invalid_output','rejected','disabled')),
    error_category TEXT,
    provenance_receipt_id TEXT,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES specialist_requests(id),
    FOREIGN KEY (specialist_id) REFERENCES specialist_registry(id)
);

CREATE TABLE IF NOT EXISTS specialist_provenance_receipts (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    response_id TEXT NOT NULL UNIQUE,
    specialist_id TEXT NOT NULL,
    output_fingerprint TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES specialist_requests(id),
    FOREIGN KEY (response_id) REFERENCES specialist_responses(id),
    FOREIGN KEY (specialist_id) REFERENCES specialist_registry(id)
);

CREATE INDEX IF NOT EXISTS idx_specialist_request_specialist ON specialist_requests(specialist_id, created_at);
CREATE INDEX IF NOT EXISTS idx_specialist_response_status ON specialist_responses(status);
