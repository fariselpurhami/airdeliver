# Read-only owner trace

Use only after this script reaches main and the application containers already run the matching patched code. Pulling source alone does not rebuild running images. Do not run `up`, migrator or deployment commands merely to obtain logs. Do not paste raw logs or `.env`.

From the repository root, using the owner's normal combined Compose/environment invocation:

```
git pull --ff-only origin main
git rev-parse HEAD
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py logs --no-color --no-log-prefix --since 15m --tail 3000 api api-worker | python3 scripts/safe_provider_trace.py
```

This only reads existing logs and filters locally. It does not generate traffic, start/restart services, subscribe or call Groq. The existing helper selects.env.dev, the combined base+dev files and projectairdeliver_dev. Return only the filtered JSON and commit hash. The extractor reads the deployed formatter's JSON `message`/`name`, not dropped arbitrary extras. It emits only fixed event names, numeric counters/status and allowlisted structural categories, never model prose, prompts, headers in full or customer text. Up to1000events are emitted; summary reports skipped/non-JSON lines.

No matching events means evidence is absent from this time window or format, not that capacity/400 is solved. If containers are older, say so rather than treating empty output as success. No new provider call is needed for this read. Any later reproduction/traffic remains the owner's decision. Current application does not persist a full cost ledger or successful-response quota headers, so this is bounded diagnostic evidence, not proof of whole-chain throughput, per-user fairness or organization-scale capacity. The broader paid-scale work remains separate.

Tests exercise the actual JsonFormatter with usage, error-shape/schema categories, quota unit/duration, unsupported input, malicious literals and unrelated/private log rejection. Text-format logs are deliberately skipped rather than loosely matched.
