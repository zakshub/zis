# Testing Strategy

Milestone 1 uses the standard-library `unittest` runner and temporary directories. Tests require no AI provider, network, external database or private data.

Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Coverage includes:

1. Valid and invalid examples for all five contracts.
2. Required fields, enum values, timestamps and undeclared-field rejection.
3. Recursive direct-identity field rejection.
4. Deterministic identifiers.
5. Database initialization and idempotent migrations.
6. Provenance and ordinal confidence preservation.
7. Supersession without loss of historical evidence.
8. Contradiction creation and rationale-backed resolution.
9. JSON export round trip plus CSV and Markdown readability.
10. Presence of all required ZOS migration classifications and inspected asset families.

Synthetic fixtures are visibly synthetic and contain no private identity.

