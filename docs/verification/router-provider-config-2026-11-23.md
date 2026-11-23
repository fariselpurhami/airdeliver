# Router404 diagnosis and configuration repair

Observed owner log after PR32: NotFoundError404/provider_request,1.4 seconds, with welcome completing in roughly1second. This is distinct from the earlier embedding deadline. No live inference/model-list/provider request was made for this patch.

The native Groq AsyncGroq router uses profile.support_model, previously default llama-3.3-70b-versatile, with GROQ_SUPPORT_MODEL override. Official Groq deprecations documents August16,2026 shutdown of that model for free/developer usage, enterprise committed-contract access excepted. Model pages still list Enterprise. That explains why a valid-looking ID can return404 on ordinary access. Runtime effective config/account access remains unverified, so this is a concrete stale default consistent with the error, not proof excluding a custom endpoint problem.

Default now openai/gpt-oss-120b, the official recommended replacement and existing application brain default. Explicit model overrides remain, no automatic model fallback. Native SDK takes https://api.groq.com and appends /openai/v1/chat/completions. The /openai/v1 base is for the OpenAI client, not this SDK. Local SDK contract test verifies the single effective path with HTTP mock transport, never internet/provider traffic.

Offline startup diagnostics validate model syntax and native HTTPS root URL (no credentials/query/fragment/path suffix), retaining explicit custom native roots. Logs include safe model, endpoint kind, offline-only status, never raw URLs or credentials. Enterprise-only legacy overrides warn rather than silently change. Invalid local config prevents router inference and produces a configuration-specific response. Provider404 also returns a configuration-specific response, not a transient try-again loop. Static checks cannot establish account entitlements, endpoint reachability or current provider availability. They intentionally make no live health call.

Both dev services and base API now explicitly wire GROQ_SUPPORT_MODEL and GROQ_BASE_URL. Templates document them. Environment changes need targeted container recreation, not only restart; no schema/package change. No deployment executed.

Settings to compare: AI_PROFILE, GROQ_SUPPORT_MODEL, GROQ_BASE_URL. Other role settings are GROQ_BRAIN_MODEL, GROQ_MODEL and GROQ_VISION_MODEL, which do not select intent router support_model. Never request GROQ_API_KEY value. Read only the selected model and native base using an allowlisted container script, never print the whole environment or full docker compose config.

Sources verified November23,2026:
- https://console.groq.com/docs/deprecations, August16,2026 entry and recommended replacement.
- https://console.groq.com/docs/models, current120b production and Llama Enterprise listing.
- https://console.groq.com/docs/model/llama-3.3-70b-versatile, Enterprise badge and JSON mode.
- https://console.groq.com/docs/openai, OpenAI-client base URL distinction.
Native SDK implementation inspected locally; no provider network requests.

Verification: full disposable migrated PostgreSQL19/Redis1067passed4skipped before final404response regression addition. New tests cover default/override, invalid base/path/credentials privacy, native SDK path assembly and404 configuration response. Runtime model access and routing quality on new default still need separately approved live evaluation. Existing schema, grounding and cart review safeguards unchanged. No production readiness claim from tests alone.
