"""Stable identifiers derived from canonical record material."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def deterministic_id(prefix: str, material: Any) -> str:
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]}"

