# M2 ZOS Evidence Migration Implementation

## Scope

M2 adds a local, deterministic and reviewable bridge from explicitly selected ZOS files to existing ZIS EvidenceRecords. It does not mass-import ZOS, interpret arbitrary prose, add a memory engine, connect an external source, call AI, or change the ZIS architecture.

## Durable records

SQLite migration `002_zos_migration.sql` adds:

1. `migration_sources`: machine manifest entries containing repository/ref/path/hash and classification, confidence, gate, review, import and lineage state. Raw source content is absent.
2. `migration_candidates`: normalized cognitive units and their privacy, specialist, temporal, contradiction, review and import states.
3. `migration_review_events`: application-level append-only human decision history.

`ZOSMigrationManifest.schema.json` and `ZOSMigrationCandidate.schema.json` are the portable contracts. As with M1, the bundled validator supports only the ZIS-required Draft 2020-12 subset.

## Lifecycle

1. `scan` reads only selected paths below a supplied local source root, hashes bytes, applies deterministic A-G path rules and stores metadata.
2. `candidate-add` accepts a human-authored JSON specification. Stable semantic fields produce a deterministic candidate ID.
3. Privacy screening blocks detected structural identity signals. The detected candidate text, scope and notes are replaced before persistence by an omission marker plus SHA-256 fingerprint and finding categories. All otherwise clean free text still requires human review.
4. Specialist screening routes primarily specialist content outside core. An explicitly marked transferable pattern is still review-required, never automatically safe.
5. Temporal state is explicit: `historical`, `currently_valid`, `uncertain_current_validity`, `superseded`, `contradicted` or `obsolete`.
6. `candidates --id` returns the candidate, its source manifest and full source reference for review.
7. A reviewer records one of `approve`, `reject`, `defer`, `requires_redaction`, `route_to_specialist` or `mark_obsolete`, with a required note.
8. `import` accepts only approved, privacy-reviewed and core-safe candidates. It preserves confidence and time, embeds source ref/path/hash plus candidate lineage, and uses EvidenceStore validation/audit rules.

Approval does not mean current truth. Historical/superseded imports become non-current expired records; uncertain/contradicted imports remain non-current. A declared candidate conflict becomes an unresolved existing ZIS contradiction only after both sides are approved and imported. No automatic winner or resolution exists.

## CLI

```powershell
$env:PYTHONPATH = "src"
python -m zis.cli migrate zos --help
python -m zis.cli migrate zos dry-run --source-root D:\read-only\zos --source-ref <commit> core/kernel/ZOS-CONSTITUTION.md
python -m zis.cli migrate zos scan --source-root D:\read-only\zos --source-ref <commit> core/kernel/ZOS-CONSTITUTION.md
python -m zis.cli migrate zos inventory
python -m zis.cli migrate zos candidate-add .\local-private-candidate.json
python -m zis.cli migrate zos candidates --id <candidate-id>
python -m zis.cli migrate zos approve <candidate-id> --note "Reviewed source, privacy, specialist scope and time context."
python -m zis.cli migrate zos import <candidate-id>
python -m zis.cli migrate zos status
```

Candidate specification files can contain sensitive working material and should remain outside Git. Runtime databases and exports are already gitignored.

Dry-run accepts optional repeated `--candidate-file` arguments and returns source/candidate details plus summary counts. It opens no evidence database and reports `durable_mutations: 0` and `eligible_for_import: 0` because approval is never implied by extraction.

## Transaction and idempotency guarantees

Each import uses one SQLite connection/transaction for EvidenceRecord creation, candidate and manifest updates, contradiction creation and audit writes. An exception rolls the unit back. Re-import returns the already linked record. Source and candidate IDs use deterministic SHA-256 material; source content is referenced by its SHA-256 fingerprint.

## Verification against ZOS

Read-only inspection used ZOS commit `46952de2af418528a2f7911c9583d9c915b1b645`. A non-mutating dry-run selected six paths spanning classifications A, B, C, D, E and G: kernel constitution, personal constitution, product-thinking model, design operating model, decision engine and deployment configuration. The run created no candidates and no durable record. Sensitive files were not copied.

## Known limitations

1. Path and keyword rules are conservative routing aids, not semantic understanding.
2. Structural patterns cannot reliably identify every real name, company, address or private fact in prose; human review is mandatory.
3. No semantic anonymization or automatic redaction is claimed. Structurally detected candidate text is omitted from persistence; a blocked candidate must be rewritten as a new reviewed candidate outside Git.
4. Source content changes produce a new manifest ID; M2 does not fetch repositories or attest that a supplied directory matches its claimed commit.
5. Review authentication and signatures are not implemented. Review/audit records are application-level append-only, not cryptographically tamper-evident.
6. Candidate extraction is manual-structured. No real ZOS candidate has been approved or imported.
7. General backup, restore, corruption recovery, concurrency and power-loss hardening remain M3 work.
