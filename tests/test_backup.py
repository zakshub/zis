import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAMP, specialist
from tests.test_store import make_record
from zis.backup import DURABLE_TABLES, create_backup, restore_backup, verify_backup
from zis.migration import ZOSMigrationStore
from zis.runtime import ClassicalRuntime, build_capability_record, build_source_record
from zis.store import EvidenceStore


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = EvidenceStore(self.root / "source.sqlite3")
        self.runtime = ClassicalRuntime(self.store)
        self.runtime.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _populate_all_families(self):
        first = make_record("Synthetic backup evidence A")
        second = make_record("Synthetic backup evidence B")
        self.store.add_evidence(first)
        self.store.add_evidence(second)
        self.store.add_contradiction(first["id"], second["id"])
        zos_root = self.root / "synthetic-zos"
        zos_file = zos_root / "core" / "kernel" / "ZOS-CONSTITUTION.md"
        zos_file.parent.mkdir(parents=True)
        zos_file.write_text("Synthetic migration source", encoding="utf-8")
        ZOSMigrationStore(self.store).scan(zos_root, "synthetic-ref", ["core/kernel/ZOS-CONSTITUTION.md"])
        self.runtime.register_source(build_source_record("synthetic", "Backup source", "fixture:backup-source", created_at=STAMP))
        self.runtime.propose_memory("Synthetic backup memory", "evidence_backed", [first["id"]], "backup", "strong", "Synthetic backup drill", created_at=STAMP)
        self.runtime.register_capability(build_capability_record("Backup capability", "Synthetic metadata only", "manual_workflow", "manual:backup", created_at=STAMP))
        self.runtime.register_specialist(specialist())
        self.runtime.run_task({"action_type": "runtime_status", "scope": "runtime", "requested_at": STAMP})
        return first, second

    def test_backup_creation_and_checksum_verification(self):
        self._populate_all_families()
        result = create_backup(self.store, self.root / "backups")
        self.assertTrue(Path(result["backup"]).is_file())
        self.assertTrue(Path(result["manifest"]).is_file())
        self.assertTrue(result["verification"]["valid"])
        self.assertEqual(result["metadata"]["schema_version"], 7)
        self.assertEqual(set(result["metadata"]["counts"]), set(DURABLE_TABLES))

    def test_tampered_backup_is_detected(self):
        result = create_backup(self.store, self.root / "backups")
        backup = Path(result["backup"])
        with backup.open("ab") as handle:
            handle.write(b"synthetic-tamper")
        verification = verify_backup(result["manifest"])
        self.assertFalse(verification["valid"])
        self.assertIn("checksum mismatch", verification["errors"][0])

    def test_restore_drill_preserves_important_state(self):
        first, second = self._populate_all_families()
        original_status = self.runtime.status()
        backup = create_backup(self.store, self.root / "backups")
        restored_path = self.root / "restored" / "zis.sqlite3"
        result = restore_backup(backup["manifest"], restored_path)
        restored_store = EvidenceStore(restored_path)
        restored_runtime = ClassicalRuntime(restored_store)
        self.assertTrue(result["restored"])
        self.assertEqual(restored_runtime.status()["counts"], original_status["counts"])
        self.assertIsNotNone(restored_store.get_evidence(first["id"]))
        self.assertIsNotNone(restored_store.get_evidence(second["id"]))
        self.assertEqual(len(restored_store.list_contradictions()), 1)
        self.assertEqual(len(ZOSMigrationStore(restored_store).list_sources()), 1)
        self.assertEqual(len(restored_runtime.list_sources()), 1)
        self.assertEqual(len(restored_runtime.list_memories()), 1)
        self.assertEqual(len(restored_runtime.list_capabilities()), 1)
        self.assertEqual(len(restored_runtime.list_specialists()), 1)
        self.assertEqual(len(restored_runtime.list_approvals()), 1)
        self.assertEqual(len(restored_runtime.list_operations()), 1)
        self.assertEqual(len(restored_store.audit_events()), len(self.store.audit_events()))
        self.assertTrue(restored_runtime.health()["healthy"])

    def test_incompatible_manifest_and_corrupt_backup_are_rejected(self):
        result = create_backup(self.store, self.root / "backups")
        manifest_path = Path(result["manifest"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["runtime_version"] = "99.0.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertFalse(verify_backup(manifest_path)["valid"])
        with self.assertRaisesRegex(ValueError, "verification failed"):
            restore_backup(manifest_path, self.root / "incompatible.sqlite3")
        corrupt = self.root / "corrupt.manifest.json"
        corrupt.write_text("not-json", encoding="utf-8")
        self.assertFalse(verify_backup(corrupt)["valid"])

    def test_failed_restore_does_not_damage_existing_destination(self):
        result = create_backup(self.store, self.root / "backups")
        destination = self.root / "existing.sqlite3"
        original = b"synthetic-existing-database-placeholder"
        destination.write_bytes(original)
        backup = Path(result["backup"])
        with backup.open("ab") as handle:
            handle.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "verification failed"):
            restore_backup(result["manifest"], destination, overwrite=True)
        self.assertEqual(destination.read_bytes(), original)

    def test_restore_refuses_existing_destination_without_explicit_overwrite(self):
        result = create_backup(self.store, self.root / "backups")
        destination = self.root / "existing.sqlite3"
        destination.write_bytes(b"synthetic-existing")
        with self.assertRaisesRegex(ValueError, "explicit overwrite"):
            restore_backup(result["manifest"], destination)


if __name__ == "__main__":
    unittest.main()
