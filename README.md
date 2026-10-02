# ZIS

ZIS is an indefinite, evolving, multilingual, identity protected and technology resilient cognitive system.

ZIS is not a single AI model and not a copy of one person. It is a persistent cognitive operating architecture that can observe authorized evidence, model durable patterns, form ideas, learn on demand, route work to specialist intelligences, decide the minimum useful solution level, request approval for persistent capability creation, execute through tools, and preserve learning across technology generations.

## Core principle

Modern AI, APIs, cloud services and automation are accelerators. They are not existential dependencies.

The durable object is the cognitive specification, evidence model, memory, rules, interfaces, lineage and reconstruction genome.

## Current status

Milestone 1 — Evidence Contracts and ZOS Migration Foundation — is implemented locally. ZIS now has machine-validated contracts, a SQLite evidence store, deterministic identifiers, explicit provenance/confidence/time semantics, contradiction and supersession history, a minimal CLI, durable exports and an audited ZOS migration plan. No AI provider or frontend is required.

## Quick start

Python 3.11+ is required. The runtime has no third-party dependencies.

```powershell
$env:PYTHONPATH = "src"
python -m zis.cli init
python -m zis.cli status
python -m unittest discover -s tests -v
```

Example evidence capture:

```powershell
python -m zis.cli evidence add "Synthetic example" --type observation --source-type synthetic --source-reference example:1 --scope example --confidence weak
python -m zis.cli evidence list
python -m zis.cli export .\local-export
```

Runtime data defaults to `.zis/zis.sqlite3` and is excluded from Git. Exported evidence may be private and must be reviewed before publication.

Read in this order:

1. docs/00_VISION_MISSION.md
2. docs/01_SYSTEM_DEFINITION.md
3. docs/02_COGNITIVE_ARCHITECTURE.md
4. docs/03_MEMORY_EVIDENCE_LEARNING.md
5. docs/04_SPECIALIST_INTELLIGENCE_ROUTER.md
6. docs/05_CAPABILITY_SENSING_AND_BUILD_GATE.md
7. docs/06_OBSERVATION_PRIVACY_TRANSPARENCY.md
8. docs/07_TECHNOLOGY_RESILIENCE.md
9. docs/08_ZOS_MIGRATION.md
10. docs/09_REPOSITORY_CAPABILITY_MAP.md
11. docs/10_PRODUCT_AND_SIMULATION_WORLD.md
12. docs/11_SYSTEM_ARCHITECTURE.md
13. docs/12_ROADMAP.md
14. docs/13_MILESTONES_AND_MICRO_TASKS.md
15. docs/14_STATUS.md
16. docs/15_GOVERNANCE_AND_ACCEPTANCE.md

Implementation details are in `docs/architecture/M1_IMPLEMENTATION.md`; privacy boundaries and the ZOS migration inventory are under `docs/privacy/` and `docs/migration/`.

No direct personal identity, face, employer or exact private identity data belongs in the public ZIS core.
