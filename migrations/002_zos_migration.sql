CREATE TABLE IF NOT EXISTS migration_sources (
    id TEXT PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content_fingerprint TEXT NOT NULL,
    classification TEXT NOT NULL CHECK (classification IN ('A','B','C','D','E','F','G')),
    classification_rationale TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('unknown','weak','probable','strong','established')),
    privacy_screening_result TEXT NOT NULL,
    identity_scrub_status TEXT NOT NULL,
    specialist_routing_result TEXT NOT NULL,
    extraction_status TEXT NOT NULL,
    candidate_ids_json TEXT NOT NULL,
    human_review_status TEXT NOT NULL,
    import_status TEXT NOT NULL,
    imported_evidence_ids_json TEXT NOT NULL,
    rejection_reason TEXT,
    extracted_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    migration_version INTEGER NOT NULL,
    transformation_history_json TEXT NOT NULL,
    UNIQUE (source_repository, source_ref, source_path, content_fingerprint)
);

CREATE TABLE IF NOT EXISTS migration_candidates (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    candidate_type TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL,
    confidence TEXT NOT NULL,
    privacy_status TEXT NOT NULL,
    identity_scrub_status TEXT NOT NULL,
    privacy_findings_json TEXT NOT NULL,
    specialist_status TEXT NOT NULL,
    specialist_domains_json TEXT NOT NULL,
    temporal_status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    contradiction_candidate_ids_json TEXT NOT NULL,
    transformation_notes_json TEXT NOT NULL,
    review_status TEXT NOT NULL,
    review_note TEXT,
    reviewed_at TEXT,
    import_status TEXT NOT NULL,
    evidence_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    migration_version INTEGER NOT NULL,
    FOREIGN KEY (source_id) REFERENCES migration_sources(id)
);

CREATE INDEX IF NOT EXISTS idx_migration_candidate_review ON migration_candidates(review_status);
CREATE INDEX IF NOT EXISTS idx_migration_candidate_import ON migration_candidates(import_status);

CREATE TABLE IF NOT EXISTS migration_review_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    candidate_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    note TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES migration_candidates(id)
);

