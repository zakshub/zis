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

## AI adapter

1. M5 resolves the provider-neutral boundary, disabled behavior, first real adapter, structured validation and candidate isolation.
2. Which exact OpenAI models should an owner configure for particular purposes remains a runtime choice, not durable architecture.
3. When should pricing metadata be refreshed, reviewed and retired without implying exact billed cost?
4. Should a later milestone support provider-reported billed cost separately from M5 estimates?
5. Multi-provider selection, retries, streaming, tool calling and provider failover remain intentionally unresolved future proposals.

## Observation

1. Which source is the first real connector?
2. Which data categories are never allowed into durable memory?
3. What default retention period applies to raw observations?

## Specialist federation

1. M6 resolves the common boundary: multiple future transport-specific adapters may implement one explicit request/response/provenance protocol.
2. M6 requires exact request/response contract versions and declared runtime-major/minor compatibility; future range negotiation needs a separate proposal.
3. M6 returns a visible unavailable/incompatible state and does not fallback automatically.
4. Which specialist will first publish an approved stable, privacy-scoped task endpoint?
5. Should ZIST become a writing specialist, an M7 corpus source, or remain outside ZIS after its interface and privacy boundary are reviewed?

## Simulation world

1. 2D, 2.5D or 3D first?
2. Browser renderer or native renderer?
3. How many creature states are needed for useful visualization?
4. Which backend events deserve visible world animation?

## Product future

1. Will ZIS always remain single owner, or will isolated instances later become a product?
2. If productized, what parts remain private intellectual property versus public specification?
