CREATE TABLE IF NOT EXISTS runtime_sources (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    source_type TEXT NOT NULL,
    canonical_reference TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('active','inactive')),
    privacy_class TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_reference TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','deferred','expired','revoked')),
    requested_at TEXT NOT NULL,
    decided_at TEXT,
    version INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_approval_action ON approval_records(action_type, action_reference);
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_records(status);

CREATE TABLE IF NOT EXISTS memory_records (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed','active','superseded','rejected','expired','deprecated')),
    confidence TEXT NOT NULL,
    current_interpretation INTEGER NOT NULL CHECK (current_interpretation IN (0,1)),
    approval_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (approval_id) REFERENCES approval_records(id)
);

CREATE TABLE IF NOT EXISTS memory_evidence_links (
    memory_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (memory_id, evidence_id),
    FOREIGN KEY (memory_id) REFERENCES memory_records(id),
    FOREIGN KEY (evidence_id) REFERENCES evidence_records(id)
);

CREATE TABLE IF NOT EXISTS capability_registry (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    capability_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed','approved','available','unavailable','deprecated','retired')),
    availability TEXT NOT NULL CHECK (availability IN ('unknown','available','unavailable')),
    approval_required INTEGER NOT NULL CHECK (approval_required IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS capability_dependencies (
    capability_id TEXT NOT NULL,
    dependency_id TEXT NOT NULL,
    PRIMARY KEY (capability_id, dependency_id),
    CHECK (capability_id <> dependency_id),
    FOREIGN KEY (capability_id) REFERENCES capability_registry(id),
    FOREIGN KEY (dependency_id) REFERENCES capability_registry(id)
);

CREATE TABLE IF NOT EXISTS specialist_registry (
    id TEXT PRIMARY KEY,
    manifest_json TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed','approved','available','unavailable','retired')),
    availability TEXT NOT NULL CHECK (availability IN ('unknown','available','unavailable')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS route_decisions (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    selected_route TEXT NOT NULL,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_operations (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    request_id TEXT NOT NULL,
    route_decision_id TEXT NOT NULL,
    approval_id TEXT,
    capability_id TEXT,
    specialist_id TEXT,
    execution_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (route_decision_id) REFERENCES route_decisions(id),
    FOREIGN KEY (approval_id) REFERENCES approval_records(id),
    FOREIGN KEY (capability_id) REFERENCES capability_registry(id),
    FOREIGN KEY (specialist_id) REFERENCES specialist_registry(id)
);

