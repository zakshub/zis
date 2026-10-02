"""Durable, human-readable exports of the local evidence store."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .store import EvidenceStore, utc_now


def export_store(store: EvidenceStore, destination: str | Path) -> dict[str, Path]:
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    evidence = store.list_evidence()
    contradictions = store.list_contradictions()
    audit = store.audit_events()
    payload = {
        "format": "zis-evidence-export",
        "format_version": 1,
        "exported_at": utc_now(),
        "schema_version": store.schema_version(),
        "evidence": evidence,
        "contradictions": contradictions,
        "audit_events": audit,
    }
    json_path = target / "zis-export.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path = target / "evidence.csv"
    fields = ["id", "record_type", "content", "scope", "status", "confidence", "observed_at", "recorded_at", "valid_from", "valid_until", "source_type", "source_reference", "supersedes", "superseded_by", "current_interpretation", "version"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in evidence:
            writer.writerow({**{key: record.get(key) for key in fields}, "source_type": record["source"]["type"], "source_reference": record["source"]["reference"]})

    markdown_path = target / "SUMMARY.md"
    lines = ["# ZIS Evidence Export", "", f"Exported: {payload['exported_at']}", f"Schema version: {payload['schema_version']}", f"Evidence records: {len(evidence)}", f"Contradictions: {len(contradictions)}", "", "## Evidence", ""]
    for record in evidence:
        lines.extend([f"### {record['id']}", "", f"- Type: {record['record_type']}", f"- Status: {record['status']}", f"- Confidence: {record['confidence']}", f"- Scope: {record['scope']}", f"- Observed: {record['observed_at']}", f"- Source: {record['source']['type']} — `{record['source']['reference']}`", f"- Current interpretation: {str(record['current_interpretation']).lower()}", "", record["content"], ""])
    if contradictions:
        lines.extend(["## Contradictions", ""])
        for item in contradictions:
            lines.append(f"- {item['id']}: {item['evidence_id_a']} ↔ {item['evidence_id_b']} ({item['status']})")
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}

