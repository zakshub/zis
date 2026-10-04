"""Deterministic, local-only Classical Runtime registries and governance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

from . import __version__
from .contracts import validate
from .identity import enforce_identity_boundary
from .ids import deterministic_id
from .store import EvidenceStore, utc_now


LATEST_SCHEMA_VERSION = 7
APPROVAL_TRANSITIONS = {
    "pending": {"approved", "rejected", "deferred", "expired"},
    "deferred": {"approved", "rejected", "expired"},
    "approved": {"revoked"},
    "rejected": set(),
    "expired": set(),
    "revoked": set(),
}
MEMORY_TRANSITIONS = {
    "proposed": {"active", "rejected", "expired"},
    "active": {"superseded", "deprecated", "expired"},
    "superseded": set(),
    "rejected": set(),
    "expired": set(),
    "deprecated": set(),
}
CAPABILITY_TRANSITIONS = {
    "proposed": {"approved", "retired"},
    "approved": {"available", "retired"},
    "available": {"unavailable", "deprecated", "retired"},
    "unavailable": {"available", "deprecated", "retired"},
    "deprecated": {"retired"},
    "retired": set(),
}
SPECIALIST_TRANSITIONS = {
    "proposed": {"approved", "retired"},
    "approved": {"available", "unavailable", "retired"},
    "available": {"unavailable", "retired"},
    "unavailable": {"available", "retired"},
    "retired": set(),
}


def _timestamp(value: str | None = None) -> str:
    stamp = value or utc_now()
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return parsed.isoformat().replace("+00:00", "Z")


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_source_record(
    source_type: str,
    label: str,
    canonical_reference: str,
    reliability: str = "unknown",
    privacy_class: str = "internal",
    status: str = "active",
    provenance_method: str = "manual_registration",
    provenance_actor: str = "owner",
    source_references: Iterable[str] = (),
    created_at: str | None = None,
) -> dict[str, Any]:
    now = _timestamp(created_at)
    chain = list(dict.fromkeys([canonical_reference, *source_references]))
    record = {
        "id": deterministic_id("src", {"source_type": source_type, "canonical_reference": canonical_reference, "version": 1}),
        "source_type": source_type,
        "label": label,
        "canonical_reference": canonical_reference,
        "reliability": reliability,
        "privacy_class": privacy_class,
        "status": status,
        "provenance": {"method": provenance_method, "actor": provenance_actor, "chain": chain},
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    enforce_identity_boundary(record)
    validate("source", record)
    return record


def build_capability_record(
    name: str,
    description: str,
    capability_type: str,
    implementation_reference: str,
    dependencies: Iterable[str] = (),
    approval_required: bool = True,
    proposal_id: str | None = None,
    privacy_impact: str = "No additional private data required.",
    security_impact: str = "No external execution.",
    provenance_method: str = "manual_registration",
    provenance_actor: str = "owner",
    source_references: Iterable[str] = (),
    created_at: str | None = None,
) -> dict[str, Any]:
    now = _timestamp(created_at)
    dependencies = sorted(set(dependencies))
    record = {
        "id": deterministic_id("cr", {"name": name, "capability_type": capability_type, "implementation_reference": implementation_reference, "version": 1}),
        "name": name,
        "description": description,
        "capability_type": capability_type,
        "status": "proposed",
        "implementation_reference": implementation_reference,
        "availability": "unknown",
        "dependencies": dependencies,
        "approval_required": approval_required,
        "approval_id": None,
        "proposal_id": proposal_id,
        "privacy_impact": privacy_impact,
        "security_impact": security_impact,
        "provenance": {"method": provenance_method, "actor": provenance_actor, "chain": list(source_references)},
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    enforce_identity_boundary(record)
    validate("capability-record", record)
    return record


def build_approval_record(
    action_type: str,
    action_reference: str,
    rationale: str,
    scope: str,
    risk: str,
    impact: str,
    provenance_method: str = "manual_request",
    provenance_actor: str = "owner",
    requested_at: str | None = None,
) -> dict[str, Any]:
    now = _timestamp(requested_at)
    material = {"action_type": action_type, "action_reference": action_reference, "scope": scope, "requested_at": now, "version": 1}
    record = {
        "id": deterministic_id("apr", material),
        **material,
        "rationale": rationale,
        "risk": risk,
        "impact": impact,
        "status": "pending",
        "decided_at": None,
        "decision": None,
        "decision_note": None,
        "provenance": {"method": provenance_method, "actor": provenance_actor, "chain": [action_reference]},
    }
    enforce_identity_boundary(record)
    validate("approval", record)
    return record


class ClassicalRuntime:
    """M3 storage, governance and deterministic routing over the M1 store."""

    def __init__(self, store: EvidenceStore):
        self.store = store

    def initialize(self) -> list[int]:
        return self.store.initialize()

    @staticmethod
    def _json_row(connection: sqlite3.Connection, table: str, record_id: str, json_column: str = "record_json") -> dict[str, Any] | None:
        row = connection.execute(f"SELECT {json_column} FROM {table} WHERE id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _list_json(self, table: str, json_column: str = "record_json") -> list[dict[str, Any]]:
        self.initialize()
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(f"SELECT {json_column} FROM {table} ORDER BY id")]

    def register_source(self, record: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(record)
        validate("source", record)
        self.initialize()
        with self.store.connect() as connection:
            if self._json_row(connection, "runtime_sources", record["id"]):
                raise ValueError(f"source already registered: {record['id']}")
            if connection.execute("SELECT 1 FROM runtime_sources WHERE canonical_reference=?", (record["canonical_reference"],)).fetchone():
                raise ValueError("source canonical reference is already registered")
            connection.execute(
                "INSERT INTO runtime_sources(id,record_json,source_type,canonical_reference,status,privacy_class,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)",
                (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["source_type"], record["canonical_reference"], record["status"], record["privacy_class"], record["created_at"], record["updated_at"], record["version"]),
            )
            self.store._audit(connection, "source.registered", "source", record["id"], {"record": record})
        return record

    def list_sources(self) -> list[dict[str, Any]]:
        return self._list_json("runtime_sources")

    def get_source(self, source_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "runtime_sources", source_id)
            if not record:
                raise KeyError(source_id)
            return record

    def set_source_status(self, source_id: str, status: str) -> dict[str, Any]:
        if status not in {"active", "inactive"}:
            raise ValueError("source status must be active or inactive")
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "runtime_sources", source_id)
            if not record:
                raise KeyError(source_id)
            if record["status"] == status:
                raise ValueError("source is already in the requested state")
            before = deepcopy(record)
            record.update({"status": status, "updated_at": utc_now(), "version": record["version"] + 1})
            validate("source", record)
            connection.execute("UPDATE runtime_sources SET record_json=?,status=?,updated_at=?,version=? WHERE id=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), status, record["updated_at"], record["version"], source_id))
            self.store._audit(connection, "source.status_changed", "source", source_id, {"before": before, "after": record})
            return record

    def _insert_approval(self, connection: sqlite3.Connection, record: dict[str, Any]) -> None:
        validate("approval", record)
        connection.execute(
            "INSERT INTO approval_records(id,record_json,action_type,action_reference,scope,status,requested_at,decided_at,version) VALUES (?,?,?,?,?,?,?,?,?)",
            (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["action_type"], record["action_reference"], record["scope"], record["status"], record["requested_at"], record["decided_at"], record["version"]),
        )
        self.store._audit(connection, "approval.requested", "approval", record["id"], {"record": record})

    def request_approval(self, record: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(record)
        validate("approval", record)
        if record["status"] != "pending":
            raise ValueError("new approval records must start pending")
        self.initialize()
        with self.store.connect() as connection:
            if self._json_row(connection, "approval_records", record["id"]):
                raise ValueError(f"approval already exists: {record['id']}")
            self._insert_approval(connection, record)
        return record

    def list_approvals(self) -> list[dict[str, Any]]:
        return self._list_json("approval_records")

    def get_approval(self, approval_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "approval_records", approval_id)
            if not record:
                raise KeyError(approval_id)
            return record

    def decide_approval(self, approval_id: str, decision: str, note: str) -> dict[str, Any]:
        if not note.strip():
            raise ValueError("decision note is required")
        if decision not in {"approved", "rejected", "deferred", "expired", "revoked"}:
            raise ValueError("unsupported approval decision")
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "approval_records", approval_id)
            if not record:
                raise KeyError(approval_id)
            if decision not in APPROVAL_TRANSITIONS[record["status"]]:
                raise ValueError(f"invalid approval transition: {record['status']} -> {decision}")
            before = deepcopy(record)
            record.update({"status": decision, "decision": decision, "decision_note": note, "decided_at": utc_now(), "version": record["version"] + 1})
            enforce_identity_boundary(record)
            validate("approval", record)
            connection.execute("UPDATE approval_records SET record_json=?,status=?,decided_at=?,version=? WHERE id=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), record["status"], record["decided_at"], record["version"], approval_id))
            self.store._audit(connection, "approval.decided", "approval", approval_id, {"before": before, "after": record})
            return record

    def _authorize(self, connection: sqlite3.Connection, approval_id: str, action_type: str, action_reference: str, scope: str) -> dict[str, Any]:
        approval = self._json_row(connection, "approval_records", approval_id)
        if not approval or approval["status"] != "approved":
            raise ValueError("an approved approval record is required")
        expected = (action_type, action_reference, scope)
        actual = (approval["action_type"], approval["action_reference"], approval["scope"])
        if actual != expected:
            raise ValueError("approval does not authorize this exact action and scope")
        return approval

    def authorize(self, approval_id: str, action_type: str, action_reference: str, scope: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            return self._authorize(connection, approval_id, action_type, action_reference, scope)

    def propose_memory(
        self,
        content: str,
        memory_type: str,
        evidence_ids: Iterable[str],
        scope: str,
        confidence: str,
        rationale: str,
        risk: str = "medium",
        impact: str = "Promotes reviewed evidence into durable memory storage.",
        valid_from: str | None = None,
        valid_until: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        evidence_ids = sorted(set(evidence_ids))
        if not evidence_ids:
            raise ValueError("memory requires at least one source evidence ID")
        now = _timestamp(created_at)
        self.initialize()
        with self.store.connect() as connection:
            evidence = [self.store._get_evidence(connection, evidence_id) for evidence_id in evidence_ids]
            if any(item is None for item in evidence):
                raise ValueError("all source evidence records must exist")
            evidence = [item for item in evidence if item is not None]
            start = _timestamp(valid_from or max(item["valid_from"] for item in evidence))
            until = _timestamp(valid_until) if valid_until else None
            if until and until < start:
                raise ValueError("valid_until must not precede valid_from")
            placeholders = ",".join("?" for _ in evidence_ids)
            contradiction_rows = connection.execute(
                f"SELECT status FROM contradictions WHERE evidence_id_a IN ({placeholders}) AND evidence_id_b IN ({placeholders})",
                (*evidence_ids, *evidence_ids),
            ).fetchall()
            conflict_status = "unresolved" if any(row[0] == "unresolved" for row in contradiction_rows) else ("resolved" if contradiction_rows else "none")
            material = {"memory_type": memory_type, "content": content, "source_evidence_ids": evidence_ids, "scope": scope, "valid_from": start, "version": 1}
            memory_id = deterministic_id("mem", material)
            approval = build_approval_record("memory.promote", memory_id, rationale, scope, risk, impact, requested_at=now)
            record = {
                "id": memory_id,
                "memory_type": memory_type,
                "content": content,
                "source_evidence_ids": evidence_ids,
                "scope": scope,
                "status": "proposed",
                "confidence": confidence,
                "conflict_status": conflict_status,
                "valid_from": start,
                "valid_until": until,
                "current_interpretation": False,
                "approval_id": approval["id"],
                "provenance": {"method": "governed_evidence_promotion", "actor": "owner", "chain": evidence_ids},
                "created_at": now,
                "updated_at": now,
                "version": 1,
            }
            enforce_identity_boundary(record)
            validate("memory", record)
            if self._json_row(connection, "memory_records", memory_id):
                raise ValueError(f"memory already exists: {memory_id}")
            self._insert_approval(connection, approval)
            connection.execute(
                "INSERT INTO memory_records(id,record_json,memory_type,scope,status,confidence,current_interpretation,approval_id,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["memory_type"], record["scope"], record["status"], record["confidence"], 0, record["approval_id"], record["created_at"], record["updated_at"], record["version"]),
            )
            connection.executemany("INSERT INTO memory_evidence_links(memory_id,evidence_id) VALUES (?,?)", [(memory_id, evidence_id) for evidence_id in evidence_ids])
            self.store._audit(connection, "memory.proposed", "memory", memory_id, {"record": record})
            return {"memory": record, "approval": approval}

    def list_memories(self) -> list[dict[str, Any]]:
        return self._list_json("memory_records")

    def get_memory(self, memory_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "memory_records", memory_id)
            if not record:
                raise KeyError(memory_id)
            return record

    def set_memory_status(self, memory_id: str, status: str, approval_id: str | None = None) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "memory_records", memory_id)
            if not record:
                raise KeyError(memory_id)
            if status not in MEMORY_TRANSITIONS[record["status"]]:
                raise ValueError(f"invalid memory transition: {record['status']} -> {status}")
            if status == "active":
                self._authorize(connection, approval_id or "", "memory.promote", memory_id, record["scope"])
            before = deepcopy(record)
            record.update({"status": status, "current_interpretation": status == "active", "updated_at": utc_now(), "version": record["version"] + 1})
            validate("memory", record)
            connection.execute("UPDATE memory_records SET record_json=?,status=?,current_interpretation=?,updated_at=?,version=? WHERE id=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), status, int(record["current_interpretation"]), record["updated_at"], record["version"], memory_id))
            self.store._audit(connection, "memory.status_changed", "memory", memory_id, {"before": before, "after": record, "approval_id": approval_id})
            return record

    def register_capability(self, record: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(record)
        validate("capability-record", record)
        if record["status"] != "proposed" or record["availability"] != "unknown":
            raise ValueError("new capabilities must start proposed with unknown availability")
        self.initialize()
        with self.store.connect() as connection:
            if self._json_row(connection, "capability_registry", record["id"]):
                raise ValueError(f"capability already registered: {record['id']}")
            if connection.execute("SELECT 1 FROM capability_registry WHERE name=?", (record["name"],)).fetchone():
                raise ValueError("capability name is already registered")
            for dependency_id in record["dependencies"]:
                if not self._json_row(connection, "capability_registry", dependency_id):
                    raise ValueError(f"capability dependency is not registered: {dependency_id}")
            connection.execute(
                "INSERT INTO capability_registry(id,record_json,name,capability_type,status,availability,approval_required,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["name"], record["capability_type"], record["status"], record["availability"], int(record["approval_required"]), record["created_at"], record["updated_at"], record["version"]),
            )
            connection.executemany("INSERT INTO capability_dependencies(capability_id,dependency_id) VALUES (?,?)", [(record["id"], dependency_id) for dependency_id in record["dependencies"]])
            self.store._audit(connection, "capability.registered", "capability", record["id"], {"record": record})
        return record

    def list_capabilities(self) -> list[dict[str, Any]]:
        return self._list_json("capability_registry")

    def get_capability(self, capability_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "capability_registry", capability_id)
            if not record:
                raise KeyError(capability_id)
            return record

    def set_capability_status(self, capability_id: str, status: str, approval_id: str | None = None) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, "capability_registry", capability_id)
            if not record:
                raise KeyError(capability_id)
            if status not in CAPABILITY_TRANSITIONS[record["status"]]:
                raise ValueError(f"invalid capability transition: {record['status']} -> {status}")
            if status == "approved":
                self._authorize(connection, approval_id or "", "capability.approve", capability_id, "capability_registry")
            if status == "available":
                dependencies = [self._json_row(connection, "capability_registry", dependency_id) for dependency_id in record["dependencies"]]
                if any(item is None or item["status"] != "available" or item["availability"] != "available" for item in dependencies):
                    raise ValueError("all capability dependencies must be available")
            before = deepcopy(record)
            availability = "available" if status == "available" else ("unavailable" if status in {"unavailable", "deprecated", "retired"} else "unknown")
            record.update({"status": status, "availability": availability, "approval_id": approval_id or record["approval_id"], "updated_at": utc_now(), "version": record["version"] + 1})
            validate("capability-record", record)
            connection.execute("UPDATE capability_registry SET record_json=?,status=?,availability=?,updated_at=?,version=? WHERE id=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), status, availability, record["updated_at"], record["version"], capability_id))
            self.store._audit(connection, "capability.status_changed", "capability", capability_id, {"before": before, "after": record, "approval_id": approval_id})
            return record

    def register_specialist(self, manifest: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(manifest)
        validate("specialist", manifest)
        if manifest["status"] != "proposed" or manifest["availability"] != "unknown":
            raise ValueError("new specialists must start proposed with unknown availability")
        self.initialize()
        with self.store.connect() as connection:
            if self._json_row(connection, "specialist_registry", manifest["id"], "manifest_json"):
                raise ValueError(f"specialist already registered: {manifest['id']}")
            if connection.execute("SELECT 1 FROM specialist_registry WHERE name=?", (manifest["name"],)).fetchone():
                raise ValueError("specialist name is already registered")
            connection.execute(
                "INSERT INTO specialist_registry(id,manifest_json,name,domain,status,availability,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)",
                (manifest["id"], json.dumps(manifest, ensure_ascii=False, sort_keys=True), manifest["name"], manifest["domain"], manifest["status"], manifest["availability"], manifest["created_at"], manifest["updated_at"], manifest["version"]),
            )
            self.store._audit(connection, "specialist.registered", "specialist", manifest["id"], {"manifest": manifest})
        return manifest

    def list_specialists(self) -> list[dict[str, Any]]:
        return self._list_json("specialist_registry", "manifest_json")

    def get_specialist(self, specialist_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            manifest = self._json_row(connection, "specialist_registry", specialist_id, "manifest_json")
            if not manifest:
                raise KeyError(specialist_id)
            return manifest

    def set_specialist_status(self, specialist_id: str, status: str, approval_id: str | None = None) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            manifest = self._json_row(connection, "specialist_registry", specialist_id, "manifest_json")
            if not manifest:
                raise KeyError(specialist_id)
            if status not in SPECIALIST_TRANSITIONS[manifest["status"]]:
                raise ValueError(f"invalid specialist transition: {manifest['status']} -> {status}")
            if status == "approved":
                self._authorize(connection, approval_id or "", "specialist.approve", specialist_id, "specialist_registry")
            before = deepcopy(manifest)
            availability = "available" if status == "available" else ("unavailable" if status in {"unavailable", "retired"} else "unknown")
            manifest.update({"status": status, "availability": availability, "updated_at": utc_now(), "version": manifest["version"] + 1})
            validate("specialist", manifest)
            connection.execute("UPDATE specialist_registry SET manifest_json=?,status=?,availability=?,updated_at=?,version=? WHERE id=?", (json.dumps(manifest, ensure_ascii=False, sort_keys=True), status, availability, manifest["updated_at"], manifest["version"], specialist_id))
            self.store._audit(connection, "specialist.status_changed", "specialist", specialist_id, {"before": before, "after": manifest, "approval_id": approval_id})
            return manifest

    def _route(self, connection: sqlite3.Connection, request: dict[str, Any]) -> dict[str, Any]:
        action_type = request.get("action_type") or "unspecified"
        scope = request.get("scope") or "unspecified"
        requested_at = _timestamp(request.get("requested_at"))
        capability_id = request.get("capability_id")
        specialist_id = request.get("specialist_id")
        approval_id = request.get("approval_id")
        action_reference = request.get("action_reference")
        request_material = {"action_type": action_type, "scope": scope, "requested_at": requested_at, "capability_id": capability_id, "specialist_id": specialist_id, "approval_id": approval_id, "action_reference": action_reference, "version": 1}
        request_id = request.get("request_id") or deterministic_id("task", request_material)
        capability = self._json_row(connection, "capability_registry", capability_id) if capability_id else None
        specialist = self._json_row(connection, "specialist_registry", specialist_id, "manifest_json") if specialist_id else None
        approval = self._json_row(connection, "approval_records", approval_id) if approval_id else None
        state_fingerprint = _fingerprint({"schema_version": LATEST_SCHEMA_VERSION, "capability": capability, "specialist": specialist, "approval": approval})
        rules = ["require_explicit_structured_action"]
        selected = "unsupported"
        reason = "The structured action type is not supported."
        unsupported_reason: str | None = "insufficient_information" if action_type == "unspecified" else "unsupported_action_type"
        approval_required = False
        if action_type == "no_action":
            rules.append("no_action_is_valid")
            selected, reason, unsupported_reason = "no_action", "The request explicitly requires no action.", None
        elif action_type == "runtime_status":
            rules.append("runtime_status_is_local_classical_action")
            selected, reason, unsupported_reason = "classical_runtime", "Runtime status is a supported local deterministic action.", None
        elif action_type == "existing_capability":
            rules.extend(["capability_id_required", "capability_must_be_available"])
            if not capability_id:
                reason, unsupported_reason = "A capability ID is required.", "insufficient_information"
            elif not capability:
                reason, unsupported_reason = "The requested capability is not registered.", "capability_not_registered"
            elif capability["status"] != "available" or capability["availability"] != "available":
                reason, unsupported_reason = "The requested capability is not currently available.", "capability_unavailable"
            elif capability["approval_required"]:
                rules.append("approval_must_match_capability_action_and_scope")
                expected = ("capability.execute", capability_id, scope)
                actual = (approval["action_type"], approval["action_reference"], approval["scope"]) if approval and approval["status"] == "approved" else None
                if actual != expected:
                    selected, reason, unsupported_reason, approval_required = "approval_required", "Exact approved authorization is required for this capability action and scope.", None, True
                else:
                    selected, reason, unsupported_reason = "existing_capability", "An available registered capability and exact approval were found.", None
            else:
                selected, reason, unsupported_reason = "existing_capability", "An available registered capability was found.", None
        elif action_type == "specialist":
            rules.extend(["specialist_id_required", "specialist_must_be_available", "specialist_runtime_version_must_match", "m3_does_not_invoke_specialists"])
            if not specialist_id:
                reason, unsupported_reason = "A specialist ID is required.", "insufficient_information"
            elif not specialist:
                reason, unsupported_reason = "The requested specialist is not registered.", "specialist_not_registered"
            elif specialist["status"] != "available" or specialist["availability"] != "available":
                reason, unsupported_reason = "The requested specialist is not currently available.", "specialist_unavailable"
            elif __version__.rsplit(".", 1)[0] not in specialist["compatible_runtime_versions"]:
                reason, unsupported_reason = "The specialist does not declare compatibility with this runtime version.", "specialist_incompatible"
            else:
                selected, reason, unsupported_reason = "specialist_candidate", "The specialist is registered and available; M3 records the candidate route but does not invoke it.", None
        elif action_type == "persistent_change":
            rules.extend(["persistent_change_requires_exact_approval", "m8_capability_sensing_not_implemented"])
            approval_required = True
            if not action_reference:
                reason, unsupported_reason = "A persistent action reference is required.", "insufficient_information"
            else:
                expected = ("persistent_change", action_reference, scope)
                actual = (approval["action_type"], approval["action_reference"], approval["scope"]) if approval and approval["status"] == "approved" else None
                if actual != expected:
                    selected, reason, unsupported_reason = "approval_required", "Persistent change requires exact explicit approval.", None
                else:
                    selected, reason, unsupported_reason, approval_required = "unsupported", "Approval is valid, but M3 does not implement capability sensing or persistent creation.", "persistent_change_execution_not_implemented", False
        decision_material = {**request_material, "request_id": request_id, "selected_route": selected, "reason": reason, "rules_evaluated": rules, "state_fingerprint": state_fingerprint}
        decision = {
            "id": deterministic_id("route", decision_material),
            "request_id": request_id,
            "action_type": action_type,
            "scope": scope,
            "requested_at": requested_at,
            "requested_action_reference": action_reference,
            "requested_capability_id": capability_id,
            "requested_specialist_id": specialist_id,
            "selected_route": selected,
            "reason": reason,
            "rules_evaluated": rules,
            "capability_considered": capability_id,
            "specialist_considered": specialist_id,
            "approval_required": approval_required,
            "approval_id": approval_id,
            "unsupported_reason": unsupported_reason,
            "state_fingerprint": state_fingerprint,
            "created_at": requested_at,
            "version": 1,
        }
        validate("route", decision)
        return decision

    def route(self, request: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(request)
        self.initialize()
        with self.store.connect() as connection:
            return self._route(connection, request)

    def run_task(self, request: dict[str, Any]) -> dict[str, Any]:
        enforce_identity_boundary(request)
        self.initialize()
        with self.store.connect() as connection:
            decision = self._route(connection, request)
            existing = self._json_row(connection, "route_decisions", decision["id"])
            if not existing:
                connection.execute("INSERT INTO route_decisions(id,record_json,request_id,action_type,selected_route,created_at,version) VALUES (?,?,?,?,?,?,?)", (decision["id"], json.dumps(decision, ensure_ascii=False, sort_keys=True), decision["request_id"], decision["action_type"], decision["selected_route"], decision["created_at"], decision["version"]))
                self.store._audit(connection, "route.decided", "route", decision["id"], {"decision": decision})
            operation_id = deterministic_id("op", {"route_decision_id": decision["id"], "version": 1})
            existing_operation = self._json_row(connection, "runtime_operations", operation_id)
            if existing_operation:
                return {"route": existing or decision, "operation": existing_operation}
            selected = decision["selected_route"]
            if selected in {"no_action", "classical_runtime"}:
                execution_status = "completed"
            elif selected in {"existing_capability", "specialist_candidate"}:
                execution_status = "routed"
            elif selected == "approval_required":
                execution_status = "blocked"
            else:
                execution_status = "unsupported"
            result: dict[str, Any] = {"outcome": selected}
            if selected == "classical_runtime":
                result["counts"] = self._counts(connection)
            now = utc_now()
            operation = {
                "id": operation_id,
                "request_id": decision["request_id"],
                "route_decision_id": decision["id"],
                "approval_id": decision["approval_id"],
                "capability_id": decision["capability_considered"],
                "specialist_id": decision["specialist_considered"],
                "execution_status": execution_status,
                "result_metadata": result,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "version": 1,
            }
            validate("operation", operation)
            connection.execute("INSERT INTO runtime_operations(id,record_json,request_id,route_decision_id,approval_id,capability_id,specialist_id,execution_status,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (operation["id"], json.dumps(operation, ensure_ascii=False, sort_keys=True), operation["request_id"], operation["route_decision_id"], operation["approval_id"], operation["capability_id"], operation["specialist_id"], operation["execution_status"], operation["created_at"], operation["updated_at"], operation["version"]))
            self.store._audit(connection, "runtime.operation_recorded", "runtime_operation", operation_id, {"operation": operation})
            return {"route": decision, "operation": operation}

    def list_operations(self) -> list[dict[str, Any]]:
        return self._list_json("runtime_operations")

    def list_routes(self) -> list[dict[str, Any]]:
        return self._list_json("route_decisions")

    @staticmethod
    def _counts(connection: sqlite3.Connection) -> dict[str, int]:
        tables = {
            "evidence": "evidence_records",
            "contradictions": "contradictions",
            "migration_sources": "migration_sources",
            "migration_candidates": "migration_candidates",
            "sources": "runtime_sources",
            "memories": "memory_records",
            "capabilities": "capability_registry",
            "specialists": "specialist_registry",
            "approvals": "approval_records",
            "routes": "route_decisions",
            "operations": "runtime_operations",
            "audit_events": "audit_events",
            "cognitive_sessions": "cognitive_sessions",
            "attention_signals": "attention_signals",
            "associations": "association_records",
            "patterns": "pattern_candidates",
            "hypotheses": "hypothesis_records",
            "ideas": "idea_records",
            "evaluations": "evaluation_records",
            "reflections": "reflection_records",
            "model_update_proposals": "model_update_proposals",
            "ai_requests": "ai_requests",
            "ai_responses": "ai_responses",
            "ai_candidates": "ai_candidates",
            "specialist_requests": "specialist_requests",
            "specialist_responses": "specialist_responses",
            "specialist_receipts": "specialist_provenance_receipts",
            "observation_sources": "observation_sources",
            "observation_sessions": "observation_collection_sessions",
            "observations": "observation_records",
            "observation_duplicates": "observation_duplicate_links",
            "observation_evidence_proposals": "observation_evidence_proposals",
            "observation_proposal_links": "observation_proposal_links",
        }
        return {name: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for name, table in tables.items()}

    def status(self) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            return {"runtime_version": __version__, "schema_version": int(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]), "counts": self._counts(connection), "ai_required": False, "network_required": False}

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        self.initialize()
        tables = {
            "sources": ("runtime_sources", "record_json"),
            "memories": ("memory_records", "record_json"),
            "capabilities": ("capability_registry", "record_json"),
            "specialists": ("specialist_registry", "manifest_json"),
            "approvals": ("approval_records", "record_json"),
            "routes": ("route_decisions", "record_json"),
            "operations": ("runtime_operations", "record_json"),
        }
        with self.store.connect() as connection:
            return {name: [json.loads(row[0]) for row in connection.execute(f"SELECT {column} FROM {table} ORDER BY id")] for name, (table, column) in tables.items()}

    def health(self) -> dict[str, Any]:
        errors: list[str] = []
        required_tables = {"schema_migrations", "evidence_records", "contradictions", "audit_events", "migration_sources", "migration_candidates", "migration_review_events", "runtime_sources", "memory_records", "memory_evidence_links", "capability_registry", "capability_dependencies", "specialist_registry", "approval_records", "route_decisions", "runtime_operations", "cognitive_sessions", "attention_signals", "association_records", "pattern_candidates", "hypothesis_records", "idea_records", "evaluation_records", "reflection_records", "model_update_proposals", "cognitive_references", "ai_requests", "ai_responses", "ai_candidates", "specialist_requests", "specialist_responses", "specialist_provenance_receipts", "observation_sources", "observation_collection_sessions", "observation_records", "observation_duplicate_links", "observation_evidence_proposals", "observation_proposal_links"}
        try:
            self.initialize()
            with self.store.connect() as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    errors.append(f"sqlite_integrity:{integrity}")
                existing_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                missing = sorted(required_tables - existing_tables)
                if missing:
                    errors.append("missing_tables:" + ",".join(missing))
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
                if versions != list(range(1, LATEST_SCHEMA_VERSION + 1)):
                    errors.append("unexpected_migration_state:" + ",".join(map(str, versions)))
                foreign_key_issues = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
                if foreign_key_issues:
                    errors.append(f"foreign_key_issues:{len(foreign_key_issues)}")
                reference_tables = {
                    "evidence": "evidence_records", "memory": "memory_records", "contradiction": "contradictions",
                    "approval": "approval_records", "association": "association_records", "pattern": "pattern_candidates",
                    "hypothesis": "hypothesis_records", "idea": "idea_records", "evaluation": "evaluation_records",
                }
                cognitive_orphans = 0
                if "cognitive_references" in existing_tables:
                    for reference_type, reference_id in connection.execute("SELECT DISTINCT reference_type,reference_id FROM cognitive_references"):
                        table = reference_tables.get(reference_type)
                        if table and not connection.execute(f"SELECT 1 FROM {table} WHERE id=?", (reference_id,)).fetchone():
                            cognitive_orphans += 1
                if cognitive_orphans:
                    errors.append(f"cognitive_orphan_references:{cognitive_orphans}")
                counts = self._counts(connection) if not missing else {}
                schema_version = max(versions, default=0)
        except (sqlite3.DatabaseError, OSError, ValueError) as error:
            integrity, counts, schema_version = "error", {}, 0
            errors.append(f"database_error:{error}")
        return {"healthy": not errors, "database": str(self.store.path), "runtime_version": __version__, "schema_version": schema_version, "integrity_check": integrity, "counts": counts, "errors": errors}
