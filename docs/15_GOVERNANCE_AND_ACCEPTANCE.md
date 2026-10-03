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

## Change governance

Every architecture change should record reason, evidence, alternatives, decision, consequences and migration impact.

The system must preserve old versions enough to explain how current behavior evolved.
