"""Governed, explicit and local Observation Ledger for M7.

Observation capture is not evidence, memory, truth or permission. Adapters are
invoked only by an explicit collection call against one approved source.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from .contracts import validate
from .identity import direct_identity_text_findings, enforce_identity_boundary, rejected_identity_paths
from .ids import deterministic_id
from .records import build_evidence
from .runtime import APPROVAL_TRANSITIONS, ClassicalRuntime, build_approval_record
from .store import EvidenceStore, utc_now


LEDGER_VERSION = "m7.v1"
ALLOWED_FILE_EXTENSIONS = frozenset({".txt", ".md", ".json"})
DEFAULT_MAX_FILE_BYTES = 1_048_576
SECRET_FINDINGS = frozenset({"credential_or_token", "authorization_bearer"})
SECRET_FIELD_NAMES = frozenset({"credential", "credentials", "token", "access_token", "refresh_token", "api_key", "secret_key", "authorization", "authorization_header"})
SOURCE_TRANSITIONS = {
    "pending": {"approved", "retired"},
    "approved": {"paused", "revoked", "retired"},
    "paused": {"approved", "revoked", "retired"},
    "revoked": set(),
    "retired": set(),
}
REVIEW_TRANSITIONS = {
    "captured": {"review_pending", "rejected", "quarantined", "expired"},
    "review_pending": {"accepted_for_evidence_review", "rejected", "quarantined", "expired"},
    "accepted_for_evidence_review": {"rejected", "expired"},
    "quarantined": {"review_pending", "rejected", "expired"},
    "rejected": set(),
    "expired": set(),
    "deleted_marker": set(),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _bytes_fingerprint(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _timestamp(value: str | None = None) -> str:
    stamp = value or utc_now()
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_error(message: str) -> str:
    lowered = message.casefold()
    if any(token in lowered for token in ("secret", "token", "credential", "password", "authorization")):
        return "Collection input failed a secret-safety check."
    return message[:240]


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).casefold() in SECRET_FIELD_NAMES or _contains_secret_field(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_secret_field(child) for child in value)
    return False


@dataclass(frozen=True)
class ObservationAdapterResult:
    items: list[dict[str, Any]]
    safe_metadata: dict[str, Any]


class ObservationAdapter(Protocol):
    adapter_id: str
    adapter_version: str
    source_type: str

    def availability(self) -> dict[str, Any]: ...

    def compatibility(self, source: dict[str, Any]) -> bool: ...

    def collect(self, request: dict[str, Any]) -> ObservationAdapterResult: ...


class ManualObservationAdapter:
    adapter_id = "manual"
    adapter_version = LEDGER_VERSION
    source_type = "manual"

    def availability(self) -> dict[str, Any]:
        return {"state": "available", "external": False, "background": False}

    def compatibility(self, source: dict[str, Any]) -> bool:
        return source["source_type"] == self.source_type and source["adapter_id"] == self.adapter_id and source["adapter_version"] == self.adapter_version

    def collect(self, request: dict[str, Any]) -> ObservationAdapterResult:
        item = request.get("item")
        if not isinstance(item, dict):
            raise ValueError("manual collection requires one structured item")
        return ObservationAdapterResult([deepcopy(item)], {"mode": "explicit_single"})


class FileImportObservationAdapter:
    adapter_id = "file_import"
    adapter_version = LEDGER_VERSION
    source_type = "file_import"

    def availability(self) -> dict[str, Any]:
        return {"state": "available", "external": False, "background": False}

    def compatibility(self, source: dict[str, Any]) -> bool:
        return source["source_type"] == self.source_type and source["adapter_id"] == self.adapter_id and source["adapter_version"] == self.adapter_version

    def collect(self, request: dict[str, Any]) -> ObservationAdapterResult:
        supplied = request.get("path")
        if not isinstance(supplied, str) or not supplied.strip():
            raise ValueError("file import requires one explicit file path")
        path = Path(supplied)
        if path.is_symlink():
            raise ValueError("symbolic links are not accepted for file import")
        if not path.exists() or not path.is_file():
            raise ValueError("explicit file path is not a regular file")
        suffix = path.suffix.casefold()
        if suffix not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError("unsupported file type")
        maximum = int(request.get("max_bytes", DEFAULT_MAX_FILE_BYTES))
        if maximum < 1 or maximum > DEFAULT_MAX_FILE_BYTES:
            raise ValueError("file maximum must be between 1 and 1048576 bytes")
        size = path.stat().st_size
        if size > maximum:
            raise ValueError("file exceeds the bounded import size")
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("unsupported file encoding; UTF-8 is required") from error
        file_fingerprint = _bytes_fingerprint(raw)
        item = {
            "observation_type": "file_content",
            "data_class": request.get("data_class", "text_document"),
            "content": text,
            "structured_payload": {"file_extension": suffix, "byte_size": size, "file_fingerprint": file_fingerprint},
            "source_reference": f"file:{file_fingerprint}",
            "explicit_event_id": request.get("explicit_event_id"),
            "observed_at": request.get("observed_at"),
            "valid_from": request.get("valid_from"),
            "valid_until": request.get("valid_until"),
            "privacy_class": request.get("privacy_class", "private"),
            "capture_confidence": request.get("capture_confidence", "strong"),
            "subject_labels": list(request.get("subject_labels", [])),
            "context_labels": list(request.get("context_labels", [])),
            "transformation_notes": ["explicit_utf8_file_import", "path_not_persisted"],
        }
        return ObservationAdapterResult([item], {"mode": "explicit_file", "extension": suffix, "byte_size": size, "file_fingerprint": file_fingerprint})


class SyntheticObservationAdapter:
    """Deterministic injected adapter for tests; never registered by default."""

    adapter_id = "synthetic_test"
    adapter_version = LEDGER_VERSION
    source_type = "other"

    def availability(self) -> dict[str, Any]:
        return {"state": "available", "external": False, "background": False, "test_only": True}

    def compatibility(self, source: dict[str, Any]) -> bool:
        return source["adapter_id"] == self.adapter_id and source["adapter_version"] == self.adapter_version

    def collect(self, request: dict[str, Any]) -> ObservationAdapterResult:
        items = request.get("items")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError("synthetic collection requires a list of structured items")
        return ObservationAdapterResult(deepcopy(items), {"mode": "synthetic_test", "items": len(items)})


class ObservationAdapterRegistry:
    def __init__(self, adapters: list[ObservationAdapter] | None = None):
        values = adapters if adapters is not None else [ManualObservationAdapter(), FileImportObservationAdapter()]
        self._adapters = {adapter.adapter_id: adapter for adapter in values}

    def register(self, adapter: ObservationAdapter) -> None:
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> ObservationAdapter | None:
        return self._adapters.get(adapter_id)

    def status(self) -> dict[str, Any]:
        return {key: adapter.availability() for key, adapter in sorted(self._adapters.items())}


class ObservationLedger:
    def __init__(self, store: EvidenceStore, adapters: ObservationAdapterRegistry | None = None):
        self.store = store
        self.runtime = ClassicalRuntime(store)
        self.adapters = adapters or ObservationAdapterRegistry()

    def initialize(self) -> list[int]:
        return self.store.initialize()

    @staticmethod
    def _json_row(connection: sqlite3.Connection, table: str, record_id: str) -> dict[str, Any] | None:
        row = connection.execute(f"SELECT record_json FROM {table} WHERE id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def register_source(self, specification: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "source_type", "approval_scope", "collection_mode", "allowed_scopes", "allowed_data_classes", "denied_data_classes", "retention_policy", "external", "adapter_id", "adapter_version", "privacy_notes", "created_at"}
        extra = sorted(set(specification) - allowed)
        if extra:
            raise ValueError("unsupported observation source fields: " + ", ".join(extra))
        required = {"name", "source_type", "approval_scope", "allowed_scopes", "allowed_data_classes", "adapter_id"}
        missing = sorted(name for name in required if not specification.get(name))
        if missing:
            raise ValueError("observation source requires: " + ", ".join(missing))
        adapter = self.adapters.get(str(specification["adapter_id"]))
        if not adapter:
            raise ValueError("observation adapter is not registered")
        if specification["source_type"] != adapter.source_type:
            raise ValueError("source type does not match the observation adapter")
        retention = deepcopy(specification.get("retention_policy", {"mode": "manual", "days": None}))
        if retention.get("mode") == "days" and not isinstance(retention.get("days"), int):
            raise ValueError("days retention requires an integer day count")
        if retention.get("mode") != "days":
            retention["days"] = None
        allowed_scopes = sorted(set(specification["allowed_scopes"]))
        allowed_classes = sorted(set(specification["allowed_data_classes"]))
        denied_classes = sorted(set(specification.get("denied_data_classes", [])))
        if set(allowed_classes) & set(denied_classes):
            raise ValueError("a data class cannot be both allowed and denied")
        now = _timestamp(specification.get("created_at"))
        material = {"name": specification["name"], "source_type": specification["source_type"], "approval_scope": specification["approval_scope"], "adapter_id": adapter.adapter_id, "allowed_scopes": allowed_scopes, "version": 1}
        source_id = deterministic_id("osrc", material)
        approval = build_approval_record("observation_source.approve", source_id, "Approve bounded explicit observation collection.", specification["approval_scope"], "high" if specification.get("external") else "medium", "Allows only the declared scopes and data classes through an explicit adapter call.", provenance_method="m7_observation_source_registration", requested_at=now)
        source = {
            "id": source_id, "name": specification["name"], "source_type": specification["source_type"],
            "approval_scope": specification["approval_scope"], "approval_id": approval["id"], "status": "pending",
            "collection_mode": specification.get("collection_mode", "explicit_single"), "allowed_scopes": allowed_scopes,
            "allowed_data_classes": allowed_classes, "denied_data_classes": denied_classes, "retention_policy": retention,
            "external": bool(specification.get("external", False)), "adapter_id": adapter.adapter_id,
            "adapter_version": specification.get("adapter_version", adapter.adapter_version), "last_collection": None,
            "privacy_notes": specification.get("privacy_notes", "Local explicit collection only; no implicit permission expansion."),
            "provenance": {"method": "manual_source_registration", "actor": "owner", "chain": [specification["approval_scope"]]},
            "created_at": now, "updated_at": now, "version": 1,
        }
        enforce_identity_boundary(source)
        if direct_identity_text_findings(source):
            raise ValueError("observation source metadata contains direct identity or credential signals")
        validate("observation-source", source)
        self.initialize()
        with self.store.connect() as connection:
            if self._json_row(connection, "observation_sources", source_id):
                raise ValueError("observation source is already registered")
            self.runtime._insert_approval(connection, approval)
            connection.execute("INSERT INTO observation_sources(id,record_json,source_type,status,approval_scope,approval_id,adapter_id,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?,?)", (source_id, _canonical(source), source["source_type"], source["status"], source["approval_scope"], source["approval_id"], source["adapter_id"], now, now, 1))
            self.store._audit(connection, "observation.source_registered", "observation_source", source_id, {"source_id": source_id, "source_type": source["source_type"], "adapter_id": source["adapter_id"], "approval_id": approval["id"], "allowed_scopes": allowed_scopes, "allowed_data_classes": allowed_classes})
        return {"source": source, "approval": approval}

    def list_sources(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute("SELECT record_json FROM observation_sources ORDER BY id")]

    def get_source(self, source_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "observation_sources", source_id)
            if not record:
                raise KeyError(source_id)
            return record

    def set_source_status(self, source_id: str, status: str, approval_id: str | None = None) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            source = self._json_row(connection, "observation_sources", source_id)
            if not source:
                raise KeyError(source_id)
            if status not in SOURCE_TRANSITIONS[source["status"]]:
                raise ValueError(f"invalid observation source transition: {source['status']} -> {status}")
            if status == "approved":
                self.runtime._authorize(connection, approval_id or source["approval_id"], "observation_source.approve", source_id, source["approval_scope"])
            before = deepcopy(source)
            source.update({"status": status, "updated_at": utc_now(), "version": source["version"] + 1})
            validate("observation-source", source)
            connection.execute("UPDATE observation_sources SET record_json=?,status=?,updated_at=?,version=? WHERE id=?", (_canonical(source), status, source["updated_at"], source["version"], source_id))
            self.store._audit(connection, f"observation.source_{status}", "observation_source", source_id, {"source_id": source_id, "before_status": before["status"], "after_status": status, "approval_id": approval_id})
            return source

    def _failed_session(self, source: dict[str, Any], scope: str, operation: str, adapter: ObservationAdapter, started_at: str, safe_error: str) -> dict[str, Any]:
        session_id = deterministic_id("ocsession", {"source_id": source["id"], "scope": scope, "operation": operation, "started_at": started_at, "failure": safe_error, "version": 1})
        session = {"id": session_id, "source_id": source["id"], "approval_scope": scope, "requested_operation": operation, "adapter_id": adapter.adapter_id, "adapter_version": adapter.adapter_version, "started_at": started_at, "completed_at": utc_now(), "status": "failed", "items_considered": 0, "items_accepted": 0, "items_quarantined": 0, "items_rejected": 0, "duplicates": 0, "observation_ids": [], "duplicate_observation_ids": [], "privacy_findings": [], "errors": [safe_error], "provenance": {"method": "explicit_collection_failure", "actor": "owner", "chain": [source["id"]]}, "version": 1}
        validate("observation-session", session)
        with self.store.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO observation_collection_sessions(id,record_json,source_id,approval_scope,adapter_id,status,started_at,completed_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (session_id, _canonical(session), source["id"], scope, adapter.adapter_id, "failed", started_at, session["completed_at"], 1))
            self.store._audit(connection, "observation.collection_failed", "observation_collection_session", session_id, {"session_id": session_id, "source_id": source["id"], "scope": scope, "adapter_id": adapter.adapter_id, "error": safe_error})
        return session

    def collect(self, source_id: str, scope: str, operation: str, request: dict[str, Any], started_at: str | None = None) -> dict[str, Any]:
        self.initialize()
        source = self.get_source(source_id)
        adapter = self.adapters.get(source["adapter_id"])
        if not adapter:
            raise ValueError("observation adapter is not registered")
        started = _timestamp(started_at)
        try:
            if source["status"] != "approved":
                raise ValueError(f"observation source cannot collect while {source['status']}")
            if scope not in source["allowed_scopes"] or scope != source["approval_scope"]:
                raise ValueError("collection scope is outside the exact approved source scope")
            if source["external"]:
                raise ValueError("external observation connectors are not implemented in M7")
            expected_operation = {"manual": "manual_capture", "file_import": "file_import", "synthetic_test": "synthetic_test"}.get(adapter.adapter_id)
            if operation != expected_operation:
                raise ValueError("collection operation does not match the approved observation adapter")
            if not adapter.compatibility(source):
                raise ValueError("observation adapter is incompatible with the source")
            if adapter.availability().get("state") != "available":
                raise ValueError("observation adapter is unavailable")
            result = adapter.collect(deepcopy(request))
            if len(result.items) > 100:
                raise ValueError("collection result exceeds the bounded 100-item limit")
        except (OSError, UnicodeError, ValueError) as error:
            session = self._failed_session(source, scope, operation, adapter, started, _safe_error(str(error)))
            raise ValueError(session["errors"][0]) from error

        request_fingerprint = _fingerprint({"source_id": source_id, "scope": scope, "operation": operation, "items": result.items, "started_at": started})
        session_id = deterministic_id("ocsession", {"request_fingerprint": request_fingerprint, "version": 1})
        running = {"id": session_id, "source_id": source_id, "approval_scope": scope, "requested_operation": operation, "adapter_id": adapter.adapter_id, "adapter_version": adapter.adapter_version, "started_at": started, "completed_at": None, "status": "running", "items_considered": len(result.items), "items_accepted": 0, "items_quarantined": 0, "items_rejected": 0, "duplicates": 0, "observation_ids": [], "duplicate_observation_ids": [], "privacy_findings": [], "errors": [], "provenance": {"method": "explicit_bounded_collection", "actor": "owner", "chain": [source_id, request_fingerprint]}, "version": 1}
        validate("observation-session", running)
        with self.store.connect() as connection:
            existing_session = self._json_row(connection, "observation_collection_sessions", session_id)
            if existing_session:
                return {"session": existing_session, "observations": [self._json_row(connection, "observation_records", item) for item in existing_session["observation_ids"]]}
            connection.execute("INSERT INTO observation_collection_sessions(id,record_json,source_id,approval_scope,adapter_id,status,started_at,completed_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (session_id, _canonical(running), source_id, scope, adapter.adapter_id, "running", started, None, 1))
            self.store._audit(connection, "observation.collection_started", "observation_collection_session", session_id, {"session_id": session_id, "source_id": source_id, "scope": scope, "adapter_id": adapter.adapter_id, "items_considered": len(result.items), "request_fingerprint": request_fingerprint})
            observations: list[dict[str, Any]] = []
            duplicate_ids: list[str] = []
            privacy_findings: set[str] = set()
            for item in result.items:
                record, quarantine_reasons = self._build_observation(source, running, item)
                privacy_findings.update(quarantine_reasons)
                existing = connection.execute("SELECT record_json FROM observation_records WHERE source_id=? AND source_reference=? AND content_fingerprint=? AND ((explicit_event_id IS NULL AND ? IS NULL) OR explicit_event_id=?)", (source_id, record["source_reference"], record["content_fingerprint"], record["explicit_event_id"], record["explicit_event_id"])).fetchone()
                if existing:
                    prior = json.loads(existing[0])
                    duplicate_ids.append(prior["id"])
                    connection.execute("INSERT OR IGNORE INTO observation_duplicate_links(collection_session_id,existing_observation_id,duplicate_fingerprint,source_reference) VALUES (?,?,?,?)", (session_id, prior["id"], record["content_fingerprint"], record["source_reference"]))
                    continue
                connection.execute("INSERT INTO observation_records(id,record_json,source_id,collection_session_id,scope,data_class,privacy_class,review_state,retention_state,observed_at,recorded_at,retention_expires_at,content_fingerprint,source_reference,explicit_event_id,version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (record["id"], _canonical(record), source_id, session_id, scope, record["data_class"], record["privacy_class"], record["review_state"], record["retention_state"], record["observed_at"], record["recorded_at"], record["retention_expires_at"], record["content_fingerprint"], record["source_reference"], record["explicit_event_id"], 1))
                observations.append(record)
                event = "observation.quarantined" if record["review_state"] == "quarantined" else "observation.captured"
                self.store._audit(connection, event, "observation", record["id"], {"observation_id": record["id"], "source_id": source_id, "session_id": session_id, "scope": scope, "privacy_class": record["privacy_class"], "data_class": record["data_class"], "content_fingerprint": record["content_fingerprint"], "review_state": record["review_state"], "findings": quarantine_reasons})
            completed_at = utc_now()
            session = deepcopy(running)
            session.update({"completed_at": completed_at, "status": "completed", "items_accepted": sum(item["review_state"] != "quarantined" for item in observations), "items_quarantined": sum(item["review_state"] == "quarantined" for item in observations), "duplicates": len(duplicate_ids), "observation_ids": [item["id"] for item in observations], "duplicate_observation_ids": sorted(set(duplicate_ids)), "privacy_findings": sorted(privacy_findings), "version": 2})
            validate("observation-session", session)
            connection.execute("UPDATE observation_collection_sessions SET record_json=?,status='completed',completed_at=?,version=2 WHERE id=?", (_canonical(session), completed_at, session_id))
            self.store._audit(connection, "observation.collection_completed", "observation_collection_session", session_id, {"session_id": session_id, "source_id": source_id, "items_considered": session["items_considered"], "items_accepted": session["items_accepted"], "items_quarantined": session["items_quarantined"], "duplicates": session["duplicates"]})
            source["last_collection"] = {"session_id": session_id, "completed_at": completed_at, "status": "completed", "items_considered": session["items_considered"]}
            source["updated_at"] = completed_at
            source["version"] += 1
            validate("observation-source", source)
            connection.execute("UPDATE observation_sources SET record_json=?,updated_at=?,version=? WHERE id=?", (_canonical(source), completed_at, source["version"], source_id))
            return {"session": session, "observations": observations}

    def _build_observation(self, source: dict[str, Any], session: dict[str, Any], item: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        allowed = {"scope", "observation_type", "data_class", "content", "structured_payload", "source_reference", "explicit_event_id", "observed_at", "valid_from", "valid_until", "privacy_class", "capture_confidence", "subject_labels", "context_labels", "transformation_notes"}
        if set(item) - allowed:
            raise ValueError("observation adapter item contains unsupported fields")
        data_class = str(item.get("data_class", "general"))
        scope = str(item.get("scope") or session["approval_scope"])
        privacy = str(item.get("privacy_class", "private"))
        content = item.get("content")
        payload = item.get("structured_payload")
        if content is None and payload is None:
            raise ValueError("observation item requires content or structured_payload")
        if content is not None and (not isinstance(content, str) or not content):
            raise ValueError("observation content must be a non-empty string")
        if payload is not None and not isinstance(payload, dict):
            raise ValueError("observation structured_payload must be an object")
        source_reference = str(item.get("source_reference") or f"manual:{_fingerprint({'content': content, 'payload': payload})}")
        raw_material = {"content": content, "structured_payload": payload}
        content_fingerprint = _fingerprint(raw_material)
        findings = direct_identity_text_findings(item)
        structural_identity = bool(rejected_identity_paths(item))
        if structural_identity:
            findings = sorted(set(findings) | {"direct_identity_field"})
        secret_findings = sorted(set(findings) & SECRET_FINDINGS)
        if _contains_secret_field(item):
            secret_findings = sorted(set(secret_findings) | {"secret_field"})
        quarantine: list[str] = []
        if scope not in source["allowed_scopes"] or scope != session["approval_scope"]:
            quarantine.append("scope_outside_approval")
        if data_class in source["denied_data_classes"] or data_class not in source["allowed_data_classes"]:
            quarantine.append("data_class_not_allowed")
        if privacy == "restricted":
            quarantine.append("restricted_requires_review")
        if secret_findings:
            quarantine.append("suspected_secret")
        if privacy in {"public", "internal"} and findings:
            quarantine.append("identity_or_secret_not_public_safe")
        identity_status = "retained_private" if findings and privacy == "private" and not secret_findings else ("excluded" if quarantine else "not_detected")
        if secret_findings or (privacy in {"public", "internal"} and findings):
            source_reference = f"quarantine:{content_fingerprint}"
        if quarantine:
            content, payload = None, None
        observed_at = _timestamp(item["observed_at"]) if item.get("observed_at") else None
        valid_from = _timestamp(item["valid_from"]) if item.get("valid_from") else observed_at
        valid_until = _timestamp(item["valid_until"]) if item.get("valid_until") else None
        if valid_from and valid_until and valid_until < valid_from:
            raise ValueError("valid_until must not precede valid_from")
        recorded_at = utc_now()
        retention = source["retention_policy"]
        expires = None
        if retention["mode"] == "days":
            expires = (datetime.fromisoformat(recorded_at.replace("Z", "+00:00")) + timedelta(days=retention["days"])).isoformat().replace("+00:00", "Z")
        elif retention["mode"] == "session_only":
            expires = recorded_at
        identity_material = {"source_id": source["id"], "source_reference": source_reference, "content_fingerprint": content_fingerprint, "explicit_event_id": item.get("explicit_event_id"), "version": 2}
        record = {
            "id": deterministic_id("obs", identity_material), "source_id": source["id"], "collection_session_id": session["id"],
            "adapter_id": session["adapter_id"], "adapter_version": session["adapter_version"], "observed_at": observed_at,
            "observed_time_status": "known" if observed_at else "unknown", "recorded_at": recorded_at, "imported_at": recorded_at,
            "valid_from": valid_from, "valid_until": valid_until, "scope": scope,
            "observation_type": item.get("observation_type", "observation"), "data_class": data_class,
            "content": content, "structured_payload": payload, "source_reference": source_reference,
            "explicit_event_id": item.get("explicit_event_id"),
            "provenance": {"source_id": source["id"], "collection_session_id": session["id"], "adapter_id": session["adapter_id"], "adapter_version": session["adapter_version"], "source_reference": source_reference, "ingestion_method": session["requested_operation"], "transformation_notes": list(item.get("transformation_notes", [])) + (["private_content_removed_for_quarantine"] if quarantine else []), "original_privacy_class": privacy},
            "privacy_class": privacy, "capture_confidence": item.get("capture_confidence", "unknown"),
            "subject_labels": sorted(set(item.get("subject_labels", []))), "context_labels": sorted(set(item.get("context_labels", []))),
            "review_state": "quarantined" if quarantine else "captured", "retention_state": "quarantined" if quarantine else "active",
            "retention_expires_at": expires, "content_fingerprint": content_fingerprint, "identity_status": identity_status,
            "secret_status": "suspected_quarantined" if secret_findings else "none_detected", "linked_evidence_ids": [], "version": 1,
        }
        validate("observation", record)
        return record, sorted(set(quarantine))

    def list_observations(self, source_id: str | None = None, review_state: str | None = None, privacy_class: str | None = None, recorded_from: str | None = None, recorded_until: str | None = None) -> list[dict[str, Any]]:
        clauses, values = [], []
        for column, value in (("source_id", source_id), ("review_state", review_state), ("privacy_class", privacy_class)):
            if value:
                clauses.append(f"{column}=?")
                values.append(value)
        if recorded_from:
            clauses.append("recorded_at>=?")
            values.append(_timestamp(recorded_from))
        if recorded_until:
            clauses.append("recorded_at<=?")
            values.append(_timestamp(recorded_until))
        query = "SELECT record_json FROM observation_records" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY recorded_at,id"
        self.initialize()
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(query, values)]

    def get_observation(self, observation_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "observation_records", observation_id)
            if not record:
                raise KeyError(observation_id)
            return record

    def list_sessions(self, source_id: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        query = "SELECT record_json FROM observation_collection_sessions" + (" WHERE source_id=?" if source_id else "") + " ORDER BY started_at,id"
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(query, (source_id,) if source_id else ())]

    def list_quarantine(self) -> list[dict[str, Any]]:
        return self.list_observations(review_state="quarantined")

    def set_review_state(self, observation_id: str, state: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "observation_records", observation_id)
            if not record:
                raise KeyError(observation_id)
            if state not in REVIEW_TRANSITIONS[record["review_state"]]:
                raise ValueError(f"invalid observation review transition: {record['review_state']} -> {state}")
            before = record["review_state"]
            record["review_state"] = state
            if state == "expired":
                record["retention_state"] = "expired"
            elif state == "quarantined":
                record["retention_state"] = "quarantined"
            record["version"] += 1
            validate("observation", record)
            connection.execute("UPDATE observation_records SET record_json=?,review_state=?,retention_state=?,version=? WHERE id=?", (_canonical(record), state, record["retention_state"], record["version"], observation_id))
            self.store._audit(connection, "observation.review_transition", "observation", observation_id, {"observation_id": observation_id, "from": before, "to": state, "content_fingerprint": record["content_fingerprint"]})
            return record

    def purge(self, observation_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "observation_records", observation_id)
            if not record:
                raise KeyError(observation_id)
            if record["retention_state"] == "purged":
                return record
            marker = f"purged:{record['content_fingerprint']}"
            record.update({"content": None, "structured_payload": None, "source_reference": marker, "subject_labels": [], "context_labels": [], "review_state": "deleted_marker", "retention_state": "purged", "identity_status": "excluded", "version": record["version"] + 1})
            record["provenance"]["source_reference"] = marker
            record["provenance"]["transformation_notes"] = [*record["provenance"]["transformation_notes"], "logical_purge_content_removed"]
            validate("observation", record)
            connection.execute("UPDATE observation_records SET record_json=?,review_state='deleted_marker',retention_state='purged',source_reference=?,version=? WHERE id=?", (_canonical(record), marker, record["version"], observation_id))
            self.store._audit(connection, "observation.purged", "observation", observation_id, {"observation_id": observation_id, "content_fingerprint": record["content_fingerprint"], "logical_purge": True})
            return record

    def propose_evidence(self, specification: dict[str, Any]) -> dict[str, Any]:
        allowed = {"observation_ids", "proposed_content", "proposed_evidence_type", "scope", "confidence", "observed_at", "valid_from", "valid_until", "rationale", "uncertainty", "counter_context", "created_at"}
        if set(specification) - allowed:
            raise ValueError("evidence proposal contains unsupported fields")
        for required in ("observation_ids", "proposed_content", "proposed_evidence_type", "scope", "confidence", "rationale", "uncertainty"):
            if not specification.get(required):
                raise ValueError(f"evidence proposal requires {required}")
        enforce_identity_boundary(specification)
        findings = direct_identity_text_findings(specification)
        if findings:
            raise ValueError("evidence proposal is not public-safe: " + ", ".join(findings))
        observation_ids = sorted(set(specification["observation_ids"]))
        self.initialize()
        with self.store.connect() as connection:
            observations = [self._json_row(connection, "observation_records", item) for item in observation_ids]
            if any(item is None for item in observations):
                raise ValueError("all proposal observations must exist")
            observations = [item for item in observations if item]
            if any(item["review_state"] != "accepted_for_evidence_review" or item["retention_state"] == "purged" for item in observations):
                raise ValueError("proposal observations must be accepted for evidence review and not purged")
            known_times = [item["observed_at"] for item in observations if item["observed_at"]]
            observed_at = _timestamp(specification.get("observed_at") or (min(known_times) if known_times else None)) if (specification.get("observed_at") or known_times) else None
            if not observed_at:
                raise ValueError("an explicit evidence observed_at is required when observation time is unknown")
            valid_from = _timestamp(specification.get("valid_from") or observed_at)
            valid_until = _timestamp(specification["valid_until"]) if specification.get("valid_until") else None
            now = _timestamp(specification.get("created_at"))
            material = {"observation_ids": observation_ids, "proposed_content": specification["proposed_content"], "proposed_evidence_type": specification["proposed_evidence_type"], "scope": specification["scope"], "observed_at": observed_at, "version": 1}
            proposal_id = deterministic_id("oeprop", material)
            existing = self._json_row(connection, "observation_evidence_proposals", proposal_id)
            if existing:
                return {"proposal": existing, "approval": self.runtime._json_row(connection, "approval_records", existing["approval_id"])}
            approval = build_approval_record("observation_evidence.promote", proposal_id, "Review one bounded observation evidence proposal.", specification["scope"], "medium", "May create one governed M1 EvidenceRecord; never memory.", provenance_method="m7_observation_evidence_proposal", requested_at=now)
            proposal = {"id": proposal_id, "observation_ids": observation_ids, "proposed_content": specification["proposed_content"], "proposed_evidence_type": specification["proposed_evidence_type"], "scope": specification["scope"], "confidence": specification["confidence"], "observed_at": observed_at, "valid_from": valid_from, "valid_until": valid_until, "rationale": specification["rationale"], "uncertainty": specification["uncertainty"], "counter_context": list(specification.get("counter_context", [])), "status": "pending_review", "approval_id": approval["id"], "evidence_id": None, "provenance": {"method": "explicit_observation_evidence_proposal", "actor": "owner", "chain": observation_ids}, "created_at": now, "updated_at": now, "version": 1}
            validate("observation-evidence-proposal", proposal)
            self.runtime._insert_approval(connection, approval)
            connection.execute("INSERT INTO observation_evidence_proposals(id,record_json,scope,status,approval_id,evidence_id,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (proposal_id, _canonical(proposal), proposal["scope"], proposal["status"], approval["id"], None, now, now, 1))
            connection.executemany("INSERT INTO observation_proposal_links(proposal_id,observation_id) VALUES (?,?)", [(proposal_id, item) for item in observation_ids])
            self.store._audit(connection, "observation.evidence_proposal_created", "observation_evidence_proposal", proposal_id, {"proposal_id": proposal_id, "observation_ids": observation_ids, "approval_id": approval["id"], "scope": proposal["scope"]})
            return {"proposal": proposal, "approval": approval}

    def decide_evidence_proposal(self, proposal_id: str, decision: str, note: str) -> dict[str, Any]:
        if decision not in {"approved", "rejected"} or not note.strip():
            raise ValueError("proposal decision must be approved or rejected with a note")
        enforce_identity_boundary({"note": note})
        if direct_identity_text_findings(note):
            raise ValueError("proposal decision note is not public-safe")
        self.initialize()
        with self.store.connect() as connection:
            proposal = self._json_row(connection, "observation_evidence_proposals", proposal_id)
            if not proposal:
                raise KeyError(proposal_id)
            if proposal["status"] != "pending_review":
                raise ValueError("proposal has already been decided")
            approval = self.runtime._json_row(connection, "approval_records", proposal["approval_id"])
            if not approval or decision not in APPROVAL_TRANSITIONS[approval["status"]]:
                raise ValueError("proposal approval cannot make this transition")
            now = utc_now()
            approval.update({"status": decision, "decision": decision, "decision_note": note, "decided_at": now, "version": approval["version"] + 1})
            validate("approval", approval)
            connection.execute("UPDATE approval_records SET record_json=?,status=?,decided_at=?,version=? WHERE id=?", (_canonical(approval), decision, now, approval["version"], approval["id"]))
            self.store._audit(connection, "approval.decided", "approval", approval["id"], {"approval_id": approval["id"], "action_type": approval["action_type"], "action_reference": proposal_id, "decision": decision})
            proposal.update({"status": decision, "updated_at": now, "version": proposal["version"] + 1})
            validate("observation-evidence-proposal", proposal)
            connection.execute("UPDATE observation_evidence_proposals SET record_json=?,status=?,updated_at=?,version=? WHERE id=?", (_canonical(proposal), decision, now, proposal["version"], proposal_id))
            self.store._audit(connection, "observation.evidence_proposal_decided", "observation_evidence_proposal", proposal_id, {"proposal_id": proposal_id, "approval_id": approval["id"], "decision": decision})
            return proposal

    def promote_evidence_proposal(self, proposal_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            proposal = self._json_row(connection, "observation_evidence_proposals", proposal_id)
            if not proposal:
                raise KeyError(proposal_id)
            if proposal["status"] == "promoted" and proposal["evidence_id"]:
                evidence = self.store._get_evidence(connection, proposal["evidence_id"])
                assert evidence is not None
                return evidence
            if proposal["status"] != "approved":
                raise ValueError("only an approved observation evidence proposal may be promoted")
            self.runtime._authorize(connection, proposal["approval_id"], "observation_evidence.promote", proposal_id, proposal["scope"])
            observations = [self._json_row(connection, "observation_records", item) for item in proposal["observation_ids"]]
            if any(item is None or item["review_state"] != "accepted_for_evidence_review" for item in observations):
                raise ValueError("supporting observations are no longer eligible for promotion")
            references = [f"observation:{item['id']}:{item['content_fingerprint']}" for item in observations if item]
            evidence = build_evidence(proposal["proposed_content"], proposal["proposed_evidence_type"], "observation_ledger", f"observation-proposal:{proposal_id}", proposal["scope"], proposal["confidence"], proposal["observed_at"], proposal["valid_from"], proposal["valid_until"], "internal", "m7_governed_observation_promotion", "owner_reviewer", references)
            self.store.insert_evidence(connection, evidence)
            now = utc_now()
            proposal.update({"status": "promoted", "evidence_id": evidence["id"], "updated_at": now, "version": proposal["version"] + 1})
            validate("observation-evidence-proposal", proposal)
            connection.execute("UPDATE observation_evidence_proposals SET record_json=?,status='promoted',evidence_id=?,updated_at=?,version=? WHERE id=?", (_canonical(proposal), evidence["id"], now, proposal["version"], proposal_id))
            for item in observations:
                if evidence["id"] not in item["linked_evidence_ids"]:
                    item["linked_evidence_ids"].append(evidence["id"])
                    item["version"] += 1
                    validate("observation", item)
                    connection.execute("UPDATE observation_records SET record_json=?,version=? WHERE id=?", (_canonical(item), item["version"], item["id"]))
            self.store._audit(connection, "observation.evidence_promoted", "observation_evidence_proposal", proposal_id, {"proposal_id": proposal_id, "evidence_id": evidence["id"], "observation_ids": proposal["observation_ids"], "approval_id": proposal["approval_id"]})
            return evidence

    def list_evidence_proposals(self, status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        query = "SELECT record_json FROM observation_evidence_proposals" + (" WHERE status=?" if status else "") + " ORDER BY created_at,id"
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(query, (status,) if status else ())]

    @staticmethod
    def _public_source(record: dict[str, Any]) -> dict[str, Any]:
        return {key: record[key] for key in ("id", "source_type", "approval_id", "status", "collection_mode", "external", "adapter_id", "adapter_version", "created_at", "updated_at", "version")}

    @staticmethod
    def _public_session(record: dict[str, Any]) -> dict[str, Any]:
        return {key: record[key] for key in ("id", "source_id", "requested_operation", "adapter_id", "adapter_version", "started_at", "completed_at", "status", "items_considered", "items_accepted", "items_quarantined", "items_rejected", "duplicates", "observation_ids", "duplicate_observation_ids", "version")}

    @staticmethod
    def _public_observation(record: dict[str, Any]) -> dict[str, Any]:
        if record["privacy_class"] != "public" or record["review_state"] == "quarantined":
            return {key: record[key] for key in ("id", "source_id", "collection_session_id", "adapter_id", "adapter_version", "observed_at", "observed_time_status", "recorded_at", "imported_at", "valid_from", "valid_until", "observation_type", "data_class", "privacy_class", "capture_confidence", "review_state", "retention_state", "retention_expires_at", "content_fingerprint", "identity_status", "secret_status", "linked_evidence_ids", "version")}
        return deepcopy(record)

    @staticmethod
    def _public_evidence_proposal(record: dict[str, Any]) -> dict[str, Any]:
        return {
            **{key: record[key] for key in ("id", "proposed_evidence_type", "confidence", "observed_at", "valid_from", "valid_until", "status", "approval_id", "evidence_id", "created_at", "updated_at", "version")},
            "observation_count": len(record["observation_ids"]),
        }

    def public_snapshot(self) -> dict[str, Any]:
        sources = [self._public_source(item) for item in self.list_sources()]
        sessions = [self._public_session(item) for item in self.list_sessions()]
        observations = [self._public_observation(item) for item in self.list_observations()]
        proposals = [self._public_evidence_proposal(item) for item in self.list_evidence_proposals()]
        return {"sources": sources, "sessions": sessions, "observations": observations, "evidence_proposals": proposals}

    def health(self) -> dict[str, Any]:
        self.initialize()
        errors: list[str] = []
        with self.store.connect() as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"observation_sources", "observation_collection_sessions", "observation_records", "observation_duplicate_links", "observation_evidence_proposals", "observation_proposal_links"}
            missing = sorted(required - tables)
            if missing:
                errors.append("missing_tables:" + ",".join(missing))
            orphan_count = 0
            registry_errors = 0
            source_adapter_states: dict[str, Any] = {}
            if not missing:
                for row in connection.execute("SELECT id,record_json,adapter_id,status FROM observation_sources ORDER BY id"):
                    try:
                        source = json.loads(row[1])
                        validate("observation-source", source)
                        if source["id"] != row[0] or source["adapter_id"] != row[2] or source["status"] != row[3]:
                            raise ValueError("projection mismatch")
                        adapter = self.adapters.get(source["adapter_id"])
                        source_adapter_states[source["id"]] = adapter.availability() if adapter else {"state": "not_configured", "external": False, "background": False}
                    except (json.JSONDecodeError, ValueError):
                        registry_errors += 1
                if registry_errors:
                    errors.append(f"observation_source_registry_errors:{registry_errors}")
                orphan_queries = (
                    "SELECT COUNT(*) FROM observation_collection_sessions s LEFT JOIN observation_sources o ON o.id=s.source_id WHERE o.id IS NULL",
                    "SELECT COUNT(*) FROM observation_records r LEFT JOIN observation_sources o ON o.id=r.source_id LEFT JOIN observation_collection_sessions s ON s.id=r.collection_session_id WHERE o.id IS NULL OR s.id IS NULL",
                    "SELECT COUNT(*) FROM observation_proposal_links l LEFT JOIN observation_records o ON o.id=l.observation_id LEFT JOIN observation_evidence_proposals p ON p.id=l.proposal_id WHERE o.id IS NULL OR p.id IS NULL",
                )
                orphan_count = sum(int(connection.execute(query).fetchone()[0]) for query in orphan_queries)
                if orphan_count:
                    errors.append(f"observation_orphan_references:{orphan_count}")
            counts = {
                "sources": int(connection.execute("SELECT COUNT(*) FROM observation_sources").fetchone()[0]),
                "observations": int(connection.execute("SELECT COUNT(*) FROM observation_records").fetchone()[0]),
                "quarantined": int(connection.execute("SELECT COUNT(*) FROM observation_records WHERE review_state='quarantined'").fetchone()[0]),
                "failed_sessions": int(connection.execute("SELECT COUNT(*) FROM observation_collection_sessions WHERE status='failed'").fetchone()[0]),
                "retention_backlog": int(connection.execute("SELECT COUNT(*) FROM observation_records WHERE retention_state='active' AND retention_expires_at IS NOT NULL AND retention_expires_at<=?", (utc_now(),)).fetchone()[0]),
            }
        return {"healthy": not errors, "optional": True, "schema_version": self.store.schema_version(), "adapter_availability": self.adapters.status(), "source_adapter_states": source_adapter_states, "counts": counts, "orphan_references": orphan_count, "errors": errors}
