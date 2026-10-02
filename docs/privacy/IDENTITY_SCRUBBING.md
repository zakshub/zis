# Identity Scrubbing Specification

## Purpose

Future migration must exclude direct personal identity from the public ZIS core while preserving useful, reviewable cognitive evidence and provenance references.

## Deterministic pipeline

1. Classify the source and intended destination.
2. Parse structured fields without modifying the source.
3. Match normalized field names against the exclusion registry.
4. Detect candidate identifiers in free text and references.
5. Replace only approved reusable references with stable abstract aliases.
6. Exclude sensitive payloads; retain a non-secret source locator where safe.
7. produce a review report containing matches, transformations, exclusions and uncertainty.
8. Require human approval before a scrubbed artifact enters public Git.

The same input, registry version and decisions must produce the same output and report.

## Exclusion categories

- real names and name variants
- emails
- phone numbers
- precise or private addresses
- employer names
- company identity tied to the owner
- account identifiers and usernames that reveal identity
- personal documents and document identifiers
- faces, biometric material and identifying image references
- credentials, passwords, API keys, cookies and tokens
- private family names, roles or identifiers

## Structured field guard

M1 rejects known direct-identity keys recursively, including `real_name`, `email`, `phone_number`, `precise_address`, `employer_name`, `company_identity`, `account_identifier`, `face_id`, `credentials`, `token`, `personal_document_id` and `family_identifier`.

## Free-text detection

Future scrubbing may use deterministic patterns and review dictionaries for emails, phone-like strings, account IDs, addresses, secrets and known identity terms. Pattern matches are candidates, not proof: false positives and false negatives are unavoidable.

## Alias rule

Aliases must express function rather than identity, such as `owner`, `source-person-01` or `historical-employer-01`. The private alias map must remain outside Git. Public artifacts must not contain a reversible mapping.

## Mandatory human review

Automatic anonymization is not perfect. Any uncertain match, unstructured narrative, image reference, personal document, mixed public/private source, or context where removal could change meaning must be marked `pending_review`. No uncertain item may be promoted to the public core automatically.

## Audit requirements

The future scrubber must record tool/version, source reference, rule matches, excluded categories, approved aliases, reviewer decision and timestamp. It must not place the sensitive matched value in a public log.

