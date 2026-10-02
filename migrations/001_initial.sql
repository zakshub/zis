CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    record_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    supersedes TEXT,
    superseded_by TEXT,
    current_interpretation INTEGER NOT NULL CHECK (current_interpretation IN (0, 1)),
    version INTEGER NOT NULL,
    FOREIGN KEY (supersedes) REFERENCES evidence_records(id),
    FOREIGN KEY (superseded_by) REFERENCES evidence_records(id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_scope ON evidence_records(scope);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence_records(status);
CREATE INDEX IF NOT EXISTS idx_evidence_observed ON evidence_records(observed_at);

CREATE TABLE IF NOT EXISTS contradictions (
    id TEXT PRIMARY KEY,
    evidence_id_a TEXT NOT NULL,
    evidence_id_b TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('unresolved', 'resolved')),
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution_rationale TEXT,
    resolution_source_reference TEXT,
    version INTEGER NOT NULL,
    CHECK (evidence_id_a <> evidence_id_b),
    UNIQUE (evidence_id_a, evidence_id_b),
    FOREIGN KEY (evidence_id_a) REFERENCES evidence_records(id),
    FOREIGN KEY (evidence_id_b) REFERENCES evidence_records(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    version INTEGER NOT NULL
);

