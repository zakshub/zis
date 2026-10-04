# Open Questions

These questions are intentionally deferred until the relevant milestone. They are not blockers for documentation foundation.

## Runtime decisions resolved for the current implementation

1. Python 3.11+ owns the first classical runtime under D011; replacement remains possible.
2. SQLite owns current local durable state under D012.
3. JSON, CSV and Markdown are the current readable exports; verified SQLite backup/restore is added by M3.

## Memory

1. Ordinal confidence (`unknown`, `weak`, `probable`, `strong`, `established`) is canonical under D013.
2. What decay rules should apply to preferences versus factual evidence?
3. What evidence volume triggers consolidation?

## Cognitive engine

1. M4 resolves the first deterministic ruleset boundary: explicit context, exact structured comparisons, ordinal signals and first-class unknowns.
2. Which M5 provider-neutral adapter interface can add optional semantic assistance without changing deterministic artifact contracts?
3. Which future Learning Engine policy may apply an approved ModelUpdateProposal, and how will it preserve prior memory plus rollback/reconstruction evidence?
4. What reviewed rule-change process should version a future `m4.v2` ruleset without making old session reconstruction ambiguous?

## Observation

1. Which source is the first real connector?
2. Which data categories are never allowed into durable memory?
3. What default retention period applies to raw observations?

## Specialist federation

1. Should specialists be invoked through local CLI, HTTP, repository contracts or multiple adapters?
2. How should version compatibility be negotiated?
3. What is the fallback when a specialist is unavailable?

## Simulation world

1. 2D, 2.5D or 3D first?
2. Browser renderer or native renderer?
3. How many creature states are needed for useful visualization?
4. Which backend events deserve visible world animation?

## Product future

1. Will ZIS always remain single owner, or will isolated instances later become a product?
2. If productized, what parts remain private intellectual property versus public specification?
