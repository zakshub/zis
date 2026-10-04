CREATE TABLE IF NOT EXISTS cognitive_sessions (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running','completed','failed')),
    ruleset_version TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attention_signals (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    attention_level TEXT NOT NULL CHECK (attention_level IN ('low','medium','high','critical')),
    novelty_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id),
    FOREIGN KEY (evidence_id) REFERENCES evidence_records(id)
);

CREATE TABLE IF NOT EXISTS association_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    from_type TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('known','candidate')),
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS pattern_candidates (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate','under_review','supported','rejected','superseded')),
    confidence TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS hypothesis_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed','exploring','supported','weakened','rejected','superseded')),
    confidence TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS idea_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('spark','unclear','exploring','researching','promising','rejected','parked','ready')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS evaluation_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS reflection_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE TABLE IF NOT EXISTS model_update_proposals (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    session_id TEXT NOT NULL,
    target_memory_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed','under_review','approved','rejected','applied')),
    approval_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id),
    FOREIGN KEY (target_memory_id) REFERENCES memory_records(id),
    FOREIGN KEY (approval_id) REFERENCES approval_records(id)
);

CREATE TABLE IF NOT EXISTS cognitive_references (
    session_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (artifact_type, artifact_id, reference_type, reference_id, role),
    FOREIGN KEY (session_id) REFERENCES cognitive_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_cognitive_session_scope ON cognitive_sessions(scope);
CREATE INDEX IF NOT EXISTS idx_attention_session ON attention_signals(session_id);
CREATE INDEX IF NOT EXISTS idx_association_session ON association_records(session_id);
CREATE INDEX IF NOT EXISTS idx_pattern_status ON pattern_candidates(status);
CREATE INDEX IF NOT EXISTS idx_hypothesis_status ON hypothesis_records(status);
CREATE INDEX IF NOT EXISTS idx_idea_status ON idea_records(status);
CREATE INDEX IF NOT EXISTS idx_model_update_status ON model_update_proposals(status);
CREATE INDEX IF NOT EXISTS idx_cognitive_reference ON cognitive_references(reference_type, reference_id);
