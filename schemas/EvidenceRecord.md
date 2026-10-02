# EvidenceRecord

Machine contract: `EvidenceRecord.schema.json`. Implemented in Milestone 1; this document is retained as the conceptual source.

Required fields:

id

source_id

source_type

observed_at

recorded_at

content_reference

scope

status

confidence

provenance

privacy_class

retention_class

supersedes

counterevidence_ids

notes

Allowed status examples:

observation

claim

inference

hypothesis

confirmed_pattern

correction

deprecated

Invariant: an inference must never be stored as if it were a direct observation.
