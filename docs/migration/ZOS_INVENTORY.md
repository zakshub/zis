# ZOS Migration Inventory

Date inspected: 2026-10-02

Source: `zakshub/zos`, commit `46952de` (`main`)

Method: read-only temporary checkout; no ZOS file was imported.

ZOS is an ancestor system and evidence source. Its architecture is not the ZIS architecture.

## Category A — Directly reusable concepts

| Asset | Evidence | Reuse boundary |
| --- | --- | --- |
| `core/kernel/ZOS-CONSTITUTION.md` | Person/model separation, uncertainty, human authority, privacy, correctability | Reuse abstract invariants, not named identity language |
| `core/ZAK-EVIDENCE-RULES.md` and `core/foundation/HCOS-EVIDENCE-HIERARCHY-SOURCE.md` | Evidence classes, conflict preservation, recency and domain-transfer cautions | Translate into ZIS evidence policy; do not copy person-specific examples |
| `core/kernel/PERMISSION-MODEL.md` | READ/PROPOSE/WRITE/SUDO/ROOT separation | Reuse as approval-model evidence, not as M1 runtime scope |
| `core/kernel/MODEL-UPDATE-PROTOCOL.md` | Proposed diff, evidence, counterevidence and review before stable change | Reuse proposal/audit principle |
| `docs/architecture/EVIDENCE-ARCHITECTURE.md` | Explicit evidence type, provenance, confidence and contradiction relation | Reuse conceptually with stronger temporal contracts |
| `docs/architecture/MEMORY-ARCHITECTURE.md` | Working/episodic/semantic/procedural/hypothesis separation | Reuse later after ZIS memory design review |
| `src/zos/approvals.py` and `src/zos/model_updates.py` | Append-only request/decision events | Reuse event-history pattern only |

## Category B — Reusable only after anonymization

| Asset | Reason |
| --- | --- |
| `core/kernel/PERSONAL-CONSTITUTION.md` | Contains named identity, personal beliefs, relationships and private behavioral interpretation |
| `core/ZAK-EVOLUTION-TIMELINE.md` | Personal history and dated identity-bearing material |
| `core/ZAK-CAPABILITY-OS-2008-2026.md` and `core/ZAK-SKILL-MATRIX.md` | Potential cognitive/process evidence mixed with personal and professional identity |
| `evidence/derived/**` | Derived personal/project evidence; requires source-by-source provenance and identity review |
| Historical project records governed by `schemas/project.schema.json` | May contain company, role, URLs and personal authorship claims |

No Category B item is approved for automatic migration.

## Category C — Useful as evidence but not architecture

| Asset | Use |
| --- | --- |
| `core/models/PRODUCT-THINKING-MODEL.md` | Evidence of a prior problem-to-workflow framing |
| `core/models/CREATIVE-OS-v0.1.md` | Historical hypothesis about creative process |
| `core/models/registry.json` | Evidence of model status/version vocabulary |
| `core/ZAK-QUALITY-STANDARD.md` | Historical quality checklist evidence |
| ZOS tests | Evidence of prior acceptance boundaries and implementation behavior |
| Factory and project pipeline code | Evidence of what ZOS operationalized; not a base for ZIS runtime |

## Category D — Specialist knowledge that should remain outside ZIS

| Asset | Destination/boundary |
| --- | --- |
| `core/models/DESIGN-OPERATING-MODEL.md`, `core/ZAK-DESIGN-DNA-v1.md`, Figma files and design skills | Designer specialist |
| Image/visual direction and factory execution logic | Studio/Designer specialist boundary |
| `core/models/WRITING-MODEL-v0.1.md` and corpus-oriented writing material | Writing/content specialist candidate; ZIS stores routing and approved cross-domain evidence only |
| UI trend library and era kits | Designer research assets, not ZIS core |

## Category E — Obsolete or incompatible

| Asset | Reason |
| --- | --- |
| ZOS product/GUI/factory architecture as the ZIS runtime | ZIS has separate layers and M1 forbids frontend/factory scope |
| JSONL as the only durable operational store | Useful prototype evidence, but insufficient for relational contradiction and migration guarantees selected for ZIS |
| Numeric 0–1 confidence in ZOS schemas | Conflicts with M1's explicit non-precision requirement; ZIS uses ordinal states |
| ZOS-specific CLI and task routing implementation | Couples to the ZAK skill catalog and factory workflows |
| Docker/VPS production topology | Unnecessary infrastructure for local-first M1 |

## Category F — Sensitive and must not be imported

| Asset | Reason |
| --- | --- |
| Raw private evidence/runtime stores referenced by ZOS | Private data boundary |
| Credentials, tokens, cookies, environment values and secret stores | Secret material |
| Direct identity, face/biometric references, precise address, employer/company identity and account IDs | ZIS public identity boundary |
| Private conversations, family identifiers, financial or medical records | Sensitive personal data |
| Reversible alias maps | Would defeat public anonymization |

## Category G — Requires human review

| Asset | Review question |
| --- | --- |
| `core/models/DECISION-ENGINE-v0.1.md` | Which steps are general cognitive procedure versus personal constitution? |
| `core/models/BLIND-SPOT-MODEL.md` | Is each claim current, sufficiently evidenced and safe after anonymization? |
| `core/models/WRITING-MODEL-v0.1.md` | Should it remain wholly specialist-owned or yield a small cross-domain pattern? |
| Personal constitution abstractions | Which principles are owner-approved stable ZIS rules rather than personal evidence? |
| Memory records and model updates | Are source, time, consent, identity scrub and contradiction context complete? |
| Existing ZOS schemas | Which fields translate without carrying numeric confidence or identity-bearing structures? |

## Required-area inspection notes

- **core/kernel:** strong human-authority, permission, privacy and model-update concepts; personal constitution is sensitive.
- **core/foundation:** evidence hierarchy is valuable but includes person-oriented examples and an ordinal weighting narrative, not a machine contract.
- **core/models:** decision, product and creative models are evidence; design and writing models belong with specialists; blind spot models require review.
- **task routing:** `core/ZAK-TASK-ROUTER.md`, routing rules and `src/zos/router.py` are tied to the ZAK skill catalog. Only minimum-routing principles are reusable.
- **evidence rules:** provenance and contradiction concepts are reusable; numeric confidence and automatic hierarchy outcomes are not adopted wholesale.
- **permission model:** useful conceptual source for later approval implementation.
- **model update protocol:** proposal-before-mutation and reviewable history align with ZIS governance.
- **personal constitution:** identity-bearing and sensitive; never direct-import.
- **decision models:** potentially reusable after separating universal process from personal moral/context rules.
- **writing models:** specialist knowledge; corpus content stays outside ZIS.
- **blind spot models:** hypotheses, not permanent truth; anonymization plus human approval required.
- **memory:** JSONL prototype and schemas demonstrate local/private separation; ZIS M1 selects SQLite plus readable exports.
- **schemas:** useful field inventory but inconsistent timestamp validation and numeric confidence; evidence schema is less temporal than ZIS requires.
- **runtime architecture:** single core across interfaces and local/private boundaries are useful. Factory, web, Figma and VPS layers are out of scope.

