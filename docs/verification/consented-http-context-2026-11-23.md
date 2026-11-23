# Consented context on the HTTP sales path

November23,2026. This step reconnects canonical saved-shopping preference recall to HTTP sales, not legacy inferred/vector personality memory or automatic preference collection.

Existing CUSTOMER_MEMORY_ENABLED feature flag remains off by default. Only authenticated positive owner ID plus current canonical consent can read saved color/material/style preferences. Guest/feature-off do not access saved memory. Owner ID comes from authentication, not the browser payload. Existing90-day retention, strict explicit-preference policy and self-service controls are reused unchanged.

Preferences are request-local optional writer/reviewer evidence, never router product identity, hard search filters, budget, recipient taste or compatibility proof. Current customer words override optional saved hints. No raw SQL records, private sources or inferred financial/life-event traits are sent. No extra model call is introduced. Current HTTP does not silently collect new durable preferences; collection remains its existing separately consented route.

Canonical recall runs again after model work. Revocation/change/failure withholds that in-flight personalized reply. Redis conversation persistence is deferred until recheck succeeds so the rejected reply cannot contaminate future context. Context-local tokens reset on success/failure/cancellation. Earlier chat history remains a separate retained record: revocation does not rewrite already-delivered messages, and an earlier personalized answer may still occur in recent history. This PR does not claim retrospective deletion or that a concurrent revocation can undo already-sent bytes. No source memory is deleted by this patch.

Verification:1176passed,4skipped full disposableSQL/realRedis suite. Five mountedHTTP tests with actual SQL consent/preferences and Redis history cover enabled recall, other owner, prior revoke, feature off and revoke during writer call. The final case withholds and leaves no rejected response in Redis. Controlled model transport only, no live quality or deployment claim.

No schema, flag enabling, dependencies/images, owner-machine migration/deploy, provider calls or spending. Existing data lifecycle remains, including legacy inferred-memory gate. SQL/cache outages fall back to non-personalized work at initial recall; failed post-use revalidation fails closed. Current SQL implementation bounds output to five preferences, but no new database network deadline is added here; operational query latency remains part of broader runtime hardening.
