import csv
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_store import make_record
from zis.export import export_store
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


if __name__ == "__main__":
    unittest.main()

