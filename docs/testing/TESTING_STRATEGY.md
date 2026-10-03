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
11. Transaction rollback when an audit write fails during evidence capture or supersession.

Synthetic fixtures are visibly synthetic and contain no private identity.

## Future durability and adversarial backlog

These tests are deliberately queued for Classical Runtime hardening; their presence here is not a claim that they pass in M1.

1. Simulated interruption, process termination and power-loss recovery around each multi-write operation.
2. Disk-full, read-only filesystem, permission-denied and SQLite I/O failure behavior.
3. Concurrent writers, lock contention, busy timeout behavior and duplicate submissions.
4. Migration failure midway through a script, restart behavior and recovery from partially initialized databases.
5. Corrupt, truncated or manually modified database detection and documented recovery behavior.
6. Direct audit-table modification tests once a tamper-evidence mechanism is proposed and approved.
7. Deterministic-ID collision handling and duplicate canonical record behavior.
8. Clock rollback, identical timestamps and audit-event identifier collision behavior.
9. Oversized, deeply nested, malformed Unicode and control-character payloads.
10. Export interruption, partial files, destination permission failures and atomic replacement behavior.
11. Path traversal, symlink/reparse-point and unsafe export/database destination cases.
12. Cross-validation of every contract against a standards-complete Draft 2020-12 validator.
13. Transaction rollback tests for status changes, contradiction creation and contradiction resolution.

