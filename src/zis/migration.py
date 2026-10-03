"""Deterministic, human-gated ZOS evidence migration support."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .contracts import validate
from .ids import deterministic_id
from .records import build_evidence
from .store import EvidenceStore, utc_now


SOURCE_REPOSITORY = "https://github.com/zakshub/zos"
MIGRATION_VERSION = 1

CLASSIFICATION_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("F", (".env", "private/", "secrets/", "credentials", "token", "raw-private"), "Sensitive or secret-bearing source must not be imported."),
    ("D", ("figma/", "design-dna", "design-operating", "writing-model", "ui-trend", "visual_assets", "era-kit"), "Primary specialist knowledge remains outside ZIS core."),
    ("E", ("deploy/", "compose", "dockerfile", "docs/gui/", "control_center", "web_app", "factory"), "ZOS product/runtime implementation is obsolete or incompatible as ZIS architecture."),
    ("B", ("personal-constitution", "evolution-timeline", "capability-os", "skill-matrix", "evidence/derived/", "project.schema"), "Potentially reusable material requires identity scrubbing and human review."),
    ("A", ("zos-constitution", "evidence-rules", "hcos-evidence-hierarchy", "permission-model", "model-update-protocol", "evidence-architecture", "memory-architecture", "src/zos/approvals.py", "src/zos/model_updates.py"), "General concept is directly reusable only as a reviewed ZIS candidate."),
    ("C", ("product-thinking-model", "creative-os", "models/registry.json", "quality-standard", "tests/"), "Useful historical evidence, not ZIS architecture."),
    ("G", ("decision-engine", "blind-spot", "schemas/", "memory", "router"), "Meaning and current validity require human review."),
)

IDENTITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("real_name", re.compile(r"\b(?:real|legal|full)[_ -]?name\b\s*[:=]", re.I)),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")),
    ("employer_or_company_identity", re.compile(r"\b(?:employer|company|organization)[_ -]?name\b\s*[:=]", re.I)),
    ("personal_document_identifier", re.compile(r"\b(?:passport|national[_ -]?id|driver'?s?[_ -]?licen[cs]e)[_ -]?(?:number|id|no)\b\s*[:=]", re.I)),
    ("credential_or_token", re.compile(r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]", re.I)),
    ("account_identifier", re.compile(r"\b(?:account[_ -]?id|user[_ -]?id|customer[_ -]?id)\b\s*[:=]", re.I)),
    ("address_like", re.compile(r"\b\d{1,5}\s+[A-Za-z][A-Za-z .'-]+\s(?:street|st|road|rd|avenue|ave|lane|ln|house)\b", re.I)),
    ("face_or_identity_image", re.compile(r"\b(?:face scan|facial image|passport photo|identity photo|selfie)\b", re.I)),
    ("private_family_identifier", re.compile(r"\b(?:my wife|my husband|my son|my daughter|family identifier)\b", re.I)),
)

SPECIALIST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "designer": ("ux", "ui", "figma", "typography", "design system", "visual design", "product design"),
    "studio": ("photography", "image generation", "camera", "lighting", "visual production", "photo editing"),
    "seo": ("seo", "search ranking", "keyword research", "web venture"),
    "taxbot": ("tax", "taxation", "filing return", "income tax"),
    "finance": ("finance", "financial record", "investment", "banking", "budget"),
    "content": ("publishing", "content calendar", "writing workflow", "editorial operation", "urdu corpus"),
}

CANDIDATE_TO_EVIDENCE = {
    "direct_statement": "user_statement",
    "observation": "observation",
    "inferred_cognitive_pattern": "inference",
    "rule_principle": "external_fact",
    "historical_preference": "user_statement",
    "decision_pattern": "derived_pattern",
    "writing_communication_pattern": "derived_pattern",
    "uncertainty": "hypothesis",
    "contradiction": "hypothesis",
    "obsolete_claim": "external_fact",
}

REVIEW_DECISIONS = {"approve", "reject", "defer", "requires_redaction", "route_to_specialist", "mark_obsolete"}


def fingerprint_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def classify_source_path(source_path: str) -> tuple[str, str]:
    normalized = PurePosixPath(source_path.replace("\\", "/")).as_posix().lower().lstrip("./")
    for classification, markers, rationale in CLASSIFICATION_RULES:
        if any(marker in normalized for marker in markers):
            return classification, rationale
    return "G", "No safe automatic classification rule matched; human review is required."


def privacy_findings(text: str) -> list[str]:
    return sorted({label for label, pattern in IDENTITY_PATTERNS if pattern.search(text)})


def specialist_domains(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(domain for domain, keywords in SPECIALIST_KEYWORDS.items() if any(keyword in lowered for keyword in keywords))


def _safe_source_file(source_root: str | Path, source_path: str) -> Path:
    root = Path(source_root).resolve()
    candidate = (root / source_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("source path escapes the ZOS source root") from exc
    if not candidate.is_file():
        raise ValueError(f"source file not found: {source_path}")
    return candidate


def inspect_source(source_root: str | Path, source_ref: str, source_path: str, source_repository: str = SOURCE_REPOSITORY) -> dict[str, Any]:
    path = _safe_source_file(source_root, source_path)
    content = path.read_bytes()
    fingerprint = fingerprint_bytes(content)
    normalized_path = path.relative_to(Path(source_root).resolve()).as_posix()
    if privacy_findings(normalized_path.replace("/", " ")):
        raise ValueError("source path contains structurally detectable identity data; use a human-safe source path")
    classification, rationale = classify_source_path(normalized_path)
    decoded = content.decode("utf-8", errors="replace")
    findings = privacy_findings(decoded)
    privacy_result = "blocked" if classification == "F" else "review_required"
    identity_status = "excluded" if classification == "F" else "pending_review"
    specialist_result = "route_to_specialist" if classification == "D" else "none_detected"
    now = utc_now()
    material = {"repository": source_repository, "ref": source_ref, "path": normalized_path, "fingerprint": fingerprint, "version": MIGRATION_VERSION}
    manifest = {
        "id": deterministic_id("zsrc", material),
        "source_repository": source_repository,
        "source_ref": source_ref,
        "source_path": normalized_path,
        "content_fingerprint": fingerprint,
        "classification": classification,
        "classification_rationale": rationale,
        "confidence": "unknown" if classification == "G" else "probable",
        "privacy_screening_result": privacy_result,
        "identity_scrub_status": identity_status,
        "specialist_routing_result": specialist_result,
        "extraction_status": "blocked" if classification == "F" else "inventoried",
        "candidate_ids": [],
        "human_review_status": "not_applicable" if classification in {"D", "E", "F"} else "pending",
        "import_status": "blocked" if classification in {"D", "E", "F"} else "not_started",
        "imported_evidence_ids": [],
        "rejection_reason": rationale if classification == "F" else None,
        "extracted_at": now,
        "updated_at": now,
        "migration_version": MIGRATION_VERSION,
        "transformation_history": ["fingerprinted", f"classified:{classification}", f"privacy_findings:{','.join(findings) if findings else 'none'}", "raw_content_not_stored"],
    }
    validate("zos-migration-manifest", manifest)
    return manifest


def source_reference(source: dict[str, Any]) -> str:
    return f"zos:{source['source_repository']}@{source['source_ref']}:{source['source_path']}#{source['content_fingerprint']}"


class ZOSMigrationStore:
    def __init__(self, evidence_store: EvidenceStore):
        self.evidence_store = evidence_store

    def initialize(self) -> list[int]:
        return self.evidence_store.initialize()

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for source_key, target_key in (("candidate_ids_json", "candidate_ids"), ("imported_evidence_ids_json", "imported_evidence_ids"), ("transformation_history_json", "transformation_history")):
            item[target_key] = json.loads(item.pop(source_key))
        validate("zos-migration-manifest", item)
        return item

    @staticmethod
    def _candidate_from_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for source_key, target_key in (("privacy_findings_json", "privacy_findings"), ("specialist_domains_json", "specialist_domains"), ("contradiction_candidate_ids_json", "contradiction_candidate_ids"), ("transformation_notes_json", "transformation_notes")):
            item[target_key] = json.loads(item.pop(source_key))
        validate("zos-migration-candidate", item)
        return item

    def _get_source(self, connection: sqlite3.Connection, source_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM migration_sources WHERE id=?", (source_id,)).fetchone()
        return self._source_from_row(row) if row else None

    def _get_candidate(self, connection: sqlite3.Connection, candidate_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM migration_candidates WHERE id=?", (candidate_id,)).fetchone()
        return self._candidate_from_row(row) if row else None

    def register_source(self, manifest: dict[str, Any]) -> dict[str, Any]:
        validate("zos-migration-manifest", manifest)
        self.initialize()
        with self.evidence_store.connect() as connection:
            existing = self._get_source(connection, manifest["id"])
            if existing:
                return existing
            connection.execute(
                "INSERT INTO migration_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (manifest["id"], manifest["source_repository"], manifest["source_ref"], manifest["source_path"], manifest["content_fingerprint"], manifest["classification"], manifest["classification_rationale"], manifest["confidence"], manifest["privacy_screening_result"], manifest["identity_scrub_status"], manifest["specialist_routing_result"], manifest["extraction_status"], json.dumps(manifest["candidate_ids"]), manifest["human_review_status"], manifest["import_status"], json.dumps(manifest["imported_evidence_ids"]), manifest["rejection_reason"], manifest["extracted_at"], manifest["updated_at"], manifest["migration_version"], json.dumps(manifest["transformation_history"])),
            )
            self.evidence_store._audit(connection, "migration.source_registered", "migration_source", manifest["id"], {"source_path": manifest["source_path"], "fingerprint": manifest["content_fingerprint"], "classification": manifest["classification"]})
        return manifest

    def scan(self, source_root: str | Path, source_ref: str, paths: Iterable[str], source_repository: str = SOURCE_REPOSITORY) -> list[dict[str, Any]]:
        return [self.register_source(inspect_source(source_root, source_ref, path, source_repository)) for path in paths]

    def list_sources(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.evidence_store.connect() as connection:
            return [self._source_from_row(row) for row in connection.execute("SELECT * FROM migration_sources ORDER BY source_path,id")]

    def get_source(self, source_id: str) -> dict[str, Any]:
        self.initialize()
        with self.evidence_store.connect() as connection:
            item = self._get_source(connection, source_id)
            if not item:
                raise KeyError(source_id)
            return item

    @staticmethod
    def build_candidate(source: dict[str, Any], specification: dict[str, Any]) -> dict[str, Any]:
        required = {"candidate_type", "content", "scope", "confidence", "temporal_status", "observed_at"}
        missing = sorted(required - specification.keys())
        if missing:
            raise ValueError("candidate specification missing: " + ", ".join(missing))
        raw_content = str(specification["content"]).strip()
        if not raw_content:
            raise ValueError("candidate content must not be empty")
        raw_scope = str(specification["scope"]).strip()
        raw_notes = [str(note) for note in specification.get("transformation_notes", ["manually_structured_candidate"])]
        screened_text = "\n".join([raw_content, raw_scope, *raw_notes])
        findings = privacy_findings(screened_text)
        domains = specialist_domains(raw_content)
        if findings:
            omitted_fingerprint = fingerprint_bytes(screened_text.encode("utf-8"))
            content = "[BLOCKED: identity-bearing candidate content omitted]"
            content_material = omitted_fingerprint
            scope = "migration.private_candidate"
            transformation_notes = ["identity_bearing_text_omitted", f"omitted_content_fingerprint:{omitted_fingerprint}"]
        else:
            content = raw_content
            content_material = content
            scope = raw_scope
            transformation_notes = raw_notes
        if specification.get("transferable_cognitive_pattern", False):
            transformation_notes.append("transferable_cognitive_pattern_requested")
        transferable = bool(specification.get("transferable_cognitive_pattern", False))
        classification = source["classification"]
        privacy_status = "blocked" if classification == "F" or findings else "review_required"
        identity_status = "excluded" if classification == "F" else "pending_review"
        if classification == "D" or (domains and not transferable):
            specialist_status = "route_to_specialist"
        elif domains:
            specialist_status = "review_required"
        else:
            specialist_status = "none_detected"
        temporal_status = specification["temporal_status"]
        candidate_type = specification["candidate_type"]
        if classification == "F" or privacy_status == "blocked":
            review_status, import_status = "requires_redaction", "blocked"
        elif classification == "D" or specialist_status == "route_to_specialist":
            review_status, import_status = "routed_to_specialist", "blocked"
        elif classification == "E" or temporal_status == "obsolete" or candidate_type == "obsolete_claim":
            review_status, import_status = "obsolete", "blocked"
        else:
            review_status, import_status = "pending", "not_imported"
        material = {
            "source_id": source["id"], "candidate_type": candidate_type, "content_material": content_material,
            "scope": scope, "confidence": specification["confidence"],
            "temporal_status": temporal_status, "observed_at": specification["observed_at"],
            "valid_from": specification.get("valid_from") or specification["observed_at"],
            "valid_until": specification.get("valid_until"), "version": MIGRATION_VERSION,
        }
        now = utc_now()
        item = {
            "id": deterministic_id("zcand", material),
            "source_id": source["id"],
            "candidate_type": candidate_type,
            "content": content,
            "scope": scope,
            "confidence": specification["confidence"],
            "privacy_status": privacy_status,
            "identity_scrub_status": identity_status,
            "privacy_findings": findings,
            "specialist_status": specialist_status,
            "specialist_domains": domains,
            "temporal_status": temporal_status,
            "observed_at": specification["observed_at"],
            "valid_from": specification.get("valid_from") or specification["observed_at"],
            "valid_until": specification.get("valid_until"),
            "contradiction_candidate_ids": sorted(set(specification.get("contradiction_candidate_ids", []))),
            "transformation_notes": transformation_notes,
            "review_status": review_status,
            "review_note": None,
            "reviewed_at": None,
            "import_status": import_status,
            "evidence_id": None,
            "created_at": now,
            "updated_at": now,
            "migration_version": MIGRATION_VERSION,
        }
        validate("zos-migration-candidate", item)
        return item

    def create_candidate(self, specification: dict[str, Any]) -> dict[str, Any]:
        source_id = specification.get("source_id")
        if not source_id:
            raise ValueError("candidate specification requires source_id")
        self.initialize()
        with self.evidence_store.connect() as connection:
            source = self._get_source(connection, source_id)
            if not source:
                raise KeyError(source_id)
            item = self.build_candidate(source, specification)
            existing = self._get_candidate(connection, item["id"])
            if existing:
                return existing
            connection.execute(
                "INSERT INTO migration_candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (item["id"], item["source_id"], item["candidate_type"], item["content"], item["scope"], item["confidence"], item["privacy_status"], item["identity_scrub_status"], json.dumps(item["privacy_findings"]), item["specialist_status"], json.dumps(item["specialist_domains"]), item["temporal_status"], item["observed_at"], item["valid_from"], item["valid_until"], json.dumps(item["contradiction_candidate_ids"]), json.dumps(item["transformation_notes"]), item["review_status"], item["review_note"], item["reviewed_at"], item["import_status"], item["evidence_id"], item["created_at"], item["updated_at"], item["migration_version"]),
            )
            source["candidate_ids"].append(item["id"])
            source["extraction_status"] = "candidate_created"
            source["human_review_status"] = "pending" if item["review_status"] == "pending" else source["human_review_status"]
            source["updated_at"] = utc_now()
            source["transformation_history"].append(f"candidate_created:{item['id']}")
            self._update_source(connection, source)
            self.evidence_store._audit(connection, "migration.candidate_created", "migration_candidate", item["id"], {"source_id": source_id, "candidate_type": item["candidate_type"], "review_status": item["review_status"]})
            return item

    def _update_source(self, connection: sqlite3.Connection, source: dict[str, Any]) -> None:
        validate("zos-migration-manifest", source)
        connection.execute(
            "UPDATE migration_sources SET extraction_status=?,candidate_ids_json=?,human_review_status=?,import_status=?,imported_evidence_ids_json=?,rejection_reason=?,updated_at=?,transformation_history_json=? WHERE id=?",
            (source["extraction_status"], json.dumps(source["candidate_ids"]), source["human_review_status"], source["import_status"], json.dumps(source["imported_evidence_ids"]), source["rejection_reason"], source["updated_at"], json.dumps(source["transformation_history"]), source["id"]),
        )

    def list_candidates(self, review_status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        query = "SELECT * FROM migration_candidates"
        values: tuple[str, ...] = ()
        if review_status:
            query += " WHERE review_status=?"
            values = (review_status,)
        query += " ORDER BY created_at,id"
        with self.evidence_store.connect() as connection:
            return [self._candidate_from_row(row) for row in connection.execute(query, values)]

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        self.initialize()
        with self.evidence_store.connect() as connection:
            item = self._get_candidate(connection, candidate_id)
            if not item:
                raise KeyError(candidate_id)
            return item

    def review_packet(self, candidate_id: str) -> dict[str, Any]:
        """Return all local information a human needs for a review decision."""
        self.initialize()
        with self.evidence_store.connect() as connection:
            candidate = self._get_candidate(connection, candidate_id)
            if not candidate:
                raise KeyError(candidate_id)
            source = self._get_source(connection, candidate["source_id"])
            assert source is not None
            return {"candidate": candidate, "source": source, "source_reference": source_reference(source)}

    def review_candidate(self, candidate_id: str, decision: str, note: str) -> dict[str, Any]:
        if decision not in REVIEW_DECISIONS:
            raise ValueError(f"unsupported review decision: {decision}")
        if not note.strip():
            raise ValueError("review note is required")
        if privacy_findings(note):
            raise ValueError("review note contains structurally detectable identity data")
        self.initialize()
        with self.evidence_store.connect() as connection:
            item = self._get_candidate(connection, candidate_id)
            if not item:
                raise KeyError(candidate_id)
            source = self._get_source(connection, item["source_id"])
            assert source is not None
            if decision == "approve":
                if source["classification"] in {"D", "E", "F"}:
                    raise ValueError(f"classification {source['classification']} cannot be approved for ZIS core import")
                if item["privacy_findings"] or item["privacy_status"] == "blocked":
                    raise ValueError("candidate requires redaction before approval")
                if item["specialist_status"] == "route_to_specialist":
                    raise ValueError("specialist material cannot be approved for ZIS core import")
                if item["temporal_status"] == "obsolete" or item["candidate_type"] == "obsolete_claim":
                    raise ValueError("obsolete material cannot be approved for import")
                item.update({"review_status": "approved", "privacy_status": "reviewed_safe", "identity_scrub_status": "reviewed_safe", "specialist_status": "core_safe", "import_status": "not_imported"})
            else:
                mapping = {"reject": "rejected", "defer": "deferred", "requires_redaction": "requires_redaction", "route_to_specialist": "routed_to_specialist", "mark_obsolete": "obsolete"}
                item["review_status"] = mapping[decision]
                if decision in {"reject", "requires_redaction", "route_to_specialist", "mark_obsolete"}:
                    item["import_status"] = "blocked"
            now = utc_now()
            item.update({"review_note": note, "reviewed_at": now, "updated_at": now})
            validate("zos-migration-candidate", item)
            connection.execute(
                "UPDATE migration_candidates SET privacy_status=?,identity_scrub_status=?,specialist_status=?,review_status=?,review_note=?,reviewed_at=?,import_status=?,updated_at=? WHERE id=?",
                (item["privacy_status"], item["identity_scrub_status"], item["specialist_status"], item["review_status"], note, now, item["import_status"], now, candidate_id),
            )
            event_id = deterministic_id("mrev", {"candidate": candidate_id, "decision": decision, "at": now, "note": note})
            connection.execute("INSERT INTO migration_review_events(event_id,candidate_id,decision,note,occurred_at,version) VALUES (?,?,?,?,?,1)", (event_id, candidate_id, decision, note, now))
            source["human_review_status"] = "completed" if all(candidate["review_status"] != "pending" for candidate in self._candidates_for_source(connection, source["id"], replacement=item)) else "in_review"
            source["updated_at"] = now
            source["transformation_history"].append(f"review:{candidate_id}:{decision}")
            self._update_source(connection, source)
            self.evidence_store._audit(connection, "migration.candidate_reviewed", "migration_candidate", candidate_id, {"decision": decision, "review_event_id": event_id})
            return item

    def _candidates_for_source(self, connection: sqlite3.Connection, source_id: str, replacement: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items = [self._candidate_from_row(row) for row in connection.execute("SELECT * FROM migration_candidates WHERE source_id=?", (source_id,))]
        if replacement:
            items = [replacement if item["id"] == replacement["id"] else item for item in items]
        return items

    def import_candidate(self, candidate_id: str) -> dict[str, Any]:
        self.initialize()
        with self.evidence_store.connect() as connection:
            item = self._get_candidate(connection, candidate_id)
            if not item:
                raise KeyError(candidate_id)
            if item["import_status"] == "imported" and item["evidence_id"]:
                existing = self.evidence_store._get_evidence(connection, item["evidence_id"])
                if existing:
                    return existing
            if item["review_status"] != "approved":
                raise ValueError("candidate requires explicit approval before import")
            if item["privacy_status"] != "reviewed_safe" or item["identity_scrub_status"] != "reviewed_safe":
                raise ValueError("candidate has not passed privacy review")
            if item["specialist_status"] != "core_safe":
                raise ValueError("candidate has not passed specialist-domain review")
            if item["temporal_status"] == "obsolete" or item["candidate_type"] == "obsolete_claim":
                raise ValueError("obsolete candidate cannot be imported")
            source = self._get_source(connection, item["source_id"])
            assert source is not None
            reference = source_reference(source)
            record = build_evidence(
                content=item["content"], record_type=CANDIDATE_TO_EVIDENCE[item["candidate_type"]],
                source_type="zos_migration", source_reference=reference, scope=item["scope"],
                confidence=item["confidence"], observed_at=item["observed_at"], valid_from=item["valid_from"],
                valid_until=item["valid_until"], privacy_class="internal", provenance_method="zos_m2_reviewed_migration",
                provenance_actor="owner_reviewer", source_references=[f"migration-candidate:{candidate_id}"],
            )
            if item["temporal_status"] in {"historical", "superseded"}:
                record["status"] = "expired"
                record["current_interpretation"] = False
                record["valid_until"] = record["valid_until"] or item["observed_at"]
            elif item["temporal_status"] in {"uncertain_current_validity", "contradicted"}:
                record["current_interpretation"] = False
            validate("evidence", record)
            existing = self.evidence_store._get_evidence(connection, record["id"])
            if existing and existing != record:
                comparable_existing = {key: value for key, value in existing.items() if key != "recorded_at"}
                comparable_record = {key: value for key, value in record.items() if key != "recorded_at"}
                if comparable_existing != comparable_record:
                    raise ValueError("deterministic evidence ID already exists with different record data")
                record = existing
            elif not existing:
                self.evidence_store.insert_evidence(connection, record)
            now = utc_now()
            connection.execute("UPDATE migration_candidates SET import_status='imported',evidence_id=?,updated_at=? WHERE id=?", (record["id"], now, candidate_id))
            if record["id"] not in source["imported_evidence_ids"]:
                source["imported_evidence_ids"].append(record["id"])
            candidates = self._candidates_for_source(connection, source["id"])
            imported_ids = {candidate_id}
            imported_ids.update(candidate["id"] for candidate in candidates if candidate["import_status"] == "imported")
            source["import_status"] = "imported" if source["candidate_ids"] and set(source["candidate_ids"]) <= imported_ids else "partially_imported"
            source["updated_at"] = now
            source["transformation_history"].append(f"imported:{candidate_id}:{record['id']}")
            self._update_source(connection, source)
            self._materialize_available_contradictions(connection, candidate_id, record["id"])
            self.evidence_store._audit(connection, "migration.candidate_imported", "migration_candidate", candidate_id, {"source_id": source["id"], "evidence_id": record["id"]})
            return record

    def _materialize_available_contradictions(self, connection: sqlite3.Connection, candidate_id: str, evidence_id: str) -> None:
        current = self._get_candidate(connection, candidate_id)
        assert current is not None
        all_candidates = [self._candidate_from_row(row) for row in connection.execute("SELECT * FROM migration_candidates")]
        for other in all_candidates:
            linked = other["id"] in current["contradiction_candidate_ids"] or candidate_id in other["contradiction_candidate_ids"]
            if linked and other["import_status"] == "imported" and other["evidence_id"]:
                self.evidence_store.insert_contradiction(connection, evidence_id, other["evidence_id"])

    def import_approved(self) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        for item in self.list_candidates("approved"):
            imported.append(self.import_candidate(item["id"]))
        return imported

    def status(self) -> dict[str, Any]:
        sources = self.list_sources()
        candidates = self.list_candidates()
        return {
            "sources": len(sources),
            "classifications": dict(sorted(Counter(item["classification"] for item in sources).items())),
            "candidates": len(candidates),
            "review_statuses": dict(sorted(Counter(item["review_status"] for item in candidates).items())),
            "import_statuses": dict(sorted(Counter(item["import_status"] for item in candidates).items())),
            "evidence_imported": sum(1 for item in candidates if item["import_status"] == "imported"),
        }


def dry_run(source_root: str | Path, source_ref: str, paths: Iterable[str], candidate_specs: Iterable[dict[str, Any]] = (), source_repository: str = SOURCE_REPOSITORY) -> dict[str, Any]:
    sources = [inspect_source(source_root, source_ref, path, source_repository) for path in paths]
    by_id = {source["id"]: source for source in sources}
    by_path = {source["source_path"]: source for source in sources}
    candidates: list[dict[str, Any]] = []
    for specification in candidate_specs:
        specification = dict(specification)
        source = by_id.get(specification.get("source_id")) or by_path.get(specification.get("source_path"))
        if not source:
            raise ValueError("dry-run candidate source_id/source_path was not included in scanned paths")
        specification["source_id"] = source["id"]
        specification.pop("source_path", None)
        candidates.append(ZOSMigrationStore.build_candidate(source, specification))
    return {
        "dry_run": True,
        "durable_mutations": 0,
        "sources_considered": len(sources),
        "classifications": dict(sorted(Counter(item["classification"] for item in sources).items())),
        "candidates_produced": len(candidates),
        "blocked_candidates": sum(1 for item in candidates if item["import_status"] == "blocked"),
        "privacy_review_cases": sum(1 for item in sources if item["privacy_screening_result"] == "review_required") + sum(1 for item in candidates if item["privacy_status"] == "review_required"),
        "specialist_routed_cases": sum(1 for item in sources if item["specialist_routing_result"] == "route_to_specialist") + sum(1 for item in candidates if item["specialist_status"] == "route_to_specialist"),
        "obsolete_cases": sum(1 for item in sources if item["classification"] == "E") + sum(1 for item in candidates if item["review_status"] == "obsolete"),
        "contradiction_cases": sum(1 for item in candidates if item["contradiction_candidate_ids"] or item["candidate_type"] == "contradiction"),
        "eligible_for_review": sum(1 for item in candidates if item["review_status"] == "pending"),
        "eligible_for_import": 0,
        "sources": sources,
        "candidates": candidates,
    }


def load_candidate_specifications(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]

