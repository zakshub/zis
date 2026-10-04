# IdeaLineage v2

Machine contract: `IdeaLineage.schema.json`. M4 implements this as the durable IdeaRecord/lineage contract.

It requires the idea ID and cognitive session, statement, scope, origin type, parent idea IDs, evidence/pattern/hypothesis/association references, trigger, transformations, current status, rationale, explicit `idea_not_truth` marker, provenance, ordinal confidence, timestamps and version.

M4 states are limited to:

1. `spark`
2. `unclear`
3. `exploring`
4. `researching`
5. `promising`
6. `rejected`
7. `parked`
8. `ready`

`approved`, `executing`, `completed` and `learned` are not M4 states because execution and learning belong to later milestones. An M4 idea requires at least one explicit lineage reference and begins at `spark`; it is not truth, execution authority or durable memory.

Invariant: lineage preserves the path from explicit origin references and transformations to the current pre-execution idea state rather than only a final statement.
