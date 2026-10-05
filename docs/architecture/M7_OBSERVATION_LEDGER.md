# M7 Observation Ledger

Status: implemented and verified locally on 2026-10-05. The design below was recorded before code changes and now describes the verified behavior, including the independent-audit public-projection fix.

## Decision

M7 extends the accepted Python 3.11+ and SQLite runtime with a governed local Observation Ledger. Collection is always an explicit caller action against one approved source and one exact scope. There is no background observer, recursive disk discovery, external connector, external transmission, semantic search, autonomous learning or capability sensing.

The executable boundary is:

```text
approved ObservationSource
-> explicit ObservationCollectionSession
-> privacy, scope and data-class checks
-> immutable ObservationRecord or quarantined safe marker
-> explicit review
-> optional EvidenceProposal
-> exact M3 ApprovalRecord
-> M1 EvidenceRecord
```

An observation is captured input, not evidence, memory, truth, personality, diagnosis or permission. Observation confidence describes capture integrity only. Review acceptance permits evidence review; it does not create evidence. Evidence promotion never creates memory or resolves a contradiction.

## Contracts and storage

M7 adds portable strict contracts for `ObservationSource`, `ObservationCollectionSession`, `ObservationRecord` v2 and `ObservationEvidenceProposal`. Migration 007 stores JSON projections plus indexed lifecycle/reference fields in four focused tables. Arbitrary payloads remain inside the observation JSON projection rather than being over-normalized.

Source states are `pending`, `approved`, `paused`, `revoked` and `retired`. Registration creates an exact pending M3 approval for `observation_source.approve`, the source ID and the source's approval scope. Only that exact approved record can move a source to approved. Pausing, resuming, revoking and retiring are explicit audited transitions. Revoked and retired are terminal; resuming a paused source rechecks the still-approved exact authorization.

Collection-session states are `running`, `completed` and `failed`. Observation review states are `captured`, `review_pending`, `accepted_for_evidence_review`, `rejected`, `quarantined`, `expired` and `deleted_marker`. Retention states are `active`, `expired`, `quarantined` and `purged`.

## Adapters and collection

`ObservationAdapter` is a separate protocol from the M5 AI and M6 specialist adapter protocols. It exposes an adapter ID/version, source type, availability, compatibility and one bounded `collect` operation.

M7 implements only:

1. `ManualObservationAdapter`, which accepts one explicit structured observation item;
2. `FileImportObservationAdapter`, which accepts one explicit regular file path, rejects directories and symbolic links, allows a small documented text/JSON extension set, enforces a byte limit, uses explicit UTF-8 decoding, never expands archives and records a SHA-256 file fingerprint;
3. `SyntheticObservationAdapter`, for injected deterministic tests only.

There is no browser, social, messaging, email, clipboard, screen, camera, microphone, application or directory-watching connector. Adapters do not transmit data externally and cannot invoke shells.

The adapter produces a bounded in-memory result before persistence. The service validates the whole result, then writes the session, observations/quarantine markers and metadata-only audit events through one connection and transaction. A technical validation or database failure rolls back the whole successful collection unit. A pre-persistence adapter failure is recorded as one explicit failed session with no observation rows. Policy-denied items are deterministic quarantined markers, not silent partial failures.

## Privacy, identity and secrets

The local SQLite database is the private observation vault and remains outside Git. Public repository content is limited to code, schemas, documentation and synthetic fixtures.

Local private observations may retain identity-bearing content only when the source is approved, the exact scope and data class are allowed, the record is `private`, and the retention policy permits local retention. `restricted` items are quarantined by default. Public/internal observations must pass the existing structural and direct-text identity checks.

Obvious credential/token signals are conservatively detected. Such items are quarantined as content-free markers: the raw value is not written to SQLite, audit, errors or public-safe export. Detection is defense in depth, not perfect secret discovery or anonymization.

Before an evidence proposal is stored, proposed content must pass the existing identity and direct-text checks regardless of the observation's local privacy class. The proposal retains private lineage by observation ID and safe fingerprints, not raw identifying content.

## Time, provenance and duplicates

Every observation preserves source ID, collection-session ID, adapter ID/version, safe source reference, observed-time state, observed time when known, recorded/imported times, content fingerprint, ingestion method, transformation notes, original privacy class and version. Unknown event time is represented by `observed_at: null` plus `observed_time_status: unknown`; import time is never substituted for event time.

Exact duplicate identity uses source ID, source reference, explicit event ID when present and the content fingerprint. M7 does not use embeddings or semantic similarity. A repeated exact item creates no second observation. The completed session records the existing observation ID as a duplicate outcome and increments the duplicate count.

Conflicting observations may coexist. The ledger neither identifies a winner nor changes M1 contradiction state.

## Retention and purge

Policies are `manual`, `session_only`, `days` and `indefinite_local`; a day count is required only for `days`. Expiration is explicit. Purge is logical in M7: private content and payload fields are removed from the current projection, the record becomes a `deleted_marker` with retention state `purged`, and metadata-only audit is retained.

M7 does not claim secure erasure. SQLite pages, filesystem behavior and older backups may retain historical bytes. Backups therefore remain private, and owners must retire older backups separately when deletion requirements demand it.

## Evidence proposal and promotion

An `ObservationEvidenceProposal` references one or more observations, carries separately authored public-safe evidence content, type, scope, ordinal evidence confidence, rationale, uncertainty, counter-context and provenance, and creates an exact pending M3 approval for `observation_evidence.promote`.

Only observations in `accepted_for_evidence_review` may support a proposal. Only an exact approved approval can promote it. Promotion reuses `build_evidence` and `EvidenceStore.insert_evidence` within the same transaction, preserves observation lineage and known observation time, writes one EvidenceRecord exactly once, and audits only safe metadata. If no observation has a known event time, the proposal must provide an explicit evidence observation time; ZIS does not invent one.

No observation API creates or updates memory, resolves contradictions, modifies cognition, invokes AI/specialists or changes routing.

## Export, backup, health and query

Default export uses four explicit least-disclosure projections rather than serializing private-vault rows directly:

1. Sources retain stable ID, safe type/lifecycle/adapter fields, timestamps, approval ID and version. Name, approval-scope text, allow/deny policy, retention policy, last-collection detail, privacy notes and provenance are omitted.
2. Sessions retain stable/source IDs, safe operation/adapter fields, timestamps, status, counts, observation IDs and version. Approval scope, privacy findings, errors and provenance are omitted.
3. Only explicitly `public`, non-quarantined observations may retain their validated payload. Internal, private, restricted and quarantined observations retain bounded structural/temporal metadata and content fingerprints but omit content, structured payload, source reference, explicit event ID, scope, subject/context labels and provenance/transformation details recursively.
4. Evidence proposals are metadata-only by default. They retain stable ID, type, ordinal confidence, safe timestamps, lifecycle/approval/evidence IDs, observation count and version, while omitting observation lineage, proposed content, scope, rationale, uncertainty, counter-context and provenance.

Identity-safe or structurally valid metadata is not assumed to be public-safe. The proposal's free-text rationale is kept only in the private proposal row; its M3 approval uses a fixed metadata-only review reason so public runtime export does not duplicate that rationale.

Local SQLite backup/restore includes all M7 tables and preserves provenance and retention state. A backup can contain private local observations and must never be committed or treated as a public export.

Health remains read-only and reports migration/table state, registry integrity, orphan references, adapter availability, quarantine count, failed sessions and due retention backlog. Optional or disabled sources/adapters do not make core health fail.

Queries are exact filters only: source, review state, privacy class and recorded-time range, plus session, quarantine and evidence-proposal listings. M7 adds no semantic search.

## Alternatives rejected

- Background collection was rejected as surveillance and outside explicit consent.
- Automatic observation-to-evidence or observation-to-memory conversion was rejected because it collapses governance boundaries.
- A shared AI/specialist/observation adapter was rejected because the authority and privacy boundaries differ.
- Recursive directory scanning, archive expansion and arbitrary command adapters were rejected as unnecessary attack surface.
- Physical secure deletion was not claimed because SQLite/filesystem/backups cannot provide it through a small portable M7 implementation.
- Partial best-effort persistence was rejected in favor of one deterministic transaction plus explicit failed-session records.

## Migration and compatibility impact

Migration 007 extends schema 6 without rewriting M1-M6 rows. Runtime version becomes 0.7.0 and public export format advances by one version. Existing deterministic cognition, optional AI and specialist federation remain unchanged and never auto-collect observations. M8 capability sensing remains unimplemented.

## Verification

The complete standard-library suite passes 136 tests: 115 accepted M1-M6 tests plus 21 M7 test methods. Coverage includes schema 6-to-7 upgrade and fresh initialization, lifecycle/approval gates, manual and file adapters, temporal/provenance fields, exact duplicates, quarantine and secret non-persistence, least-disclosure projection for all M7 families, evidence promotion, memory/contradiction isolation, transactional rollback, logical purge, full private backup/restore, health/orphans and CLI smoke. `python -m compileall -q src tests` and `git diff --check` also pass.
