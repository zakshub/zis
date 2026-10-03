# Decision Log

## D001 ZIS is not a specialist monolith
Decision: specialist expertise stays in specialist brains where practical.
Reason: prevent duplication, stale copies and conflicting sources of truth.

## D002 English is canonical specification language
Decision: architecture, schemas, roadmaps and production specifications use English.
Reason: implementation clarity and cross tool interoperability.

## D003 ZIS remains multilingual
Decision: Urdu and Roman Urdu are first class interaction languages.
Reason: language of interaction should not constrain canonical technical specification.

## D004 Direct identity is excluded from public core
Decision: real name, face, employer, company and precise private identifiers are not required in public ZIS.
Reason: identity protection and portability.

## D005 AI is optional infrastructure
Decision: modern AI may accelerate ZIS but cannot be an existential dependency.
Reason: long term technological resilience.

## D006 Persistent new capability requires approval
Decision: ZIS may detect and propose a feature, tool, product, system or specialist intelligence but must request approval before persistent creation.
Reason: human authority, cost control and anti overengineering.

## D007 Observation must be transparent
Decision: connected sources, permissions, observations, inferences and learning promotion are visible through an Observation Ledger.
Reason: no silent surveillance.

## D008 World simulation is a later interface layer
Decision: immersive electronic species world is optional and must reflect real backend state.
Reason: visual metaphor must not replace the real system.

## D009 ZOS is an ancestor and evidence source
Decision: ZOS is selectively migrated rather than cloned.
Reason: preserve prior work while adopting the newer ZIS architecture.

## D010 Minimum sufficient solution is default
Decision: no build and manual methods are valid outcomes.
Reason: prevent system building from becoming the goal itself.

## D011 Python standard library is the first executable runtime
Decision: use Python 3.11+ without runtime third-party dependencies for Milestone 1.
Reason: it is portable, inspectable and sufficient for schemas, CLI, hashing, timestamps, SQLite and exports.
Alternatives: TypeScript/Node, Go, Rust or a service framework. These add no required M1 capability.
Migration impact: JSON contracts, SQL migrations and export formats remain language-neutral.

## D012 SQLite is the first local evidence store
Decision: use one local SQLite database under the gitignored `.zis/` directory.
Reason: transactions, relational integrity, mature tooling and minimal operations fit the existing local-first architecture.
Alternatives: JSONL was considered but is weaker for contradiction relations and migrations; server databases are unnecessary.
Migration impact: JSON/CSV/Markdown export prevents SQLite from becoming the only representation.

## D013 Confidence is ordinal
Decision: use `unknown`, `weak`, `probable`, `strong`, `established`.
Reason: the requested M1 model rejects fake mathematical precision while remaining explicit and sortable by human meaning.
Migration impact: ZOS numeric confidence must not be converted automatically; it requires review.

## D014 Evidence history is preserved through projections and audit events
Decision: keep evidence rows, represent contradictions separately, and record lifecycle/supersession actions in append-only audit events.
Reason: a newer interpretation must not erase old evidence or resolution rationale.
Alternative: immutable event sourcing for every read was rejected as unnecessary M1 complexity.

## D015 User Milestone 1 includes bounded Phase 1–3 foundations
Decision: implement the user's named Milestone 1 as one bounded delivery while preserving the repository's longer roadmap numbering.
Reason: the requested definition of done explicitly includes contracts, ZOS inventory, local database, CLI, migrations and export. This is a scope aggregation, not a change to the product architecture.

## D016 No internal documentation contradiction blocked implementation
Decision: treat open runtime/confidence/export questions as intentionally deferred choices resolved by the approved Milestone 1 request.
Reason: the foundation documents name options and boundaries but do not prescribe conflicting implementations.

## D017 M1 validator and audit guarantees are explicitly bounded
Decision: describe the bundled validator as the ZIS-required subset of JSON Schema Draft 2020-12, and describe audit events as application-level append-only rather than cryptographically tamper-evident.
Reason: accurate guarantees are required for portability, security review and future replacement decisions.
Architecture impact: none. This clarifies existing behavior.

## D018 Logical evidence operations use one SQLite transaction and connection
Decision: validation reads, evidence/contradiction mutations and their audit writes execute within one connection and transaction for each logical operation.
Reason: a failed operation must not leave its state and audit history inconsistent.
Architecture impact: none. This tightens the existing SQLite implementation boundary.

## D019 ZOS migration is manifest-driven and human-gated
Decision: M2 stores source hashes/metadata and manually structured candidates, screens every candidate, and separates explicit approval from EvidenceStore import.
Reason: deterministic code cannot safely infer arbitrary prose, raw private sources must not be copied into ZIS, and ZOS remains evidence rather than architecture.
Alternatives: bulk file copying, automatic paragraph conversion and LLM extraction were rejected for this milestone.
Migration impact: real ZOS material remains unimported until an owner reviews a specific candidate; specialist, sensitive and obsolete material stays outside core.

## D020 M2 reuses M1 storage and contradiction primitives
Decision: approved import, lineage updates, contradiction materialization and audit history use the existing SQLite database and one caller-owned transaction.
Reason: this preserves established contracts and rollback behavior without a second evidence or conflict system.
Architecture impact: none; migration 002 adds bounded manifest/review tables.
