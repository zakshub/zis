# ZOS Migration and Reuse Plan

ZOS is an existing intelligence asset and should be mined, not blindly copied.

The reviewed ZOS repository already contains useful architecture around a kernel, evidence, models, memory, routing, runtime, permissions, human authority, private data separation and update protocols. It also contains structured material on cognitive patterns, writing, product thinking, blind spots, design, task routing and personal constitution.

## Migration rule

ZIS will inherit validated cognitive evidence and reusable architecture while removing direct personal identity and avoiding duplication of specialist brains.

## What to reuse

1. Evidence hierarchy concepts
2. Confidence and contradiction handling
3. Permission model concepts
4. Model update protocol
5. Task routing principles
6. General blind-spot pattern candidates, after evidence review
7. Transferable communication patterns, without specialist writing operations or private corpus content
8. Cognitive sequence candidates
9. Human approval rules
10. Local first and private data separation patterns
11. Audit and provenance patterns
12. Useful historical answers that reveal reasoning patterns

## What not to copy directly

1. Real names
2. Employer or company identity
3. Face or identifying profile data
4. Specialist design knowledge that now belongs in Designer
5. Image production knowledge that now belongs in Studio
6. Outdated architecture that conflicts with current ZIS principles
7. Claims based only on personality tests
8. Sensitive private records

## Implemented M2 flow

The local, dependency-free flow is:

`selected source -> SHA-256 fingerprint -> A-G classification -> structured candidate -> privacy/specialist/temporal gates -> human review -> approved EvidenceRecord import`

The machine manifest preserves the repository, immutable source ref, path, fingerprint, classification and rationale, ordinal confidence, gate states, candidate IDs, review/import state, resulting evidence IDs, timestamps, version and transformation history. Raw source content is read only for hashing and structural screening and is not stored in the manifest database.

Candidate creation is deterministic for stable semantic input but deliberately manual-structured. M2 does not pretend to understand arbitrary prose and does not turn every paragraph into evidence. Candidate types distinguish statements, observations, patterns, principles, historical preferences, uncertainty, contradictions and obsolete claims.

All candidate free text remains `review_required` until a human approves it. Structurally detected identity-bearing candidate text is omitted before persistence and approval is blocked; D-class or primarily specialist candidates route outside core; E-class and obsolete candidates are blocked. A `transferable_cognitive_pattern` hint only moves detected specialist material to review—it never approves it.

Historical and superseded imports are non-current and expired. Uncertain or contradicted imports are non-current. Linked approved candidates use the existing contradiction table when both evidence records exist; no winner is selected.

Review decisions are `approve`, `reject`, `defer`, `requires_redaction`, `route_to_specialist` and `mark_obsolete`. Approval and import are separate audited operations. Import reuses the existing EvidenceStore, is idempotent by deterministic identifiers, and keeps the evidence write, lineage update, contradiction creation and audit event in one SQLite transaction.

Dry-run performs no database write. It reports source classifications, candidate/gate counts and approval/import eligibility. See `docs/migration/M2_IMPLEMENTATION.md` for commands and limitations.

## Deliberate boundaries

No source is mass-imported. No raw private ZOS file is copied into ZIS. No specialist expertise becomes ZIS core. Structural screening cannot prove free-text anonymity, so uncertain material requires human review. ZOS remains the historical source; lineage is preserved rather than erased.
