from __future__ import annotations

from zis.ids import deterministic_id
from zis.records import build_evidence


STAMP = "2026-10-02T12:00:00Z"
PROVENANCE = {"method": "synthetic_fixture", "actor": "test", "chain": ["fixture:source"]}


def evidence(content: str = "A synthetic observation"):
    return build_evidence(content, "observation", "synthetic_fixture", "fixture:source", "tests", "probable", STAMP, provenance_method="synthetic_fixture", provenance_actor="test")


def observation():
    fingerprint = "sha256:" + "1" * 64
    material = {"source_id": "osrc_11111111111111111111", "source_reference": "fixture:source", "content_fingerprint": fingerprint, "explicit_event_id": None, "version": 2}
    return {"id": deterministic_id("obs", material), "source_id": "osrc_11111111111111111111", "collection_session_id": "ocsession_11111111111111111111", "adapter_id": "synthetic_test", "adapter_version": "m7.v1", "observed_at": STAMP, "observed_time_status": "known", "recorded_at": STAMP, "imported_at": STAMP, "valid_from": STAMP, "valid_until": None, "scope": "tests", "observation_type": "observation", "data_class": "synthetic", "content": "Synthetic signal", "structured_payload": None, "source_reference": "fixture:source", "explicit_event_id": None, "provenance": {"source_id": "osrc_11111111111111111111", "collection_session_id": "ocsession_11111111111111111111", "adapter_id": "synthetic_test", "adapter_version": "m7.v1", "source_reference": "fixture:source", "ingestion_method": "synthetic_test", "transformation_notes": ["synthetic_fixture"], "original_privacy_class": "public"}, "privacy_class": "public", "capture_confidence": "strong", "subject_labels": [], "context_labels": ["synthetic"], "review_state": "captured", "retention_state": "active", "retention_expires_at": None, "content_fingerprint": fingerprint, "identity_status": "reviewed_safe", "secret_status": "none_detected", "linked_evidence_ids": [], "version": 1}


def specialist():
    return {"id": "sp_synthetic", "name": "Synthetic specialist", "domain": "synthetic validation", "purpose": "Contract testing", "capabilities": ["validate fixtures"], "input_contract": "fixture input v1", "output_contract": "fixture output v1", "interface_version": "1", "compatible_runtime_versions": ["0.7"], "when_to_use": ["contract tests"], "when_not_to_use": ["production"], "maturity": "experimental", "location": "repository:synthetic", "invocation_modes": ["manual"], "health_check": None, "security_boundary": "No private data", "fallback": "Manual validation", "provenance_requirement": "Return source references", "owner_approval_required_for_changes": True, "status": "proposed", "availability": "unknown", "confidence": "weak", "provenance": PROVENANCE, "created_at": STAMP, "updated_at": STAMP, "source_references": ["fixture:source"], "version": 1}


def capability():
    item_id = deterministic_id("cap", "synthetic capability")
    return {"id": item_id, "created_at": STAMP, "updated_at": STAMP, "observed_need": "Validate a proposal", "evidence_ids": [], "source_references": ["fixture:source"], "current_capabilities_checked": ["manual review"], "problem_frequency": "one_off", "problem_severity": "low", "proposed_solution_level": "no_action", "alternatives": ["manual review"], "expected_value": "Contract coverage", "implementation_cost": "none", "maintenance_cost": "none", "privacy_impact": "none", "security_impact": "none", "architecture_summary": "No build", "reversibility": "easy", "approval_status": "not_required", "approval_record": None, "status": "draft", "provenance": PROVENANCE, "confidence": "weak", "version": 1}


def idea():
    item_id = deterministic_id("idea", "synthetic idea")
    return {"id": item_id, "session_id": "cog_11111111111111111111", "statement": "Could this contract work?", "scope": "tests", "origin_type": "curiosity", "parent_idea_ids": [], "evidence_ids": [], "pattern_ids": [], "hypothesis_ids": [], "association_ids": [], "trigger": "Synthetic contract fixture", "transformations": ["explicit fixture"], "status": "spark", "rationale": "Validate the portable idea contract.", "truth_status": "idea_not_truth", "provenance": PROVENANCE, "confidence": "unknown", "created_at": STAMP, "updated_at": STAMP, "version": 1}

