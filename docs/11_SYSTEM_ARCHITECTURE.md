# System Architecture

## Logical layers

1. Kernel
Constitution, identity boundary, human authority, permission policy and invariant rules.

2. Cognitive engine
Perception, attention, intuition, curiosity, association, pattern detection, abstraction, idea formation, evaluation and reflection.

3. Evidence engine
Observations, provenance, confidence, contradiction and temporal context.

4. Memory engine
Working memory, durable memory, experimental memory, project memory and archive.

5. Learning engine
Consolidation, promotion, decay, supersession and forgetting.

6. Capability engine
Capability registry, dependency graph, specialist registry and solution scale decision.

7. Approval engine
Human approval for persistent capability creation and high impact actions.

8. Router
Dispatch to specialist brains, tools, research sources and execution adapters.

9. Runtime
State machines, local database, jobs, events, APIs and CLI.

10. Integration adapters
GitHub, files, browser, future social connectors, specialist repositories and model providers.

11. Interface layer
Operations interface, command interface and future immersive simulation world.

12. Recovery layer
Exports, migrations, deterministic fallback and reconstruction genome.

## Architectural defaults

Local first for sensitive data.

Public Git stores safe architecture, schemas and derived intelligence only.

Private evidence is external to public Git.

Python 3.11+ and SQLite are the accepted first classical runtime. They remain replaceable implementation layers under the technology-resilience policy.

All model providers must sit behind adapters.

Every automated state change must be auditable.

Every external capability must fail visibly rather than invent success.

## Implemented classical runtime boundary

M3 implements storage and deterministic governance across the evidence, memory-substrate, capability, approval, router, runtime and recovery layers. Registries store metadata and lifecycle projections; audit events preserve state-change history. Memory promotion and persistent capability/specialist activation require exact application-level approval records.

The router evaluates only explicit structured action types and registry state. It does not infer intent, discover capabilities, invoke specialists or perform cognitive reasoning. Specialist entries are queryable metadata only. Backup uses SQLite's backup API and restore verifies into a temporary database before publishing to an explicit destination.

The Cognitive Engine, Learning Engine, specialist federation, capability sensing, observation adapters, AI adapters and interface layers remain unimplemented.
