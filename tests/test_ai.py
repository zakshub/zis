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
from zis.ai import (
    AIAdapterRegistry,
    AIConfiguration,
    AIService,
    AdapterResult,
    DisabledAIAdapter,
    OpenAIResponsesAdapter,
    PricingEntry,
    ProviderInvocationError,
)
from zis.backup import create_backup, restore_backup
from zis.cognition import CognitiveEngine
from zis.export import export_store
from zis.records import build_evidence
from zis.runtime import ClassicalRuntime
from zis.store import EvidenceStore


class FakeAdapter:
    provider_id = "fake"
    adapter_version = "fake.v1"
    requires_credential = False

    def __init__(self, result=None):
        self.result = result or AdapterResult(status="success", structured_output={"label": "synthetic candidate"}, usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}, provider_reference="fake-response")
        self.requests = []

    def availability(self, configuration, credential):
        return {"state": "available", "configured": True, "network_verified": False}

    def request(self, request_record, credential):
        self.requests.append(request_record)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class AIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = EvidenceStore(self.root / "zis.sqlite3")
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _configuration(self, provider="fake", model="fake-model", enabled=True):
        return AIConfiguration(enabled=enabled, provider_id=provider, model_id=model, timeout_seconds=2, max_output_tokens=100)

    def _specification(self, **overrides):
        value = {
            "purpose": "Synthetic structured assistance",
            "task_type": "structured_assistance",
            "instruction": "Return one short synthetic label.",
            "context": {"facts": ["Synthetic safe context"]},
            "expected_output_schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label"],
                "properties": {"label": {"type": "string", "minLength": 1}},
            },
            "context_references": ["fixture:explicit-context"],
            "privacy_class": "public",
            "external_transmission_approved": True,
            "created_at": STAMP,
        }
        value.update(overrides)
        return value

    def _service(self, adapter=None, pricing=None):
        adapter = adapter or FakeAdapter()
        return AIService(self.store, self._configuration(adapter.provider_id), AIAdapterRegistry([DisabledAIAdapter(), adapter]), pricing), adapter

    def _evidence(self):
        record = build_evidence("Synthetic cognition input", "observation", "synthetic_fixture", "fixture:ai-cognition", "tests", "probable", STAMP, provenance_method="synthetic_fixture", provenance_actor="test")
        self.store.add_evidence(record)
        return record

    def test_core_and_m4_work_with_ai_disabled(self):
        service = AIService(self.store, self._configuration(provider="none", model="none", enabled=False))
        self.assertTrue(ClassicalRuntime(self.store).health()["healthy"])
        evidence = self._evidence()
        cognition = CognitiveEngine(self.store).run_session({"trigger_reference": "fixture:disabled-ai", "scope": "tests", "evidence_ids": [evidence["id"]], "effective_at": STAMP})
        self.assertEqual(cognition["session"]["status"], "completed")
        interaction = service.request_assistance(self._specification())
        self.assertEqual(interaction["response"]["status"], "disabled")
        self.assertIsNone(interaction["candidate"])

    def test_missing_credential_is_explicit_and_core_remains_healthy(self):
        adapter = OpenAIResponsesAdapter(transport=lambda *_: self.fail("transport must not run"))
        service = AIService(self.store, self._configuration("openai", "synthetic-model"), AIAdapterRegistry([adapter]))
        with patch.dict(os.environ, {}, clear=True):
            result = service.request_assistance(self._specification())
        self.assertEqual(result["response"]["status"], "unavailable")
        self.assertEqual(result["response"]["error_category"], "not_configured")
        self.assertTrue(service.status()["core_healthy"])

    def test_fake_provider_succeeds_through_provider_neutral_interface(self):
        service, adapter = self._service()
        result = service.request_assistance(self._specification())
        self.assertEqual(result["response"]["status"], "success")
        self.assertEqual(result["candidate"]["truth_status"], "ai_candidate_not_truth")
        self.assertEqual(len(adapter.requests), 1)

    def test_openai_request_construction_is_deterministic_and_explicit(self):
        captured = []

        def transport(url, headers, payload, timeout):
            captured.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
            return {"id": "provider-safe-reference", "status": "completed", "output_text": json.dumps({"label": "synthetic candidate"}), "usage": {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}}

        adapter = OpenAIResponsesAdapter(transport=transport)
        service = AIService(self.store, self._configuration("openai", "synthetic-model"), AIAdapterRegistry([adapter]))
        secret = "synthetic-credential-fixture-value"
        with patch.dict(os.environ, {"OPENAI_API_KEY": secret}, clear=True):
            request_a = service.build_request(self._specification())
            request_b = service.build_request(self._specification())
            self.assertEqual(request_a["prompt_fingerprint"], request_b["prompt_fingerprint"])
            result = service.request_assistance(self._specification())
        expected_payload = OpenAIResponsesAdapter.build_payload(request_a)
        self.assertEqual(captured[0]["payload"], expected_payload)
        sent = json.loads(captured[0]["payload"]["input"])
        self.assertEqual(sent["context"], {"facts": ["Synthetic safe context"]})
        self.assertNotIn("database", sent)
        self.assertNotIn("history", sent)
        self.assertEqual(result["response"]["usage"]["total_tokens"], 10)

    def test_identity_or_secret_input_is_rejected_before_transport(self):
        called = []
        adapter = OpenAIResponsesAdapter(transport=lambda *args: called.append(args))
        service = AIService(self.store, self._configuration("openai", "synthetic-model"), AIAdapterRegistry([adapter]))
        with self.assertRaisesRegex(ValueError, "identity"):
            service.request_assistance(self._specification(context={"note": "contact synthetic@example.test"}))
        with self.assertRaisesRegex(ValueError, "identity fields"):
            service.request_assistance(self._specification(context={"api_key": "not-a-real-secret"}))
        self.assertEqual(called, [])
        self.assertEqual(service.list_records("requests"), [])

    def test_runtime_credential_never_persists_or_enters_audit_export_or_backup(self):
        secret = "synthetic-runtime-credential-fixture"
        captured_headers = []

        def transport(url, headers, payload, timeout):
            captured_headers.append(headers)
            return {"id": "safe-provider-ref", "status": "completed", "output_text": json.dumps({"label": "safe"})}

        adapter = OpenAIResponsesAdapter(transport=transport)
        service = AIService(self.store, self._configuration("openai", "synthetic-model"), AIAdapterRegistry([adapter]))
        with patch.dict(os.environ, {"OPENAI_API_KEY": secret}, clear=True):
            service.request_assistance(self._specification())
        self.assertIn(secret, captured_headers[0]["Authorization"])
        self.assertNotIn(secret.encode(), self.store.path.read_bytes())
        self.assertNotIn(secret, json.dumps(self.store.audit_events()))
        self.assertNotIn("Authorization", json.dumps(self.store.audit_events()))
        self.assertNotIn(b"Authorization", self.store.path.read_bytes())
        exported = export_store(self.store, self.root / "export")
        self.assertNotIn(secret, exported["json"].read_text(encoding="utf-8"))
        backup = create_backup(self.store, self.root / "backup")
        self.assertNotIn(secret.encode(), Path(backup["backup"]).read_bytes())
        self.assertNotIn(secret, Path(backup["manifest"]).read_text(encoding="utf-8"))

    def test_timeout_and_provider_failures_are_normalized(self):
        cases = [
            ("timeout", "timeout", "timeout"),
            ("authentication", "provider_error", "authentication"),
            ("rate_limit", "provider_error", "rate_limit"),
            ("provider_server", "provider_error", "provider_server"),
            ("transport", "provider_error", "transport"),
        ]
        for index, (category, status, expected_category) in enumerate(cases):
            store = EvidenceStore(self.root / f"failure-{index}.sqlite3")
            adapter = FakeAdapter(ProviderInvocationError(category, f"safe {category} failure"))
            service = AIService(store, self._configuration(), AIAdapterRegistry([adapter]))
            result = service.request_assistance(self._specification())
            self.assertEqual(result["response"]["status"], status)
            self.assertEqual(result["response"]["error_category"], expected_category)
            self.assertIsNone(result["candidate"])

    def test_malformed_provider_and_structured_output_are_rejected(self):
        malformed_envelope = OpenAIResponsesAdapter(transport=lambda *_: {"id": "no-output"})
        malformed_json = OpenAIResponsesAdapter(transport=lambda *_: {"id": "bad-json", "output_text": "{"})
        wrong_schema = OpenAIResponsesAdapter(transport=lambda *_: {"id": "wrong-schema", "output_text": json.dumps({"unexpected": True})})
        for index, adapter in enumerate((malformed_envelope, malformed_json, wrong_schema)):
            store = EvidenceStore(self.root / f"invalid-{index}.sqlite3")
            service = AIService(store, self._configuration("openai", "synthetic-model"), AIAdapterRegistry([adapter]))
            with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-not-real"}, clear=True):
                result = service.request_assistance(self._specification())
            self.assertEqual(result["response"]["status"], "invalid_output")
            self.assertIsNone(result["response"]["structured_output"])
            self.assertIsNone(result["candidate"])

    def test_hidden_reasoning_field_is_never_accepted_or_stored(self):
        adapter = FakeAdapter(AdapterResult(status="success", structured_output={"label": "safe", "chain_of_thought": "not allowed"}))
        service, _ = self._service(adapter)
        result = service.request_assistance(self._specification())
        self.assertEqual(result["response"]["status"], "invalid_output")
        database_text = self.store.path.read_bytes()
        self.assertNotIn(b"chain_of_thought", database_text)

    def test_schema_requesting_hidden_reasoning_is_rejected_before_transport(self):
        adapter = FakeAdapter()
        service, _ = self._service(adapter)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["chain_of_thought"],
            "properties": {"chain_of_thought": {"type": "string"}},
        }
        with self.assertRaisesRegex(ValueError, "forbidden hidden-reasoning field"):
            service.request_assistance(self._specification(expected_output_schema=schema))
        self.assertEqual(adapter.requests, [])

    def test_instruction_requesting_hidden_reasoning_is_rejected_before_transport(self):
        adapter = FakeAdapter()
        service, _ = self._service(adapter)
        with self.assertRaisesRegex(ValueError, "requests forbidden hidden reasoning"):
            service.request_assistance(self._specification(instruction="Return your private internal reasoning trace."))
        self.assertEqual(adapter.requests, [])

    def test_nested_hidden_reasoning_output_is_rejected_even_when_schema_permits_it(self):
        output = {"details": {"internal_monologue": "hidden nested fixture"}}
        adapter = FakeAdapter(AdapterResult(status="success", structured_output=output))
        service, _ = self._service(adapter)
        permissive_nested_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["details"],
            "properties": {"details": {"type": "object"}},
        }
        result = service.request_assistance(self._specification(expected_output_schema=permissive_nested_schema))
        self.assertEqual(result["response"]["status"], "invalid_output")
        self.assertIsNone(result["response"]["structured_output"])
        self.assertIsNone(result["candidate"])

    def test_rejected_hidden_reasoning_never_enters_database_or_audit(self):
        output = {"details": {"scratchpad": "sensitive hidden trace fixture"}}
        adapter = FakeAdapter(AdapterResult(status="success", structured_output=output))
        service, _ = self._service(adapter)
        schema = {"type": "object", "properties": {"details": {"type": "object"}}}
        service.request_assistance(self._specification(expected_output_schema=schema))
        database = self.store.path.read_bytes()
        audit = json.dumps(self.store.audit_events())
        self.assertNotIn(b"scratchpad", database)
        self.assertNotIn(b"sensitive hidden trace fixture", database)
        self.assertNotIn("scratchpad", audit)
        self.assertNotIn("sensitive hidden trace fixture", audit)

    def test_user_visible_reason_and_rationale_fields_remain_allowed(self):
        output = {"reason": "Concise visible reason", "rationale": "Concise visible rationale"}
        adapter = FakeAdapter(AdapterResult(status="success", structured_output=output))
        service, _ = self._service(adapter)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["reason", "rationale"],
            "properties": {"reason": {"type": "string"}, "rationale": {"type": "string"}},
        }
        result = service.request_assistance(self._specification(expected_output_schema=schema))
        self.assertEqual(result["response"]["status"], "success")
        self.assertEqual(result["candidate"]["output"], output)

    def test_response_never_becomes_evidence_memory_approval_or_contradiction(self):
        evidence = self._evidence()
        before = {
            "evidence": self.store.list_evidence(),
            "memory": ClassicalRuntime(self.store).list_memories(),
            "approval": ClassicalRuntime(self.store).list_approvals(),
            "contradiction": self.store.list_contradictions(),
        }
        service, _ = self._service()
        result = service.request_assistance(self._specification(context_references=[evidence["id"]]))
        self.assertEqual(result["candidate"]["review_state"], "pending_review")
        self.assertEqual(self.store.list_evidence(), before["evidence"])
        self.assertEqual(ClassicalRuntime(self.store).list_memories(), before["memory"])
        self.assertEqual(ClassicalRuntime(self.store).list_approvals(), before["approval"])
        self.assertEqual(self.store.list_contradictions(), before["contradiction"])

    def test_usage_unknown_and_cost_estimation_are_transparent(self):
        unknown_service, _ = self._service(FakeAdapter(AdapterResult(status="success", structured_output={"label": "safe"})))
        unknown = unknown_service.request_assistance(self._specification())
        self.assertEqual(unknown["response"]["usage"], {"input_tokens": None, "output_tokens": None, "total_tokens": None})
        self.assertEqual(unknown["response"]["cost"]["status"], "unknown")

        priced_store = EvidenceStore(self.root / "priced.sqlite3")
        adapter = FakeAdapter()
        price = PricingEntry("fake", "fake-model", 2.0, 4.0, "USD", "fixture-v1", "synthetic:test-pricing")
        priced = AIService(priced_store, self._configuration(), AIAdapterRegistry([adapter]), [price]).request_assistance(self._specification())
        self.assertEqual(priced["response"]["cost"]["status"], "estimated")
        self.assertEqual(priced["response"]["cost"]["amount"], 0.00004)
        self.assertNotEqual(priced["response"]["usage"]["total_tokens"], priced["response"]["cost"]["amount"])

    def test_audit_is_metadata_only_and_failure_rolls_back_all_ai_state(self):
        service, _ = self._service()
        result = service.request_assistance(self._specification())
        event = self.store.audit_events()[-1]
        serialized = json.dumps(event)
        self.assertIn(result["response"]["id"], serialized)
        self.assertNotIn("Synthetic safe context", serialized)
        self.assertNotIn("Return one short synthetic label", serialized)

        rollback_store = EvidenceStore(self.root / "rollback.sqlite3")
        rollback_service = AIService(rollback_store, self._configuration(), AIAdapterRegistry([FakeAdapter()]))
        original = rollback_store._audit

        def fail_ai_audit(connection, event_type, entity_type, entity_id, payload):
            if event_type == "ai.interaction_recorded":
                raise RuntimeError("synthetic AI audit failure")
            return original(connection, event_type, entity_type, entity_id, payload)

        with patch.object(rollback_store, "_audit", side_effect=fail_ai_audit):
            with self.assertRaisesRegex(RuntimeError, "synthetic AI audit failure"):
                rollback_service.request_assistance(self._specification())
        self.assertEqual(rollback_service.list_records("requests"), [])
        self.assertEqual(rollback_service.list_records("responses"), [])
        self.assertEqual(rollback_service.list_records("candidates"), [])

    def test_provider_registry_switches_without_cognitive_engine_dependency(self):
        first = FakeAdapter(AdapterResult(status="success", structured_output={"label": "first"}))
        first.provider_id = "first"
        second = FakeAdapter(AdapterResult(status="success", structured_output={"label": "second"}))
        second.provider_id = "second"
        registry = AIAdapterRegistry([first, second, DisabledAIAdapter()])
        first_result = AIService(EvidenceStore(self.root / "first.sqlite3"), self._configuration("first"), registry).request_assistance(self._specification())
        second_result = AIService(EvidenceStore(self.root / "second.sqlite3"), self._configuration("second"), registry).request_assistance(self._specification())
        self.assertEqual(first_result["candidate"]["output"]["label"], "first")
        self.assertEqual(second_result["candidate"]["output"]["label"], "second")
        cognition_source = (Path(__file__).resolve().parents[1] / "src" / "zis" / "cognition.py").read_text(encoding="utf-8")
        self.assertNotIn("OpenAI", cognition_source)
        self.assertNotIn("AIService", cognition_source)

    def test_cognitive_augmentation_is_explicit_and_does_not_overwrite_session(self):
        evidence = self._evidence()
        engine = CognitiveEngine(self.store)
        session = engine.run_session({"trigger_reference": "fixture:augmentation", "scope": "tests", "evidence_ids": [evidence["id"]], "effective_at": STAMP})
        before = engine.session_result(session["session"]["id"])
        service, _ = self._service()
        result = service.request_cognitive_assistance(session["session"]["id"], self._specification())
        self.assertIn(session["session"]["id"], result["request"]["context_references"])
        self.assertEqual(engine.session_result(session["session"]["id"]), before)

    def test_migration_005_upgrade_fresh_health_export_and_restore(self):
        legacy_path = self.root / "schema-v4.sqlite3"
        connection = sqlite3.connect(legacy_path)
        try:
            for migration in sorted(EvidenceStore.migration_dir().glob("*.sql")):
                if migration.name.startswith("005_"):
                    break
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES (?,?,?)", (int(migration.name[:3]), migration.name, STAMP))
            connection.commit()
        finally:
            connection.close()
        legacy = EvidenceStore(legacy_path)
        self.assertEqual(legacy.initialize(), [5])
        self.assertEqual(legacy.schema_version(), 5)

        service, _ = self._service()
        result = service.request_assistance(self._specification())
        self.assertTrue(ClassicalRuntime(self.store).health()["healthy"])
        export = export_store(self.store, self.root / "m5-export")
        payload = json.loads(export["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["format_version"], 4)
        self.assertEqual(payload["ai"]["responses"][0]["id"], result["response"]["id"])
        self.assertIn("AI Responses: 1", export["markdown"].read_text(encoding="utf-8"))
        backup = create_backup(self.store, self.root / "m5-backup")
        restored_path = self.root / "restored.sqlite3"
        restore_backup(backup["manifest"], restored_path)
        restored = AIService(EvidenceStore(restored_path), self._configuration(), AIAdapterRegistry([FakeAdapter()]))
        self.assertEqual(restored.snapshot(), service.snapshot())

    def test_ai_cli_disabled_smoke(self):
        input_path = self.root / "ai-request.json"
        input_path.write_text(json.dumps(self._specification()), encoding="utf-8")
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        environment["ZIS_AI_ENABLED"] = "false"

        def run(*arguments):
            completed = subprocess.run([sys.executable, "-m", "zis.cli", "--database", str(self.store.path), *arguments], check=True, capture_output=True, text=True, env=environment)
            return json.loads(completed.stdout)

        self.assertEqual(run("ai", "status")["ai"]["state"], "disabled")
        self.assertIn("none", run("ai", "providers")["registered"])
        result = run("ai", "request", str(input_path))
        self.assertEqual(result["response"]["status"], "disabled")
        self.assertEqual(len(run("ai", "records", "responses")), 1)


if __name__ == "__main__":
    unittest.main()
