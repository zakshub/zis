from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import STAMP
from zis.ai import AIService
from zis.backup import create_backup, restore_backup
from zis.cognition import CognitiveEngine
from zis.export import export_store
from zis.federation import SpecialistFederation
from zis.observations import (
    FileImportObservationAdapter,
    ManualObservationAdapter,
    ObservationAdapterRegistry,
    ObservationLedger,
    SyntheticObservationAdapter,
)
from zis.runtime import ClassicalRuntime
from zis.store import EvidenceStore


class ObservationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = EvidenceStore(self.root / "zis.sqlite3")
        self.ledger = ObservationLedger(self.store)
        self.runtime = ClassicalRuntime(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def _source_spec(self, **changes):
        value = {
            "name": "Synthetic manual source",
            "source_type": "manual",
            "approval_scope": "observations.synthetic",
            "collection_mode": "explicit_single",
            "allowed_scopes": ["observations.synthetic"],
            "allowed_data_classes": ["general", "preference"],
            "denied_data_classes": ["credential"],
            "retention_policy": {"mode": "manual", "days": None},
            "external": False,
            "adapter_id": "manual",
            "privacy_notes": "Synthetic local-only test source.",
            "created_at": STAMP,
        }
        value.update(changes)
        return value

    def _register(self, **changes):
        return self.ledger.register_source(self._source_spec(**changes))

    def _approve(self, registered):
        approval = self.runtime.decide_approval(registered["approval"]["id"], "approved", "Synthetic owner approval.")
        source = self.ledger.set_source_status(registered["source"]["id"], "approved", approval["id"])
        return source

    def _item(self, **changes):
        value = {
            "observation_type": "observation",
            "data_class": "general",
            "content": "Synthetic bounded observation.",
            "structured_payload": {"synthetic": True},
            "source_reference": "fixture:observation-1",
            "observed_at": "2026-09-01T10:00:00Z",
            "privacy_class": "internal",
            "capture_confidence": "strong",
            "subject_labels": ["synthetic-subject"],
            "context_labels": ["test"],
            "transformation_notes": ["synthetic_manual_entry"],
        }
        value.update(changes)
        return value

    def _capture(self, source=None, item=None, started_at=STAMP):
        source = source or self._approve(self._register())
        return self.ledger.collect(source["id"], source["approval_scope"], "manual_capture", {"item": item or self._item()}, started_at)

    def test_source_registry_and_exact_approval_lifecycle(self):
        registered = self._register()
        self.assertEqual(registered["source"]["status"], "pending")
        self.assertEqual(len(self.ledger.list_sources()), 1)
        with self.assertRaisesRegex(ValueError, "cannot collect"):
            self.ledger.collect(registered["source"]["id"], "observations.synthetic", "manual_capture", {"item": self._item()}, STAMP)
        with self.assertRaisesRegex(ValueError, "approved approval"):
            self.ledger.set_source_status(registered["source"]["id"], "approved")
        source = self._approve(registered)
        self.assertEqual(source["status"], "approved")
        with self.assertRaisesRegex(ValueError, "outside the exact approved"):
            self.ledger.collect(source["id"], "observations.other", "manual_capture", {"item": self._item()}, STAMP)
        self.ledger.set_source_status(source["id"], "paused")
        with self.assertRaisesRegex(ValueError, "paused"):
            self.ledger.collect(source["id"], source["approval_scope"], "manual_capture", {"item": self._item()}, STAMP)
        self.ledger.set_source_status(source["id"], "revoked")
        with self.assertRaisesRegex(ValueError, "revoked"):
            self.ledger.collect(source["id"], source["approval_scope"], "manual_capture", {"item": self._item()}, STAMP)
        retired = self._register(name="Synthetic retired source", created_at="2026-10-04T00:00:01Z")
        self.ledger.set_source_status(retired["source"]["id"], "retired")
        with self.assertRaisesRegex(ValueError, "retired"):
            self.ledger.collect(retired["source"]["id"], retired["source"]["approval_scope"], "manual_capture", {"item": self._item()}, STAMP)

    def test_manual_capture_session_provenance_and_temporal_distinctions(self):
        result = self._capture()
        record = result["observations"][0]
        self.assertEqual(result["session"]["status"], "completed")
        self.assertEqual(result["session"]["items_accepted"], 1)
        self.assertEqual(record["observed_at"], "2026-09-01T10:00:00Z")
        self.assertNotEqual(record["observed_at"], record["recorded_at"])
        self.assertEqual(record["capture_confidence"], "strong")
        self.assertEqual(record["provenance"]["source_id"], record["source_id"])
        self.assertEqual(record["provenance"]["collection_session_id"], result["session"]["id"])
        self.assertEqual(record["provenance"]["adapter_id"], "manual")
        self.assertEqual(self.store.list_evidence(), [])
        self.assertEqual(self.runtime.list_memories(), [])

    def test_unknown_observed_time_is_explicit(self):
        result = self._capture(item=self._item(observed_at=None, source_reference="fixture:unknown-time"))
        record = result["observations"][0]
        self.assertIsNone(record["observed_at"])
        self.assertEqual(record["observed_time_status"], "unknown")
        self.assertIsNone(record["valid_from"])

    def test_exact_duplicate_is_linked_without_multiplication(self):
        source = self._approve(self._register())
        first = self._capture(source, started_at="2026-10-04T00:00:01Z")
        second = self._capture(source, started_at="2026-10-04T00:00:02Z")
        self.assertEqual(len(self.ledger.list_observations()), 1)
        self.assertEqual(second["session"]["duplicates"], 1)
        self.assertEqual(second["session"]["duplicate_observation_ids"], [first["observations"][0]["id"]])

    def test_restricted_denied_and_secret_items_are_content_free_quarantine(self):
        source = self._approve(self._register())
        restricted = self._capture(source, self._item(source_reference="fixture:restricted", privacy_class="restricted"), "2026-10-04T00:00:03Z")["observations"][0]
        denied = self._capture(source, self._item(source_reference="fixture:denied", data_class="credential"), "2026-10-04T00:00:04Z")["observations"][0]
        secret_value = "password=synthetic-secret-value"
        secret = self._capture(source, self._item(source_reference="fixture:secret", privacy_class="private", content=secret_value), "2026-10-04T00:00:05Z")["observations"][0]
        for record in (restricted, denied, secret):
            self.assertEqual(record["review_state"], "quarantined")
            self.assertIsNone(record["content"])
        self.assertEqual(secret["secret_status"], "suspected_quarantined")
        self.assertNotIn(secret_value, json.dumps(self.store.audit_events()))
        self.assertNotIn(secret_value.encode(), self.store.path.read_bytes())
        exported = export_store(self.store, self.root / "secret-export")
        self.assertNotIn(secret_value, exported["json"].read_text(encoding="utf-8"))
        self.assertEqual(len(self.ledger.list_quarantine()), 3)

    def test_private_identity_stays_local_and_public_safe_export_redacts_it(self):
        source = self._approve(self._register())
        private_value = "synthetic.owner@example.test"
        private = self._capture(source, self._item(content=private_value, privacy_class="private", source_reference="fixture:private"))["observations"][0]
        self.assertEqual(private["identity_status"], "retained_private")
        self.assertEqual(self.ledger.get_observation(private["id"])["content"], private_value)
        exported = export_store(self.store, self.root / "export-private")
        text = exported["json"].read_text(encoding="utf-8")
        self.assertNotIn(private_value, text)
        public = self._capture(source, self._item(content="Synthetic public-safe observation.", privacy_class="public", source_reference="fixture:public"), started_at="2026-10-04T00:00:06Z")["observations"][0]
        exported = export_store(self.store, self.root / "export-public")
        payload = json.loads(exported["json"].read_text(encoding="utf-8"))
        exported_public = next(item for item in payload["observations"]["observations"] if item["id"] == public["id"])
        self.assertEqual(exported_public["content"], public["content"])

    def test_public_snapshot_projects_all_m7_families_by_least_disclosure(self):
        source_note = "Synthetic private source note only for the local vault."
        source_name = "Synthetic private source name"
        source = self._approve(self._register(name=source_name, privacy_notes=source_note))
        private_content = "Synthetic private observation payload only for the local vault."
        private_reference = "fixture:private-source-reference"
        private_subject = "private-subject-label"
        private_context = "private-context-label"
        private_transform = "private-transformation-detail"
        collected = self._capture(
            source,
            self._item(
                content=private_content,
                structured_payload={"private_payload": "private-structured-value"},
                source_reference=private_reference,
                privacy_class="private",
                subject_labels=[private_subject],
                context_labels=[private_context],
                transformation_notes=[private_transform],
            ),
            "2026-10-04T00:00:06Z",
        )
        observation = collected["observations"][0]
        self.ledger.set_review_state(observation["id"], "review_pending")
        self.ledger.set_review_state(observation["id"], "accepted_for_evidence_review")
        proposal_content = "Synthetic proposed content retained only in the private proposal record."
        proposal_rationale = "Synthetic private proposal rationale."
        proposal_uncertainty = "Synthetic private proposal uncertainty."
        proposal_counter = "Synthetic private proposal counter-context."
        proposal = self.ledger.propose_evidence({
            "observation_ids": [observation["id"]],
            "proposed_content": proposal_content,
            "proposed_evidence_type": "observation",
            "scope": "observations.synthetic",
            "confidence": "probable",
            "rationale": proposal_rationale,
            "uncertainty": proposal_uncertainty,
            "counter_context": [proposal_counter],
        })["proposal"]

        exported = export_store(self.store, self.root / "least-disclosure-export")
        public_export_text = exported["json"].read_text(encoding="utf-8")
        snapshot = json.loads(public_export_text)["observations"]
        public_source = next(item for item in snapshot["sources"] if item["id"] == source["id"])
        public_session = next(item for item in snapshot["sessions"] if item["id"] == collected["session"]["id"])
        public_observation = next(item for item in snapshot["observations"] if item["id"] == observation["id"])
        public_proposal = next(item for item in snapshot["evidence_proposals"] if item["id"] == proposal["id"])

        self.assertTrue({"id", "source_type", "status", "adapter_id", "version"} <= set(public_source))
        self.assertTrue({"id", "source_id", "status", "items_considered", "items_accepted", "items_quarantined", "duplicates", "observation_ids", "version"} <= set(public_session))
        self.assertTrue({"id", "source_id", "collection_session_id", "review_state", "privacy_class", "content_fingerprint", "version"} <= set(public_observation))
        self.assertTrue({"id", "status", "proposed_evidence_type", "observation_count", "version"} <= set(public_proposal))
        self.assertEqual(public_session["items_considered"], 1)
        self.assertEqual(public_session["observation_ids"], [observation["id"]])
        self.assertEqual(public_proposal["observation_count"], 1)

        self.assertFalse({"name", "approval_scope", "allowed_scopes", "allowed_data_classes", "denied_data_classes", "retention_policy", "last_collection", "privacy_notes", "provenance"} & set(public_source))
        self.assertFalse({"approval_scope", "privacy_findings", "errors", "provenance"} & set(public_session))
        self.assertFalse({"content", "structured_payload", "source_reference", "explicit_event_id", "scope", "subject_labels", "context_labels", "provenance"} & set(public_observation))
        self.assertFalse({"observation_ids", "proposed_content", "scope", "rationale", "uncertainty", "counter_context", "provenance"} & set(public_proposal))

        for private_value in (source_note, source_name, private_content, private_reference, private_subject, private_context, private_transform, "private-structured-value", proposal_content, proposal_rationale, proposal_uncertainty, proposal_counter):
            self.assertNotIn(private_value, public_export_text)

    def test_internal_observation_uses_metadata_only_public_projection(self):
        internal_content = "Synthetic internal-only observation content."
        observation = self._capture(item=self._item(content=internal_content, privacy_class="internal"))["observations"][0]
        public = next(item for item in self.ledger.public_snapshot()["observations"] if item["id"] == observation["id"])
        self.assertNotIn("content", public)
        self.assertNotIn("structured_payload", public)
        self.assertNotIn("source_reference", public)
        self.assertEqual(public["content_fingerprint"], observation["content_fingerprint"])

    def test_file_import_is_explicit_bounded_utf8_and_non_symlink(self):
        file_source = self._approve(self._register(name="Synthetic file source", source_type="file_import", adapter_id="file_import", allowed_data_classes=["text_document"]))
        document = self.root / "synthetic-note.txt"
        document.write_text("Synthetic explicit file observation.", encoding="utf-8")
        result = self.ledger.collect(file_source["id"], file_source["approval_scope"], "file_import", {"path": str(document), "privacy_class": "internal", "observed_at": STAMP}, STAMP)
        record = result["observations"][0]
        self.assertEqual(record["observation_type"], "file_content")
        self.assertTrue(record["source_reference"].startswith("file:sha256:"))
        self.assertNotIn(str(document), json.dumps(record))
        unsupported = self.root / "synthetic.exe"
        unsupported.write_bytes(b"synthetic")
        with self.assertRaisesRegex(ValueError, "unsupported file type"):
            self.ledger.collect(file_source["id"], file_source["approval_scope"], "file_import", {"path": str(unsupported)}, "2026-10-04T00:00:07Z")
        large = self.root / "large.txt"
        large.write_bytes(b"x" * 33)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.ledger.collect(file_source["id"], file_source["approval_scope"], "file_import", {"path": str(large), "max_bytes": 32}, "2026-10-04T00:00:08Z")
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.ledger.collect(file_source["id"], file_source["approval_scope"], "file_import", {"path": str(self.root)}, "2026-10-04T00:00:09Z")
        link = self.root / "link.txt"
        try:
            link.symlink_to(document)
        except OSError:
            pass
        else:
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                self.ledger.collect(file_source["id"], file_source["approval_scope"], "file_import", {"path": str(link)}, "2026-10-04T00:00:10Z")

    def test_adapter_separation_and_no_connector_or_background_surface(self):
        registry = ObservationAdapterRegistry()
        self.assertEqual(sorted(registry.status()), ["file_import", "manual"])
        self.assertNotIsInstance(ManualObservationAdapter(), type(AIService(self.store).registry))
        self.assertNotIsInstance(FileImportObservationAdapter(), type(SpecialistFederation(self.store).adapters))
        self.assertNotIn("browser", json.dumps(registry.status()).casefold())
        self.assertNotIn("daemon", json.dumps(registry.status()).casefold())
        self.assertFalse(any(value["background"] for value in registry.status().values()))
        synthetic = ObservationAdapterRegistry([SyntheticObservationAdapter()])
        self.assertEqual(synthetic.status()["synthetic_test"]["test_only"], True)

    def test_review_transitions_and_logical_purge_are_metadata_only(self):
        record = self._capture()["observations"][0]
        self.ledger.set_review_state(record["id"], "review_pending")
        accepted = self.ledger.set_review_state(record["id"], "accepted_for_evidence_review")
        self.assertEqual(accepted["review_state"], "accepted_for_evidence_review")
        with self.assertRaisesRegex(ValueError, "invalid observation review transition"):
            self.ledger.set_review_state(record["id"], "captured")
        private_value = record["content"]
        purged = self.ledger.purge(record["id"])
        self.assertEqual(purged["review_state"], "deleted_marker")
        self.assertEqual(purged["retention_state"], "purged")
        self.assertIsNone(purged["content"])
        purge_event = self.store.audit_events()[-1]
        self.assertEqual(purge_event["event_type"], "observation.purged")
        self.assertNotIn(private_value, json.dumps(purge_event))

    def test_evidence_proposal_requires_review_and_promotes_exactly_once(self):
        observation = self._capture()["observations"][0]
        with self.assertRaisesRegex(ValueError, "accepted for evidence review"):
            self.ledger.propose_evidence({"observation_ids": [observation["id"]], "proposed_content": "Synthetic evidence candidate.", "proposed_evidence_type": "observation", "scope": "observations.synthetic", "confidence": "probable", "rationale": "Explicit synthetic review.", "uncertainty": "May not generalize."})
        self.ledger.set_review_state(observation["id"], "review_pending")
        self.ledger.set_review_state(observation["id"], "accepted_for_evidence_review")
        created = self.ledger.propose_evidence({"observation_ids": [observation["id"]], "proposed_content": "Synthetic evidence candidate.", "proposed_evidence_type": "observation", "scope": "observations.synthetic", "confidence": "probable", "rationale": "Explicit synthetic review.", "uncertainty": "May not generalize."})
        proposal = created["proposal"]
        self.assertEqual(proposal["observation_ids"], [observation["id"]])
        with self.assertRaisesRegex(ValueError, "only an approved"):
            self.ledger.promote_evidence_proposal(proposal["id"])
        self.ledger.decide_evidence_proposal(proposal["id"], "approved", "Synthetic evidence approval.")
        first = self.ledger.promote_evidence_proposal(proposal["id"])
        second = self.ledger.promote_evidence_proposal(proposal["id"])
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.list_evidence()), 1)
        self.assertEqual(first["confidence"], "probable")
        self.assertEqual(first["observed_at"], observation["observed_at"])
        self.assertIn(observation["id"], json.dumps(first["provenance"]))
        self.assertTrue(any(item["event_type"] == "observation.evidence_promoted" for item in self.store.audit_events()))

    def test_unknown_time_proposal_requires_explicit_evidence_time(self):
        observation = self._capture(item=self._item(observed_at=None, source_reference="fixture:unknown-proposal"))["observations"][0]
        self.ledger.set_review_state(observation["id"], "review_pending")
        self.ledger.set_review_state(observation["id"], "accepted_for_evidence_review")
        specification = {"observation_ids": [observation["id"]], "proposed_content": "Synthetic time-bounded evidence.", "proposed_evidence_type": "observation", "scope": "observations.synthetic", "confidence": "weak", "rationale": "Synthetic proposal.", "uncertainty": "Original event time is unknown."}
        with self.assertRaisesRegex(ValueError, "explicit evidence observed_at"):
            self.ledger.propose_evidence(specification)
        specification["observed_at"] = STAMP
        self.assertEqual(self.ledger.propose_evidence(specification)["proposal"]["observed_at"], STAMP)

    def test_identity_is_rejected_before_evidence_proposal(self):
        observation = self._capture(item=self._item(content="synthetic.owner@example.test", privacy_class="private", source_reference="fixture:identity"))["observations"][0]
        self.ledger.set_review_state(observation["id"], "review_pending")
        self.ledger.set_review_state(observation["id"], "accepted_for_evidence_review")
        with self.assertRaisesRegex(ValueError, "not public-safe"):
            self.ledger.propose_evidence({"observation_ids": [observation["id"]], "proposed_content": "Contact synthetic.owner@example.test", "proposed_evidence_type": "observation", "scope": "observations.synthetic", "confidence": "unknown", "rationale": "Synthetic privacy test.", "uncertainty": "Identity-bearing."})

    def test_observation_never_mutates_memory_or_contradictions_or_auto_collects(self):
        before = self.runtime.status()["counts"]
        self._capture()
        after = self.runtime.status()["counts"]
        self.assertEqual(after["memories"], before["memories"])
        self.assertEqual(after["contradictions"], before["contradictions"])
        self.assertEqual(CognitiveEngine(self.store).list_family("sessions"), [])
        self.assertEqual(AIService(self.store).list_records("requests"), [])
        self.assertEqual(SpecialistFederation(self.store).list_records("requests"), [])

    def test_collection_audit_is_metadata_only_and_final_audit_failure_rolls_back(self):
        source = self._approve(self._register())
        content = "Synthetic rollback private payload."
        original = self.store._audit

        def fail_final(connection, event_type, entity_type, entity_id, payload):
            if event_type == "observation.collection_completed":
                raise RuntimeError("synthetic observation audit failure")
            return original(connection, event_type, entity_type, entity_id, payload)

        with patch.object(self.store, "_audit", side_effect=fail_final):
            with self.assertRaisesRegex(RuntimeError, "synthetic observation audit failure"):
                self._capture(source, self._item(content=content), "2026-10-04T00:00:11Z")
        self.assertEqual(self.ledger.list_observations(), [])
        self.assertEqual(self.ledger.list_sessions(), [])
        success = self._capture(source, self._item(content=content), "2026-10-04T00:00:12Z")
        audit = json.dumps(self.store.audit_events())
        self.assertNotIn(content, audit)
        self.assertIn(success["observations"][0]["content_fingerprint"], audit)

    def test_adapter_failure_is_explicit_failed_session_without_observation(self):
        source = self._approve(self._register())
        with self.assertRaisesRegex(ValueError, "requires one structured item"):
            self.ledger.collect(source["id"], source["approval_scope"], "manual_capture", {}, STAMP)
        sessions = self.ledger.list_sessions()
        self.assertEqual(sessions[-1]["status"], "failed")
        self.assertEqual(self.ledger.list_observations(), [])

    def test_backup_restore_preserves_private_m7_state_and_provenance(self):
        source = self._approve(self._register(privacy_notes="Synthetic private backup source note."))
        collected = self._capture(source, self._item(content="Synthetic private vault record.", privacy_class="private", structured_payload={"private_backup": True}, subject_labels=["private-backup-subject"], context_labels=["private-backup-context"], transformation_notes=["private_backup_transform"]))
        private = collected["observations"][0]
        self.ledger.set_review_state(private["id"], "review_pending")
        self.ledger.set_review_state(private["id"], "accepted_for_evidence_review")
        proposal = self.ledger.propose_evidence({"observation_ids": [private["id"]], "proposed_content": "Synthetic backup proposal content.", "proposed_evidence_type": "observation", "scope": "observations.synthetic", "confidence": "probable", "rationale": "Synthetic backup proposal rationale.", "uncertainty": "Synthetic backup proposal uncertainty.", "counter_context": ["Synthetic backup proposal counter-context."]})["proposal"]
        backup = create_backup(self.store, self.root / "backup")
        restored_path = self.root / "restored.sqlite3"
        restore_backup(backup["manifest"], restored_path)
        restored = ObservationLedger(EvidenceStore(restored_path))
        restored_record = restored.get_observation(private["id"])
        current_private = self.ledger.get_observation(private["id"])
        self.assertEqual(restored_record, current_private)
        self.assertEqual(restored_record["provenance"], current_private["provenance"])
        self.assertEqual(restored.get_source(source["id"]), self.ledger.get_source(source["id"]))
        self.assertEqual(restored.list_sessions(), self.ledger.list_sessions())
        self.assertEqual(restored.list_evidence_proposals(), [proposal])
        self.assertEqual(restored_record["content"], "Synthetic private vault record.")
        self.assertEqual(restored_record["structured_payload"], {"private_backup": True})
        self.assertTrue(restored.health()["healthy"])

    def test_health_reports_quarantine_failures_retention_and_orphans_but_paused_is_optional(self):
        source = self._approve(self._register(retention_policy={"mode": "session_only", "days": None}))
        self._capture(source, self._item(source_reference="fixture:retention"), "2026-10-04T00:00:13Z")
        self._capture(source, self._item(source_reference="fixture:quarantine", privacy_class="restricted"), "2026-10-04T00:00:14Z")
        with self.assertRaises(ValueError):
            self.ledger.collect(source["id"], source["approval_scope"], "manual_capture", {}, "2026-10-04T00:00:15Z")
        self.ledger.set_source_status(source["id"], "paused")
        health = self.ledger.health()
        self.assertTrue(health["healthy"])
        self.assertEqual(health["counts"]["quarantined"], 1)
        self.assertEqual(health["counts"]["failed_sessions"], 1)
        self.assertGreaterEqual(health["counts"]["retention_backlog"], 1)
        connection = sqlite3.connect(self.store.path)
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("UPDATE observation_records SET source_id='osrc_00000000000000000000' WHERE id=(SELECT id FROM observation_records LIMIT 1)")
            connection.commit()
        finally:
            connection.close()
        unhealthy = self.ledger.health()
        self.assertFalse(unhealthy["healthy"])
        self.assertTrue(any(item.startswith("observation_orphan_references:") for item in unhealthy["errors"]))

    def test_schema_6_to_7_upgrade_and_fresh_initialization(self):
        legacy_path = self.root / "schema-v6.sqlite3"
        connection = sqlite3.connect(legacy_path)
        try:
            for migration in sorted(EvidenceStore.migration_dir().glob("*.sql")):
                if migration.name.startswith("007_"):
                    break
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES (?,?,?)", (int(migration.name[:3]), migration.name, STAMP))
            connection.commit()
        finally:
            connection.close()
        legacy = EvidenceStore(legacy_path)
        self.assertEqual(legacy.initialize(), [7])
        self.assertEqual(legacy.schema_version(), 7)
        fresh = EvidenceStore(self.root / "fresh.sqlite3")
        self.assertEqual(fresh.initialize(), [1, 2, 3, 4, 5, 6, 7])
        self.assertTrue(ClassicalRuntime(fresh).health()["healthy"])

    def test_cli_smoke(self):
        source_file = self.root / "source.json"
        source_file.write_text(json.dumps(self._source_spec()), encoding="utf-8")
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        database = self.root / "cli.sqlite3"

        def run(*arguments):
            return subprocess.run([sys.executable, "-m", "zis.cli", "--database", str(database), *arguments], check=True, capture_output=True, text=True, env=environment)

        added = json.loads(run("observations", "source-add", str(source_file)).stdout)
        approval_id = added["approval"]["id"]
        source_id = added["source"]["id"]
        run("approval", "decide", approval_id, "approve", "--note", "Synthetic approval.")
        run("observations", "source-status", source_id, "approved", "--approval-id", approval_id)
        item_file = self.root / "item.json"
        item_file.write_text(json.dumps({"item": self._item()}), encoding="utf-8")
        collected = json.loads(run("observations", "collect", source_id, str(item_file), "--scope", "observations.synthetic", "--operation", "manual_capture").stdout)
        self.assertEqual(collected["session"]["status"], "completed")
        self.assertEqual(len(json.loads(run("observations", "list").stdout)), 1)
        self.assertIn("observations", json.loads(run("health").stdout))


if __name__ == "__main__":
    unittest.main()
