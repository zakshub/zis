# Governance and Acceptance

## Human authority

The owner remains final authority over persistent capability creation, sensitive permissions, irreversible actions, production release and major cognitive model changes.

## Approval categories

Low impact temporary reasoning may proceed automatically.

Reversible read only research may proceed within granted permissions.

Persistent learning requires governed promotion.

New connectors require explicit permission.

Persistent feature, tool, product, system or specialist intelligence creation requires explicit approval.

High risk external actions require explicit approval even when automation mode exists.

## Truth rules

ZIS must not claim that a task ran when it did not run.

ZIS must not claim that a specialist was consulted when it was unavailable.

ZIS must not promote one observation into a durable trait without evidence.

ZIS must distinguish observed facts, user statements, inferences, hypotheses and external claims.

## Definition of Done for documentation phase

1. Core concepts have explicit definitions.
2. Contradictions are recorded and resolved or marked open.
3. Identity boundary is clear.
4. Specialist duplication policy is clear.
5. Technology independence policy is clear.
6. Observation transparency is clear.
7. Build approval gate is clear.
8. Roadmap and milestones are actionable.

## Definition of Done for any future implementation milestone

1. Code exists.
2. Tests exist.
3. Reproduction instructions exist.
4. State is persisted where required.
5. Failures are visible.
6. Security boundary is documented.
7. No fake data is presented as real activity.
8. Recovery path exists.
9. Status document is updated.
10. Human acceptance criteria are satisfied.

## Milestone 1 acceptance evidence

1. Five machine contracts and a deterministic validator exist.
2. SQLite initialization, versioned migration, evidence persistence and audit history are tested.
3. Provenance, ordinal confidence, contradictions and temporal supersession are preserved.
4. JSON, CSV and Markdown exports provide non-proprietary recovery representations.
5. Identity scrubbing and Git/private-data boundaries are documented and partially enforced structurally.
6. ZOS was inventoried as an ancestor source; no personal or specialist material was imported.
7. The automated suite runs without AI, network or external services.
8. Human acceptance is still required before beginning the next milestone or importing reviewed ZOS evidence.

M1 acceptance is bounded: the validator is not standards-complete, and application-level append-only audit events are not cryptographically tamper-evident. These limits must remain visible until a later approved implementation changes them.

## Milestone 2 acceptance evidence

1. Machine contracts and SQLite state exist for source manifests, candidates and review events.
2. Selected read-only ZOS paths can be fingerprinted, classified and dry-run without durable mutation.
3. Candidate creation is deterministic/manual-structured; no LLM or external service is used.
4. Privacy, specialist, obsolete and approval gates prevent unsafe import.
5. Approved imports reuse EvidenceStore and preserve confidence, temporal context, provenance and source lineage.
6. Duplicate import is idempotent and linked conflicts reuse the existing contradiction model.
7. Synthetic rollback coverage proves a failed final audit cannot leave partial import state.
8. The 33-test suite passes and contains no real private ZOS fixture.
9. No actual ZOS candidate/import is approved by this implementation milestone; each future selection remains a human decision.

## Milestone 3 acceptance evidence

1. Source, memory-storage, capability, specialist and approval registries persist through migration 003.
2. Memory remains proposed and non-current until an exact approved `memory.promote` action activates it.
3. Rejected, revoked, missing or scope-mismatched approvals cannot authorize an operation.
4. CapabilityProposal remains distinct from installed capability metadata; no capability is automatically created.
5. Specialist registration stores metadata only and cannot invoke or copy a specialist brain.
6. Routing is deterministic from structured input and registry state, records evaluated rules and returns unsupported rather than guessing.
7. New projections validate lifecycle transitions and write audit history in the same transaction.
8. Backup manifests bind SHA-256 checksum, schema/runtime versions, source metadata and durable record counts.
9. Tampered/incompatible backups are rejected; restore verifies a temporary database and does not overwrite by default.
10. Health reports SQLite, schema, required-table and foreign-key integrity without destructive repair.
11. The 59-test suite and synthetic full-state restore drill pass without AI, network or private fixtures.

M3 approvals are application-level governance records. They do not authenticate a human cryptographically, provide non-repudiation or make audit history tamper-evident against direct database access.

## Milestone 4 acceptance evidence

1. Explicit cognitive sessions and ruleset/state fingerprints provide an inspectable deterministic boundary.
2. Attention and novelty/repetition are ordinal, reasoned and limited to explicit structured comparison.
3. Known contradictions remain unresolved unless the existing human-governed contradiction API is used; candidates never choose a winner.
4. Associations require deterministic bases and are not semantic proof.
5. Pattern, hypothesis and idea contracts explicitly distinguish candidates from truth and memory.
6. Evaluations preserve per-criterion reasoning and carry no decision authority; reflections preserve uncertainty and claim no consciousness.
7. Model-update proposals require exact M3 approval and cannot be applied by M4 or mutate target memory.
8. Session writes, references, generated approvals and audit events commit in one transaction; injected final-audit failure rolls them all back.
9. Migration 004 upgrades schema v3 and initializes cleanly; health, export and backup/restore cover M4 durable state.
10. The 79-test suite passes with synthetic fixtures and no AI, network, specialist invocation or private evidence.

M4 acceptance remains human-controlled. An ordinal attention level is not importance truth, repetition is not correctness, confidence is not probability and approval remains application-level governance rather than cryptographic identity.

## Milestone 5 acceptance evidence

1. Provider-neutral request/response/candidate contracts and adapter protocol exist independently of the real provider.
2. Disabled and missing-credential modes return explicit normalized states while core health and M4 cognition remain operational.
3. Exactly one real provider adapter is isolated from EvidenceStore, ClassicalRuntime and CognitiveEngine.
4. External transmission requires explicit safe context and privacy approval; identity/credential signals are rejected before transport.
5. Credentials, authorization headers, raw provider envelopes and hidden reasoning are absent from durable records and audit payloads; recursive code checks enforce the hidden-reasoning boundary independently of caller schemas and provider obedience.
6. Malformed envelopes, malformed JSON and schema-invalid structured output create `invalid_output`, never partial candidates.
7. Successful output becomes only a pending-review AI candidate and cannot mutate evidence, memory, contradictions, approvals or operations.
8. Usage and optional estimated cost retain unknown states and never equate token count with billing.
9. AI request, response, candidate and metadata-only audit write atomically; injected audit failure rolls back all M5 durable state.
10. Migration 005, health, export and backup/restore cover M5 records; optional AI availability remains separate from core health.
11. The 100-test suite passes without a live provider credential, external network or private fixture.

M5 acceptance does not authorize AI output as truth, approval, decision or execution and does not authorize specialist federation.

## Milestone 6 acceptance evidence

1. Portable specialist request, normalized response and execution-provenance contracts exist independently of any specialist repository.
2. Designer, Studio, SEO and TaxBot are registered as governed metadata only; repository expertise is not copied into ZIS.
3. Current adapters report not configured because no approved stable general specialist-task interface was verified; no callable capability is fabricated.
4. ZIST is explicitly evaluated and deferred rather than forced into the registry.
5. Identity, credential, privacy, explicit-context, manifest capability, registry state, compatibility and approval checks precede adapter invocation.
6. A successful result validates completely and creates a provenance receipt; malformed output is rejected whole.
7. Specialist output cannot create evidence, memory, approval, contradiction resolution or external execution authority.
8. Tax submission is absent, and bounded high-impact TaxBot preparation requires exact pre-existing approval.
9. Request, response, receipt and metadata-only audit commit atomically; audit failure rolls all M6 interaction state back.
10. Migration 006, health, export and backup/restore cover M6 records while specialist availability remains separate from core health.
11. The 115-test suite passes without credentials, network, external services, private fixtures or a live specialist runtime.

M6 acceptance authorizes only explicit federation through an approved adapter. It does not authorize autonomous selection, fallback, specialist chains, capability sensing, observation or any M7+ behavior.

## Milestone 7 acceptance evidence

1. Observation sources require exact application-level approval and enforce declared scope/data classes through explicit collection sessions.
2. Manual and bounded file-import adapters are separate from AI and specialist adapters; no background or external connector exists.
3. ObservationRecord preserves capture provenance, time, privacy, capture integrity, retention and review state without becoming evidence, memory or truth.
4. Restricted, denied and suspected-secret input is quarantined without durable raw payload or private-content audit.
5. Private local observations remain in the gitignored vault and default public-safe export emits metadata/fingerprints only.
6. Exact duplicates link to prior observations; conflict is not resolved and no semantic deduplication is claimed.
7. Evidence promotion requires accepted observations, a separately authored public-safe proposal, exact M3 approval and one atomic M1 EvidenceRecord insertion.
8. Observation APIs cannot mutate memory, resolve contradictions, auto-run cognition, call AI/specialists or sense capabilities.
9. Migration 007, health, query, export and private backup/restore cover durable M7 state.
10. The 134-test suite passes with synthetic fixtures and no network, credentials, real observation content or external connector.

M7 acceptance authorizes only explicit local collection through an approved adapter. It does not authorize surveillance, external-source integration, autonomous learning, memory rewriting, contradiction resolution or M8 capability sensing. Logical purge is not a secure-erasure guarantee, and backups remain private.

## Change governance

Every architecture change should record reason, evidence, alternatives, decision, consequences and migration impact.

The system must preserve old versions enough to explain how current behavior evolved.
