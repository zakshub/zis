# M4 Cognitive Engine v0.1

## Pre-implementation consistency review

The accepted M0-M3 documentation, contracts, migrations, implementation and tests were read before M4 changes. One scope tension was documented before code: the original IdeaLineage contract included `approved`, `executing`, `completed` and `learned`, while M4 explicitly forbids pretending that later execution or learning exists. M4 therefore keeps only `spark`, `unclear`, `exploring`, `researching`, `promising`, `rejected`, `parked` and `ready`. Later states remain architectural intent for later milestones.

No other contradiction required an architecture change. M4 extends the accepted evidence, contradiction, memory-substrate, approval, transaction, audit, export, backup and health foundations.

## Meaning and boundary

M4 cognition is a deterministic transformation of explicitly supplied structured context into inspectable candidate artifacts. It can prioritize, compare exact structured properties, preserve known relations, form support-bounded candidates, evaluate them against named criteria and record uncertainty.

It is not an LLM agent, semantic understanding, consciousness, emotion, intuition by assertion, personality diagnosis, truth generation, a Learning Engine or an AI provider. It does not automatically load history, store chain-of-thought, invoke specialists, sense capabilities, execute actions, resolve contradictions or modify durable memory.

The architectural distinctions are executable invariants:

1. Evidence is an input record; a pattern requires at least two distinct evidence records and carries `truth_status: candidate_not_truth` and `is_memory: false`.
2. A pattern is a repeated deterministic structure; a hypothesis is an explicitly supplied testable interpretation with strengthening and falsification conditions.
3. A hypothesis carries `truth_status: untested_interpretation` and `is_memory: false`; only governed memory APIs can create memory projections.
4. An idea carries `truth_status: idea_not_truth` and requires explicit lineage.
5. An evaluation stores per-criterion findings and `decision_authority: false`.
6. A reflection stores structured post-analysis and `consciousness_claim: false`.
7. A model-update proposal requires approval, but `applied` is rejected until a future Learning Engine implements application.
8. An association requires an explicit deterministic basis and is not semantic proof.
9. Attention is an explainable processing signal, not a declaration of importance truth.
10. Repetition can justify a candidate pattern but its rationale states that repetition is not correctness.
11. Confidence uses ordinal terms and evaluation explicitly states that it is not probability.
12. Cognition runs entirely without an AI provider.

## Session and deterministic pipeline

`CognitiveEngine.run_session` requires an explicit trigger, scope, at least one evidence ID and an effective timestamp. Memory IDs, importance, tags, contradiction candidates, hypotheses, ideas, model-update proposals and reflection inputs are optional and explicit. Unknown fields and references outside the supplied session context are rejected. The engine never scans or loads the owner's entire history.

The pipeline:

1. enforces the structural and direct-text identity boundary;
2. validates and loads only referenced evidence and memory;
3. fingerprints normalized input and the referenced database state;
4. derives a session ID from those fingerprints, ruleset `m4.v1` and effective time;
5. calculates attention plus novelty/repetition and temporal signals;
6. surfaces known contradictions and records only justified contradiction candidates;
7. creates structured associations;
8. creates supported pattern candidates and explicit hypotheses/ideas where supplied;
9. evaluates generated candidates per criterion;
10. creates governed model-update proposals where explicitly supplied;
11. records one structured reflection;
12. completes the session and all audit writes in the same SQLite transaction.

No pattern, no hypothesis and no update proposal are valid outcomes. Re-running the same explicit input against the same referenced state and ruleset returns the same content-derived session and artifact IDs. `started_at`, `completed_at` and audit timestamps are operational execution metadata and are not used as cognitive identity.

## Attention, novelty and time

Attention levels are `low`, `medium`, `high` and `critical`. Rules can cite explicit importance, unresolved contradiction, novelty/repetition, weak or unknown confidence, temporal state and current-context relevance. Every signal contains its reasons, source confidence, contradiction references, novelty state and repetition count. There is no floating-point intelligence score.

Novelty states are `exact_duplicate`, `repeated_support`, `possible_variation`, `novel_in_context` and `insufficient_basis`. Comparison uses only exact normalized content, explicit structured tags, scope, source/reference relations, contradiction/supersession state and deterministic fingerprints. It does not claim semantic equivalence and uses no embeddings.

Temporal classification distinguishes current, historical, expired, superseded, non-current and not-yet-valid evidence relative to the explicit `effective_at`. Historical behavior is never automatically converted into a current trait.

## Contradictions and associations

Existing contradiction records are surfaced with their existing lifecycle. A structured input may create an association with status `candidate` and relation `contradiction_candidate`; it does not create or resolve an EvidenceStore contradiction. Both sides remain preserved and no winner is selected.

Association reasons are limited to exact deterministic bases implemented by the ruleset: shared source, exact scope, shared structured tag, exact normalized content, existing contradiction, explicit supersession or an explicitly supplied contradiction candidate. Each record preserves endpoints, relation type, reason, support, ordinal strength, status, provenance and time. M4 does not build a general knowledge graph.

## Candidate artifacts

Pattern candidates are created only from at least two distinct evidence records sharing exact normalized content or an explicit repeated structured tag. They retain evidence, association and counterevidence references, support count, temporal scope, ordinal confidence, lifecycle and rationale. They are never automatically promoted to memory.

Hypotheses are created only from explicit structured session inputs. They require origin/support references, assumptions, strengthening conditions and falsification conditions. Lifecycle is `proposed`, `exploring`, `supported`, `weakened`, `rejected` or `superseded`; no state makes the hypothesis truth or memory.

Ideas require a statement, trigger, rationale and at least one explicit parent/evidence/pattern/hypothesis/association lineage reference. M4 validates only the pre-execution lifecycle recorded above. It does not autonomously generate ideas from arbitrary prose.

Evaluations record named findings for evidence support, counterevidence, contradiction state, temporal relevance, ordinal confidence, exact scope fit and unresolved assumptions. Outcomes are bounded artifact labels such as `insufficient_evidence`, `needs_review`, `promising`, `weak`, `contradicted` and `supported_for_current_scope`.

Reflection records considered references, generated artifacts, uncertainty, unresolved contradictions, assumptions, missing evidence and reconsiderations. It never changes memory and never claims subjective experience.

## Model-update governance

A model-update proposal can target only a memory ID explicitly supplied to the session. It preserves the proposed change, rationale, support, counterevidence, confidence, impact and provenance. Creation atomically creates a pending M3 ApprovalRecord for exact action `model_update.approve`, exact proposal ID and scope. Approval must use that existing mechanism.

M4 can transition a correctly approved proposal to `approved`; it cannot transition it to `applied`. Applying a proposal and mutating the target memory are future Learning Engine responsibilities. Tests compare the target memory before and after proposal creation, approval and blocked application.

## Storage, portability and operations

Migration 004 adds focused tables for sessions and eight artifact families plus one normalized `cognitive_references` table. Validated JSON projections preserve portable public contracts; indexed lifecycle/reference columns and normalized references keep important relationships queryable without over-normalizing every nested field.

Every logical session write uses one connection and transaction. A final audit failure rolls back the session, artifacts, references, generated approval and audit events together. Audit history remains application-level append-only, not cryptographically tamper-evident.

JSON export includes all M4 projections and Markdown includes counts. SQLite backup/restore includes every M4 table and the normalized references. Health checks require migration 004 tables and detect orphaned cognitive references. The minimal CLI supports `cognition run`, session inspection, artifact inspection and validated lifecycle transitions.

The nine M4 schemas use the dependency-free validator's ZIS-required subset of JSON Schema Draft 2020-12; the validator is not standards-complete. The runtime remains Python 3.11+ standard library and SQLite, with no network or AI dependency.

## Privacy and limitations

Cognitive inputs and artifacts are subject to the existing recursive identity-field boundary plus conservative direct-text checks for email, phone, credential/token and precise-address patterns. This is defense in depth, not perfect anonymization; uncertain free text still requires human review. Session records store references and fingerprints, not a hidden copy of the input specification. Tests use synthetic content only.

Deterministic exact rules cannot recognize paraphrases, implication, sarcasm, causal structure or general semantic relatedness. Ordinal confidence is not calibrated probability. Pattern support is not correctness. Model-update approval is application governance, not cryptographic human authentication. Power-loss, disk-full, high-contention and cryptographic audit guarantees remain in the resilience backlog.

## Verification and next boundary

The verified suite contains the accepted 59 M1-M3 tests plus 20 M4 tests, including CLI smoke: 79 tests total. It covers the original M4 behavior list, fresh migration through 004, schema-v3 to v4 upgrade, atomic rollback, deterministic IDs, temporal handling, identity rejection, export, health, and full M4 backup/restore state equivalence.

M5 is the exact next recommended milestone after owner review. It may add an optional provider-neutral AI adapter with a no-provider fallback. It must not replace these deterministic contracts or start specialist federation, observation, capability sensing, UI or simulation work.
