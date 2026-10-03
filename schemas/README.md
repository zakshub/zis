# ZIS Schema Foundation

The five conceptual contracts now have machine-validated JSON Schema Draft 2020-12 representations. The Markdown files preserve the original design input; `*.schema.json` files are the executable contracts.

Core contracts:

1. EvidenceRecord
2. ObservationRecord
3. SpecialistManifest
4. CapabilityProposal
5. IdeaLineage

M2 migration contracts:

1. ZOSMigrationManifest
2. ZOSMigrationCandidate

Validation is available through `zis validate`. Core synthetic examples are covered by `tests/test_contracts.py`; migration contracts are exercised by `tests/test_migration.py`. Contracts are strict (`additionalProperties: false`) and use ordinal confidence rather than pseudo-precise numeric scores. The dependency-free validator implements only the schema keywords required by these ZIS contracts, not all of Draft 2020-12.
