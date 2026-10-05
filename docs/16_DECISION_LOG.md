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

## D021 M3 uses projection tables plus existing audit history
Decision: store current validated records as JSON projections with indexed relational lifecycle/reference columns, while recording every mutation in the existing application-level audit table.
Reason: this preserves portable contracts, relational integrity and atomic rollback without introducing event-sourcing infrastructure.
Alternatives: microservices, queues, a new event store and distributed workflow infrastructure were rejected as unnecessary.
Architecture impact: migration 003 extends the accepted SQLite runtime without changing its layer model.

## D022 Durable memory requires exact approval
Decision: evidence-backed memory begins `proposed` and non-current; activation requires an approved record matching `memory.promote`, the exact memory ID and scope.
Reason: evidence existence, confidence or repetition alone must not silently become durable truth.
Architecture impact: M3 implements storage and governance only; consolidation, decay, semantic memory and cognition remain later milestones.

## D023 Classical routing is explicit and non-semantic
Decision: M3 routes only declared structured action types against current registry/approval state and records every rule evaluated.
Reason: insufficient information must be visible rather than filled by probabilistic or pretend semantic reasoning.
Architecture impact: capability sensing remains M8, specialist invocation remains M6 and cognitive routing remains M4.

## D024 Backup publication and restore are verify-before-replace
Decision: use SQLite's backup API, publish a checksum/version/count manifest, restore through a verified temporary database, and refuse destination overwrite by default.
Reason: copying a live database directly or replacing a destination before verification creates avoidable partial-state risk.
Architecture impact: backup remains local and explicit; cloud synchronization and cross-version recovery are not introduced.

## D025 M4 cognition uses explicit context and versioned deterministic rules
Decision: each cognitive run names its evidence, optional memory, scope, trigger and effective time; content identities include explicit input, referenced state and ruleset `m4.v1`, while execution timestamps remain metadata.
Reason: cognition must be reproducible and inspectable without hidden global personality state or automatic history loading.
Alternatives: implicit whole-database context and provider-generated reasoning were rejected as privacy risks and non-deterministic M4 scope expansion.
Architecture impact: CognitiveSession becomes the boundary; M5 adapters, if approved later, must preserve it.

## D026 Cognitive artifacts remain candidates distinct from truth and memory
Decision: patterns, hypotheses and ideas carry explicit non-truth/non-memory semantics; evaluations have no decision authority and reflections make no consciousness claim.
Reason: repetition, interpretation, ideation and analysis must not silently become durable belief.
Architecture impact: durable memory remains governed by the accepted M3 substrate and future Learning Engine.

## D027 Model-update proposal reuses M3 approval and cannot apply in M4
Decision: proposal creation atomically requests an exact M3 approval; M4 may record approval but rejects `applied` and never mutates the target memory.
Reason: recognizing that an interpretation may need revision is cognition, while applying durable learning belongs to a future approved Learning Engine.
Architecture impact: no second approval system and no autonomous self-modification path are introduced.

## D028 M4 stores portable projections plus normalized important references
Decision: migration 004 stores strict JSON contract projections with indexed lifecycle fields and one normalized reference table.
Reason: portable reconstruction and queryable lineage are both required; a single opaque blob is insufficient and dozens of relation-specific tables are unnecessary.
Architecture impact: export, backup and health include all M4 tables and orphan-reference checks.

## D029 M5 AI remains an explicit optional outer adapter
Decision: AI assistance is invoked only through `AIService`; deterministic cognition never calls it automatically and provider failure does not make ZIS fail.
Reason: D005 requires replaceability and the accepted M3/M4 path must remain authoritative without network or credentials.
Architecture impact: adapters can augment explicit requests but cannot replace cognition, governance or execution.

## D030 M5 implements one dependency-free OpenAI adapter
Decision: implement exactly one real OpenAI Responses adapter with Python standard-library HTTPS and injected transport; add no provider SDK or retry framework.
Reason: the current runtime already has the required JSON, TLS/HTTP and timeout primitives, while injection provides deterministic tests and provider isolation.
Alternatives: a provider SDK and multiple real adapters were rejected as unnecessary M5 dependencies and federation scope.
Migration impact: endpoint/model are runtime configuration and provider-specific parsing stays in `ai.py`.

## D031 AI transmission is explicit-safe and credentials are runtime-only
Decision: permit only explicitly approved `public` or `internal` structured context after identity/credential checks; read the credential from its environment variable only at invocation.
Reason: the provider boundary is an external disclosure boundary and secrets must never enter SQLite, audit, export or backup.
Architecture impact: request records may retain the exact approved safe structured payload for reproducibility, but audit stores fingerprints and metadata only.

## D032 Provider output persists only as a validated candidate
Decision: validate response envelopes and requested output schema before creating an `ai_candidate_not_truth` pending-review record; never auto-convert it to any M1-M4 artifact.
Reason: provider output is untrusted interpretation, not evidence, memory, approval, decision or execution.
Architecture impact: migration 005 stores request, response and candidate projections in one audited transaction.

## D033 Usage and cost are separate and bounded
Decision: preserve provider token counts when supplied, retain null when unknown, and calculate cost only from explicit versioned local pricing metadata as an estimate.
Reason: tokens are not money and model prices are time-dependent external facts.
Architecture impact: no timeless price is hard-coded and unknown pricing produces unknown cost.

## D034 M6 federation is explicit and separate from AI
Decision: add a SpecialistAdapter protocol and explicit SpecialistFederation invocation method without changing M3 routing, M4 cognition or M5 provider selection.
Reason: a specialist owns domain intelligence while an AI provider is optional infrastructure; conflating them would hide authority and execution boundaries.
Architecture impact: the router still returns `specialist_candidate`; only an explicit federation call can invoke one named specialist.

## D035 Initial specialists remain metadata-only
Decision: register Designer, Studio, SEO and TaxBot, but mark their adapters not configured until each repository exposes an approved stable general task contract. Defer ZIST.
Reason: inspected repositories expose knowledge governance, incomplete retrieval, infrastructure-specific workflows or storage operations—not a safe common task endpoint. ZIST's interface and privacy boundary could not be verified.
Alternatives: invented CLI commands, internal-module calls and starting specialist infrastructure were rejected.

## D036 Specialist results remain isolated execution records
Decision: a validated response receives an execution provenance receipt but is never auto-promoted into evidence, memory, approval, contradiction resolution or execution authority.
Reason: specialist expertise does not remove ZIS truth and governance requirements.
Migration impact: migration 006 stores requests, responses and receipts atomically with metadata-only audit.

## D037 M6 uses fail-visible compatibility and no fallback graph
Decision: require exact request/response contract versions and declared runtime compatibility, return normalized failures, and never substitute another specialist automatically.
Reason: silent coercion or fallback could change domain authority, privacy exposure and consequences.
Architecture impact: health is read-only and specialist availability remains independent of core integrity.

## D038 M7 collection is explicit, session-bound and source-approved
Decision: every collection call names one approved ObservationSource, its exact approval scope, one adapter operation and one explicit input; no background observer exists.
Reason: observation must be transparent and attributable rather than becoming surveillance or implied unlimited permission.
Architecture impact: migration 007 adds source/session projections while adapters remain separate from AI and specialist protocols.

## D039 M7 uses a local private vault with public-safe projection
Decision: owner-approved private observation content may exist only in the gitignored SQLite vault. Default export uses explicit least-disclosure projections for ObservationSource, ObservationCollectionSession, ObservationRecord and ObservationEvidenceProposal. Source/session operational free text and proposal payload/lineage are omitted; only explicitly public ObservationRecord payload may be included.
Reason: identity-safe metadata is not automatically public-safe, and local identity-bearing capture and public/external safety are different boundaries.
Architecture impact: backups contain complete private vault state and remain private; default export preserves structural IDs, lifecycle/status, safe classifications, counts, timestamps and fingerprints without publishing private M7 context.

## D040 M7 exact duplicates link and logical purge marks
Decision: exact source/reference/event/fingerprint duplicates create a session link to the existing record, not another observation. Purge removes current content and leaves a metadata marker.
Reason: deterministic behavior avoids silent multiplication while retaining collection accountability; portable SQLite cannot honestly guarantee secure erasure across pages and old backups.
Architecture impact: duplicate links and purge markers are durable; semantic deduplication and secure erasure are not claimed.

## D041 Observation-to-evidence is a separately approved transaction
Decision: only accepted observations may support a public-safe ObservationEvidenceProposal; exact M3 approval is required before one idempotent M1 EvidenceRecord is created.
Reason: observation, review acceptance, evidence and memory carry different authority and confidence meanings.
Architecture impact: M7 reuses M1 evidence insertion and M3 approvals; it adds no memory mutation, contradiction resolution or learning application.
