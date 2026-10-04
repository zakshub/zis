import csv
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_store import make_record
from zis.export import export_store
from zis.runtime import ClassicalRuntime, build_source_record
from zis.store import EvidenceStore


class ExportTests(unittest.TestCase):
    def test_export_round_trip_and_human_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = EvidenceStore(root / "zis.sqlite3")
            record = make_record("Export round trip")
            store.add_evidence(record)
            paths = export_store(store, root / "export")
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["evidence"], store.list_evidence())
            with paths["csv"].open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["id"], record["id"])
            self.assertIn(record["id"], paths["markdown"].read_text(encoding="utf-8"))

    def test_export_includes_classical_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = EvidenceStore(root / "zis.sqlite3")
            runtime = ClassicalRuntime(store)
            source = build_source_record(
                "synthetic",
                "Synthetic export source",
                "fixture:export-source",
                created_at="2025-01-01T00:00:00Z",
            )
            runtime.register_source(source)

            paths = export_store(store, root / "export")
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))

            self.assertEqual(payload["format"], "zis-cognitive-runtime-export")
            self.assertEqual(payload["format_version"], 3)
            self.assertEqual(payload["runtime"]["sources"], [source])
            self.assertIn("Sources: 1", paths["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

