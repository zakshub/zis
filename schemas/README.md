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

SpecialistManifest was extended for registry use with explicit domain, interface version, compatible runtime versions and availability. It remains metadata only and does not authorize invocation.

Validation is available through `zis validate`. Core synthetic examples are covered by `tests/test_contracts.py`; migration contracts are exercised by `tests/test_migration.py`. Contracts are strict (`additionalProperties: false`) and use ordinal confidence rather than pseudo-precise numeric scores. The dependency-free validator implements only the schema keywords required by these ZIS contracts, not all of Draft 2020-12.
