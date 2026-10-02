# ZOS Migration Map

No migration is executed in Milestone 1. This map defines a future review path.

| ZOS source family | ZIS target | Transformation | Approval |
| --- | --- | --- | --- |
| Evidence hierarchy and evidence rules | Evidence policy and `EvidenceRecord` | Normalize types, convert numeric/ambiguous confidence to an explicitly reviewed ordinal state, add time/provenance | Architecture review |
| Permission model | Future approval contracts | Translate roles/actions; preserve human authority | Owner approval before implementation |
| Model update protocol | Future governed promotion workflow | Preserve proposal, counterevidence, rationale and decision | Owner approval |
| Memory architecture | Future memory contracts | Map only after M1 evidence IDs and temporal semantics are stable | Architecture review |
| Personal constitution | Private evidence candidates only | Identity scrub, split claims, add source/time/confidence, retain private source reference | Mandatory per-record human review |
| Decision model | Candidate procedural evidence | Separate general method from personal moral rules | Human review |
| Blind spot model | Hypothesis evidence | Import only supported, current, anonymized hypotheses; preserve falsification context | Mandatory human review |
| Writing model/corpus | External writing specialist | Register routing contract later; do not duplicate corpus or specialist model | Specialist federation approval |
| Design/Figma/factory knowledge | Designer/Studio specialists | Keep external; ZIS stores only future manifests and provenance receipts | Specialist federation approval |
| ZOS JSON schemas | Contract-design evidence | Compare fields; do not copy incompatible confidence or identity-bearing fields | Architecture review |
| ZOS Python runtime | Implementation evidence | Reuse patterns only after independent ZIS design and tests | Code review |

## Future migration stages

1. Select a bounded, owner-approved ZOS source set.
2. Hash and register source files in a private migration workspace.
3. Run deterministic structural identity checks.
4. Mark uncertain text and all sensitive categories for human review.
5. Produce candidate ZIS records without writing the canonical store.
6. Validate contracts, timestamps, provenance, confidence and source references.
7. Run contradiction comparison against existing ZIS evidence.
8. Present an approval packet containing included, excluded and unresolved items.
9. Import approved records transactionally.
10. Export and compare IDs/provenance for round-trip verification.

## Explicit non-mappings

- ZOS application architecture → ZIS architecture: no.
- ZOS specialist knowledge → ZIS core: no.
- ZOS raw private stores → Git: never.
- ZOS direct identity → public ZIS: never.
- ZOS confidence float → automatic ordinal value: no; requires evidence-aware review.
- Newer ZOS record → automatic truth: no; contradictions and temporal context remain visible.

