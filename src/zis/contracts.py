"""Dependency-free validation for the portable JSON contracts.

This implements only the JSON Schema Draft 2020-12 keywords required by the
current ZIS contracts. It is not a standards-complete JSON Schema validator.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACTS = {
    "evidence": "EvidenceRecord.schema.json",
    "observation": "ObservationRecord.schema.json",
    "specialist": "SpecialistManifest.schema.json",
    "capability": "CapabilityProposal.schema.json",
    "idea": "IdeaLineage.schema.json",
}


class ContractError(ValueError):
    """Raised when a document does not conform to a ZIS contract."""


def schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas"


def load_schema(contract: str) -> dict[str, Any]:
    try:
        filename = CONTRACTS[contract]
    except KeyError as exc:
        raise ContractError(f"unknown contract: {contract}") from exc
    return json.loads((schema_dir() / filename).read_text(encoding="utf-8"))


def _is_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[expected]


def _validate(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    for branch in schema.get("allOf", []):
        condition = branch.get("if")
        if condition is None:
            errors.extend(_validate(value, branch, path))
        elif not _validate(value, condition, path):
            errors.extend(_validate(value, branch.get("then", {}), path))
        elif "else" in branch:
            errors.extend(_validate(value, branch["else"], path))
    expected = schema.get("type")
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, item) for item in types):
            return [f"{path}: expected {' or '.join(types)}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: unsupported value {value!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: must not be empty")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: invalid format")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
            except ValueError:
                errors.append(f"{path}: must be an ISO 8601 timestamp with timezone")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            errors.append(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(_validate(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value.keys() - properties.keys():
                errors.append(f"{path}.{key}: additional field is not allowed")
        for key, child in properties.items():
            if key in value:
                errors.extend(_validate(value[key], child, f"{path}.{key}"))
    return errors


def validate(contract: str, document: dict[str, Any]) -> None:
    errors = _validate(document, load_schema(contract), "$")
    if errors:
        raise ContractError("; ".join(errors))

