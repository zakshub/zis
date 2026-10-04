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
from tests.test_store import make_record
from zis.backup import create_backup, restore_backup
from zis.cognition import CognitiveEngine
from zis.export import export_store
from zis.federation import (
    REQUEST_CONTRACT_VERSION,
    RESPONSE_CONTRACT_VERSION,
    SpecialistAdapterRegistry,
    SpecialistAdapterResult,
    SpecialistFederation,
    SpecialistInvocationError,
)
from zis.runtime import ClassicalRuntime, build_approval_record
from zis.store import EvidenceStore


class FakeSpecialistAdapter:
    adapter_version = "fake-specialist.v1"
    request_contract_version = REQUEST_CONTRACT_VERSION
    response_contract_version = RESPONSE_CONTRACT_VERSION
    output_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["recommendation"],
        "properties": {"recommendation": {"type": "string", "minLength": 1}},
    }

    def __init__(self, specialist_id="sp_designer", result=None, state="available"):
        self.specialist_id = specialist_id
        self.result = result or SpecialistAdapterResult("success", {"recommendation": "Synthetic bounded result"}, ["synthetic warning"], ["not production advice"], "trace-safe")
        self.state = state
        self.requests = []

    def availability(self, manifest):
        return {"state": self.state, "reason": None if self.state == "available" else "Synthetic unavailable state.", "destructive": False}

    def compatibility(self, manifest, runtime_version):
        runtime_line = runtime_version.rsplit(".", 1)[0]
        compatible = (
            runtime_line in manifest["compatible_runtime_versions"]
            and manifest.get("request_contract_version") == self.request_contract_version
            and manifest.get("response_contract_version") == self.response_contract_version
        )
        return {
            "compatible": compatible,
            "required": {"runtime": runtime_line, "request_contract": manifest.get("request_contract_version"), "response_contract": manifest.get("response_contract_version")},
            "available": {"runtime": manifest["compatible_runtime_versions"], "request_contract": self.request_contract_version, "response_contract": self.response_contract_version},
        }

    def request(self, request_record):
        self.requests.append(request_record)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class SpecialistFederationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = EvidenceStore(self.root / "zis.sqlite3")
        self.service = SpecialistFederation(self.store)
        self.service.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _spec(self, specialist_id="sp_designer", capability="ux_ui", **overrides):
        value = {
            "specialist_id": specialist_id,
            "action": "review_design",
            "purpose": "Synthetic bounded specialist test",
            "requested_capability": capability,
            "structured_input": {"brief": "Synthetic public fixture"},
            "context_references": ["fixture:bounded-context"],
            "privacy_class": "public",
            "context_forwarding_approved": True,
            "timeout_seconds": 2,
            "created_at": STAMP,
        }
        value.update(overrides)
        return value

    def _make_available(self, specialist_id):
        runtime = ClassicalRuntime(self.store)
        approval = build_approval_record("specialist.approve", specialist_id, "Approve synthetic federation test", "specialist_registry", "low", "Synthetic metadata only", requested_at=STAMP)
        runtime.request_approval(approval)
        runtime.decide_approval(approval["id"], "approved", "Approved for bounded synthetic federation testing.")
        runtime.set_specialist_status(specialist_id, "approved", approval["id"])
        return runtime.set_specialist_status(specialist_id, "available")

    def _callable(self, adapter=None):
        adapter = adapter or FakeSpecialistAdapter()
        self._make_available(adapter.specialist_id)
        return SpecialistFederation(self.store, SpecialistAdapterRegistry([adapter])), adapter

    def test_initial_registry_and_zist_evaluation_are_explicit(self):
        manifests = {item["id"]: item for item in ClassicalRuntime(self.store).list_specialists()}
        self.assertEqual(set(manifests), {"sp_designer", "sp_studio", "sp_seo", "sp_taxbot"})
        for specialist_id in manifests:
            self.assertEqual(manifests[specialist_id]["adapter_type"], "metadata_only")
            self.assertEqual(manifests[specialist_id]["health_state"], "not_configured")
        evaluation = self.service.zist_evaluation()
        self.assertEqual(evaluation["decision"], "deferred_not_registered")
        self.assertNotIn("sp_zist", manifests)

    def test_metadata_only_specialists_report_honest_unavailable_state(self):
        for specialist_id, capability in (("sp_designer", "ux_ui"), ("sp_studio", "image_generation"), ("sp_seo", "niche_research"), ("sp_taxbot", "iris_workflow_review")):
            with self.subTest(specialist_id=specialist_id):
                result = self.service.invoke(self._spec(specialist_id, capability))
                self.assertEqual(result["response"]["status"], "unavailable")
                self.assertEqual(result["response"]["error_category"], "not_configured")
                self.assertIsNone(result["provenance_receipt"])
        health = self.service.health()
        self.assertTrue(health["core_healthy"])
        self.assertTrue(all(item["availability"]["state"] == "not_configured" for item in health["specialists"].values()))

    def test_disabled_and_incompatible_specialists_are_not_invoked(self):
        runtime = ClassicalRuntime(self.store)
        runtime.set_specialist_status("sp_designer", "retired")
        disabled_adapter = FakeSpecialistAdapter()
        disabled = SpecialistFederation(self.store, SpecialistAdapterRegistry([disabled_adapter])).invoke(self._spec())
        self.assertEqual(disabled["response"]["status"], "disabled")
        self.assertEqual(disabled_adapter.requests, [])

        adapter = FakeSpecialistAdapter("sp_studio")
        adapter.request_contract_version = "9.0"
        incompatible = SpecialistFederation(self.store, SpecialistAdapterRegistry([adapter])).invoke(self._spec("sp_studio", "image_generation"))
        self.assertEqual(incompatible["response"]["status"], "incompatible")
        self.assertEqual(incompatible["response"]["error_category"], "version_mismatch")
        self.assertIn("required", incompatible["response"]["error_message"])
        self.assertEqual(adapter.requests, [])

    def test_request_validation_explicit_context_and_privacy_precede_invocation(self):
        service, adapter = self._callable()
        valid = service.build_request(self._spec())
        self.assertEqual(valid["structured_input"], {"brief": "Synthetic public fixture"})
        self.assertTrue(valid["input_fingerprint"].startswith("sha256:"))
        with self.assertRaisesRegex(ValueError, "unsupported specialist request fields"):
            service.invoke(self._spec(database="full.sqlite3"))
        with self.assertRaisesRegex(ValueError, "identity"):
            service.invoke(self._spec(structured_input={"note": "contact synthetic@example.test"}))
        with self.assertRaisesRegex(ValueError, "identity fields"):
            service.invoke(self._spec(structured_input={"api_key": "synthetic-secret"}))
        with self.assertRaisesRegex(ValueError, "context_forwarding_approved"):
            service.invoke(self._spec(context_forwarding_approved=False))
        self.assertEqual(adapter.requests, [])

    def test_fake_success_is_normalized_and_has_complete_provenance(self):
        service, adapter = self._callable()
        result = service.invoke(self._spec())
        response = result["response"]
        receipt = result["provenance_receipt"]
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["structured_output"], {"recommendation": "Synthetic bounded result"})
        self.assertGreaterEqual(response["latency_ms"], 0)
        self.assertEqual(receipt["request_id"], result["request"]["id"])
        self.assertEqual(receipt["response_id"], response["id"])
        self.assertEqual(receipt["specialist_id"], "sp_designer")
        self.assertEqual(receipt["capability"], "ux_ui")
        self.assertEqual(receipt["context_references"], ["fixture:bounded-context"])
        self.assertEqual(receipt["adapter_version"], adapter.adapter_version)
        self.assertTrue(receipt["output_fingerprint"].startswith("sha256:"))
        self.assertEqual(receipt["trace_id"], "trace-safe")

    def test_invalid_output_is_rejected_as_a_whole(self):
        adapter = FakeSpecialistAdapter(result=SpecialistAdapterResult("success", {"unexpected": True}))
        service, adapter = self._callable(adapter)
        result = service.invoke(self._spec())
        self.assertEqual(result["response"]["status"], "invalid_output")
        self.assertIsNone(result["response"]["structured_output"])
        self.assertIsNone(result["provenance_receipt"])

    def test_timeout_internal_and_transport_failures_are_normalized(self):
        cases = (
            (SpecialistInvocationError("timeout", "Synthetic timeout."), "timeout", "timeout"),
            (SpecialistInvocationError("internal", "Synthetic internal failure."), "specialist_error", "internal"),
            (RuntimeError("unsafe transport detail"), "specialist_error", "transport"),
        )
        for index, (failure, status, category) in enumerate(cases):
            store = EvidenceStore(self.root / f"failure-{index}.sqlite3")
            base = SpecialistFederation(store)
            base.initialize()
            runtime = ClassicalRuntime(store)
            approval = build_approval_record("specialist.approve", "sp_designer", "Synthetic", "specialist_registry", "low", "Synthetic", requested_at=STAMP)
            runtime.request_approval(approval)
            runtime.decide_approval(approval["id"], "approved", "Synthetic exact approval.")
            runtime.set_specialist_status("sp_designer", "approved", approval["id"])
            runtime.set_specialist_status("sp_designer", "available")
            adapter = FakeSpecialistAdapter(result=failure)
            result = SpecialistFederation(store, SpecialistAdapterRegistry([adapter])).invoke(self._spec())
            self.assertEqual(result["response"]["status"], status)
            self.assertEqual(result["response"]["error_category"], category)
            self.assertIsNone(result["provenance_receipt"])

    def test_output_never_promotes_or_executes_core_state(self):
        first = make_record("Federation evidence A")
        second = make_record("Federation evidence B")
        self.store.add_evidence(first)
        self.store.add_evidence(second)
        contradiction = self.store.add_contradiction(first["id"], second["id"])
        runtime = ClassicalRuntime(self.store)
        before = {"evidence": self.store.list_evidence(), "memory": runtime.list_memories(), "approvals": runtime.list_approvals(), "contradiction": self.store.get_contradiction(contradiction["id"])}
        service, _ = self._callable()
        service.invoke(self._spec(context_references=[first["id"], second["id"]]))
        self.assertEqual(self.store.list_evidence(), before["evidence"])
        self.assertEqual(runtime.list_memories(), before["memory"])
        self.assertEqual(len(runtime.list_approvals()), len(before["approvals"]) + 1)
        self.assertEqual(self.store.get_contradiction(contradiction["id"]), before["contradiction"])

    def test_cognition_ai_and_router_do_not_auto_invoke(self):
        service, adapter = self._callable()
        evidence = make_record("No hidden specialist delegation")
        self.store.add_evidence(evidence)
        CognitiveEngine(self.store).run_session({"trigger_reference": "fixture:no-delegation", "scope": "tests", "evidence_ids": [evidence["id"]], "effective_at": STAMP})
        route = ClassicalRuntime(self.store).run_task({"action_type": "specialist", "scope": "tests", "specialist_id": "sp_designer", "requested_at": STAMP})
        self.assertEqual(route["route"]["selected_route"], "specialist_candidate")
        self.assertEqual(adapter.requests, [])
        ai_source = (Path(__file__).resolve().parents[1] / "src" / "zis" / "ai.py").read_text(encoding="utf-8")
        cognition_source = (Path(__file__).resolve().parents[1] / "src" / "zis" / "cognition.py").read_text(encoding="utf-8")
        self.assertNotIn("SpecialistFederation", ai_source)
        self.assertNotIn("SpecialistFederation", cognition_source)

    def test_taxbot_high_impact_requires_exact_approval_and_submission_is_absent(self):
        adapter = FakeSpecialistAdapter("sp_taxbot")
        service, adapter = self._callable(adapter)
        specification = self._spec("sp_taxbot", "filing_preparation", action="filing_preparation")
        with self.assertRaisesRegex(ValueError, "approved approval"):
            service.invoke(specification)
        approval = build_approval_record("specialist.invoke.high_impact", "sp_taxbot", "Approve bounded preparation", "filing_preparation", "high", "Preparation only; no submission", requested_at=STAMP)
        runtime = ClassicalRuntime(self.store)
        runtime.request_approval(approval)
        runtime.decide_approval(approval["id"], "approved", "Approved bounded preparation only.")
        result = service.invoke({**specification, "approval_id": approval["id"]})
        self.assertEqual(result["response"]["status"], "success")
        with self.assertRaisesRegex(ValueError, "not implemented"):
            service.invoke(self._spec("sp_taxbot", "filing_preparation", action="submit_tax_return"))

    def test_audit_is_metadata_only_and_failure_rolls_back_every_record(self):
        service, _ = self._callable()
        result = service.invoke(self._spec(structured_input={"brief": "Payload must not enter audit"}))
        audit = json.dumps(self.store.audit_events()[-1])
        self.assertIn(result["response"]["id"], audit)
        self.assertNotIn("Payload must not enter audit", audit)
        self.assertNotIn("Synthetic bounded result", audit)

        rollback_store = EvidenceStore(self.root / "rollback.sqlite3")
        bootstrap = SpecialistFederation(rollback_store)
        bootstrap.initialize()
        runtime = ClassicalRuntime(rollback_store)
        approval = build_approval_record("specialist.approve", "sp_designer", "Synthetic", "specialist_registry", "low", "Synthetic", requested_at=STAMP)
        runtime.request_approval(approval)
        runtime.decide_approval(approval["id"], "approved", "Synthetic exact approval.")
        runtime.set_specialist_status("sp_designer", "approved", approval["id"])
        runtime.set_specialist_status("sp_designer", "available")
        rollback_service = SpecialistFederation(rollback_store, SpecialistAdapterRegistry([FakeSpecialistAdapter()]))
        original = rollback_store._audit

        def fail_final(connection, event_type, entity_type, entity_id, payload):
            if event_type == "specialist.interaction_recorded":
                raise RuntimeError("synthetic federation audit failure")
            return original(connection, event_type, entity_type, entity_id, payload)

        with patch.object(rollback_store, "_audit", side_effect=fail_final):
            with self.assertRaisesRegex(RuntimeError, "synthetic federation audit failure"):
                rollback_service.invoke(self._spec())
        self.assertEqual(rollback_service.list_records("requests"), [])
        self.assertEqual(rollback_service.list_records("responses"), [])
        self.assertEqual(rollback_service.list_records("receipts"), [])

    def test_secret_is_rejected_and_never_persisted_audited_exported_or_backed_up(self):
        service, adapter = self._callable()
        secret = "password=synthetic-federation-secret"
        with self.assertRaisesRegex(ValueError, "credential"):
            service.invoke(self._spec(structured_input={"note": secret}))
        self.assertEqual(adapter.requests, [])
        adapter.result = SpecialistAdapterResult("success", {"recommendation": secret})
        rejected_output = service.invoke(self._spec())
        self.assertEqual(rejected_output["response"]["status"], "invalid_output")
        self.assertNotIn(secret.encode(), self.store.path.read_bytes())
        self.assertNotIn(secret, json.dumps(self.store.audit_events()))
        exported = export_store(self.store, self.root / "secret-export")
        self.assertNotIn(secret, exported["json"].read_text(encoding="utf-8"))
        backup = create_backup(self.store, self.root / "secret-backup")
        self.assertNotIn(secret.encode(), Path(backup["backup"]).read_bytes())

    def test_migration_005_to_006_and_fresh_initialization(self):
        legacy_path = self.root / "schema-v5.sqlite3"
        connection = sqlite3.connect(legacy_path)
        try:
            for migration in sorted(EvidenceStore.migration_dir().glob("*.sql")):
                if migration.name.startswith("006_"):
                    break
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES (?,?,?)", (int(migration.name[:3]), migration.name, STAMP))
            connection.commit()
        finally:
            connection.close()
        legacy = EvidenceStore(legacy_path)
        self.assertEqual(legacy.initialize(), [6, 7])
        self.assertEqual(legacy.schema_version(), 7)
        fresh = EvidenceStore(self.root / "fresh.sqlite3")
        self.assertEqual(fresh.initialize(), [1, 2, 3, 4, 5, 6, 7])
        self.assertTrue(ClassicalRuntime(fresh).health()["healthy"])

    def test_backup_restore_export_and_health_include_m6_state(self):
        service, _ = self._callable()
        result = service.invoke(self._spec())
        exported = export_store(self.store, self.root / "m6-export")
        payload = json.loads(exported["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["format_version"], 6)
        self.assertEqual(payload["federation"]["responses"][0]["id"], result["response"]["id"])
        self.assertIn("Federation Responses: 1", exported["markdown"].read_text(encoding="utf-8"))
        backup = create_backup(self.store, self.root / "m6-backup")
        restored_path = self.root / "restored.sqlite3"
        restore_backup(backup["manifest"], restored_path)
        restored = SpecialistFederation(EvidenceStore(restored_path), SpecialistAdapterRegistry([FakeSpecialistAdapter()]))
        self.assertEqual(restored.snapshot(), service.snapshot())
        self.assertTrue(restored.health()["core_healthy"])

    def test_cli_smoke_for_metadata_only_federation(self):
        request_path = self.root / "specialist-request.json"
        request = self._spec()
        request.pop("specialist_id")
        request_path.write_text(json.dumps(request), encoding="utf-8")
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

        def run(*arguments):
            completed = subprocess.run([sys.executable, "-m", "zis.cli", "--database", str(self.store.path), *arguments], check=True, capture_output=True, text=True, env=environment)
            return json.loads(completed.stdout)

        self.assertEqual(len(run("specialists", "list")), 4)
        self.assertEqual(run("specialists", "show", "sp_designer")["id"], "sp_designer")
        self.assertEqual(run("specialists", "status", "--id", "sp_designer")["specialists"]["sp_designer"]["availability"]["state"], "not_configured")
        self.assertEqual(run("specialists", "invoke", "sp_designer", str(request_path))["response"]["status"], "unavailable")
        self.assertEqual(len(run("specialists", "records", "responses")), 1)
        self.assertEqual(run("specialists", "zist")["decision"], "deferred_not_registered")


if __name__ == "__main__":
    unittest.main()
