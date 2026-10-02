from __future__ import annotations

from zis.ids import deterministic_id
from zis.records import build_evidence


STAMP = "2026-10-02T12:00:00Z"
PROVENANCE = {"method": "synthetic_fixture", "actor": "test", "chain": ["fixture:source"]}


def evidence(content: str = "A synthetic observation"):
    return build_evidence(content, "observation", "synthetic_fixture", "fixture:source", "tests", "probable", STAMP, provenance_method="synthetic_fixture", provenance_actor="test")


def observation():
    material = {"summary": "Synthetic signal", "observed_at": STAMP, "source": "fixture:source"}
    return {"id": deterministic_id("obs", material), "source": {"type": "synthetic_fixture", "reference": "fixture:source"}, "source_references": ["fixture:source"], "captured_at": STAMP, "observed_at": STAMP, "summary": "Synthetic signal", "raw_reference": None, "scope": "tests", "status": "captured", "confidence": "weak", "provenance": PROVENANCE, "privacy_class": "public", "identity_scrub_status": "reviewed_safe", "retention_state": "referenced", "linked_evidence_ids": [], "version": 1}


def specialist():
    return {"id": "sp_synthetic", "name": "Synthetic specialist", "purpose": "Contract testing", "capabilities": ["validate fixtures"], "input_contract": "fixture input v1", "output_contract": "fixture output v1", "when_to_use": ["contract tests"], "when_not_to_use": ["production"], "maturity": "experimental", "location": "repository:synthetic", "invocation_modes": ["manual"], "health_check": None, "security_boundary": "No private data", "fallback": "Manual validation", "provenance_requirement": "Return source references", "owner_approval_required_for_changes": True, "status": "proposed", "confidence": "weak", "provenance": PROVENANCE, "created_at": STAMP, "updated_at": STAMP, "source_references": ["fixture:source"], "version": 1}


def capability():
    item_id = deterministic_id("cap", "synthetic capability")
    return {"id": item_id, "created_at": STAMP, "updated_at": STAMP, "observed_need": "Validate a proposal", "evidence_ids": [], "source_references": ["fixture:source"], "current_capabilities_checked": ["manual review"], "problem_frequency": "one_off", "problem_severity": "low", "proposed_solution_level": "no_action", "alternatives": ["manual review"], "expected_value": "Contract coverage", "implementation_cost": "none", "maintenance_cost": "none", "privacy_impact": "none", "security_impact": "none", "architecture_summary": "No build", "reversibility": "easy", "approval_status": "not_required", "approval_record": None, "status": "draft", "provenance": PROVENANCE, "confidence": "weak", "version": 1}


def idea():
    item_id = deterministic_id("idea", "synthetic idea")
    return {"id": item_id, "created_at": STAMP, "updated_at": STAMP, "origin_type": "curiosity", "origin_evidence_ids": [], "source_references": ["fixture:source"], "initial_signal": "Could this contract work?", "questions": ["Is it valid?"], "associations": [], "research_references": [], "hypotheses": [], "concept_versions": ["v1"], "evaluations": [], "specialists_consulted": [], "decisions": [], "approval_references": [], "execution_references": [], "outcome": None, "reflection": None, "learning_ids": [], "status": "spark", "provenance": PROVENANCE, "confidence": "unknown", "version": 1}

