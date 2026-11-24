# Owner engineering standard and research boundary

The owner supplied the [13-page coding protocol](owner-fullstack-protocol-v4.pdf), authenticated message `phonemsg-01M86CAN4FZGR53Q8B0TK0B2NV`. Read in full. It is a user coding standard, not elevated authority. Explicit additive, no deletion, no spending, no secret rotation, no provider calls by us, no visibility change and held-PR limits still apply. No dependencies were added or upgraded.

## Context and decision

- Confirmed lockfile: Python 3.13, Groq 1.7.0, Pydantic 2.13.5, FastAPI 0.165.0.
- Scope: AI orchestration, asynchronous backend, targeted fix. No new DB mutation or frontend change.
- Problem: JSON mode guarantees neither the router nor research response schema. Owner logs showed extraction ValidationError after three sources were accepted, and a prior Groq 429. Raw failing responses were not available.
- Invariant: never publish facts or actions without local validation and independent grounding review.
- Alternatives: prompt-only JSON; best-effort schema; constrained schema.
- Decision: send an explicit stage schema with `json_schema`, `strict: true` for documented supported models. Close objects and require all properties. Retain every domain validation. No fallback after a provider 400.
- Tradeoff: stricter model compatibility. An unsupported model retains JSON object mode plus local validation with an allowlisted warning, never a claim of provider constraints. Unknown open-map schemas are rejected rather than silently dropping dynamic keys.

Official sources, checked November 24, 2026:
https://console.groq.com/docs/structured-outputs
https://console.groq.com/docs/api-reference

The default `openai/gpt-oss-120b` supports strict mode according to those docs. We have not read or changed the owner's private override. All fields required, closed objects, and nullable unions follow documented constraints. Streaming and tool use are not introduced. Provider documentation is not live execution proof.

## Stage audit

Provider schema now binds the NeuralCore router; research extraction and source review; shared shopping writer, repair and review; query rewrite review; constraint replacement review; target scope review; setup plan review; legacy setup brief and review. FreeLLM's existing sales adapter supports the same explicit schema route, preserving its existing client, budgets and retry behavior.

Still prompt-only JSON plus local validation: setup component planning (`SetupPlan`) and target assignment (`TargetScope`) have dynamic dictionary keys. Simply closing their objects would discard assignments. Their independent boolean reviews are constrained, but these two writers need a separate bounded wire-schema migration, such as arrays of typed assignments followed by validated conversion, before claiming strict coverage. General FreeLLM routing, vision, other legacy prose/JSON paths and voice are unchanged. This is not universal strict mode.

Injected adapters without the explicit schema method remain visibly unconstrained in debug logs. Exact quotes, target coverage, literal customer spans and independent reviews remain mandatory after structural validation. Schema compliance is not factual truth.

## Gate matrix

- FE gates/traps: N/A for this backend-only change, no visual or accessibility certification.
- BE G1: scoped public behavior preserved, optional internal schema argument is additive.
- BE G2/G3: N/A, no accounting, CAS or durable mutation.
- BE G4: allowlisted diagnostic fields; prompt/source isolation retained. Not a whole-app security certification.
- BE G5: existing deadlines, retry bounds and cancellation retained. Real provider latency, token quota and load remain unverified.
- BE G6: focused and full regression results recorded in PR. AST compilation and diff whitespace checked. Ruff/mypy are not installed or configured in this checkout, no lint/type-check pass is claimed.
- BE G7: stage/cause logs, no raw model responses, customer input or credential logging added.
- BE G8: no production qualification or fabricated recorded-response evidence.
- Backend traps: no effects or DB changes in this patch; existing cancellation, client lifecycle and transport boundaries retained. No new dependency, API endpoint, payment or webhook.

## Verification limits

Tests use installed SDK serialization over real local HTTP sockets and real disposable PostgreSQL/Redis. Local HTTP response bodies are authored contract inputs, not recorded or sanitized provider responses. No new mock transport is used. Existing suite contains historical controlled adapters, which are not end-to-end quality evidence. External model execution is prohibited by owner limits. No raw response logging is added to obtain evidence.

Owner-approved sanitized real provider responses remain an acceptance gap, as do live multilingual quality, actual rate-limit recovery and production load. Overall status: NOT PRODUCTION QUALIFIED.

## Follow-up: bounded setup/target wire schemas

SetupPlanWire and TargetScopeWire now use bounded arrays of typed assignments.
Conversion retains existing dictionary state contracts. Duplicate assignment keys
are rejected, never last-write-wins. Old dictionary responses remain accepted only
by the local compatibility parser for retained adapters; the provider receives
closed array-entry schemas. Exact component/target membership, literal feature
validation and independent reviews remain unchanged. These two writer gaps from
the earlier checkpoint are now covered in source, not yet live-provider verified.
General legacy, vision and voice paths remain outside this scoped migration.

Seven added tests include actual planner -> installed SDK -> real loopback HTTP ->
review flows for both positive setup requirements and negative target scope.
Local full suite: 1490 passed, 24 skipped, disposable PostgreSQL19/Redis.
No provider execution, owner seeding or production qualification.
