import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tests.helpers import STAMP
from tests.test_store import make_record
from zis.backup import create_backup, restore_backup
from zis.cognition import CognitiveEngine
from zis.export import export_store
from zis.records import build_evidence
from zis.runtime import ClassicalRuntime
from zis.store import EvidenceStore


EFFECTIVE = "2026-10-04T00:00:00Z"


class CognitiveEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = EvidenceStore(self.root / "zis.sqlite3")
        self.engine = CognitiveEngine(self.store)
        self.runtime = ClassicalRuntime(self.store)
        self.engine.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def _add(self, content, record_type="observation", confidence="probable", scope="tests", source_reference=None):
        reference = source_reference or f"fixture:{content}"
        record = build_evidence(content, record_type, "synthetic_fixture", reference, scope, confidence, STAMP, provenance_method="synthetic_fixture", provenance_actor="test")
        self.store.add_evidence(record)
        return record

    def _spec(self, records, **overrides):
        value = {
            "trigger_reference": "fixture:cognitive-session",
            "scope": "tests",
            "evidence_ids": [record["id"] for record in records],
            "effective_at": EFFECTIVE,
        }
        value.update(overrides)
        return value

    def test_attention_is_explained_and_contradiction_is_critical(self):
        first = self._add("Synthetic position A")
        second = self._add("Synthetic position not A")
        contradiction = self.store.add_contradiction(first["id"], second["id"])
        result = self.engine.run_session(self._spec([first, second]))
        signals = {item["evidence_id"]: item for item in result["attention"]}
        self.assertEqual(signals[first["id"]]["attention_level"], "critical")
        self.assertIn("unresolved_known_contradiction", signals[first["id"]]["reasons"])
        self.assertIn(contradiction["id"], signals[first["id"]]["contradiction_ids"])

    def test_novelty_repetition_duplicate_and_insufficient_states(self):
        first = self._add("Synthetic exact duplicate", source_reference="fixture:one")
        second = self._add("Synthetic exact duplicate", source_reference="fixture:two")
        repeated = self.engine.run_session(self._spec([first, second]))
        self.assertEqual({item["novelty_state"] for item in repeated["attention"]}, {"exact_duplicate"})
        self.assertTrue(all(item["repetition_count"] == 2 for item in repeated["attention"]))

        third = self._add("Synthetic distinct subject", source_reference="fixture:three")
        fourth = self._add("Another distinct subject", source_reference="fixture:four")
        novel = self.engine.run_session(self._spec([third, fourth]))
        self.assertEqual({item["novelty_state"] for item in novel["attention"]}, {"novel_in_context"})

        single = self._add("Only explicit comparison item")
        insufficient = self.engine.run_session(self._spec([single]))
        self.assertEqual(insufficient["attention"][0]["novelty_state"], "insufficient_basis")

    def test_known_and_candidate_contradictions_never_auto_resolve(self):
        first = self._add("Synthetic claim one")
        second = self._add("Synthetic claim two")
        known = self.store.add_contradiction(first["id"], second["id"])
        result = self.engine.run_session(self._spec([first, second], contradiction_candidates=[{"evidence_id_a": first["id"], "evidence_id_b": second["id"], "reason": "Explicit synthetic candidate reason."}]))
        relation_types = {item["relation_type"] for item in result["associations"]}
        self.assertIn("known_contradiction", relation_types)
        self.assertIn("contradiction_candidate", relation_types)
        self.assertEqual(self.store.get_contradiction(known["id"])["status"], "unresolved")
        self.assertEqual(len(self.store.list_contradictions()), 1)

    def test_association_requires_structured_basis_and_never_invents_semantics(self):
        first = self._add("Concept alpha", scope="scope-a", source_reference="fixture:a")
        second = self._add("Concept beta", scope="scope-b", source_reference="fixture:b")
        result = self.engine.run_session(self._spec([first, second]))
        self.assertEqual(result["associations"], [])

        tagged = self.engine.run_session(self._spec([first, second], trigger_reference="fixture:tagged", structured_tags={first["id"]: ["explicit-tag"], second["id"]: ["explicit-tag"]}))
        shared = [item for item in tagged["associations"] if item["relation_type"] == "shared_tag"]
        self.assertEqual(len(shared), 1)
        self.assertIn("explicit-tag", shared[0]["reason"])

    def test_pattern_requires_multiple_records_and_preserves_provenance(self):
        single = self._add("One observation is not a pattern")
        self.assertEqual(self.engine.run_session(self._spec([single]))["patterns"], [])

        first = self._add("Repeated structured occurrence", source_reference="fixture:p1")
        second = self._add("Repeated structured occurrence", source_reference="fixture:p2")
        result = self.engine.run_session(self._spec([first, second]))
        pattern = result["patterns"][0]
        self.assertEqual(pattern["support_count"], 2)
        self.assertEqual(set(pattern["supporting_evidence_ids"]), {first["id"], second["id"]})
        self.assertEqual(pattern["truth_status"], "candidate_not_truth")
        self.assertFalse(pattern["is_memory"])
        self.assertTrue(set(pattern["supporting_evidence_ids"]) <= set(pattern["provenance"]["chain"]))

    def test_pattern_counterevidence_remains_attached_and_affects_evaluation(self):
        first = self._add("Repeated but conflicting signal", source_reference="fixture:c1")
        second = self._add("Repeated but conflicting signal", source_reference="fixture:c2")
        self.store.add_contradiction(first["id"], second["id"])
        result = self.engine.run_session(self._spec([first, second]))
        pattern = result["patterns"][0]
        evaluation = next(item for item in result["evaluations"] if item["target_id"] == pattern["id"])
        self.assertEqual(set(pattern["counterevidence_ids"]), {first["id"], second["id"]})
        self.assertEqual(evaluation["outcome"], "contradicted")
        self.assertTrue(any(item["criterion"] == "contradiction_state" and item["finding"] == "contradicted" for item in evaluation["criteria"]))

    def test_hypothesis_is_testable_non_truth_and_non_memory(self):
        evidence = self._add("Synthetic support for a testable interpretation")
        result = self.engine.run_session(self._spec([evidence], hypotheses=[{
            "statement": "The explicit synthetic condition may recur.",
            "supporting_evidence_ids": [evidence["id"]],
            "confidence": "weak",
            "assumptions": ["The fixture remains comparable."],
            "strengthening_conditions": ["A second independent structured record appears."],
            "falsification_conditions": ["A reviewed counterexample is recorded."],
        }]))
        hypothesis = result["hypotheses"][0]
        self.assertEqual(hypothesis["status"], "proposed")
        self.assertEqual(hypothesis["truth_status"], "untested_interpretation")
        self.assertFalse(hypothesis["is_memory"])
        self.assertEqual(hypothesis["falsification_conditions"], ["A reviewed counterexample is recorded."])
        self.assertEqual(self.runtime.list_memories(), [])

    def test_idea_lineage_and_lifecycle_are_bounded_to_pre_execution(self):
        evidence = self._add("Synthetic idea origin")
        first_result = self.engine.run_session(self._spec([evidence], ideas=[{
            "statement": "Explore a bounded synthetic idea.", "origin_type": "curiosity",
            "evidence_ids": [evidence["id"]], "trigger": "Explicit fixture trigger",
            "transformations": ["Reframed as a testable direction."], "rationale": "Evidence explicitly supports exploration.",
        }]))
        parent = first_result["ideas"][0]
        second_result = self.engine.run_session(self._spec([evidence], trigger_reference="fixture:child", ideas=[{
            "statement": "Refine the bounded synthetic idea.", "origin_type": "combination",
            "parent_idea_ids": [parent["id"]], "evidence_ids": [evidence["id"]],
            "trigger": "Explicit parent refinement", "rationale": "Parent and evidence are explicitly referenced.",
        }]))
        child = second_result["ideas"][0]
        self.assertEqual(child["parent_idea_ids"], [parent["id"]])
        exploring = self.engine.set_idea_status(child["id"], "exploring")
        self.assertEqual(exploring["status"], "exploring")
        with self.assertRaisesRegex(ValueError, "invalid idea transition"):
            self.engine.set_idea_status(child["id"], "ready")

    def test_evaluation_is_per_criterion_and_has_no_decision_authority(self):
        first = self._add("Evaluation repetition", source_reference="fixture:e1")
        second = self._add("Evaluation repetition", source_reference="fixture:e2")
        result = self.engine.run_session(self._spec([first, second]))
        evaluation = result["evaluations"][0]
        criteria = {item["criterion"] for item in evaluation["criteria"]}
        self.assertTrue({"evidence_support", "counterevidence", "contradiction_state", "temporal_relevance", "confidence", "scope_fit", "unresolved_assumptions"} <= criteria)
        self.assertFalse(evaluation["decision_authority"])

    def test_reflection_preserves_unknowns_and_does_not_mutate_memory(self):
        evidence = self._add("Sparse synthetic context")
        memory_result = self.runtime.propose_memory("Synthetic unchanged memory", "experimental", [evidence["id"]], "tests", "weak", "Synthetic review", created_at=STAMP)
        before = deepcopy(self.runtime.get_memory(memory_result["memory"]["id"]))
        result = self.engine.run_session(self._spec([evidence], memory_ids=[before["id"]]))
        reflection = result["reflections"][0]
        self.assertIn("no_pattern_met_minimum_deterministic_support", reflection["uncertainties"])
        self.assertTrue(reflection["missing_evidence"])
        self.assertFalse(reflection["consciousness_claim"])
        self.assertEqual(self.runtime.get_memory(before["id"]), before)

    def test_model_update_proposal_is_governed_and_cannot_apply_in_m4(self):
        evidence = self._add("Synthetic update evidence")
        memory = self.runtime.propose_memory("Synthetic target memory", "experimental", [evidence["id"]], "tests", "weak", "Synthetic memory review", created_at=STAMP)["memory"]
        before = deepcopy(self.runtime.get_memory(memory["id"]))
        result = self.engine.run_session(self._spec([evidence], memory_ids=[memory["id"]], model_update_proposals=[{
            "target_memory_id": memory["id"], "proposed_change": "Revise the synthetic interpretation.",
            "reason": "Explicit evidence suggests review.", "supporting_artifact_ids": [evidence["id"]],
            "counterevidence_ids": [], "confidence": "weak", "impact": "Would change a durable interpretation after future application.",
        }]))
        proposal = result["proposals"][0]
        self.assertEqual(proposal["status"], "proposed")
        self.assertTrue(proposal["required_approval"])
        self.assertEqual(self.runtime.get_approval(proposal["approval_id"])["status"], "pending")
        self.assertEqual(self.runtime.get_memory(memory["id"]), before)
        self.engine.set_model_update_status(proposal["id"], "under_review")
        with self.assertRaisesRegex(ValueError, "approved approval"):
            self.engine.set_model_update_status(proposal["id"], "approved", proposal["approval_id"])
        self.runtime.decide_approval(proposal["approval_id"], "approved", "Approve proposal review, not application.")
        approved = self.engine.set_model_update_status(proposal["id"], "approved", proposal["approval_id"])
        self.assertEqual(approved["status"], "approved")
        with self.assertRaisesRegex(ValueError, "future Learning Engine"):
            self.engine.set_model_update_status(proposal["id"], "applied", proposal["approval_id"])
        self.assertEqual(self.runtime.get_memory(memory["id"]), before)

    def test_temporal_evidence_is_not_treated_as_current(self):
        evidence = self._add("Historical synthetic signal")
        self.store.set_evidence_status(evidence["id"], "expired")
        result = self.engine.run_session(self._spec([evidence]))
        signal = result["attention"][0]
        self.assertEqual(signal["temporal_state"], "expired")
        self.assertIn("temporal_state:expired", signal["reasons"])

    def test_same_state_and_input_produce_same_content_ids(self):
        record = make_record("Deterministic cognition fixture")
        stores = [self.store, EvidenceStore(self.root / "second.sqlite3")]
        results = []
        for store in stores:
            if store.get_evidence(record["id"]) is None:
                store.add_evidence(deepcopy(record))
            results.append(CognitiveEngine(store).run_session(self._spec([record])))
        self.assertEqual(results[0]["session"]["id"], results[1]["session"]["id"])
        self.assertEqual([item["id"] for item in results[0]["attention"]], [item["id"] for item in results[1]["attention"]])
        self.assertEqual(results[0]["session"]["input_fingerprint"], results[1]["session"]["input_fingerprint"])

    def test_unknown_state_remains_first_class(self):
        evidence = self._add("Unknown confidence singleton", confidence="unknown")
        result = self.engine.run_session(self._spec([evidence]))
        self.assertEqual(result["attention"][0]["confidence"], "unknown")
        self.assertEqual(result["attention"][0]["novelty_state"], "insufficient_basis")
        self.assertIn("no_hypothesis_was_explicitly_justified", result["reflections"][0]["uncertainties"])

    def test_identity_bearing_input_is_rejected(self):
        evidence = self._add("Safe synthetic evidence")
        with self.assertRaisesRegex(ValueError, "direct identity fields"):
            self.engine.run_session({**self._spec([evidence]), "real_name": "Synthetic Private Person"})
        with self.assertRaisesRegex(ValueError, "identity signals"):
            self.engine.run_session({**self._spec([evidence]), "trigger_reference": "private.person@example.test"})

    def test_final_audit_failure_rolls_back_entire_session(self):
        evidence = self._add("Atomic cognitive session")
        original_audit = self.store._audit

        def fail_final(connection, event_type, entity_type, entity_id, payload):
            if event_type == "cognition.session_completed":
                raise RuntimeError("synthetic cognitive audit failure")
            return original_audit(connection, event_type, entity_type, entity_id, payload)

        with patch.object(self.store, "_audit", side_effect=fail_final):
            with self.assertRaisesRegex(RuntimeError, "synthetic cognitive audit failure"):
                self.engine.run_session(self._spec([evidence]))
        self.assertEqual(self.engine.list_family("sessions"), [])
        self.assertEqual(self.engine.list_family("attention"), [])

    def test_migration_004_upgrades_an_existing_schema_v3_database(self):
        path = self.root / "schema-v3.sqlite3"
        connection = sqlite3.connect(path)
        try:
            for version in (1, 2, 3):
                migration = next(EvidenceStore.migration_dir().glob(f"{version:03d}_*.sql"))
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES (?,?,?)", (version, migration.name, STAMP))
            connection.commit()
        finally:
            connection.close()
        store = EvidenceStore(path)
        self.assertEqual(store.initialize(), [4, 5, 6, 7])
        self.assertEqual(store.schema_version(), 7)
        self.assertTrue(ClassicalRuntime(store).health()["healthy"])

    def test_health_detects_cognitive_reference_orphan(self):
        evidence = self._add("Health cognition fixture")
        result = self.engine.run_session(self._spec([evidence]))
        self.assertTrue(self.runtime.health()["healthy"])
        connection = sqlite3.connect(self.store.path)
        try:
            connection.execute("INSERT INTO cognitive_references(session_id,artifact_type,artifact_id,reference_type,reference_id,role) VALUES (?,?,?,?,?,?)", (result["session"]["id"], "reflection", result["reflections"][0]["id"], "pattern", "pat_00000000000000000000", "synthetic_orphan"))
            connection.commit()
        finally:
            connection.close()
        unhealthy = self.runtime.health()
        self.assertFalse(unhealthy["healthy"])
        self.assertTrue(any(item.startswith("cognitive_orphan_references:") for item in unhealthy["errors"]))

    def test_export_and_backup_restore_include_cognitive_state(self):
        first = self._add("Durable cognitive repetition", source_reference="fixture:d1")
        second = self._add("Durable cognitive repetition", source_reference="fixture:d2")
        result = self.engine.run_session(self._spec([first, second]))
        export = export_store(self.store, self.root / "export")
        payload = json.loads(export["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["format_version"], 6)
        self.assertEqual(payload["cognition"]["sessions"][0]["id"], result["session"]["id"])
        self.assertIn("Cognitive Sessions: 1", export["markdown"].read_text(encoding="utf-8"))

        backup = create_backup(self.store, self.root / "backups")
        restored_path = self.root / "restored.sqlite3"
        restore_backup(backup["manifest"], restored_path)
        restored = CognitiveEngine(EvidenceStore(restored_path))
        self.assertEqual(restored.snapshot(), self.engine.snapshot())
        self.assertTrue(ClassicalRuntime(EvidenceStore(restored_path)).health()["healthy"])

    def test_cognition_cli_smoke(self):
        evidence = self._add("Synthetic CLI cognition evidence")
        specification_path = self.root / "cognition-input.json"
        specification_path.write_text(
            json.dumps(self._spec([evidence])), encoding="utf-8"
        )
        database = str(self.store.path)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

        def run(*arguments):
            completed = subprocess.run(
                [sys.executable, "-m", "zis.cli", "--database", database, *arguments],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            return json.loads(completed.stdout)

        result = run("cognition", "run", str(specification_path))
        session_id = result["session"]["id"]
        self.assertEqual(run("cognition", "sessions", "--id", session_id)["session"]["id"], session_id)
        attention = run("cognition", "artifacts", "attention", "--session-id", session_id)
        self.assertEqual(attention[0]["evidence_id"], evidence["id"])
        self.assertTrue(run("health")["healthy"])
        exported = run("export", str(self.root / "export"))
        self.assertTrue(Path(exported["json"]).exists())


if __name__ == "__main__":
    unittest.main()
