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

SpecialistManifest was extended for registry use with explicit domain, interface version, compatible runtime versions and availability. It remains metadata only and does not authorize invocation. IdeaLineage v2 is the M4 durable idea contract and intentionally stops at the pre-execution `ready` state.

AIRequest stores only explicitly approved safe structured context and a deterministic prompt fingerprint. AIResponse normalizes provider outcome, usage and cost state without raw provider payload or hidden reasoning. AICandidate is explicitly `ai_candidate_not_truth` and pending review; it is not an EvidenceRecord, MemoryRecord or approval.

Validation is available through `zis validate`. Core synthetic examples are covered by `tests/test_contracts.py`; migration contracts by `tests/test_migration.py`; M4 contracts and behavior by `tests/test_cognition.py`; M5 by `tests/test_ai.py`. Contracts are strict (`additionalProperties: false`) and use explicit unknown/null states rather than invented precision. The dependency-free validator implements only the schema keywords required by these ZIS contracts, not all of Draft 2020-12.
