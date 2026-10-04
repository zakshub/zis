# Milestones and Micro Tasks

## M0 Foundation Review

1. Review every foundation document.
2. Resolve naming conflicts between ZIS and inherited ZOS terms.
3. Confirm single owner architecture.
4. Freeze direct identity exclusion rules.
5. Freeze canonical English specification language.
6. Freeze approval gate categories.
7. Record first architecture decisions.

## M1 Evidence Contracts

Status: complete for the five requested Milestone 1 contracts and evidence foundation (2026-10-02).

1. Define EvidenceRecord schema.
2. Define Observation schema.
3. Define Claim schema.
4. Define Inference schema.
5. Define Confidence schema.
6. Define Counterevidence schema.
7. Define Correction schema.
8. Define TemporalScope schema.
9. Define Source registry schema.
10. Create synthetic fixtures.
11. Write validation tests.

Implemented additions: ordinal confidence, lifecycle states, source/provenance requirements, deterministic identifiers, contradiction relations, temporal validity and strict identity-field rejection.

## M2 ZOS Evidence Migration

Status: complete for the bounded migration pipeline (2026-10-03). No real ZOS evidence was imported; future selections still require owner review.

1. Enumerate ZOS files.
2. Classify each file.
3. Mark identity sensitive files.
4. Mark specialist knowledge that should not migrate.
5. Mark cognitive evidence candidates.
6. Mark reusable architecture patterns.
7. Produce a machine-readable migration manifest. Complete.
8. Screen identity/privacy without storing raw sources. Complete with conservative structural detection and mandatory free-text review; no claim of perfect anonymization.
9. Import only explicitly approved safe candidates. Complete and verified with synthetic records only.
10. Verify provenance round trip. Complete with source ref, path, fingerprint and candidate lineage.
11. Route specialist, obsolete and sensitive material away from core. Complete.
12. Provide non-mutating dry-run and CLI review workflow. Complete.

## M3 Classical Runtime

Status: complete and verified (2026-10-04). Existing M1/M2 foundations were reused rather than rebuilt.

Pre-runtime audit fixes completed 2026-10-03: validator scope and audit-history limitations documented; atomic evidence transaction boundaries tightened. Future durability/adversarial cases are recorded in `docs/testing/TESTING_STRATEGY.md`.

1. Select baseline language and runtime. Reused Python 3.11+ and SQLite.
2. Create CLI skeleton. Reused and extended.
3. Create local data directory contract. Reused `.zis/` boundary.
4. Create database migrations. Reused framework; added migration 003.
5. Implement evidence storage. Reused unchanged.
6. Implement memory storage. Complete as governed storage only.
7. Implement audit events. Reused for every new durable mutation.
8. Implement capability registry. Complete without sensing or creation.
9. Implement specialist registry. Complete without invocation/federation.
10. Implement approval records. Complete with exact action/reference/scope enforcement.
11. Implement deterministic task router. Complete for explicit structured routes only.
12. Implement export. Existing formats extended with runtime records.
13. Implement backup. Complete with SQLite backup API, checksum and manifest.
14. Implement restore drill. Complete with synthetic state-equivalence coverage.
15. Add unit tests. Complete.
16. Add integration tests. Complete.

## M4 Cognitive Engine v0.1

Status: complete and verified locally (2026-10-04). M3 was accepted before implementation; the later M5 adapter does not alter or replace this deterministic milestone.

1. Deterministic, explainable ordinal attention rules. Complete.
2. Exact-structured novelty, repetition, duplicate, variation and insufficient-basis signals. Complete.
3. Existing contradictions surfaced and explicit candidates recorded without automatic resolution. Complete.
4. Deterministic association links with reasons, provenance and no prose semantics. Complete.
5. Pattern candidates requiring at least two distinct supporting evidence records. Complete.
6. Explicit, testable hypothesis state with strengthening and falsification conditions. Complete.
7. Idea lineage with pre-execution lifecycle only. Complete.
8. Criteria-based evaluation without decision authority. Complete.
9. Structured reflection preserving uncertainty and no consciousness claim. Complete.
10. Approval-linked model-update proposal with application unavailable in M4. Complete.
11. Explicit cognitive sessions, migration 004, atomic audit, portable export, health and backup/restore coverage. Complete.
12. Synthetic M4 adversarial/integration suite and CLI smoke. Complete.

## M5 Modern AI Adapter

Status: complete and verified locally (2026-10-04). M4 was accepted before implementation; M6 has not started.

1. Provider-neutral adapter protocol and registry. Complete.
2. Portable AIRequest contract with deterministic prompt fingerprint. Complete.
3. Portable normalized AIResponse contract. Complete.
4. Exactly one real OpenAI Responses adapter isolated behind standard-library transport. Complete.
5. Disabled/no-provider fallback. Complete.
6. Explicit bounded timeout and no automatic retry. Complete.
7. Authentication, rate-limit, server, transport, timeout and invalid-output normalization. Complete.
8. Provider-reported token usage plus optional versioned estimated-cost calculation. Complete.
9. Fake/no-provider/real-adapter replacement through the registry. Complete.
10. Core runtime and M4 cognition with AI disabled. Complete.
11. AICandidate non-truth boundary, migration 005, audit, export, backup/restore, health and CLI. Complete.
12. Secret non-persistence and adversarial/integration coverage. Complete.

## M6 Specialist Federation

1. Define SpecialistManifest schema.
2. Register Designer.
3. Register Studio.
4. Register SEO.
5. Register TaxBot.
6. Evaluate ZIST.
7. Define request contract.
8. Define response contract.
9. Define health check.
10. Define unavailable state.
11. Define version compatibility.
12. Define provenance receipt.
13. Add specialist fallback rules.

## M7 Observation Ledger

1. Define connector permission model.
2. Define observation categories.
3. Build source connection registry.
4. Build visible permission screen.
5. Build pause all control.
6. Build source revoke flow.
7. Implement observation ingestion.
8. Implement identity scrubber.
9. Build inference explanation view.
10. Build retention state control.
11. Build learning promotion queue.

## M8 Capability Sensing

1. Implement solution ladder.
2. Create evaluation rubric.
3. Add existing capability lookup.
4. Add build versus buy comparison.
5. Add no build outcome.
6. Add proposal generator.
7. Add approval gate.
8. Add approved build handoff.
9. Add post build outcome review.
10. Add duplicate capability detection.

## M9 Operations UI

1. Ask Designer for information architecture.
2. Evaluate navigation patterns instead of assuming sidebar navigation.
3. Build search and command surface.
4. Build system status.
5. Build Observation Ledger.
6. Build Learning Feed.
7. Build Memory explorer.
8. Build Idea Lineage.
9. Build Capability Router.
10. Build Specialist registry.
11. Build Approvals.
12. Build dependency health.
13. Build recovery controls.
14. Accessibility review.
15. Responsive review.

## M10 Simulation World

1. Define world state schema.
2. Define zone mapping.
3. Ask Designer for interaction architecture.
4. Ask Studio for original pet like species language.
5. Define creature state mapping.
6. Define path and signal mapping.
7. Prototype 2D world.
8. Evaluate 2.5D or 3D renderer.
9. Bind world animation to real backend events.
10. Add reduced motion mode.
11. Add non visual fallback.
12. Run usability tests.

## M11 Resilience

1. Create dependency inventory.
2. Assign replacement strategies.
3. Implement offline mode.
4. Implement no AI mode.
5. Export all critical data to durable documented formats.
6. Write reconstruction manual.
7. Create minimal reference implementation.
8. Run migration to alternate runtime proof.
9. Run restore on clean machine.
10. Record recovery time and gaps.
