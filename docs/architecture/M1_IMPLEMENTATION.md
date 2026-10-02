# Milestone 1 Implementation

Date: 2026-10-02

## Scope

Milestone 1 implements the evidence contracts and ZOS migration foundation only. It does not add a frontend, simulation world, source connectors, model providers, specialist execution, or distributed infrastructure.

## Runtime choice

Python 3.11+ and the Python standard library are the first runtime. SQLite is the local store. This choice follows the existing architecture's SQLite candidate and ZOS's useful Python/local-first precedent without adopting ZOS as the ZIS architecture.

Reasons:

1. SQLite, JSON, CSV, Markdown and SQL are mature and broadly reproducible.
2. The standard library supplies the CLI, SQLite driver, hashing, timestamps and exports.
3. No AI, network, service, container or proprietary database is required.
4. JSON Schema remains language-neutral even though the first validator is Python.
5. Numbered SQL migrations and documented exports make replacement by another runtime practical.

## Components

- `schemas/*.schema.json`: Draft 2020-12 machine contracts.
- `src/zis/contracts.py`: dependency-free validator for the contract subset used by M1.
- `src/zis/records.py`: normalized timestamps and deterministic, content-derived IDs.
- `src/zis/store.py`: SQLite migrations, evidence projection, contradictions and append-only audit events.
- `src/zis/export.py`: JSON, CSV and Markdown exports.
- `src/zis/cli.py`: minimal M1 CLI.
- `migrations/001_initial.sql`: initial portable database migration.

## Evidence model

Evidence kinds are `observation`, `user_statement`, `external_fact`, `inference`, `hypothesis`, `correction` and `derived_pattern`. They remain explicit; an inference cannot masquerade as an observation because the record type is required and audited.

Lifecycle states are `captured`, `reviewed`, `promoted`, `superseded`, `rejected` and `expired`. The vocabulary requested for M1 already matches the documentation and needs no replacement.

Confidence is deliberately ordinal: `unknown`, `weak`, `probable`, `strong`, `established`. It is not a probability and carries no invented percentage.

## Time and supersession

Every evidence record includes `observed_at`, `recorded_at`, `valid_from`, optional `valid_until`, `supersedes`, `superseded_by` and `current_interpretation`. Supersession keeps both records, changes only the old record's lifecycle projection, and writes an audit event containing the before and after state.

## Contradictions

A contradiction is a separate relation between two preserved evidence records. It starts unresolved. Resolution requires a rationale and source reference and does not delete either record. Both creation and resolution create audit events.

## Deterministic identifiers

Record identifiers use SHA-256 over canonical JSON material with a type prefix. The same logical input, including its observation time and source reference, yields the same ID across runtimes capable of canonical key sorting and UTF-8 hashing. Audit event IDs include their event time because separate actions must remain separate.

## Validation boundary

Contracts reject undeclared fields, including direct identity fields. Runtime ingestion also performs recursive forbidden-field checks. This is a structural guard, not a claim of perfect content anonymization. Free text and uncertain source material still require human review.

## Local data boundary

The default database is `.zis/zis.sqlite3`, which is ignored by Git. Exports default only to the destination explicitly selected by the operator; `exports/` is ignored because exports can contain private evidence.

## CLI

Available commands:

```text
zis init
zis status
zis validate CONTRACT FILE
zis evidence add|list|show|status
zis contradiction add|resolve
zis contradictions
zis export DESTINATION
```

## Known boundaries

- M1 does not automatically infer contradictions.
- M1 does not automatically promote evidence or confidence.
- M1 does not claim perfect identity detection in free text.
- M1 does not import ZOS records.
- M1 does not register or invoke specialists.

