# M5 Modern AI Adapter

## Pre-implementation review and proposal

The accepted M0-M4 documentation, schemas, migrations, source and tests were reviewed before M5 implementation. No internal contradiction blocks the milestone. The accepted rules are consistent: the deterministic runtime and Cognitive Engine remain authoritative, AI is optional and replaceable, explicit context only may cross an external boundary, and provider output is never truth, memory, approval or execution.

The owner-approved bounded proposal is:

1. keep the Python 3.11+ standard-library runtime and use a small provider-neutral adapter protocol;
2. implement a disabled/no-provider adapter and exactly one real OpenAI Responses API adapter;
3. isolate HTTP and provider response parsing behind an injectable transport rather than add an SDK dependency;
4. persist only validated AI request, normalized response and candidate records through migration 005;
5. require explicit external-transmission approval and only `public` or `internal` context before transport;
6. obtain credentials from a named environment variable at call time and never persist or audit the value;
7. make timeout and failures explicit, bounded and non-retrying in M5;
8. keep AI assistance opt-in through a separate service/CLI path, never inside `CognitiveEngine.run_session`;
9. reuse the accepted transaction, audit, export, backup, restore and health patterns;
10. retain all M1-M4 behavior with AI disabled or unavailable.

This is an adapter layer, not a persistent specialist, specialist federation, capability sensing, observation, autonomous agent loop or Learning Engine.

## Executable boundaries

The following distinctions exist in contracts, code and tests:

1. An AI provider is an optional adapter, not the ZIS core.
2. AIResponse and AICandidate are distinct from EvidenceRecord and MemoryRecord tables/contracts.
3. A suggestion remains `ai_candidate_not_truth` and has no decision authority.
4. No approval or runtime-operation record is created by AI assistance.
5. Response text and provider envelopes are not stored as hidden reasoning; only validated structured output is retained.
6. Provider failure returns a normalized response while core health remains independent.
7. Disabled AI returns an explicit result while ZIS and M4 continue to operate.
8. Token usage and cost have separate fields and semantics.
9. Calculated cost is labeled `estimated`, never billed or exact.
10. The OpenAI adapter is not a specialist manifest and cannot invoke specialists.
11. `request_cognitive_assistance` links an explicit existing session but does not replace or overwrite deterministic cognition.

## Provider-neutral interface and selection

`AIProviderAdapter` is a small protocol: provider ID, adapter version, credential requirement, availability and request. `AIAdapterRegistry` selects adapters by ID and supports injected test providers without changing CognitiveEngine, EvidenceStore or ClassicalRuntime. `DisabledAIAdapter` is a real no-provider path.

Exactly one real provider is implemented: `OpenAIResponsesAdapter`. It constructs a Responses API JSON request and uses Python's standard-library HTTPS client. Provider-specific endpoint, payload construction and response parsing remain inside `ai.py`. The transport is injectable for deterministic tests; no SDK or third-party runtime dependency was added. M5 performs no automatic retry.

The real adapter was verified with injected synthetic transport, not a live account or credential. The endpoint and model are runtime configuration because external provider contracts and model availability can change.

## Configuration and secret boundary

AI is disabled by default. The bounded environment configuration is:

- `ZIS_AI_ENABLED`
- `ZIS_AI_PROVIDER`
- `ZIS_AI_MODEL`
- `ZIS_AI_ENDPOINT`
- `ZIS_AI_TIMEOUT_SECONDS`
- `ZIS_AI_MAX_OUTPUT_TOKENS`
- `OPENAI_API_KEY`

Only the credential environment-variable name exists in configuration. The credential value is read at invocation and passed directly to the adapter transport. It is never placed in a request/response/candidate record, SQLite, audit payload, export or backup manifest. Environment contents and Authorization headers are never logged.

## Request and prompt construction

AIRequest requires purpose, bounded task type, instruction, structured context, expected output schema, explicit context references, privacy class, external-transmission approval, timeout, output limit, provider/model metadata, timestamp and prompt fingerprint.

Only `public` or `internal` context with `external_transmission_approved: true` is accepted. `private` and `restricted` input is rejected. Existing recursive identity fields and conservative direct-text email, phone, address, credential/token and bearer checks run before adapter selection or transport. No database, global history, account context or cognitive session payload is loaded automatically.

Prompt construction uses stable JSON ordering. The fingerprint excludes execution time and depends on exactly what would be sent structurally. The fixed provider instruction requests concise structured output and explicitly rejects chain-of-thought, hidden reasoning, credentials and unrelated context.

Hidden-reasoning exclusion is enforced structurally in ZIS code and does not depend on provider obedience or the caller's output schema. Before transport, ZIS recursively rejects forbidden hidden-reasoning keys in request structures and schemas, and rejects instructions that solicit those traces. After transport, it recursively checks structured output before schema validation or persistence. The narrow forbidden set covers `chain_of_thought`, `chain-of-thought`, `hidden_reasoning`, `reasoning_trace`, `internal_reasoning`, `private_reasoning`, `scratchpad` and `internal_monologue`. Ordinary user-visible `reason`, `rationale` and `explanation` fields remain permitted.

## Response validation and candidate boundary

AIResponse statuses are `success`, `unavailable`, `timeout`, `provider_error`, `invalid_output`, `cancelled` and `disabled`. Error categories distinguish disabled, not configured, authentication, rate limit, provider server, transport/network, timeout, invalid provider response, invalid structured output, cancellation and unsupported provider.

The OpenAI response envelope must contain structured output text parseable as one JSON object. Independent recursive hidden-reasoning checks run before the object is checked against the request's expected schema using the documented ZIS-required JSON Schema subset. Identity/credential checking also runs before persistence. M5 performs no semantic repair or partial acceptance. Invalid output is discarded from the normalized response and creates no candidate.

Successful output creates one AICandidate with provider/model, source references, validated output, `pending_review` and `ai_candidate_not_truth`. It is never converted automatically into evidence, memory, pattern, hypothesis, idea, evaluation or reflection. It cannot resolve contradictions, approve itself or execute an action.

`request_cognitive_assistance` is an explicit optional integration method. It verifies the supplied cognitive session ID, adds that reference and delegates to the same boundary. It does not load the session's contents, invoke AI from `run_session`, or modify any M4 artifact.

## Usage and cost

Provider-supplied input, output and total token counts are preserved when integer values exist. Missing usage stays null; ZIS never invents counts.

Pricing is supplied as a versioned local `PricingEntry` containing provider/model, input/output rates per million tokens, currency, version and source. Without both usage and a matching entry, cost is explicitly unknown. With them, M5 calculates and labels an estimate. No timeless rates are hard-coded and estimated cost is not billed amount.

## Persistence, audit and recovery

Migration 005 adds `ai_requests`, `ai_responses` and `ai_candidates`. The approved safe request, normalized response, optional candidate and one metadata-only audit event commit in a single SQLite transaction after provider completion. Audit contains IDs, provider/model, purpose, outcome, timing, usage, cost status, candidate reference, error category and prompt fingerprint—never raw context, instructions, credential, headers or raw provider response.

If the final audit write fails, all three M5 projections roll back. Export format 4 contains only the validated durable records. Backup/restore counts and state equivalence include all M5 tables. Core health requires the schema-5 tables, while `AIService.status` reports optional provider state separately and does not make core health fail when AI is disabled or unconfigured.

## CLI

The minimal surface is:

- `zis ai status`
- `zis ai providers`
- `zis ai request <json-file>`
- `zis ai records <requests|responses|candidates> [--id ID]`

There is no chat UI, autonomous loop, tool calling, specialist dispatch or background provider worker.

## Verification and limitations

The verified suite contains the accepted 79 M1-M4 tests plus 21 M5 tests: 100 total. It covers disabled and missing-credential behavior, fake-provider success, deterministic request construction, explicit context, privacy rejection before transport, credential/header non-persistence, timeout/error normalization, malformed output, structural hidden-reasoning rejection before and after transport, ordinary visible reasons, candidate isolation, usage/cost states, metadata-only audit, transactional rollback, provider switching, explicit cognitive augmentation, migration 004-to-005, fresh initialization, health, export, backup/restore and CLI smoke.

The dependency-free validator is not a standards-complete Draft 2020-12 implementation. External provider compatibility was not proven against a live account. Timeout relies on the underlying blocking HTTPS timeout and there is no streaming or active cancellation handle. Application audit remains non-cryptographic. External transmission still requires human judgment because deterministic identity screening cannot prove free-text anonymity.

M5 did not implement or authorize specialist federation. The later approved M6 implementation remains a separate adapter layer and does not change this M5 boundary.
