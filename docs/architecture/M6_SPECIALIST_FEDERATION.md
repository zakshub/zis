# M6 Specialist Federation

Status: implemented and verified locally on 2026-10-04. The full M1-M6 suite passes 115 tests without a live specialist, network or credential.

## Decision

M6 adds a small standard-library federation boundary around the existing M3 specialist registry. ZIS stores only specialist identity, capability, contract, compatibility, privacy and invocation metadata. Domain knowledge remains in the specialist repositories.

The initial registry entries are Designer, Studio, SEO and TaxBot. Repository inspection found no stable, generic specialist-task endpoint that ZIS can safely call without inventing semantics or starting substantial infrastructure:

- Designer's authenticated API manages its reviewed knowledge objects; it is not a general design-task execution endpoint.
- Studio's documented API is an incomplete intelligence/retrieval skeleton; execution, persistence and authentication are not implemented.
- SEO's callable workflow requires its authenticated PostgreSQL, Redis and Temporal runtime and is not a portable specialist-task contract.
- TaxBot's public CLI is deliberately limited to storage setup, redacted status and recovery; tax analysis and filing are not exposed.

All four are therefore registered honestly with a metadata-only adapter and unavailable invocation. M6 contains no repository clone, embedded expertise, external credentials or background service. An injected adapter can implement the same protocol when a specialist later publishes an approved stable boundary.

ZIST was evaluated from the existing ZIS repository map. No local checkout or verifiable stable, privacy-scoped invocation interface was available, and its Urdu archive/writing scope may overlap future observation or corpus ingestion. It is deferred and is not registered.

## Contracts and flow

`SpecialistRequest` contains an explicit specialist, action, requested capability, bounded structured input, references, privacy class, forwarding approval, optional governance approval, bounded timeout, contract versions and deterministic input fingerprint. It never loads history, evidence, memory or a database implicitly.

`SpecialistResponse` normalizes success and failure. A successful response must validate against the adapter's registered output schema and includes a separate `SpecialistProvenanceReceipt`. A specialist result is not evidence, memory, truth, approval, contradiction resolution or execution authority.

The explicit flow is:

1. resolve an existing manifest and adapter;
2. validate the request and privacy boundary;
3. verify registry state, adapter availability and exact contract/runtime compatibility;
4. enforce any exact approval requirement;
5. invoke once with a bounded timeout contract;
6. validate the complete output;
7. atomically store request, normalized response, optional receipt and metadata-only audit event.

There is no automatic fallback, specialist substitution, autonomous selection or specialist chain. The M3 router still returns `specialist_candidate`; only the separate federation invocation method executes an adapter. M4 cognition and M5 AI do not call federation automatically.

## Availability and health

Adapter health uses `available`, `unavailable`, `not_configured`, `incompatible`, `disabled` or `degraded`. A specialist failure does not make core SQLite health fail. Health checks are read-only and must not execute a specialist job.

Compatibility is exact for request contract, response contract and the current ZIS major/minor runtime declared by the manifest. M6 does not coerce versions.

## Privacy and security

Requests reject direct-identity field names, detectable direct identifiers, credential fields and credential-like text before adapter transport. Only the supplied structured input and references cross the adapter boundary. Audit records contain IDs, outcome, compatibility, latency, error category and receipt reference—not request or response payloads.

M6 provides no arbitrary process adapter. Consequently it introduces no `shell=True`, executable selection, command string, environment dump or authorization-header handling. Adapter-specific secrets remain outside ZIS and are never represented in federation contracts, SQLite, audit, export or backup.

TaxBot filing and submission actions are explicitly unsupported. Other declared high-impact TaxBot actions require an existing exact approval record; a specialist cannot approve its own request.

## Persistence and portability

Migration 006 adds request, response and provenance-receipt tables containing portable JSON records. A whole interaction is committed through one SQLite connection/transaction after the external call. Audit failure rolls the durable interaction back. Backup, restore, JSON export, Markdown counts and health cover these tables.

The implementation remains Python-standard-library-only and the JSON contracts are reproducible in another runtime. It does not add M7 observation, M8 capability sensing, UI, AI routing or autonomous agents.
