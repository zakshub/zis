# Data Boundary

## Allowed in Git

- architecture and implementation code
- machine schemas and validation rules
- governance, privacy and migration documentation
- synthetic examples and fixtures
- tests
- SQL migration definitions
- public-safe derived intelligence approved after identity review
- non-secret provenance descriptions and source classifications

## Forbidden in Git

- private conversations or message archives
- raw WhatsApp exports
- browser history
- private Facebook or Instagram data
- financial or medical records
- credentials, secrets, cookies, API keys and tokens
- runtime databases containing private data
- raw identity data, personal documents or private family identifiers
- private alias maps used during identity scrubbing

## Runtime placement

The default local database lives under `.zis/`. Private source material belongs in an owner-controlled location outside this repository. Database files, local data directories, exports, environment files and common secret files are ignored by `.gitignore`.

Exports inherit the highest privacy class of their contents. JSON, CSV and Markdown being readable does not make them public-safe. Review is mandatory before adding any derived export to Git.

## M7 local observation vault

The SQLite database may contain owner-approved private observation content. It is a private local vault, not a public-core artifact. The default JSON/Markdown export uses a separate least-disclosure projection for each M7 family. Sources omit name, approval-scope text, privacy notes, policy details and provenance. Sessions omit approval scope, privacy findings, errors and provenance while retaining structural IDs/status/counts. Non-public, restricted and quarantined observations omit content, structured payload, source reference, scope, labels and free-text provenance/transformation details; only explicitly `public` observations may include their validated payload. Evidence proposals are metadata-only by default and omit observation lineage, proposed content, rationale, uncertainty, counter-context, scope and provenance.

SQLite backups contain the full local observation state, including private content, provenance and retention state. They must remain outside Git. Logical purge removes content from the current projection but is not secure erasure: older backups, filesystem copies and SQLite storage behavior may retain prior bytes and require separate owner-controlled retirement.

## Enforcement

1. Contracts disallow undeclared identity fields.
2. Runtime ingestion rejects registered direct-identity keys recursively.
3. `.gitignore` excludes local databases, runtime data, exports and secrets.
4. Tests use synthetic records only.
5. Human review remains required for free text and uncertain cases.
6. M7 audits store observation IDs, decisions, counts and fingerprints rather than raw observation content.

These controls reduce risk but do not replace repository scanning, secret scanning or human judgment.
