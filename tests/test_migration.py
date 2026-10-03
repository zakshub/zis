import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import STAMP
from zis.export import export_store
from zis.migration import ZOSMigrationStore, dry_run, fingerprint_bytes, inspect_source
from zis.store import EvidenceStore


class ZOSMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "zos"
        self.root.mkdir()
        self.db = Path(self.temp.name) / "zis.sqlite3"
        self.evidence = EvidenceStore(self.db)
        self.migration = ZOSMigrationStore(self.evidence)
        self.source_path = "core/kernel/ZOS-CONSTITUTION.md"
        self._write(self.source_path, "Synthetic rule source with no private identity data.")
        self.source = self.migration.scan(self.root, "synthetic-ref", [self.source_path])[0]

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, relative_path: str, text: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _spec(self, content="Preserve evidence history", **overrides):
        specification = {
            "source_id": self.source["id"],
            "candidate_type": "rule_principle",
            "content": content,
            "scope": "migration",
            "confidence": "strong",
            "temporal_status": "currently_valid",
            "observed_at": STAMP,
        }
        specification.update(overrides)
        return specification

    def _approved(self, content="Preserve evidence history", **overrides):
        candidate = self.migration.create_candidate(self._spec(content, **overrides))
        return self.migration.review_candidate(candidate["id"], "approve", "Synthetic reviewer confirmed safe core material.")

    def test_migration_manifest_creation(self):
        self.assertEqual(self.source["source_repository"], "https://github.com/zakshub/zos")
        self.assertEqual(self.source["source_ref"], "synthetic-ref")
        self.assertEqual(self.source["classification"], "A")
        self.assertEqual(self.source["confidence"], "probable")
        self.assertIn("raw_content_not_stored", self.source["transformation_history"])

    def test_source_fingerprint_is_deterministic(self):
        content = b"same synthetic bytes"
        self.assertEqual(fingerprint_bytes(content), fingerprint_bytes(content))
        first = inspect_source(self.root, "synthetic-ref", self.source_path)
        second = inspect_source(self.root, "synthetic-ref", self.source_path)
        self.assertEqual(first["content_fingerprint"], second["content_fingerprint"])
        self.assertEqual(first["id"], second["id"])

    def test_classification_is_preserved_in_manifest_store(self):
        expected = {
            "core/kernel/PERSONAL-CONSTITUTION.md": "B",
            "core/models/PRODUCT-THINKING-MODEL.md": "C",
            "core/models/DESIGN-OPERATING-MODEL.md": "D",
            "deploy/Caddyfile": "E",
            "private/.env": "F",
            "unclassified/material.md": "G",
        }
        for path in expected:
            self._write(path, "synthetic classification fixture")
        scanned = self.migration.scan(self.root, "synthetic-ref", expected)
        observed = {item["source_path"]: item["classification"] for item in scanned}
        self.assertEqual(observed, expected)
        stored = self.migration.get_source(self.source["id"])
        self.assertEqual(stored["classification"], "A")
        self.assertEqual(stored["classification_rationale"], self.source["classification_rationale"])

    def test_provenance_is_preserved_on_import(self):
        approved = self._approved()
        record = self.migration.import_candidate(approved["id"])
        self.assertEqual(record["provenance"]["method"], "zos_m2_reviewed_migration")
        self.assertEqual(record["provenance"]["actor"], "owner_reviewer")
        self.assertEqual(record["confidence"], "strong")

    def test_identity_fields_block_candidate(self):
        candidate = self.migration.create_candidate(self._spec("Contact: synthetic.person@example.test"))
        self.assertEqual(candidate["privacy_status"], "blocked")
        self.assertIn("email", candidate["privacy_findings"])
        with self.assertRaisesRegex(ValueError, "redaction"):
            self.migration.review_candidate(candidate["id"], "approve", "Not safe.")

    def test_uncertain_free_text_requires_privacy_review(self):
        candidate = self.migration.create_candidate(self._spec())
        self.assertEqual(candidate["privacy_status"], "review_required")
        self.assertEqual(candidate["identity_scrub_status"], "pending_review")
        self.assertEqual(candidate["review_status"], "pending")

    def test_specialist_material_routes_outside_core(self):
        candidate = self.migration.create_candidate(self._spec("Apply this specific Figma typography rule."))
        self.assertEqual(candidate["specialist_status"], "route_to_specialist")
        self.assertEqual(candidate["review_status"], "routed_to_specialist")
        self.assertEqual(candidate["import_status"], "blocked")

    def test_obsolete_material_is_not_auto_promoted(self):
        path = "deploy/Caddyfile"
        self._write(path, "synthetic obsolete runtime configuration")
        source = self.migration.scan(self.root, "synthetic-ref", [path])[0]
        candidate = self.migration.create_candidate(self._spec(source_id=source["id"], temporal_status="obsolete", candidate_type="obsolete_claim"))
        self.assertEqual(source["classification"], "E")
        self.assertEqual(candidate["review_status"], "obsolete")
        self.assertEqual(candidate["import_status"], "blocked")

    def test_contradiction_candidates_and_sources_are_preserved(self):
        first = self.migration.create_candidate(self._spec("A synthetic preference is active.", candidate_type="historical_preference"))
        second = self.migration.create_candidate(self._spec("A synthetic preference is inactive.", candidate_type="contradiction", contradiction_candidate_ids=[first["id"]], temporal_status="contradicted"))
        self.migration.review_candidate(first["id"], "approve", "Safe synthetic claim one.")
        self.migration.review_candidate(second["id"], "approve", "Safe synthetic conflicting claim.")
        first_record = self.migration.import_candidate(first["id"])
        second_record = self.migration.import_candidate(second["id"])
        contradictions = self.evidence.list_contradictions()
        self.assertEqual(len(contradictions), 1)
        self.assertEqual({contradictions[0]["evidence_id_a"], contradictions[0]["evidence_id_b"]}, {first_record["id"], second_record["id"]})
        self.assertIsNotNone(self.evidence.get_evidence(first_record["id"]))
        self.assertIsNotNone(self.evidence.get_evidence(second_record["id"]))

    def test_approval_is_required_before_import(self):
        candidate = self.migration.create_candidate(self._spec())
        with self.assertRaisesRegex(ValueError, "explicit approval"):
            self.migration.import_candidate(candidate["id"])

    def test_rejected_candidate_cannot_import(self):
        candidate = self.migration.create_candidate(self._spec())
        self.migration.review_candidate(candidate["id"], "reject", "Synthetic review rejected this candidate.")
        with self.assertRaisesRegex(ValueError, "explicit approval"):
            self.migration.import_candidate(candidate["id"])

    def test_approved_candidate_imports_with_temporal_state(self):
        approved = self._approved("Historical synthetic preference", candidate_type="historical_preference", temporal_status="historical")
        record = self.migration.import_candidate(approved["id"])
        self.assertEqual(record["record_type"], "user_statement")
        self.assertEqual(record["status"], "expired")
        self.assertFalse(record["current_interpretation"])

    def test_duplicate_import_is_idempotent(self):
        approved = self._approved()
        first = self.migration.import_candidate(approved["id"])
        second = self.migration.import_candidate(approved["id"])
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.evidence.list_evidence()), 1)

    def test_dry_run_makes_no_durable_mutation(self):
        result = dry_run(self.root, "synthetic-ref", [self.source_path], [{**self._spec(), "source_path": self.source_path, "source_id": "unused"}])
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["durable_mutations"], 0)
        self.assertEqual(result["eligible_for_import"], 0)
        self.assertEqual(result["privacy_review_cases"], 2)
        self.assertEqual(len(self.evidence.list_evidence()), 0)

    def test_failed_import_rolls_back_evidence_and_candidate_state(self):
        approved = self._approved()
        original_audit = self.evidence._audit

        def fail_import_audit(connection, event_type, entity_type, entity_id, payload):
            if event_type == "migration.candidate_imported":
                raise RuntimeError("synthetic final audit failure")
            return original_audit(connection, event_type, entity_type, entity_id, payload)

        with patch.object(self.evidence, "_audit", side_effect=fail_import_audit):
            with self.assertRaisesRegex(RuntimeError, "synthetic final audit failure"):
                self.migration.import_candidate(approved["id"])
        self.assertEqual(len(self.evidence.list_evidence()), 0)
        self.assertEqual(self.migration.get_candidate(approved["id"])["import_status"], "not_imported")

    def test_source_lineage_survives_import(self):
        approved = self._approved()
        record = self.migration.import_candidate(approved["id"])
        reference = record["source"]["reference"]
        self.assertIn(self.source["source_ref"], reference)
        self.assertIn(self.source["source_path"], reference)
        self.assertIn(self.source["content_fingerprint"], reference)
        self.assertIn(f"migration-candidate:{approved['id']}", record["source_references"])

    def test_raw_private_source_content_is_not_stored_or_exported(self):
        secret = "password=synthetic-private-value-never-store"
        path = "private/.env"
        self._write(path, secret)
        source = self.migration.scan(self.root, "synthetic-ref", [path])[0]
        self.assertEqual(source["classification"], "F")
        self.assertEqual(source["privacy_screening_result"], "blocked")
        connection = sqlite3.connect(self.db)
        try:
            serialized_rows = json.dumps(connection.execute("SELECT * FROM migration_sources").fetchall())
        finally:
            connection.close()
        self.assertNotIn(secret, serialized_rows)
        outputs = export_store(self.evidence, Path(self.temp.name) / "export")
        for output in outputs.values():
            self.assertNotIn(secret, output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
