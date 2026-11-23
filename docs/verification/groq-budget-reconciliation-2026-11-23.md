# Failed first Groq attempt, preserved budget diagnostic

Owner-stack acceptance proved add/remove HTTP202, matching cart membership and live Redis carousels. Reported add IDs: 76,2,21,31. Remove IDs: 53,73,62. Current catalog existence/active/inventory/uniqueness checks passed. Relevance and technical compatibility remain unverified pending current catalog inspection. The dedicated user was deactivated.

The first Groq call raised SDK NotFoundError. One request reservation is consumed even on failure. No successful model output/token usage was reported, no automatic retry occurred. Seven request attempts remain of the eight-request approval; provider billing was not inspected. Local SDK URL construction with a synthetic non-valid key, no network, produced the correct documented /openai/v1/chat/completions route. Model/account availability is plausible, not proven by a 404 class alone. The exact provider error code was not retained by the initial script.

`python -m scripts.reconcile_groq_acceptance --confirm-free-tier-only` is a SINGLE models-list diagnostic, counted as one more request. It validates the original approval ID, exactly one reserved failed case and deactivated test user. It leaves the original file untouched and creates an exclusive successor ending -models-v2.json, recording source SHA256 and inherited usage. Reservation is fsynced before request. On success or error total becomes two, leaving six. Rerun refuses. Never remove/reset either file. A changed/corrupt/unexpected source blocks instead of guessing usage.

No completion or alternate model selection happens in this diagnostic. It creates no user, cart mutation, other provider request or paid fallback. Groq endpoint is fixed, proxy/env redirection disabled, SDK retries zero. Errors expose class/status and only a small allowlist of public error codes, never raw body/settings/key. Model IDs are constrained to identifier characters. List presence does not establish completion access or free-plan account status; any later six-call continuation needs the actual listed choice reviewed and must inherit BOTH ledgers.

Tests use controlled model-list responses and errors, no actual provider request. They verify source immutability, cumulative count, second-run refusal, invalid source refusal, error output sanitization and model-ID shape filtering.

Official public model catalog still lists openai/gpt-oss-120b. Do not claim general removal or Free-tier exclusion based on this user's 404:
- https://console.groq.com/docs/models
- https://console.groq.com/docs/api-reference
