# Opening fixture opt-in correction

2026-11-24 owner worker inspection confirmed APP_ENV=development and AIRDELIVER_DEV_FIXTURES=true, yet opening pools contained candidates and zero eligible cards. This was a code-path gap: conversion preserved dev_fixture/fixture_in_stock labels, but opening selection and current-SQL publication required local_catalog/local_in_stock.

Both boundaries now use one helper that permits labeled in-stock fixtures only under the existing development opt-in. No fixture becomes a real offer. Defaults, production, historical demo exclusions, recency, current-SQL revalidation and independent model-written copy/review remain. No hardcoded product prose bypass.

Read-only diagnosis now distinguishes opted-in fixture presence when there are no real eligible rows; presence does not establish that a fixture is active/in-stock/fresh. It requests eligibility/cooldown/model-copy diagnosis rather than claiming the fixture is real stock.

Actual PostgreSQL/Redis opening tests cover opt-in fixture publication with preserved labels, default fixture withholding, real cards, demo exclusion and price changes. Full local run including provider cooldown changes: 1505 passed, 24 skipped. No external provider calls. Live Groq quota can still withhold model copy, so this is not proof that the owner's next opening will succeed. All canonical live-qualified flags remain false.

Owner rollout after merge: pull main, preserve .env.dev with AIRDELIVER_ENV_FILE=.env.dev and fixture opt-in, recreate api and api-worker with --no-deps using the combined dev Compose helper. Do not run migrations, seed or reindex. Allow existing model warmup to complete. Inspect readiness before a single owner retest after verified provider quota reset.
