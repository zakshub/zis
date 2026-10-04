import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import STAMP
from zis.records import build_evidence
from zis.store import EvidenceStore


def make_record(content: str, record_type: str = "observation", supersedes=None, confidence="unknown"):
    return build_evidence(content, record_type, "synthetic_fixture", f"fixture:{content}", "tests", confidence, STAMP, provenance_method="synthetic_fixture", provenance_actor="test", supersedes=supersedes)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = EvidenceStore(Path(self.temp.name) / "zis.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_database_initialization_and_idempotent_migration(self):
        self.assertEqual(self.store.initialize(), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(self.store.initialize(), [])
        self.assertEqual(self.store.schema_version(), 7)

    def test_provenance_and_confidence_preserved(self):
        record = make_record("Synthetic source-preservation test", confidence="strong")
        self.store.add_evidence(record)
        stored = self.store.get_evidence(record["id"])
        self.assertEqual(stored["provenance"], record["provenance"])
        self.assertEqual(stored["source"], record["source"])
        self.assertEqual(stored["confidence"], "strong")

    def test_supersession_preserves_old_record_and_audit(self):
        old = make_record("Earlier interpretation")
        self.store.add_evidence(old)
        new = make_record("Later interpretation", "correction", old["id"])
        self.store.add_evidence(new)
        previous = self.store.get_evidence(old["id"])
        self.assertEqual(previous["status"], "superseded")
        self.assertEqual(previous["superseded_by"], new["id"])
        self.assertFalse(previous["current_interpretation"])
        self.assertEqual(len(self.store.list_evidence()), 2)
        self.assertIn("evidence.superseded", [event["event_type"] for event in self.store.audit_events()])

    def test_contradiction_preserves_both_and_resolution_rationale(self):
        first = make_record("Preference is A", "user_statement")
        second = make_record("Preference is not A", "user_statement")
        self.store.add_evidence(first)
        self.store.add_evidence(second)
        contradiction = self.store.add_contradiction(first["id"], second["id"])
        self.assertEqual(contradiction["status"], "unresolved")
        resolved = self.store.resolve_contradiction(contradiction["id"], "Later explicit review favored the second statement", "fixture:review")
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["resolution_source_reference"], "fixture:review")
        self.assertIsNotNone(self.store.get_evidence(first["id"]))
        self.assertIsNotNone(self.store.get_evidence(second["id"]))

    def test_deterministic_ids(self):
        first = make_record("Same record")
        second = make_record("Same record")
        self.assertEqual(first["id"], second["id"])

    def test_lifecycle_transition_is_audited(self):
        record = make_record("Lifecycle record")
        self.store.add_evidence(record)
        reviewed = self.store.set_evidence_status(record["id"], "reviewed")
        promoted = self.store.set_evidence_status(record["id"], "promoted")
        self.assertEqual(reviewed["status"], "reviewed")
        self.assertEqual(promoted["status"], "promoted")
        self.assertIn("evidence.promoted", [event["event_type"] for event in self.store.audit_events()])
        with self.assertRaises(ValueError):
            self.store.set_evidence_status(record["id"], "reviewed")

    def test_add_evidence_and_audit_roll_back_together(self):
        record = make_record("Atomic capture")
        with patch.object(self.store, "_audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit failure"):
                self.store.add_evidence(record)
        self.assertIsNone(self.store.get_evidence(record["id"]))

    def test_supersession_and_audit_roll_back_together(self):
        old = make_record("Atomic earlier interpretation")
        self.store.add_evidence(old)
        new = make_record("Atomic later interpretation", "correction", old["id"])
        with patch.object(self.store, "_audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit failure"):
                self.store.add_evidence(new)
        self.assertIsNone(self.store.get_evidence(new["id"]))
        unchanged = self.store.get_evidence(old["id"])
        self.assertEqual(unchanged["status"], "captured")
        self.assertIsNone(unchanged["superseded_by"])
        self.assertTrue(unchanged["current_interpretation"])


if __name__ == "__main__":
    unittest.main()

