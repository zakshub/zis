# Master Roadmap

## Phase 0 Documentation Foundation

Goal: define exactly what ZIS is before coding.

Outputs: vision, cognitive architecture, evidence model, routing, capability sensing, privacy, resilience, ZOS migration, repository map, product direction, system architecture, roadmap and governance.

Exit condition: all foundation documents reviewed and contradictions resolved.

## Phase 1 Evidence and Migration Foundation

Goal: convert ZOS and existing written material into a clean identity protected evidence base.

Outputs: evidence schema, source registry, ZOS inventory, redaction rules, confidence model, contradiction model and first cognitive pattern set.

Exit condition: representative ZOS material can be imported, traced and audited.

Status (2026-10-02): the machine contracts, identity/privacy rules, ZOS inventory and migration map are implemented. Actual ZOS record import remains intentionally pending human selection and approval; no personal source material was copied.

## Phase 2 Classical Core Runtime

Goal: build the minimum non AI dependent ZIS core.

Outputs: local database, CLI, evidence ingestion, memory, deterministic router, capability registry, approval records, audit log, export and restore.

Exit condition: ZIS can operate basic workflows without any LLM.

Status (2026-10-02): a bounded foundation slice is complete: local SQLite initialization/migrations, evidence storage, audit events, contradictions, temporal supersession, CLI and JSON/CSV/Markdown export. Memory, capability/specialist registries, approvals, deterministic routing, backup and restore remain future Phase 2 work.

Audit note (2026-10-03): M1 validation and audit guarantees are now explicitly bounded, and current evidence mutations use one transaction/connection per logical operation. The durability/adversarial cases listed in the testing strategy remain a Classical Runtime backlog rather than completed M1 guarantees.

## Phase 3 Modern Intelligence Layer

Goal: add optional AI acceleration through provider adapters.

Outputs: model adapter contract, retrieval, synthesis, tool calling, structured proposal generation and human approval integration.

Exit condition: disabling AI leaves Phase 2 functional.

## Phase 4 Specialist Intelligence Federation

Goal: connect Designer, Studio, SEO, TaxBot and other approved specialists.

Outputs: specialist manifest schema, health checks, capability discovery, task contracts, fallback behavior and provenance.

Exit condition: ZIS can route tasks and combine specialist outputs without copying their knowledge.

## Phase 5 Observation and Learning

Goal: add transparent authorized observation and governed learning.

Outputs: Observation Ledger, connectors, permission controls, learning candidates, consolidation jobs, confidence decay and user corrections.

Exit condition: every observation and promoted learning is visible and traceable.

## Phase 6 Capability Sensing and Controlled Creation

Goal: let ZIS identify missing capabilities and propose appropriate solution scales.

Outputs: solution ladder engine, proposal templates, build approval gate, architecture generator and post build evaluation.

Exit condition: ZIS can propose but cannot silently create persistent capability.

## Phase 7 Production Operations Interface

Goal: build the usable human control surface.

Outputs: status, search, evidence, memory, learning, specialists, approvals, idea lineage, settings and recovery controls.

Exit condition: major system state can be understood and controlled without command line use.

## Phase 8 Immersive Simulation World

Goal: create the world first visualization of ZIS.

Outputs: world state contract, pet like electronic species, zones, real backend state animation, 2D or 3D renderer, world navigation and accessibility fallback.

Exit condition: simulation reflects real system state and remains optional.

## Phase 9 Resilience and Recovery Genome

Goal: prove ZIS can survive major technology replacement.

Outputs: dependency graph, no AI mode, offline mode, migration tests, plain data exports, reconstruction specification and disaster recovery exercises.

Exit condition: a clean environment can reconstruct core ZIS from documented assets.
