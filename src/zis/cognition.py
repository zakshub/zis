"""Deterministic, inspectable Cognitive Engine v0.1.

M4 operates only on explicitly referenced local records and structured inputs.
It creates candidates and analysis artifacts; it never promotes memory, resolves
contradictions, invokes specialists, or claims semantic understanding.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from itertools import combinations
from typing import Any, Iterable

from .contracts import validate
from .identity import direct_identity_text_findings, enforce_identity_boundary
from .ids import deterministic_id
from .runtime import ClassicalRuntime, build_approval_record
from .store import EvidenceStore, utc_now


RULESET_VERSION = "m4.v1"
CONFIDENCE_RANK = {"unknown": 0, "weak": 1, "probable": 2, "strong": 3, "established": 4}
ATTENTION_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

PATTERN_TRANSITIONS = {
    "candidate": {"under_review", "rejected"},
    "under_review": {"supported", "rejected"},
    "supported": {"superseded"},
    "rejected": set(),
    "superseded": set(),
}
HYPOTHESIS_TRANSITIONS = {
    "proposed": {"exploring", "rejected"},
    "exploring": {"supported", "weakened", "rejected", "superseded"},
    "supported": {"weakened", "superseded"},
    "weakened": {"exploring", "rejected", "superseded"},
    "rejected": set(),
    "superseded": set(),
}
IDEA_TRANSITIONS = {
    "spark": {"unclear", "exploring", "parked", "rejected"},
    "unclear": {"exploring", "parked", "rejected"},
    "exploring": {"researching", "promising", "parked", "rejected"},
    "researching": {"promising", "parked", "rejected"},
    "promising": {"ready", "parked", "rejected"},
    "parked": {"exploring", "rejected"},
    "ready": {"parked", "rejected"},
    "rejected": set(),
}
MODEL_UPDATE_TRANSITIONS = {
    "proposed": {"under_review", "rejected"},
    "under_review": {"approved", "rejected"},
    "approved": set(),
    "rejected": set(),
    "applied": set(),
}

SESSION_INPUT_FIELDS = {
    "trigger_reference", "scope", "evidence_ids", "memory_ids", "effective_at",
    "explicit_importance", "structured_tags", "contradiction_candidates",
    "hypotheses", "ideas", "model_update_proposals", "reflection",
}


def _timestamp(value: str | None = None) -> str:
    stamp = value or utc_now()
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return parsed.isoformat().replace("+00:00", "Z")


def _as_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_content(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _provenance(method: str, chain: Iterable[str]) -> dict[str, Any]:
    return {"method": method, "actor": "zis_classical_cognition", "chain": list(dict.fromkeys(chain))}


def _validate_private_input(value: Any) -> None:
    enforce_identity_boundary(value)
    findings = direct_identity_text_findings(value)
    if findings:
        raise ValueError("cognitive input contains direct identity signals: " + ", ".join(findings))


def _temporal_state(record: dict[str, Any], effective_at: str) -> str:
    if record["status"] == "superseded":
        return "superseded"
    if record["status"] == "expired":
        return "expired"
    effective = _as_datetime(effective_at)
    if _as_datetime(record["valid_from"]) > effective:
        return "not_yet_valid"
    if record["valid_until"] and _as_datetime(record["valid_until"]) < effective:
        return "historical"
    if not record["current_interpretation"]:
        return "non_current"
    return "current"


class CognitiveEngine:
    """M4 deterministic cognitive artifacts over the accepted local store."""

    FAMILY_TABLES = {
        "sessions": ("cognitive_sessions", "session"),
        "attention": ("attention_signals", "attention"),
        "associations": ("association_records", "association"),
        "patterns": ("pattern_candidates", "pattern"),
        "hypotheses": ("hypothesis_records", "hypothesis"),
        "ideas": ("idea_records", "idea"),
        "evaluations": ("evaluation_records", "evaluation"),
        "reflections": ("reflection_records", "reflection"),
        "proposals": ("model_update_proposals", "model-update-proposal"),
    }

    def __init__(self, store: EvidenceStore):
        self.store = store
        self.runtime = ClassicalRuntime(store)

    def initialize(self) -> list[int]:
        return self.store.initialize()

    @staticmethod
    def _json_row(connection: sqlite3.Connection, table: str, record_id: str) -> dict[str, Any] | None:
        row = connection.execute(f"SELECT record_json FROM {table} WHERE id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _existing_ids(connection: sqlite3.Connection, table: str) -> set[str]:
        return {row[0] for row in connection.execute(f"SELECT id FROM {table}")}

    def _list(self, table: str, session_id: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        query = f"SELECT record_json FROM {table}"
        values: tuple[str, ...] = ()
        if session_id:
            query += " WHERE session_id=?" if table != "cognitive_sessions" else " WHERE id=?"
            values = (session_id,)
        query += " ORDER BY id"
        with self.store.connect() as connection:
            return [json.loads(row[0]) for row in connection.execute(query, values)]

    def list_family(self, family: str, session_id: str | None = None) -> list[dict[str, Any]]:
        if family not in self.FAMILY_TABLES:
            raise ValueError(f"unknown cognitive family: {family}")
        return self._list(self.FAMILY_TABLES[family][0], session_id)

    def get_record(self, family: str, record_id: str) -> dict[str, Any]:
        if family not in self.FAMILY_TABLES:
            raise ValueError(f"unknown cognitive family: {family}")
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, self.FAMILY_TABLES[family][0], record_id)
            if not record:
                raise KeyError(record_id)
            return record

    def _add_references(self, connection: sqlite3.Connection, session_id: str, artifact_type: str, artifact_id: str, references: Iterable[tuple[str, str, str]]) -> None:
        rows = sorted(set((session_id, artifact_type, artifact_id, ref_type, ref_id, role) for ref_type, ref_id, role in references))
        connection.executemany(
            "INSERT INTO cognitive_references(session_id,artifact_type,artifact_id,reference_type,reference_id,role) VALUES (?,?,?,?,?,?)",
            rows,
        )

    def _insert_attention(self, connection: sqlite3.Connection, record: dict[str, Any]) -> None:
        validate("attention", record)
        connection.execute(
            "INSERT INTO attention_signals(id,record_json,session_id,evidence_id,attention_level,novelty_state,created_at,version) VALUES (?,?,?,?,?,?,?,?)",
            (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["evidence_id"], record["attention_level"], record["novelty_state"], record["created_at"], record["version"]),
        )
        self._add_references(connection, record["session_id"], "attention", record["id"], [("evidence", record["evidence_id"], "subject"), *(("contradiction", item, "attention_basis") for item in record["contradiction_ids"])])
        self.store._audit(connection, "cognition.attention_recorded", "attention", record["id"], {"record": record})

    def _insert_association(self, connection: sqlite3.Connection, record: dict[str, Any]) -> None:
        validate("association", record)
        connection.execute(
            "INSERT INTO association_records(id,record_json,session_id,from_type,from_id,to_type,to_id,relation_type,status,created_at,version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["from_type"], record["from_id"], record["to_type"], record["to_id"], record["relation_type"], record["status"], record["created_at"], record["version"]),
        )
        self._add_references(connection, record["session_id"], "association", record["id"], [(record["from_type"], record["from_id"], "from"), (record["to_type"], record["to_id"], "to")])
        self.store._audit(connection, "cognition.association_recorded", "association", record["id"], {"record": record})

    def _insert_projection(self, connection: sqlite3.Connection, family: str, record: dict[str, Any], references: Iterable[tuple[str, str, str]]) -> None:
        table, contract = self.FAMILY_TABLES[family]
        validate(contract, record)
        enforce_identity_boundary(record)
        if family == "patterns":
            connection.execute("INSERT INTO pattern_candidates(id,record_json,session_id,scope,status,confidence,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["scope"], record["status"], record["confidence"], record["created_at"], record["updated_at"], record["version"]))
        elif family == "hypotheses":
            connection.execute("INSERT INTO hypothesis_records(id,record_json,session_id,scope,status,confidence,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["scope"], record["status"], record["confidence"], record["created_at"], record["updated_at"], record["version"]))
        elif family == "ideas":
            connection.execute("INSERT INTO idea_records(id,record_json,session_id,scope,status,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["scope"], record["status"], record["created_at"], record["updated_at"], record["version"]))
        elif family == "evaluations":
            connection.execute("INSERT INTO evaluation_records(id,record_json,session_id,target_type,target_id,outcome,created_at,version) VALUES (?,?,?,?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["target_type"], record["target_id"], record["outcome"], record["created_at"], record["version"]))
        elif family == "reflections":
            connection.execute("INSERT INTO reflection_records(id,record_json,session_id,created_at,version) VALUES (?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["created_at"], record["version"]))
        elif family == "proposals":
            connection.execute("INSERT INTO model_update_proposals(id,record_json,session_id,target_memory_id,status,approval_id,created_at,updated_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (record["id"], json.dumps(record, ensure_ascii=False, sort_keys=True), record["session_id"], record["target_memory_id"], record["status"], record["approval_id"], record["created_at"], record["updated_at"], record["version"]))
        else:
            raise ValueError(f"unsupported projection family: {family}")
        self._add_references(connection, record["session_id"], family[:-1], record["id"], references)
        entity = {"patterns": "pattern", "hypotheses": "hypothesis", "ideas": "idea", "evaluations": "evaluation", "reflections": "reflection", "proposals": "model_update_proposal"}[family]
        self.store._audit(connection, f"cognition.{entity}_recorded", entity, record["id"], {"record": record})

    @staticmethod
    def _known_contradictions(connection: sqlite3.Connection, evidence_ids: list[str]) -> list[dict[str, Any]]:
        if not evidence_ids:
            return []
        placeholders = ",".join("?" for _ in evidence_ids)
        rows = connection.execute(
            f"SELECT * FROM contradictions WHERE evidence_id_a IN ({placeholders}) AND evidence_id_b IN ({placeholders}) ORDER BY id",
            (*evidence_ids, *evidence_ids),
        )
        return [dict(row) for row in rows]

    @staticmethod
    def _validate_subset(values: Iterable[str], allowed: set[str], label: str) -> list[str]:
        result = sorted(set(values))
        unknown = sorted(set(result) - allowed)
        if unknown:
            raise ValueError(f"{label} contains references outside the explicit session context: {', '.join(unknown)}")
        return result

    def _association(self, session_id: str, created_at: str, left: dict[str, Any], right: dict[str, Any], relation_type: str, reason: str, supporting: Iterable[str], strength: str, status: str = "known") -> dict[str, Any]:
        first, second = sorted((left["id"], right["id"]))
        material = {"session_id": session_id, "from_id": first, "to_id": second, "relation_type": relation_type, "supporting_references": sorted(set(supporting)), "status": status, "version": 1}
        return {
            "id": deterministic_id("assoc", material), "session_id": session_id,
            "from_type": "evidence", "from_id": first, "to_type": "evidence", "to_id": second,
            "relation_type": relation_type, "reason": reason,
            "supporting_references": material["supporting_references"], "strength": strength, "status": status,
            "provenance": _provenance("deterministic_structured_association", material["supporting_references"]),
            "created_at": created_at, "version": 1,
        }

    def run_session(self, specification: dict[str, Any]) -> dict[str, Any]:
        _validate_private_input(specification)
        extra = sorted(set(specification) - SESSION_INPUT_FIELDS)
        if extra:
            raise ValueError("unsupported cognitive input fields: " + ", ".join(extra))
        for required in ("trigger_reference", "scope", "evidence_ids", "effective_at"):
            if not specification.get(required):
                raise ValueError(f"cognitive input requires {required}")
        evidence_ids = sorted(set(specification["evidence_ids"]))
        if not evidence_ids:
            raise ValueError("cognitive session requires explicit evidence IDs")
        memory_ids = sorted(set(specification.get("memory_ids", [])))
        effective_at = _timestamp(specification["effective_at"])
        importance = dict(specification.get("explicit_importance", {}))
        tags = {key: sorted(set(value)) for key, value in specification.get("structured_tags", {}).items()}
        if any(level not in ATTENTION_RANK for level in importance.values()):
            raise ValueError("explicit importance must be low, medium, high or critical")
        if any(not isinstance(value, list) or any(not isinstance(tag, str) or not tag.strip() for tag in value) for value in tags.values()):
            raise ValueError("structured tags must be non-empty strings grouped by evidence ID")
        allowed_evidence = set(evidence_ids)
        self._validate_subset(importance, allowed_evidence, "explicit_importance")
        self._validate_subset(tags, allowed_evidence, "structured_tags")
        self.initialize()
        with self.store.connect() as connection:
            evidence = [self.store._get_evidence(connection, evidence_id) for evidence_id in evidence_ids]
            if any(item is None for item in evidence):
                missing = [evidence_ids[index] for index, item in enumerate(evidence) if item is None]
                raise ValueError("explicit evidence does not exist: " + ", ".join(missing))
            evidence = [item for item in evidence if item is not None]
            memories = [self.runtime._json_row(connection, "memory_records", memory_id) for memory_id in memory_ids]
            if any(item is None for item in memories):
                missing = [memory_ids[index] for index, item in enumerate(memories) if item is None]
                raise ValueError("explicit memory does not exist: " + ", ".join(missing))
            memories = [item for item in memories if item is not None]
            contradictions = self._known_contradictions(connection, evidence_ids)
            stable_input = deepcopy(specification)
            stable_input["evidence_ids"] = evidence_ids
            stable_input["memory_ids"] = memory_ids
            stable_input["effective_at"] = effective_at
            stable_input["structured_tags"] = tags
            stable_input["explicit_importance"] = importance
            input_fingerprint = _fingerprint(stable_input)
            state_fingerprint = _fingerprint({"evidence": evidence, "memories": memories, "contradictions": contradictions})
            session_material = {"input_fingerprint": input_fingerprint, "state_fingerprint": state_fingerprint, "ruleset_version": RULESET_VERSION, "effective_at": effective_at}
            session_id = deterministic_id("cog", session_material)
            existing = self._json_row(connection, "cognitive_sessions", session_id)
            if existing:
                return self._session_result(connection, session_id)
            started_at = utc_now()
            session = {
                "id": session_id, "trigger_reference": specification["trigger_reference"], "scope": specification["scope"],
                "evidence_ids": evidence_ids, "memory_ids": memory_ids, "effective_at": effective_at,
                "started_at": started_at, "completed_at": None, "status": "running", "ruleset_version": RULESET_VERSION,
                "input_fingerprint": input_fingerprint, "state_fingerprint": state_fingerprint, "artifact_ids": [],
                "provenance": _provenance("explicit_deterministic_cognitive_session", [specification["trigger_reference"], *evidence_ids, *memory_ids]),
                "version": 1,
            }
            validate("cognitive-session", session)
            connection.execute("INSERT INTO cognitive_sessions(id,record_json,scope,status,ruleset_version,effective_at,started_at,completed_at,version) VALUES (?,?,?,?,?,?,?,?,?)", (session_id, json.dumps(session, ensure_ascii=False, sort_keys=True), session["scope"], session["status"], RULESET_VERSION, effective_at, started_at, None, 1))
            self.store._audit(connection, "cognition.session_started", "cognitive_session", session_id, {"session": session})

            evidence_by_id = {item["id"]: item for item in evidence}
            contradiction_by_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for contradiction in contradictions:
                contradiction_by_evidence[contradiction["evidence_id_a"]].append(contradiction)
                contradiction_by_evidence[contradiction["evidence_id_b"]].append(contradiction)
            normalized_groups: dict[str, list[str]] = defaultdict(list)
            tag_groups: dict[str, list[str]] = defaultdict(list)
            for item in evidence:
                normalized_groups[_normalize_content(item["content"])].append(item["id"])
                for tag in tags.get(item["id"], []):
                    tag_groups[tag.casefold()].append(item["id"])

            associations: list[dict[str, Any]] = []
            association_keys: set[tuple[str, str, str]] = set()

            def add_association(left: dict[str, Any], right: dict[str, Any], relation: str, reason: str, supporting: Iterable[str], strength: str, status: str = "known") -> None:
                key = (*sorted((left["id"], right["id"])), relation)
                if key in association_keys:
                    return
                association_keys.add(key)
                record = self._association(session_id, started_at, left, right, relation, reason, supporting, strength, status)
                self._insert_association(connection, record)
                associations.append(record)

            contradiction_pairs = {(item["evidence_id_a"], item["evidence_id_b"]): item for item in contradictions}
            for left, right in combinations(evidence, 2):
                pair = tuple(sorted((left["id"], right["id"])))
                contradiction = contradiction_pairs.get(pair)
                if contradiction:
                    add_association(left, right, "known_contradiction", "Existing contradiction record explicitly links both evidence items.", [contradiction["id"], *pair], "established")
                if left.get("supersedes") == right["id"] or right.get("supersedes") == left["id"]:
                    add_association(left, right, "explicit_supersession", "An EvidenceRecord explicitly supersedes the other.", pair, "established")
                if _normalize_content(left["content"]) == _normalize_content(right["content"]):
                    add_association(left, right, "repeated_occurrence", "Normalized content is exactly equal; no semantic equivalence is inferred.", pair, "established")
                if left["source"]["reference"] == right["source"]["reference"]:
                    add_association(left, right, "shared_source", "Both records declare the same source reference.", [left["source"]["reference"], *pair], "strong")
                if left["scope"] == right["scope"]:
                    add_association(left, right, "shared_scope", "Both records declare the same scope.", [left["scope"], *pair], "weak")
                for shared_tag in sorted(set(tags.get(left["id"], [])) & set(tags.get(right["id"], []))):
                    add_association(left, right, "shared_tag", f"Both records explicitly declare structured tag '{shared_tag}'.", [f"tag:{shared_tag}", *pair], "probable")

            for candidate in specification.get("contradiction_candidates", []):
                allowed = {"evidence_id_a", "evidence_id_b", "reason"}
                if set(candidate) - allowed:
                    raise ValueError("contradiction candidate contains unsupported fields")
                a, b = candidate.get("evidence_id_a"), candidate.get("evidence_id_b")
                if not a or not b or a == b or a not in evidence_by_id or b not in evidence_by_id or not str(candidate.get("reason", "")).strip():
                    raise ValueError("contradiction candidate requires two distinct explicit evidence IDs and a reason")
                add_association(evidence_by_id[a], evidence_by_id[b], "contradiction_candidate", candidate["reason"], [a, b], "weak", "candidate")

            attention: list[dict[str, Any]] = []
            for item in evidence:
                normalized_count = len(normalized_groups[_normalize_content(item["content"])])
                tag_count = max((len(tag_groups[tag.casefold()]) for tag in tags.get(item["id"], [])), default=1)
                repetition_count = max(normalized_count, tag_count)
                if normalized_count > 1:
                    novelty_state = "exact_duplicate"
                elif tag_count > 1:
                    peers = [evidence_by_id[peer] for tag in tags.get(item["id"], []) for peer in tag_groups[tag.casefold()] if peer != item["id"]]
                    novelty_state = "repeated_support" if any(peer["record_type"] == item["record_type"] and peer["scope"] == item["scope"] for peer in peers) else "possible_variation"
                elif len(evidence) == 1:
                    novelty_state = "insufficient_basis"
                else:
                    novelty_state = "novel_in_context"
                reasons: list[str] = []
                level = ATTENTION_RANK.get(importance.get(item["id"], "low"), 0)
                if item["id"] in importance:
                    reasons.append(f"explicit_importance:{importance[item['id']]}")
                unresolved = [con for con in contradiction_by_evidence[item["id"]] if con["status"] == "unresolved"]
                if unresolved:
                    level = 3
                    reasons.append("unresolved_known_contradiction")
                if repetition_count >= 3:
                    level = max(level, 2)
                    reasons.append(f"repeated_across_{repetition_count}_explicit_records")
                elif repetition_count == 2:
                    level = max(level, 1)
                    reasons.append("repeated_across_2_explicit_records")
                if item["confidence"] in {"unknown", "weak"}:
                    level = max(level, 1)
                    reasons.append("weak_or_unknown_source_confidence")
                temporal = _temporal_state(item, effective_at)
                if temporal != "current":
                    level = max(level, 1)
                    reasons.append(f"temporal_state:{temporal}")
                if item["scope"] == specification["scope"]:
                    level = max(level, 1)
                    reasons.append("explicit_scope_match")
                if not reasons:
                    reasons.append("no_attention_raising_rule_matched")
                record_material = {"session_id": session_id, "evidence_id": item["id"], "novelty_state": novelty_state, "repetition_count": repetition_count, "ruleset_version": RULESET_VERSION}
                record = {
                    "id": deterministic_id("att", record_material), "session_id": session_id, "evidence_id": item["id"],
                    "attention_level": ("low", "medium", "high", "critical")[level], "reasons": sorted(set(reasons)),
                    "novelty_state": novelty_state, "repetition_count": repetition_count, "temporal_state": temporal,
                    "confidence": item["confidence"], "contradiction_ids": sorted(con["id"] for con in contradiction_by_evidence[item["id"]]),
                    "provenance": _provenance("deterministic_attention_rules", [item["id"], *sorted(con["id"] for con in contradiction_by_evidence[item["id"]])]),
                    "created_at": started_at, "version": 1,
                }
                self._insert_attention(connection, record)
                attention.append(record)

            patterns: list[dict[str, Any]] = []
            pattern_groups: list[tuple[str, str, list[str]]] = []
            for normalized, members in sorted(normalized_groups.items()):
                if len(members) >= 2:
                    pattern_groups.append(("exact_content", _fingerprint(normalized), sorted(members)))
            for tag, members in sorted(tag_groups.items()):
                members = sorted(set(members))
                if len(members) >= 2:
                    pattern_groups.append(("structured_tag", tag, members))
            seen_pattern_bases: set[tuple[str, tuple[str, ...]]] = set()
            for basis_type, basis, members in pattern_groups:
                basis_key = (basis_type, tuple(members))
                if basis_key in seen_pattern_bases:
                    continue
                seen_pattern_bases.add(basis_key)
                related_associations = [association["id"] for association in associations if association["from_id"] in members and association["to_id"] in members and association["relation_type"] in {"repeated_occurrence", "shared_tag"}]
                counters: set[str] = set()
                for contradiction in contradictions:
                    endpoints = {contradiction["evidence_id_a"], contradiction["evidence_id_b"]}
                    if endpoints & set(members):
                        outside = endpoints - set(members)
                        counters.update(outside or endpoints)
                member_confidence = [evidence_by_id[item]["confidence"] for item in members]
                if counters:
                    confidence = "weak"
                elif any(value == "unknown" for value in member_confidence):
                    confidence = "unknown"
                elif any(value == "weak" for value in member_confidence):
                    confidence = "weak"
                elif len(members) >= 3:
                    confidence = "strong"
                else:
                    confidence = "probable"
                description = "Repeated exact normalized content in the explicit session context." if basis_type == "exact_content" else f"Repeated explicit structured tag: {basis}"
                material = {"session_id": session_id, "basis_type": basis_type, "basis": basis, "supporting_evidence_ids": members, "counterevidence_ids": sorted(counters), "version": 1}
                valid_from = max((evidence_by_id[item]["valid_from"] for item in members), key=_as_datetime)
                valid_until_values = [evidence_by_id[item]["valid_until"] for item in members if evidence_by_id[item]["valid_until"]]
                record = {
                    "id": deterministic_id("pat", material), "session_id": session_id, "description": description,
                    "scope": specification["scope"], "supporting_evidence_ids": members,
                    "supporting_association_ids": sorted(related_associations), "counterevidence_ids": sorted(counters),
                    "support_count": len(members), "confidence": confidence, "status": "candidate",
                    "valid_from": valid_from, "valid_until": min(valid_until_values, key=_as_datetime) if valid_until_values else None,
                    "rationale": f"Deterministic {basis_type} basis occurs in {len(members)} distinct EvidenceRecords; repetition is not correctness.",
                    "truth_status": "candidate_not_truth", "is_memory": False,
                    "provenance": _provenance("deterministic_pattern_candidate", [*members, *sorted(related_associations)]),
                    "created_at": started_at, "updated_at": started_at, "version": 1,
                }
                references = [("evidence", item, "support") for item in members] + [("association", item, "support") for item in related_associations] + [("evidence", item, "counterevidence") for item in sorted(counters)]
                self._insert_projection(connection, "patterns", record, references)
                patterns.append(record)

            pattern_ids = {item["id"] for item in patterns} | self._existing_ids(connection, "pattern_candidates")
            existing_idea_ids = self._existing_ids(connection, "idea_records")
            hypotheses: list[dict[str, Any]] = []
            for item in specification.get("hypotheses", []):
                allowed = {"statement", "scope", "originating_pattern_ids", "originating_evidence_ids", "originating_idea_ids", "supporting_evidence_ids", "counterevidence_ids", "confidence", "assumptions", "strengthening_conditions", "falsification_conditions", "valid_from", "valid_until"}
                if set(item) - allowed:
                    raise ValueError("hypothesis input contains unsupported fields")
                support = self._validate_subset(item.get("supporting_evidence_ids", []), allowed_evidence, "hypothesis support")
                if not support:
                    raise ValueError("hypothesis requires explicit supporting evidence")
                origin_evidence = self._validate_subset(item.get("originating_evidence_ids", support), allowed_evidence, "hypothesis origin evidence")
                counters = self._validate_subset(item.get("counterevidence_ids", []), allowed_evidence, "hypothesis counterevidence")
                origin_patterns = self._validate_subset(item.get("originating_pattern_ids", []), pattern_ids, "hypothesis pattern references")
                origin_ideas = self._validate_subset(item.get("originating_idea_ids", []), existing_idea_ids, "hypothesis idea references")
                strengthening = list(item.get("strengthening_conditions", []))
                falsification = list(item.get("falsification_conditions", []))
                if not str(item.get("statement", "")).strip() or not strengthening or not falsification:
                    raise ValueError("hypothesis requires statement, strengthening conditions and falsification conditions")
                confidence = item.get("confidence", "unknown")
                if confidence not in CONFIDENCE_RANK:
                    raise ValueError("unsupported hypothesis confidence")
                if counters:
                    confidence = "weak"
                material = {"session_id": session_id, "statement": item["statement"], "support": support, "counter": counters, "patterns": origin_patterns, "ideas": origin_ideas, "version": 1}
                record = {
                    "id": deterministic_id("hyp", material), "session_id": session_id, "statement": item["statement"],
                    "scope": item.get("scope", specification["scope"]), "originating_pattern_ids": origin_patterns,
                    "originating_evidence_ids": origin_evidence, "originating_idea_ids": origin_ideas,
                    "supporting_evidence_ids": support, "counterevidence_ids": counters, "confidence": confidence,
                    "status": "proposed", "assumptions": list(item.get("assumptions", [])),
                    "strengthening_conditions": strengthening, "falsification_conditions": falsification,
                    "valid_from": _timestamp(item.get("valid_from") or max((evidence_by_id[evidence_id]["valid_from"] for evidence_id in support), key=_as_datetime)),
                    "valid_until": _timestamp(item["valid_until"]) if item.get("valid_until") else None,
                    "truth_status": "untested_interpretation", "is_memory": False,
                    "provenance": _provenance("explicit_testable_hypothesis", [*origin_evidence, *origin_patterns, *origin_ideas, *support, *counters]),
                    "created_at": started_at, "updated_at": started_at, "version": 1,
                }
                references = [("evidence", ref, "support") for ref in support] + [("evidence", ref, "counterevidence") for ref in counters] + [("pattern", ref, "origin") for ref in origin_patterns] + [("idea", ref, "origin") for ref in origin_ideas]
                self._insert_projection(connection, "hypotheses", record, references)
                hypotheses.append(record)

            hypothesis_ids = {item["id"] for item in hypotheses} | self._existing_ids(connection, "hypothesis_records")
            association_ids = {item["id"] for item in associations} | self._existing_ids(connection, "association_records")
            ideas: list[dict[str, Any]] = []
            for item in specification.get("ideas", []):
                allowed = {"statement", "scope", "origin_type", "parent_idea_ids", "evidence_ids", "pattern_ids", "hypothesis_ids", "association_ids", "trigger", "transformations", "rationale", "confidence"}
                if set(item) - allowed:
                    raise ValueError("idea input contains unsupported fields")
                parent_ids = self._validate_subset(item.get("parent_idea_ids", []), existing_idea_ids | {idea["id"] for idea in ideas}, "idea parents")
                idea_evidence = self._validate_subset(item.get("evidence_ids", []), allowed_evidence, "idea evidence")
                idea_patterns = self._validate_subset(item.get("pattern_ids", []), pattern_ids, "idea patterns")
                idea_hypotheses = self._validate_subset(item.get("hypothesis_ids", []), hypothesis_ids, "idea hypotheses")
                idea_associations = self._validate_subset(item.get("association_ids", []), association_ids, "idea associations")
                if not any((parent_ids, idea_evidence, idea_patterns, idea_hypotheses, idea_associations)):
                    raise ValueError("idea requires an explicit deterministic lineage reference")
                if not str(item.get("statement", "")).strip() or not str(item.get("trigger", "")).strip() or not str(item.get("rationale", "")).strip():
                    raise ValueError("idea requires statement, trigger and rationale")
                material = {"session_id": session_id, "statement": item["statement"], "parents": parent_ids, "evidence": idea_evidence, "patterns": idea_patterns, "hypotheses": idea_hypotheses, "associations": idea_associations, "version": 1}
                record = {
                    "id": deterministic_id("idea", material), "session_id": session_id, "statement": item["statement"],
                    "scope": item.get("scope", specification["scope"]), "origin_type": item.get("origin_type", "curiosity"),
                    "parent_idea_ids": parent_ids, "evidence_ids": idea_evidence, "pattern_ids": idea_patterns,
                    "hypothesis_ids": idea_hypotheses, "association_ids": idea_associations,
                    "trigger": item["trigger"], "transformations": list(item.get("transformations", [])),
                    "status": "spark", "rationale": item["rationale"], "truth_status": "idea_not_truth",
                    "provenance": _provenance("explicit_structured_idea_lineage", [*parent_ids, *idea_evidence, *idea_patterns, *idea_hypotheses, *idea_associations]),
                    "confidence": item.get("confidence", "unknown"), "created_at": started_at, "updated_at": started_at, "version": 1,
                }
                references = [("idea", ref, "parent") for ref in parent_ids] + [("evidence", ref, "origin") for ref in idea_evidence] + [("pattern", ref, "origin") for ref in idea_patterns] + [("hypothesis", ref, "origin") for ref in idea_hypotheses] + [("association", ref, "origin") for ref in idea_associations]
                self._insert_projection(connection, "ideas", record, references)
                ideas.append(record)
                existing_idea_ids.add(record["id"])

            attention_by_evidence = {item["evidence_id"]: item for item in attention}
            evaluations: list[dict[str, Any]] = []
            for target_type, items in (("pattern", patterns), ("hypothesis", hypotheses), ("idea", ideas)):
                for target in items:
                    support = target.get("supporting_evidence_ids", target.get("evidence_ids", []))
                    counters = target.get("counterevidence_ids", [])
                    assumptions = target.get("assumptions", [])
                    unresolved_ids = sorted({con["id"] for evidence_id in support for con in contradiction_by_evidence.get(evidence_id, []) if con["status"] == "unresolved"})
                    temporal_states = [attention_by_evidence[evidence_id]["temporal_state"] for evidence_id in support if evidence_id in attention_by_evidence]
                    criteria = [
                        {"criterion": "evidence_support", "finding": "supported" if len(support) >= 2 else ("weak" if support else "unknown"), "rationale": f"{len(support)} explicit supporting evidence record(s).", "supporting_references": support},
                        {"criterion": "counterevidence", "finding": "contradicted" if counters else "supported", "rationale": "Counterevidence remains attached and is never discarded." if counters else "No explicit counterevidence was supplied in this session.", "supporting_references": counters},
                        {"criterion": "contradiction_state", "finding": "contradicted" if unresolved_ids else "supported", "rationale": "Existing unresolved contradictions affect evaluation." if unresolved_ids else "No existing unresolved contradiction links supplied support.", "supporting_references": unresolved_ids},
                        {"criterion": "temporal_relevance", "finding": "current" if temporal_states and all(state == "current" for state in temporal_states) else ("historical" if temporal_states else "unknown"), "rationale": "Temporal finding is derived from explicit evidence validity and lifecycle fields.", "supporting_references": support},
                        {"criterion": "confidence", "finding": "supported" if CONFIDENCE_RANK.get(target.get("confidence", "unknown"), 0) >= 2 else ("weak" if target.get("confidence") == "weak" else "unknown"), "rationale": f"Ordinal confidence is {target.get('confidence', 'unknown')}; it is not a probability.", "supporting_references": [target["id"]]},
                        {"criterion": "scope_fit", "finding": "supported" if target["scope"] == specification["scope"] else "needs_review", "rationale": "Scope is compared exactly; semantic fit is not inferred.", "supporting_references": [target["scope"], specification["scope"]]},
                        {"criterion": "unresolved_assumptions", "finding": "needs_review" if assumptions else "supported", "rationale": f"{len(assumptions)} explicit unresolved assumption(s).", "supporting_references": assumptions},
                    ]
                    if counters or unresolved_ids:
                        outcome = "contradicted"
                    elif len(support) < 1 and target_type != "idea":
                        outcome = "insufficient_evidence"
                    elif assumptions:
                        outcome = "needs_review"
                    elif len(support) >= 2 and CONFIDENCE_RANK.get(target.get("confidence", "unknown"), 0) >= 2 and all(state == "current" for state in temporal_states):
                        outcome = "supported_for_current_scope"
                    elif CONFIDENCE_RANK.get(target.get("confidence", "unknown"), 0) >= 2:
                        outcome = "promising"
                    else:
                        outcome = "weak" if support else "insufficient_evidence"
                    material = {"session_id": session_id, "target_type": target_type, "target_id": target["id"], "criteria": criteria, "version": 1}
                    record = {
                        "id": deterministic_id("eval", material), "session_id": session_id, "target_type": target_type,
                        "target_id": target["id"], "scope": specification["scope"], "criteria": criteria,
                        "outcome": outcome, "decision_authority": False,
                        "provenance": _provenance("deterministic_criteria_evaluation", [target["id"], *support, *counters, *unresolved_ids]),
                        "created_at": started_at, "version": 1,
                    }
                    self._insert_projection(connection, "evaluations", record, [(target_type, target["id"], "target"), *(("evidence", ref, "support") for ref in support), *(("evidence", ref, "counterevidence") for ref in counters), *(("contradiction", ref, "constraint") for ref in unresolved_ids)])
                    evaluations.append(record)

            known_artifact_ids = allowed_evidence | pattern_ids | hypothesis_ids | existing_idea_ids | association_ids | {item["id"] for item in evaluations}
            proposals: list[dict[str, Any]] = []
            for item in specification.get("model_update_proposals", []):
                allowed = {"target_memory_id", "proposed_change", "reason", "supporting_artifact_ids", "counterevidence_ids", "confidence", "impact", "risk"}
                if set(item) - allowed:
                    raise ValueError("model-update proposal input contains unsupported fields")
                target_memory_id = item.get("target_memory_id")
                if target_memory_id not in memory_ids:
                    raise ValueError("model-update target memory must be explicitly supplied to the session")
                supporting = self._validate_subset(item.get("supporting_artifact_ids", []), known_artifact_ids, "model-update support")
                counters = self._validate_subset(item.get("counterevidence_ids", []), allowed_evidence, "model-update counterevidence")
                if not supporting or not str(item.get("proposed_change", "")).strip() or not str(item.get("reason", "")).strip() or not str(item.get("impact", "")).strip():
                    raise ValueError("model-update proposal requires change, reason, impact and supporting artifacts")
                material = {"session_id": session_id, "target_memory_id": target_memory_id, "proposed_change": item["proposed_change"], "supporting": supporting, "counterevidence": counters, "version": 1}
                proposal_id = deterministic_id("mup", material)
                approval = build_approval_record("model_update.approve", proposal_id, item["reason"], specification["scope"], item.get("risk", "high"), item["impact"], provenance_method="m4_model_update_proposal", requested_at=effective_at)
                self.runtime._insert_approval(connection, approval)
                record = {
                    "id": proposal_id, "session_id": session_id, "target_memory_id": target_memory_id,
                    "proposed_change": item["proposed_change"], "reason": item["reason"],
                    "supporting_artifact_ids": supporting, "counterevidence_ids": counters,
                    "confidence": "weak" if counters else item.get("confidence", "unknown"), "impact": item["impact"],
                    "status": "proposed", "required_approval": True, "approval_id": approval["id"], "applied_at": None,
                    "provenance": _provenance("governed_model_update_proposal", [target_memory_id, *supporting, *counters]),
                    "created_at": started_at, "updated_at": started_at, "version": 1,
                }
                reference_types = {"ev_": "evidence", "pat_": "pattern", "hyp_": "hypothesis", "idea_": "idea", "assoc_": "association", "eval_": "evaluation"}
                typed_support = [(next((kind for prefix, kind in reference_types.items() if ref.startswith(prefix)), "artifact"), ref, "support") for ref in supporting]
                refs = [("memory", target_memory_id, "target"), ("approval", approval["id"], "governance"), *typed_support, *(("evidence", ref, "counterevidence") for ref in counters)]
                self._insert_projection(connection, "proposals", record, refs)
                proposals.append(record)

            produced_before_reflection = [item["id"] for family in (attention, associations, patterns, hypotheses, ideas, evaluations, proposals) for item in family]
            unresolved_ids = sorted(item["id"] for item in contradictions if item["status"] == "unresolved")
            reflection_input = specification.get("reflection", {})
            if set(reflection_input) - {"assumptions", "missing_evidence", "reconsiderations"}:
                raise ValueError("reflection input contains unsupported fields")
            uncertainties = sorted({
                *(f"comparison_unsupported:{item['evidence_id']}" for item in attention if item["novelty_state"] == "insufficient_basis"),
                *(f"unresolved_contradiction:{item}" for item in unresolved_ids),
                *(f"temporal_state_uncertain:{item['evidence_id']}:{item['temporal_state']}" for item in attention if item["temporal_state"] != "current"),
            })
            if not patterns:
                uncertainties.append("no_pattern_met_minimum_deterministic_support")
            if not hypotheses:
                uncertainties.append("no_hypothesis_was_explicitly_justified")
            missing_evidence = list(reflection_input.get("missing_evidence", []))
            if len(evidence) < 2:
                missing_evidence.append("additional comparable evidence is required for novelty or repetition conclusions")
            reconsiderations = list(reflection_input.get("reconsiderations", []))
            if unresolved_ids:
                reconsiderations.append("review unresolved contradictions without selecting an automatic winner")
            reflection_material = {"session_id": session_id, "artifacts": sorted(produced_before_reflection), "uncertainties": sorted(set(uncertainties)), "version": 1}
            reflection = {
                "id": deterministic_id("refl", reflection_material), "session_id": session_id,
                "considered_references": [*evidence_ids, *memory_ids], "artifact_ids": sorted(produced_before_reflection),
                "uncertainties": sorted(set(uncertainties)), "unresolved_contradiction_ids": unresolved_ids,
                "assumptions": sorted(set(reflection_input.get("assumptions", []) + [assumption for hypothesis in hypotheses for assumption in hypothesis["assumptions"]])),
                "missing_evidence": sorted(set(missing_evidence)), "reconsiderations": sorted(set(reconsiderations)),
                "model_update_proposal_justified": bool(proposals), "consciousness_claim": False,
                "provenance": _provenance("structured_post_analysis_reflection", [session_id, *evidence_ids, *produced_before_reflection]),
                "created_at": started_at, "version": 1,
            }
            reflection_refs = [("evidence", ref, "considered") for ref in evidence_ids] + [("memory", ref, "considered") for ref in memory_ids] + [("contradiction", ref, "unresolved") for ref in unresolved_ids]
            self._insert_projection(connection, "reflections", reflection, reflection_refs)

            session["artifact_ids"] = sorted([*produced_before_reflection, reflection["id"]])
            session["completed_at"] = utc_now()
            session["status"] = "completed"
            session["version"] = 2
            validate("cognitive-session", session)
            connection.execute("UPDATE cognitive_sessions SET record_json=?,status='completed',completed_at=?,version=2 WHERE id=?", (json.dumps(session, ensure_ascii=False, sort_keys=True), session["completed_at"], session_id))
            self.store._audit(connection, "cognition.session_completed", "cognitive_session", session_id, {"artifact_ids": session["artifact_ids"], "ruleset_version": RULESET_VERSION})
            return self._session_result(connection, session_id)

    def _session_result(self, connection: sqlite3.Connection, session_id: str) -> dict[str, Any]:
        session = self._json_row(connection, "cognitive_sessions", session_id)
        if not session:
            raise KeyError(session_id)
        result: dict[str, Any] = {"session": session}
        for family, (table, _) in self.FAMILY_TABLES.items():
            if family == "sessions":
                continue
            result[family] = [json.loads(row[0]) for row in connection.execute(f"SELECT record_json FROM {table} WHERE session_id=? ORDER BY id", (session_id,))]
        return result

    def session_result(self, session_id: str) -> dict[str, Any]:
        self.initialize()
        with self.store.connect() as connection:
            return self._session_result(connection, session_id)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {family: self.list_family(family) for family in self.FAMILY_TABLES}

    def _transition(self, family: str, record_id: str, status: str, transitions: dict[str, set[str]], approval_id: str | None = None) -> dict[str, Any]:
        table, contract = self.FAMILY_TABLES[family]
        self.initialize()
        with self.store.connect() as connection:
            record = self._json_row(connection, table, record_id)
            if not record:
                raise KeyError(record_id)
            if status not in transitions[record["status"]]:
                raise ValueError(f"invalid {family[:-1]} transition: {record['status']} -> {status}")
            if family == "proposals" and status == "approved":
                self.runtime._authorize(connection, approval_id or "", "model_update.approve", record_id, record["scope"] if "scope" in record else self._json_row(connection, "cognitive_sessions", record["session_id"])["scope"])
            before = deepcopy(record)
            record["status"] = status
            record["updated_at"] = utc_now()
            record["version"] += 1
            validate(contract, record)
            connection.execute(f"UPDATE {table} SET record_json=?,status=?,updated_at=?,version=? WHERE id=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), status, record["updated_at"], record["version"], record_id))
            entity = {"patterns": "pattern", "hypotheses": "hypothesis", "ideas": "idea", "proposals": "model_update_proposal"}[family]
            self.store._audit(connection, f"cognition.{entity}_status_changed", entity, record_id, {"before": before, "after": record, "approval_id": approval_id})
            return record

    def set_pattern_status(self, record_id: str, status: str) -> dict[str, Any]:
        return self._transition("patterns", record_id, status, PATTERN_TRANSITIONS)

    def set_hypothesis_status(self, record_id: str, status: str) -> dict[str, Any]:
        return self._transition("hypotheses", record_id, status, HYPOTHESIS_TRANSITIONS)

    def set_idea_status(self, record_id: str, status: str) -> dict[str, Any]:
        return self._transition("ideas", record_id, status, IDEA_TRANSITIONS)

    def set_model_update_status(self, record_id: str, status: str, approval_id: str | None = None) -> dict[str, Any]:
        if status == "applied":
            raise ValueError("applying model updates belongs to a future Learning Engine milestone")
        return self._transition("proposals", record_id, status, MODEL_UPDATE_TRANSITIONS, approval_id)
