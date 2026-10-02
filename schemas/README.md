# ZIS Schema Foundation

The five conceptual contracts now have machine-validated JSON Schema Draft 2020-12 representations. The Markdown files preserve the original design input; `*.schema.json` files are the executable contracts.

Initial contracts:

1. EvidenceRecord
2. ObservationRecord
3. SpecialistManifest
4. CapabilityProposal
5. IdeaLineage

Validation is available through `zis validate`, and synthetic valid/invalid coverage is in `tests/test_contracts.py`. Contracts are strict (`additionalProperties: false`) and use ordinal confidence rather than pseudo-precise numeric scores.
