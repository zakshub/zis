import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import STAMP, specialist
from tests.test_store import make_record
from zis.runtime import ClassicalRuntime, build_approval_record, build_capability_record, build_source_record
from zis.store import EvidenceStore


class ClassicalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = EvidenceStore(Path(self.temp.name) / "zis.sqlite3")
        self.runtime = ClassicalRuntime(self.store)
        self.runtime.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _approve(self, action_type, reference, scope):
        approval = build_approval_record(action_type, reference, "Synthetic governed request", scope, "low", "Synthetic test impact", requested_at=STAMP)
        self.runtime.request_approval(approval)
        return self.runtime.decide_approval(approval["id"], "approved", "Approved for the exact synthetic action.")

    def _available_capability(self, name="Synthetic runtime status", approval_required=False):
        record = build_capability_record(name, "Synthetic classical action", "classical_action", f"classical:{name}", approval_required=approval_required, created_at=STAMP)
        self.runtime.register_capability(record)
        approval = self._approve("capability.approve", record["id"], "capability_registry")
        self.runtime.set_capability_status(record["id"], "approved", approval["id"])
        return self.runtime.set_capability_status(record["id"], "available")

    def _available_specialist(self):
        manifest = specialist()
        self.runtime.register_specialist(manifest)
        approval = self._approve("specialist.approve", manifest["id"], "specialist_registry")
        self.runtime.set_specialist_status(manifest["id"], "approved", approval["id"])
        return self.runtime.set_specialist_status(manifest["id"], "available")

    def test_source_registry_duplicate_and_lifecycle(self):
        source = build_source_record("synthetic", "Synthetic source", "fixture:runtime-source", created_at=STAMP)
        self.runtime.register_source(source)
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.runtime.register_source(source)
        inactive = self.runtime.set_source_status(source["id"], "inactive")
        self.assertEqual(inactive["status"], "inactive")
        with self.assertRaisesRegex(ValueError, "already"):
            self.runtime.set_source_status(source["id"], "inactive")
        self.assertIn("source.status_changed", [event["event_type"] for event in self.store.audit_events()])

    def test_new_registry_mutation_rolls_back_on_audit_failure(self):
        source = build_source_record("synthetic", "Rollback source", "fixture:rollback-source", created_at=STAMP)
        with patch.object(self.store, "_audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit failure"):
                self.runtime.register_source(source)
        self.assertEqual(self.runtime.list_sources(), [])

    def test_memory_is_only_proposed_until_exact_approval(self):
        evidence = make_record("Synthetic evidence for memory", confidence="weak")
        self.store.add_evidence(evidence)
        result = self.runtime.propose_memory("Synthetic reviewed memory candidate", "evidence_backed", [evidence["id"]], "tests", "weak", "Review before durable activation", created_at=STAMP)
        self.assertEqual(result["memory"]["status"], "proposed")
        self.assertFalse(result["memory"]["current_interpretation"])
        self.assertEqual(result["approval"]["status"], "pending")
        with self.assertRaisesRegex(ValueError, "approved approval"):
            self.runtime.set_memory_status(result["memory"]["id"], "active", result["approval"]["id"])
        self.runtime.decide_approval(result["approval"]["id"], "approved", "Explicitly approved the synthetic memory promotion.")
        active = self.runtime.set_memory_status(result["memory"]["id"], "active", result["approval"]["id"])
        self.assertTrue(active["current_interpretation"])

    def test_conflicting_evidence_is_preserved_in_memory_proposal(self):
        first = make_record("Synthetic position A", "user_statement")
        second = make_record("Synthetic position not A", "user_statement")
        self.store.add_evidence(first)
        self.store.add_evidence(second)
        self.store.add_contradiction(first["id"], second["id"])
        result = self.runtime.propose_memory("Synthetic unresolved memory", "experimental", [first["id"], second["id"]], "tests", "unknown", "Review unresolved conflict", created_at=STAMP)
        self.assertEqual(result["memory"]["conflict_status"], "unresolved")
        self.assertEqual(result["memory"]["status"], "proposed")

    def test_rejected_and_wrong_approval_cannot_authorize(self):
        rejected = build_approval_record("capability.execute", "cr_11111111111111111111", "Synthetic request", "scope-a", "low", "Synthetic", requested_at=STAMP)
        self.runtime.request_approval(rejected)
        self.runtime.decide_approval(rejected["id"], "rejected", "Rejected synthetic action.")
        with self.assertRaisesRegex(ValueError, "approved approval"):
            self.runtime.authorize(rejected["id"], "capability.execute", "cr_11111111111111111111", "scope-a")
        approved = self._approve("capability.execute", "cr_22222222222222222222", "scope-a")
        with self.assertRaisesRegex(ValueError, "exact action"):
            self.runtime.authorize(approved["id"], "capability.execute", "cr_33333333333333333333", "scope-a")

    def test_invalid_approval_transition_is_rejected_and_history_audited(self):
        approval = self._approve("runtime.test", "synthetic-action", "tests")
        with self.assertRaisesRegex(ValueError, "invalid approval transition"):
            self.runtime.decide_approval(approval["id"], "rejected", "Cannot reject after approval.")
        events = [event for event in self.store.audit_events() if event["entity_id"] == approval["id"]]
        self.assertEqual([event["event_type"] for event in events], ["approval.requested", "approval.decided"])

    def test_capability_registry_dependencies_and_lifecycle(self):
        dependency = self._available_capability("Synthetic dependency")
        record = build_capability_record("Synthetic dependent", "Depends on synthetic capability", "classical_action", "classical:dependent", [dependency["id"]], created_at=STAMP)
        self.runtime.register_capability(record)
        approval = self._approve("capability.approve", record["id"], "capability_registry")
        self.runtime.set_capability_status(record["id"], "approved", approval["id"])
        available = self.runtime.set_capability_status(record["id"], "available")
        self.assertEqual(available["dependencies"], [dependency["id"]])
        self.assertEqual(available["availability"], "available")
        with self.assertRaisesRegex(ValueError, "invalid capability transition"):
            self.runtime.set_capability_status(record["id"], "approved", approval["id"])

    def test_unavailable_capability_routes_unsupported(self):
        record = build_capability_record("Unavailable synthetic", "Not ready", "classical_action", "classical:unavailable", created_at=STAMP)
        self.runtime.register_capability(record)
        decision = self.runtime.route({"action_type": "existing_capability", "scope": "tests", "capability_id": record["id"], "requested_at": STAMP})
        self.assertEqual(decision["selected_route"], "unsupported")
        self.assertEqual(decision["unsupported_reason"], "capability_unavailable")

    def test_available_approval_gated_capability_requires_exact_approval(self):
        capability = self._available_capability("Approval-gated synthetic", approval_required=True)
        request = {"action_type": "existing_capability", "scope": "tests", "capability_id": capability["id"], "requested_at": STAMP}
        self.assertEqual(self.runtime.route(request)["selected_route"], "approval_required")
        approval = self._approve("capability.execute", capability["id"], "tests")
        request["approval_id"] = approval["id"]
        self.assertEqual(self.runtime.route(request)["selected_route"], "existing_capability")

    def test_rejected_approval_keeps_operation_blocked(self):
        capability = self._available_capability("Rejected execution synthetic", approval_required=True)
        approval = build_approval_record("capability.execute", capability["id"], "Synthetic request", "tests", "low", "Synthetic", requested_at=STAMP)
        self.runtime.request_approval(approval)
        self.runtime.decide_approval(approval["id"], "rejected", "Rejected synthetic execution.")
        result = self.runtime.run_task({"action_type": "existing_capability", "scope": "tests", "capability_id": capability["id"], "approval_id": approval["id"], "requested_at": STAMP})
        self.assertEqual(result["route"]["selected_route"], "approval_required")
        self.assertEqual(result["operation"]["execution_status"], "blocked")

    def test_unavailable_specialist_routes_unsupported(self):
        manifest = specialist()
        self.runtime.register_specialist(manifest)
        decision = self.runtime.route({"action_type": "specialist", "scope": "tests", "specialist_id": manifest["id"], "requested_at": STAMP})
        self.assertEqual(decision["unsupported_reason"], "specialist_unavailable")

    def test_available_specialist_is_candidate_but_not_invoked(self):
        manifest = self._available_specialist()
        result = self.runtime.run_task({"action_type": "specialist", "scope": "tests", "specialist_id": manifest["id"], "requested_at": STAMP})
        self.assertEqual(result["route"]["selected_route"], "specialist_candidate")
        self.assertEqual(result["operation"]["execution_status"], "routed")
        self.assertEqual(result["operation"]["result_metadata"]["outcome"], "specialist_candidate")

    def test_incompatible_specialist_is_not_routed(self):
        manifest = specialist()
        manifest["compatible_runtime_versions"] = ["99.0"]
        self.runtime.register_specialist(manifest)
        approval = self._approve("specialist.approve", manifest["id"], "specialist_registry")
        self.runtime.set_specialist_status(manifest["id"], "approved", approval["id"])
        self.runtime.set_specialist_status(manifest["id"], "available")
        decision = self.runtime.route({"action_type": "specialist", "scope": "tests", "specialist_id": manifest["id"], "requested_at": STAMP})
        self.assertEqual(decision["unsupported_reason"], "specialist_incompatible")

    def test_insufficient_information_returns_unsupported(self):
        decision = self.runtime.route({"scope": "tests", "requested_at": STAMP})
        self.assertEqual(decision["selected_route"], "unsupported")
        self.assertEqual(decision["unsupported_reason"], "insufficient_information")

    def test_unknown_structured_action_returns_unsupported(self):
        decision = self.runtime.route({"action_type": "synthetic_unknown_action", "scope": "tests", "requested_at": STAMP})
        self.assertEqual(decision["selected_route"], "unsupported")
        self.assertEqual(decision["unsupported_reason"], "unsupported_action_type")

    def test_routing_is_deterministic_for_same_state_and_input(self):
        request = {"action_type": "runtime_status", "scope": "runtime", "requested_at": STAMP}
        first = self.runtime.route(request)
        second = self.runtime.route(request)
        self.assertEqual(first, second)
        self.assertIn("runtime_status_is_local_classical_action", first["rules_evaluated"])

    def test_persistent_change_never_executes_in_m3(self):
        request = {"action_type": "persistent_change", "scope": "tests", "action_reference": "proposal:synthetic", "requested_at": STAMP}
        self.assertEqual(self.runtime.route(request)["selected_route"], "approval_required")
        approval = self._approve("persistent_change", "proposal:synthetic", "tests")
        request["approval_id"] = approval["id"]
        decision = self.runtime.route(request)
        self.assertEqual(decision["selected_route"], "unsupported")
        self.assertEqual(decision["unsupported_reason"], "persistent_change_execution_not_implemented")

    def test_runtime_operation_is_atomic_with_audit(self):
        request = {"action_type": "runtime_status", "scope": "runtime", "requested_at": STAMP}
        original_audit = self.store._audit

        def fail_final_audit(connection, event_type, entity_type, entity_id, payload):
            if event_type == "runtime.operation_recorded":
                raise RuntimeError("synthetic operation audit failure")
            return original_audit(connection, event_type, entity_type, entity_id, payload)

        with patch.object(self.store, "_audit", side_effect=fail_final_audit):
            with self.assertRaisesRegex(RuntimeError, "synthetic operation audit failure"):
                self.runtime.run_task(request)
        self.assertEqual(self.runtime.list_operations(), [])
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM route_decisions").fetchone()[0], 0)

    def test_health_reports_sqlite_and_orphan_integrity(self):
        healthy = self.runtime.health()
        self.assertTrue(healthy["healthy"])
        self.assertEqual(healthy["integrity_check"], "ok")
        evidence = make_record("Orphan test evidence")
        self.store.add_evidence(evidence)
        proposal = self.runtime.propose_memory("Orphan test memory", "evidence_backed", [evidence["id"]], "tests", "weak", "Synthetic", created_at=STAMP)
        connection = sqlite3.connect(self.store.path)
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("INSERT INTO memory_evidence_links(memory_id,evidence_id) VALUES (?,?)", (proposal["memory"]["id"], "ev_00000000000000000000"))
            connection.commit()
        finally:
            connection.close()
        unhealthy = self.runtime.health()
        self.assertFalse(unhealthy["healthy"])
        self.assertIn("foreign_key_issues", unhealthy["errors"][0])


if __name__ == "__main__":
    unittest.main()
