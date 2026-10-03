"""SQLite evidence store with migrations and append-only audit events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .contracts import validate
from .identity import enforce_identity_boundary
from .ids import deterministic_id


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_database_path() -> Path:
    return Path.cwd() / ".zis" / "zis.sqlite3"


class EvidenceStore:
    STATUS_TRANSITIONS = {
        "captured": {"reviewed", "rejected", "expired"},
        "reviewed": {"promoted", "rejected", "expired"},
        "promoted": {"expired"},
        "superseded": set(),
        "rejected": set(),
        "expired": set(),
    }
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_database_path()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def migration_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "migrations"

    def initialize(self) -> list[int]:
        applied: list[int] = []
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            existing = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(self.migration_dir().glob("*.sql")):
                version = int(migration.stem.split("_", 1)[0])
                if version in existing:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                    (version, migration.name, utc_now()),
                )
                applied.append(version)
        return applied

    def schema_version(self) -> int:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
            return int(row[0])

    def _audit(self, connection: sqlite3.Connection, event_type: str, entity_type: str, entity_id: str, payload: dict[str, Any]) -> None:
        occurred_at = utc_now()
        event_id = deterministic_id("audit", {"type": event_type, "entity": entity_id, "at": occurred_at, "payload": payload})
        connection.execute(
            "INSERT INTO audit_events(event_id,event_type,entity_type,entity_id,occurred_at,payload_json,version) VALUES (?,?,?,?,?,?,1)",
            (event_id, event_type, entity_type, entity_id, occurred_at, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        )

    @staticmethod
    def _get_evidence(connection: sqlite3.Connection, evidence_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT record_json FROM evidence_records WHERE id=?", (evidence_id,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _get_contradiction(connection: sqlite3.Connection, contradiction_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM contradictions WHERE id=?", (contradiction_id,)).fetchone()
        return dict(row) if row else None

    def add_evidence(self, record: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(record)
        validate("evidence", record)
        self.initialize()
        with self.connect() as connection:
            if record["supersedes"]:
                previous = self._get_evidence(connection, record["supersedes"])
                if not previous:
                    raise ValueError(f"superseded evidence does not exist: {record['supersedes']}")
                if previous["superseded_by"]:
                    raise ValueError("evidence has already been superseded")
            connection.execute(
                "INSERT INTO evidence_records(id,record_json,record_type,scope,status,confidence,observed_at,recorded_at,valid_from,valid_until,supersedes,superseded_by,current_interpretation,version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["record_type"], record["scope"], record["status"], record["confidence"], record["observed_at"], record["recorded_at"], record["valid_from"], record["valid_until"], record["supersedes"], record["superseded_by"], int(record["current_interpretation"]), record["version"]),
            )
            self._audit(connection, "evidence.captured", "evidence", record["id"], {"record": record})
            if record["supersedes"]:
                before = previous
                after = deepcopy(previous)
                after.update({"status": "superseded", "superseded_by": record["id"], "current_interpretation": False})
                validate("evidence", after)
                connection.execute(
                    "UPDATE evidence_records SET record_json=?,status='superseded',superseded_by=?,current_interpretation=0 WHERE id=?",
                    (json.dumps(after, ensure_ascii=False, sort_keys=True), record["id"], previous["id"]),
                )
                self._audit(connection, "evidence.superseded", "evidence", previous["id"], {"before": before, "after": after, "by": record["id"]})
        return record

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        self.initialize()
        with self.connect() as connection:
            return self._get_evidence(connection, evidence_id)

    def list_evidence(self, status: str | None = None, scope: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        clauses: list[str] = []
        values: list[str] = []
        if status:
            clauses.append("status=?")
            values.append(status)
        if scope:
            clauses.append("scope=?")
            values.append(scope)
        query = "SELECT record_json FROM evidence_records"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY observed_at, id"
        with self.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(query, values)]

    def set_evidence_status(self, evidence_id: str, status: str) -> dict[str, Any]:
        self.initialize()
        with self.connect() as connection:
            record = self._get_evidence(connection, evidence_id)
            if not record:
                raise KeyError(evidence_id)
            if status not in self.STATUS_TRANSITIONS.get(record["status"], set()):
                raise ValueError(f"invalid evidence transition: {record['status']} -> {status}")
            before = deepcopy(record)
            record["status"] = status
            if status in {"rejected", "expired"}:
                record["current_interpretation"] = False
            validate("evidence", record)
            connection.execute(
                "UPDATE evidence_records SET record_json=?,status=?,current_interpretation=? WHERE id=?",
                (json.dumps(record, ensure_ascii=False, sort_keys=True), status, int(record["current_interpretation"]), evidence_id),
            )
            self._audit(connection, f"evidence.{status}", "evidence", evidence_id, {"before": before, "after": record})
        return record

    def add_contradiction(self, evidence_id_a: str, evidence_id_b: str) -> dict[str, Any]:
        if evidence_id_a == evidence_id_b:
            raise ValueError("an evidence item cannot contradict itself")
        a, b = sorted((evidence_id_a, evidence_id_b))
        self.initialize()
        record = {"id": deterministic_id("con", [a, b]), "evidence_id_a": a, "evidence_id_b": b, "status": "unresolved", "created_at": utc_now(), "resolved_at": None, "resolution_rationale": None, "resolution_source_reference": None, "version": 1}
        with self.connect() as connection:
            if not self._get_evidence(connection, a) or not self._get_evidence(connection, b):
                raise ValueError("both evidence records must exist")
            connection.execute(
                "INSERT INTO contradictions(id,evidence_id_a,evidence_id_b,status,created_at,resolved_at,resolution_rationale,resolution_source_reference,version) VALUES (?,?,?,?,?,?,?,?,?)",
                tuple(record.values()),
            )
            self._audit(connection, "contradiction.recorded", "contradiction", record["id"], record)
        return record

    def resolve_contradiction(self, contradiction_id: str, rationale: str, source_reference: str) -> dict[str, Any]:
        if not rationale.strip() or not source_reference.strip():
            raise ValueError("resolution rationale and source reference are required")
        self.initialize()
        with self.connect() as connection:
            contradiction = self._get_contradiction(connection, contradiction_id)
            if not contradiction:
                raise KeyError(contradiction_id)
            if contradiction["status"] == "resolved":
                raise ValueError("contradiction is already resolved")
            resolved_at = utc_now()
            connection.execute(
                "UPDATE contradictions SET status='resolved',resolved_at=?,resolution_rationale=?,resolution_source_reference=? WHERE id=?",
                (resolved_at, rationale, source_reference, contradiction_id),
            )
            self._audit(connection, "contradiction.resolved", "contradiction", contradiction_id, {"rationale": rationale, "source_reference": source_reference, "resolved_at": resolved_at})
            resolved = self._get_contradiction(connection, contradiction_id)
            assert resolved is not None
            return resolved

    def get_contradiction(self, contradiction_id: str) -> dict[str, Any]:
        self.initialize()
        with self.connect() as connection:
            contradiction = self._get_contradiction(connection, contradiction_id)
            if not contradiction:
                raise KeyError(contradiction_id)
            return contradiction

    def list_contradictions(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM contradictions ORDER BY created_at,id")]

    def audit_events(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence")
            return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

