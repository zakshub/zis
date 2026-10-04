# ZIS

ZIS is an indefinite, evolving, multilingual, identity protected and technology resilient cognitive system.

ZIS is not a single AI model and not a copy of one person. It is a persistent cognitive operating architecture that can observe authorized evidence, model durable patterns, form ideas, learn on demand, route work to specialist intelligences, decide the minimum useful solution level, request approval for persistent capability creation, execute through tools, and preserve learning across technology generations.

## Core principle

Modern AI, APIs, cloud services and automation are accelerators. They are not existential dependencies.

The durable object is the cognitive specification, evidence model, memory, rules, interfaces, lineage and reconstruction genome.

## Current status

Milestones 1 through 5 are implemented locally. The deterministic M1-M4 core remains authoritative and fully functional without AI. M5 adds an optional provider-neutral AI boundary with disabled/no-provider mode, exactly one isolated OpenAI Responses adapter, strict structured-output validation, explicit candidate records, normalized errors, usage metadata and bounded cost estimation. AI output is not evidence, memory, truth, approval, contradiction resolution or execution. No live credential is required for initialization or tests, and no specialist federation, observation, frontend or simulation has been built. The dependency-free validator implements only the ZIS-required subset of JSON Schema Draft 2020-12; it is not standards-complete. Audit and approval records remain application-level governance, not cryptographic identity or tamper evidence.

## Quick start

Python 3.11+ is required. The runtime has no third-party dependencies.

```powershell
$env:PYTHONPATH = "src"
python -m zis.cli init
python -m zis.cli status
python -m zis.cli runtime status
python -m zis.cli health
python -m zis.cli ai status
python -m unittest discover -s tests -v
```

Example evidence capture:

```powershell
python -m zis.cli evidence add "Synthetic example" --type observation --source-type synthetic --source-reference example:1 --scope example --confidence weak
python -m zis.cli evidence list
python -m zis.cli export .\local-export
```

An M4 cognitive run accepts a JSON file containing an explicit `trigger_reference`, `scope`, `evidence_ids` and `effective_at`; optional memory and candidate inputs remain explicit:

```powershell
python -m zis.cli cognition run .\cognitive-session.json
python -m zis.cli cognition sessions
python -m zis.cli cognition artifacts patterns
```

M5 AI requests are explicit structured JSON files. AI is disabled by default; enabling the OpenAI adapter requires `ZIS_AI_ENABLED=true`, `ZIS_AI_PROVIDER=openai`, an explicit `ZIS_AI_MODEL`, and `OPENAI_API_KEY` in the runtime environment. Credentials are never stored in ZIS configuration or durable records.

The bounded M2 commands remain under `zis migrate zos`. M3 adds classical runtime/governance commands, M4 adds `cognition`, and M5 adds the minimal `ai status`, `ai providers`, `ai request` and `ai records` surface. Use `--help` for exact structured inputs.

Runtime data defaults to `.zis/zis.sqlite3` and is excluded from Git. Backups must use an explicit private destination and are never uploaded. Exports and backups may contain private state and must not be committed.

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

Implementation details are in `docs/architecture/M1_IMPLEMENTATION.md`, `docs/migration/M2_IMPLEMENTATION.md`, `docs/architecture/M3_CLASSICAL_RUNTIME.md`, `docs/architecture/M4_COGNITIVE_ENGINE.md` and `docs/architecture/M5_AI_ADAPTER.md`; privacy boundaries and the ZOS migration inventory are under `docs/privacy/` and `docs/migration/`.

No direct personal identity, face, employer or exact private identity data belongs in the public ZIS core.
