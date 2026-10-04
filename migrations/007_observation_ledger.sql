CREATE TABLE IF NOT EXISTS observation_sources (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','approved','paused','revoked','retired')),
    approval_scope TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (approval_id) REFERENCES approval_records(id)
);

CREATE INDEX IF NOT EXISTS idx_observation_source_status ON observation_sources(status);

CREATE TABLE IF NOT EXISTS observation_collection_sessions (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    source_id TEXT NOT NULL,
    approval_scope TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running','completed','failed')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    version INTEGER NOT NULL,
    FOREIGN KEY (source_id) REFERENCES observation_sources(id)
);

CREATE INDEX IF NOT EXISTS idx_observation_session_source ON observation_collection_sessions(source_id, started_at);
CREATE INDEX IF NOT EXISTS idx_observation_session_status ON observation_collection_sessions(status);

CREATE TABLE IF NOT EXISTS observation_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    source_id TEXT NOT NULL,
    collection_session_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    data_class TEXT NOT NULL,
    privacy_class TEXT NOT NULL CHECK (privacy_class IN ('public','internal','private','restricted')),
    review_state TEXT NOT NULL CHECK (review_state IN ('captured','review_pending','accepted_for_evidence_review','rejected','quarantined','expired','deleted_marker')),
    retention_state TEXT NOT NULL CHECK (retention_state IN ('active','expired','quarantined','purged')),
    observed_at TEXT,
    recorded_at TEXT NOT NULL,
    retention_expires_at TEXT,
    content_fingerprint TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    explicit_event_id TEXT,
    version INTEGER NOT NULL,
    FOREIGN KEY (source_id) REFERENCES observation_sources(id),
    FOREIGN KEY (collection_session_id) REFERENCES observation_collection_sessions(id),
    UNIQUE (source_id, source_reference, content_fingerprint, explicit_event_id)
);

CREATE INDEX IF NOT EXISTS idx_observation_source ON observation_records(source_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_observation_review ON observation_records(review_state);
CREATE INDEX IF NOT EXISTS idx_observation_privacy ON observation_records(privacy_class);
CREATE INDEX IF NOT EXISTS idx_observation_retention ON observation_records(retention_state);

CREATE TABLE IF NOT EXISTS observation_duplicate_links (
    collection_session_id TEXT NOT NULL,
    existing_observation_id TEXT NOT NULL,
    duplicate_fingerprint TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    PRIMARY KEY (collection_session_id, existing_observation_id, duplicate_fingerprint, source_reference),
    FOREIGN KEY (collection_session_id) REFERENCES observation_collection_sessions(id),
    FOREIGN KEY (existing_observation_id) REFERENCES observation_records(id)
);

CREATE TABLE IF NOT EXISTS observation_evidence_proposals (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending_review','approved','rejected','promoted')),
    approval_id TEXT NOT NULL,
    evidence_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (approval_id) REFERENCES approval_records(id),
    FOREIGN KEY (evidence_id) REFERENCES evidence_records(id)
);

CREATE INDEX IF NOT EXISTS idx_observation_proposal_status ON observation_evidence_proposals(status);

CREATE TABLE IF NOT EXISTS observation_proposal_links (
    proposal_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    PRIMARY KEY (proposal_id, observation_id),
    FOREIGN KEY (proposal_id) REFERENCES observation_evidence_proposals(id),
    FOREIGN KEY (observation_id) REFERENCES observation_records(id)
);
