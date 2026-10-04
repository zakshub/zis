# ZIS Schema Foundation

The five original conceptual contracts have machine-validated JSON Schema Draft 2020-12 representations, and later milestones add only the bounded contracts listed below. The Markdown files provide the human-readable view; `*.schema.json` files are the executable contracts.

Core contracts:

1. EvidenceRecord
2. ObservationRecord
3. SpecialistManifest
4. CapabilityProposal
5. IdeaLineage

M2 migration contracts:

1. ZOSMigrationManifest
2. ZOSMigrationCandidate

M3 classical runtime contracts:

1. SourceRecord
2. MemoryRecord
3. CapabilityRecord
4. ApprovalRecord
5. RouteDecision
6. RuntimeOperation
7. BackupManifest

M4 deterministic cognitive contracts:

1. CognitiveSession
2. AttentionSignal
3. AssociationRecord
4. PatternCandidate
5. HypothesisRecord
6. IdeaLineage v2
7. EvaluationRecord
8. ReflectionRecord
9. ModelUpdateProposal

M5 optional AI adapter contracts:

1. AIRequest
2. AIResponse
3. AICandidate

M6 specialist federation contracts:

1. SpecialistRequest
2. SpecialistResponse
3. SpecialistProvenanceReceipt

M7 observation contracts:

1. ObservationSource
2. ObservationCollectionSession
3. ObservationRecord v2
4. ObservationEvidenceProposal

SpecialistManifest v3 adds optional federation metadata for request/response versions, adapter type, health state, privacy classification and invocation policy while preserving older manifests. A registry entry does not authorize invocation. IdeaLineage v2 is the M4 durable idea contract and intentionally stops at the pre-execution `ready` state.

AIRequest stores only explicitly approved safe structured context and a deterministic prompt fingerprint. AIResponse normalizes provider outcome, usage and cost state without raw provider payload or hidden reasoning. AICandidate is explicitly `ai_candidate_not_truth` and pending review; it is not an EvidenceRecord, MemoryRecord or approval.

SpecialistRequest stores only explicitly selected structured context and a deterministic fingerprint. SpecialistResponse normalizes outcomes, and every success references a SpecialistProvenanceReceipt. These records are specialist results, not evidence, memory, truth, approval or execution authority.

Observation confidence means capture integrity, not truth confidence. `accepted_for_evidence_review` is not evidence creation; an exact approved ObservationEvidenceProposal is required. Private/restricted observation content is local-vault state and is omitted from default public-safe export.

Validation is available through `zis validate`. Core synthetic examples are covered by `tests/test_contracts.py`; migration contracts by `tests/test_migration.py`; M4 contracts and behavior by `tests/test_cognition.py`; M5 by `tests/test_ai.py`; M6 by `tests/test_federation.py`; M7 by `tests/test_observations.py`. Contracts are strict (`additionalProperties: false`) and use explicit unknown/null states rather than invented precision. The dependency-free validator implements only the schema keywords required by these ZIS contracts, not all of Draft 2020-12.
