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

## Implemented M1-M5 boundary

M3 implements storage and deterministic governance across the evidence, memory-substrate, capability, approval, router, runtime and recovery layers. Registries store metadata and lifecycle projections; audit events preserve state-change history. Memory promotion and persistent capability/specialist activation require exact application-level approval records.

The router evaluates only explicit structured action types and registry state. It does not infer intent, discover capabilities, invoke specialists or perform cognitive reasoning. Specialist entries are queryable metadata only. Backup uses SQLite's backup API and restore verifies into a temporary database before publishing to an explicit destination.

M4 adds a bounded Cognitive Engine over explicit session context. It loads only supplied evidence and memory IDs and deterministically records explainable attention, structured association, pattern-candidate, hypothesis, idea-lineage, evaluation, reflection and model-update-proposal projections. Content identity is derived from explicit input, database state, ruleset version and effective time; execution timestamps remain operational metadata. All session artifacts and audit events commit atomically.

M4 does not implement semantic understanding, embeddings, hidden reasoning, consciousness, memory consolidation, model-update application, specialist invocation, capability sensing or external action. Pattern and hypothesis records are explicitly non-memory; evaluations have no decision authority; reflection has no consciousness claim; model-update application is reserved for a future Learning Engine. The Learning Engine, specialist federation, capability sensing, observation adapters and interface layers remain unimplemented.

M5 adds an optional provider-neutral AI adapter layer outside the deterministic cognition path. An explicit AIRequest can be routed through a disabled adapter, injected fake adapter or exactly one real OpenAI Responses adapter. Normalized AIResponse and AICandidate records preserve provider/model identity, outcome, usage, cost status and provenance without storing credentials, headers, raw provider envelopes or hidden reasoning. `CognitiveEngine.run_session` remains unchanged and never calls AI automatically.

Provider failure or disabled state does not make the classical runtime unhealthy. Migration 005, export, backup and health cover safe durable AI records. Specialist federation, provider orchestration, model selection, observation, capability sensing, learning application and interfaces remain unimplemented.
