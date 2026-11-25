# Read-only operator capacity snapshot

The application usage ledger is now inspectable without printing Redis keys, raw principals, credentials, prompts or provider headers. The CLI reads numeric state in one Redis Lua evaluation; it does not prune, reset, reserve or call the provider. It uses the current standalone shared Redis deployment. Redis Cluster multi-slot operation is not supported by this combined snapshot.

After this utility is merged to main and the API code is current:

```
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py exec -T api /opt/venv/bin/python -m scripts.provider_capacity_snapshot --model openai/gpt-oss-120b
```

Repeat with openai/gpt-oss-20b for that separate model ledger. This is read-only, no test question/restart/subscription needed. Do not use it before the file is available in the running code. No new dependency or migration required. The command was not run against the owner's installation.

The output distinguishes absent metering/unknown cost from actual zero, combines model rolling usage/header clamp/cooldown and organization active/queued invocation counts, and explicitly disclaims provider-account quota and billing reconciliation. Queued entries can include expiring crashed waiters until the next admission cleanup. Usage includes retained unknown reservations. Cost only covers known numeric input/output usage for the explicitly priced exact model; unknown-cost count remains visible. A low/zero ledger reading does not prove that Groq accepts new work or that a whole chain fits. Current request/day and token/minute observations do not locally model every provider quota dimension.

Seven real Redis/PostgreSQL snapshot/meter/header tests pass, including absent-vs-zero, old-window exclusion, unknown cost counts, no private fields and no ledger mutation. Exact-head full CI required before merging. This improves operator inspection, not the scale acceptance status. External alert delivery, full billing reconciliation and high-volume provider behavior still unverified.
