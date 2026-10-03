# Testing Strategy

Milestones 1–3 use the standard-library `unittest` runner and temporary directories. Tests require no AI provider, network, external database or private data.

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
12. Migration manifest creation, deterministic fingerprints and A-G classification preservation.
13. Candidate privacy, identity, specialist, obsolete and explicit-approval gates.
14. Temporal mapping, provenance/source lineage and existing contradiction-model reuse.
15. Rejected-import prevention, approved import and duplicate-import idempotency.
16. Dry-run non-mutation and full import rollback after a final audit failure.
17. Absence of raw sensitive source content from the migration database and classical exports.

Synthetic fixtures are visibly synthetic and contain no private identity.

18. Duplicate registry protection and invalid source/memory/capability/specialist lifecycle transitions.
19. Pending, rejected, mismatched and invalid approval behavior.
20. Unavailable/incompatible capability and specialist routing.
21. Insufficient/unknown structured inputs and deterministic same-state routing.
22. Atomic rollback for new registry and operation mutations when audit writes fail.
23. Backup creation, manifest metadata, checksum verification and tamper detection.
24. Fresh restore and state equivalence across M1, M2 and M3 durable families.
25. Incompatible/corrupt backup rejection and preservation of an existing restore destination on failed verification.
26. SQLite integrity, required-table, migration-sequence and foreign-key/orphan checks.
27. Portable JSON and Markdown export of M3 runtime state.

Current verified result on Python 3.13.15: 59 passed (33 accepted M1/M2 tests and 26 M3 tests).

## Future durability and adversarial backlog

M3 completed the relevant checksum, tamper, restore, orphan and transactional cases. These cases remain explicitly deferred; their presence here is not a claim that they pass:

1. Simulated interruption, process termination and power-loss recovery around each multi-write operation.
2. Disk-full, read-only filesystem, permission-denied and SQLite I/O failure behavior.
3. Concurrent writers, lock contention, busy timeout behavior and duplicate submissions.
4. Process termination during migration scripts, backup publication or the final filesystem replace, including platform-specific durability guarantees.
5. Recovery of a corrupt/truncated live database beyond reporting failure and restoring a separately verified backup.
6. Direct audit-table modification tests once a tamper-evidence mechanism is proposed and approved.
7. Deliberately constructed SHA-256 identifier collisions beyond ordinary duplicate detection.
8. Clock rollback, identical timestamps and audit-event identifier collision behavior.
9. Oversized, deeply nested, malformed Unicode and control-character payloads.
10. Export interruption, partial files, destination permission failures and atomic replacement behavior.
11. Path traversal, symlink/reparse-point and unsafe export/database destination cases.
12. Cross-validation of every contract against a standards-complete Draft 2020-12 validator.
13. Remaining rollback fault injection for every individual lifecycle transition and contradiction resolution.
14. Cross-runtime-version and cross-schema-version backup migration/restore.
15. Cryptographically signed backup manifests, authenticated approvals and tamper-evident audit history.

