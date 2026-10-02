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

## Enforcement

1. Contracts disallow undeclared identity fields.
2. Runtime ingestion rejects registered direct-identity keys recursively.
3. `.gitignore` excludes local databases, runtime data, exports and secrets.
4. Tests use synthetic records only.
5. Human review remains required for free text and uncertain cases.

These controls reduce risk but do not replace repository scanning, secret scanning or human judgment.

