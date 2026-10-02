"""Record construction with deterministic identifiers and explicit defaults."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .contracts import validate
from .ids import deterministic_id
from .store import utc_now


def _timestamp(value: str | None) -> str:
    stamp = value or utc_now()
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return parsed.isoformat().replace("+00:00", "Z")


def build_evidence(
    content: str,
    record_type: str,
    source_type: str,
    source_reference: str,
    scope: str,
    confidence: str = "unknown",
    observed_at: str | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    privacy_class: str = "private",
    provenance_method: str = "manual_entry",
    provenance_actor: str = "owner",
    source_references: list[str] | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    observed = _timestamp(observed_at)
    valid = _timestamp(valid_from or observed)
    until = _timestamp(valid_until) if valid_until else None
    if until and until < valid:
        raise ValueError("valid_until must not precede valid_from")
    references = list(dict.fromkeys([source_reference, *(source_references or [])]))
    material = {
        "record_type": record_type,
        "content": content,
        "source": {"type": source_type, "reference": source_reference},
        "observed_at": observed,
        "scope": scope,
        "version": 1,
    }
    record = {
        "id": deterministic_id("ev", material),
        **material,
        "source_references": references,
        "recorded_at": utc_now(),
        "valid_from": valid,
        "valid_until": until,
        "status": "captured",
        "confidence": confidence,
        "provenance": {"method": provenance_method, "actor": provenance_actor, "chain": references},
        "privacy_class": privacy_class,
        "supersedes": supersedes,
        "superseded_by": None,
        "current_interpretation": True,
        "version": 1,
    }
    validate("evidence", record)
    return record

