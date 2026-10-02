"""Conservative structural identity boundary checks.

This is deliberately not presented as a complete anonymizer. Content review is
still required as documented in docs/privacy/IDENTITY_SCRUBBING.md.
"""

from __future__ import annotations

from typing import Any


FORBIDDEN_IDENTITY_FIELDS = {
    "real_name", "full_name", "first_name", "last_name", "face", "face_id",
    "employer", "employer_name", "company", "company_identity", "email",
    "email_address", "phone", "phone_number", "address", "precise_address",
    "account_id", "account_identifier", "credential", "credentials", "token",
    "access_token", "refresh_token", "family_name", "family_identifier",
    "personal_document", "personal_document_id",
}


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

