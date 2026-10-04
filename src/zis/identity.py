"""Conservative structural identity boundary checks.

This is deliberately not presented as a complete anonymizer. Content review is
still required as documented in docs/privacy/IDENTITY_SCRUBBING.md.
"""

from __future__ import annotations

import re
from typing import Any


FORBIDDEN_IDENTITY_FIELDS = {
    "real_name", "full_name", "first_name", "last_name", "face", "face_id",
    "employer", "employer_name", "company", "company_identity", "email",
    "email_address", "phone", "phone_number", "address", "precise_address",
    "account_id", "account_identifier", "credential", "credentials", "token",
    "access_token", "refresh_token", "family_name", "family_identifier",
    "personal_document", "personal_document_id", "api_key", "secret_key",
    "authorization", "authorization_header",
}

DIRECT_IDENTITY_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?:\+\d{8,15}\b|\b\d{2,4}[ ()]\d{3,4}[ -]\d{3,6}\b)")),
    ("credential_or_token", re.compile(r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]", re.I)),
    ("authorization_bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)),
    ("precise_address", re.compile(r"\b\d{1,5}\s+[A-Za-z][A-Za-z .'-]+\s(?:street|st|road|rd|avenue|ave|lane|ln|house)\b", re.I)),
)


def rejected_identity_paths(value: Any, path: str = "$") -> list[str]:
    rejected: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in FORBIDDEN_IDENTITY_FIELDS:
                rejected.append(child_path)
            rejected.extend(rejected_identity_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rejected.extend(rejected_identity_paths(child, f"{path}[{index}]"))
    return rejected


def enforce_identity_boundary(value: Any) -> None:
    paths = rejected_identity_paths(value)
    if paths:
        raise ValueError("direct identity fields are not allowed: " + ", ".join(paths))


def direct_identity_text_findings(value: Any) -> list[str]:
    """Return conservative direct-identifier signals found in string values.

    This is a structural safety gate, not complete anonymization. Human review is
    still required for names, indirect identifiers and context-dependent prose.
    """
    findings: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            findings.update(direct_identity_text_findings(child))
    elif isinstance(value, list):
        for child in value:
            findings.update(direct_identity_text_findings(child))
    elif isinstance(value, str):
        for label, pattern in DIRECT_IDENTITY_TEXT_PATTERNS:
            if pattern.search(value):
                findings.add(label)
    return sorted(findings)

