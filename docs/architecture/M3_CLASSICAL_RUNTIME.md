# M3 Classical Runtime

## Pre-implementation consistency review

The complete repository state was reviewed before M3 code changes. Three documentation inconsistencies were found and are resolved here before implementation:

1. `docs/11_SYSTEM_ARCHITECTURE.md` still describes SQLite as a candidate whose final selection remains future work. Accepted decisions D011 and D012, migrations 001–002 and the closed M1 state establish Python 3.11+ plus SQLite as the current classical runtime. M3 extends that accepted choice; it does not reopen it.
2. `docs/17_OPEN_QUESTIONS.md` still asks which runtime, confidence scale and durable exports should be selected. D011, D013 and the implemented JSON/CSV/Markdown export resolved those questions for the current implementation. Future replacement remains possible under the technology-resilience principle.
3. The M1 checklist mentions a source-registry schema, while the accepted M1/M2 implementation contains embedded EvidenceRecord source fields and a ZOS migration-source manifest, not a general runtime source registry. M3 therefore adds the missing general registry without rewriting historical evidence or treating migration manifests as general sources.

These are documentation lag, not competing product architectures. M3 preserves the existing layer model, identity boundary, approval model, specialist separation and deterministic fallback.

## Implemented bounded scope

M3 adds only classical runtime infrastructure: general source, memory-storage, capability and specialist registries; application-level approval records; an explicit deterministic router; minimal runtime operation records; local SQLite backup/verification/restore; and non-destructive health reporting.

Memory in M3 is storage and governed promotion only, not a Memory Engine. Specialist registration is metadata only, not federation or invocation. Routing uses explicit structured fields and does not perform semantic interpretation, capability sensing or cognition. Approval records prove only application state, not cryptographic human identity.

## Reused foundations

M3 reuses the accepted Python 3.11+ runtime, `.zis/` local data boundary, SQLite migration runner, EvidenceStore, audit table, deterministic identifier helpers, contract validator, CLI framework and JSON/CSV/Markdown exporter. M1 and M2 records and workflows were not rebuilt. Migration 003 extends the same database and every new durable mutation follows the existing caller-owned transaction pattern.

The bundled validator continues to implement only the ZIS-required subset of JSON Schema Draft 2020-12. It is not a standards-complete validator.

## Portable contracts and storage

The new contracts are `SourceRecord`, `MemoryRecord`, `CapabilityRecord`, `ApprovalRecord`, `RouteDecision`, `RuntimeOperation` and `BackupManifest`. `SpecialistManifest` is reused and extended with domain, interface version, compatible runtime versions and availability. `CapabilityProposal` remains distinct from the capability registry.

Migration `003_classical_runtime.sql` adds projection tables and relational indexes/foreign keys for sources, approvals, memory/evidence links, capabilities/dependencies, specialists, route decisions and runtime operations. The JSON records remain the portable canonical representation; indexed columns enforce current relational state. The existing audit table stores before/after history for mutations. Audit history is application-level append-only and is not cryptographically tamper-evident against direct database modification.

## Registries and governed lifecycle

Source records use deterministic IDs derived from stable source fields and store an ordinal reliability value, privacy class, provenance and active/inactive state. A registry entry is metadata only: it does not fetch or activate a source. Existing M1/M2 evidence remains valid with embedded source references and does not require rewriting.

Memory proposals require at least one existing EvidenceRecord. Proposal creation and its matching pending `memory.promote` ApprovalRecord occur in one transaction. A proposal remains non-current until an approval exactly matches action type, memory ID and scope; evidence confidence alone never activates it. Contradiction state is derived from preserved evidence contradictions. Supported terminal/current transitions are validated, versioned and audited; historical evidence is never removed.

Capability records begin proposed with unknown availability. An exact `capability.approve` approval is required before approval, and all declared dependencies must be present and available before the capability becomes available. An optionally approval-gated capability requires a separate exact `capability.execute` approval at routing time. Registration does not create or sense a capability.

Specialist records begin proposed with unknown availability. Approval, availability and runtime-version compatibility are checked before a specialist can be returned as a candidate. Registration stores only a manifest: no specialist code or knowledge is copied, and no invocation occurs.

Approval records support pending, approved, rejected, deferred, expired and revoked states. Authorization compares the exact action type, action reference and scope and accepts only approved state. Decisions produce new versions and audit events rather than silently erasing history. These records do not implement user accounts, authentication, signatures or proof of human identity.

## Router and operations

The router accepts explicit structured action types and produces one of `no_action`, `classical_runtime`, `existing_capability`, `specialist_candidate`, `approval_required` or `unsupported`. Every RouteDecision includes its reason, rules evaluated, considered references, approval requirement, unsupported reason where applicable and a fingerprint of the current registry state. The same timestamped input and state produces the same deterministic request, route and operation identifiers.

M3 executes only the bounded local `runtime_status` action and the no-op path. Capability and specialist outcomes are routing results, not invocations. Persistent-change requests route to approval but are not executed because capability creation/sensing belongs to M8. Missing, unknown or inadequate structured inputs return `unsupported` rather than being guessed.

RouteDecision and RuntimeOperation persistence plus the associated audit event use one SQLite transaction. Operations end as completed, routed, blocked, unsupported or failed; there is no queue, worker or background lifecycle.

## Backup and restore guarantees

Backup uses Python's SQLite backup API to create a consistent local database copy at an explicit destination. It verifies SQLite integrity and foreign keys, records durable table counts, computes SHA-256, and publishes a versioned `BackupManifest` containing schema version, runtime version, source path and creation time. Temporary output is removed if final publication verification fails. Nothing is uploaded.

Verification checks the manifest contract, filename binding, checksum, exact supported schema/runtime versions, integrity, foreign keys and stored counts. Restore verifies before reading, copies through SQLite into a temporary database, rechecks integrity/counts/version, and only then replaces the explicit destination. A fresh destination is the default; overwrite requires `--overwrite`. Failure before publication leaves an existing destination unchanged.

These guarantees cover the tested local process path, not power-loss durability of filesystem replacement, damaged-live-database recovery, cross-version migration, cryptographic manifests or cloud disaster recovery. Backups can contain private runtime state and must stay outside public Git.

## Health and export

`zis health` reports database accessibility, SQLite integrity, the exact migration sequence, required tables, foreign-key violations, durable counts, schema version and runtime version. It reports errors and performs no destructive repair.

JSON export format version 2 includes all M3 runtime projections alongside evidence, contradictions and audit events. Markdown includes human-readable family counts; CSV remains the tabular EvidenceRecord export. These exports require no AI or proprietary reader.

## CLI surface

The CLI adds the bounded command families `runtime`, `source`, `memory`, `capability`, `specialist`, `approval`, `route`, `backup`, `restore` and `health`. Mutating commands require explicit structured fields. Listing/showing/status commands expose stored state without implying execution or intelligence.

## Verification and limitations

The complete suite passes 59 tests: 33 accepted M1/M2 tests and 26 M3 tests. Coverage includes lifecycle and approval rejection, duplicate registries, deterministic/unsupported routing, audit-failure rollback, runtime export, checksum tamper detection, incompatible/corrupt rejection, safe failed restore, integrity/orphan reporting and a full synthetic backup/restore state-equivalence drill. `python -m compileall -q src tests`, CLI smoke tests and `git diff --check` also pass.

M3 does not implement the Cognitive Engine (M4), Specialist Federation or invocation (M6), capability sensing/solution ladder (M8), observation connectors, semantic memory, embeddings, AI providers, frontend, cloud backup or distributed infrastructure. Deferred durability cases are listed in `docs/testing/TESTING_STRATEGY.md`.
