# Owner-configured provider capacity, no paid activation

Sources inspected November25,2026:
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/models

Groq lists GPT-OSS120B/20B free30RPM,1000RPD,8000TPM,200000TPD. Developer model table lists250000TPM/1000RPM.120B prices per1Mtokens:$0.15input/$0.60output;20B:$0.075/$0.30. These are published base values, not verification of this organization's account. Exact organization limits may differ, apply across organization traffic, and input/output per-minute limits may apply separately. Cached tokens do not count towards published rate limits. No account upgrade or API request was made.

## Configuration

Defaults are unchanged in effect:

```
PROVIDER_CAPACITY_PLAN=free
PROVIDER_PLAN_TPM_LIMIT=8000
PROVIDER_TPM_HEADROOM_PERCENT=10
```

This derives PROVIDER_TPM_BUDGET=7200. Optional explicit PROVIDER_TPM_BUDGET may lower the guard, never exceed plan minus headroom. A free profile cannot silently declare more than8000. Custom requires an explicit verified limit. Settings fail closed on conflict.

After the OWNER separately activates/verifies the desired plan and exact model/organization quota, the owner may configure both API and worker consistently:

```
PROVIDER_CAPACITY_PLAN=developer
PROVIDER_PLAN_TPM_LIMIT=250000
PROVIDER_TPM_HEADROOM_PERCENT=10
```

This derives225000, not250000, preserving10percent headroom. Remove a stale explicit PROVIDER_TPM_BUDGET or deliberately keep a lower override. Use a lower limit if the organization account says so. Restart/recreate API and worker with the same environment. Base Compose forwards plan/limit/headroom to API; worker already loads the configured environment file. No deployment settings were changed by this patch.

No paid profile is enabled by the examples. Configuration does not subscribe, authorize spend, establish account quota or prove capacity. Requests/day, tokens/day, requests/minute and any separate input/output limits remain provider enforced; the shared local ledger models combined rolling TPM only. Six-call/16000reserved-turn bound, current per-stage output caps, models, independent review, evidence/card/history gates and synchronous execution remain unchanged. Unknown request cost remains reserved. No automatic cap adaptation from untrusted provider text.

47actual Redis/PostgreSQL/adapter/profile tests pass, including free default, developer/custom limits, lower overrides, invalid conflicts, actual ledger plan limit and unchanged turn bound. Full exact-head matrix remains required. Large-volume and live400 acceptance remain open until authorized numeric trace/account-limit evidence is available.
