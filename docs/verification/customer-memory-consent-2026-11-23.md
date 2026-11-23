# Customer shopping memory v1, 2026-11-23

## Decision and scope

Customer-memory development approved by Faris at 01:57 EET on 2026-11-23. This is the first bounded checkpoint, not the full personalization vision.

- Feature defaults OFF globally, explicitly ON only for api/api-worker in dev Compose.
- Each authenticated customer must opt in. No consent records are auto-created by deployment or inferred from use.
- Canonical PostgreSQL consent and preference tables. Existing AIMemory and Milvus collections are preserved, not migrated or deleted.
- V1 accepts only explicit affirmative color/material/style preferences from a fixed vocabulary. Extractor evidence must be an exact substring of the customer statement, with an affirmative preference expression and the allowed value. No free-text profile, inferred personality, financial tier, profession, identity, health, religion, politics or life-event collection through the new path.
- Normalized SHA256 fingerprint dedupes per customer. A repeat refreshes expiry. Ninety-day retention; reads/export exclude expired rows immediately. Worker physically purges expired v1 rows hourly and on startup. Collection also purges that customer's expired rows.
- Opt-out/delete atomically revokes consent and erases canonical v1 rows. Row-lock recheck prevents an extraction started before revocation from committing afterward.
- Self-only GET /api/v1/users/me/memory, PUT /api/v1/users/me/memory/consent and DELETE /api/v1/users/me/memory. No request parameter selects another customer.
- Recall feeds saved preferences into the existing conversation-context path as untrusted data. General product answer puts them in user-role JSON, not policy. Current request and current catalog facts win.
- Four-second optional collection deadline, error-type-only logs and rollback on failure. No extraction before consent or for statements without explicit English preference expressions.

## Why no new Milvus copy

The finite v1 preference set does not require semantic retrieval. Canonical PostgreSQL avoids a new dual-store erasure/revocation gap. Existing free-text Milvus hooks are retained as an explicitly legacy implementation, not called by active collection. No claim of tested Milvus memory deletion or cross-store consistency is made. A broader semantic-memory design needs a separately verified index/tombstone lifecycle.

## Executed

712 passed, 2 skipped, 20 existing warnings on the full migrated disposable PostgreSQL19 suite. Includes real Redis conversation follow-up tests from the preceding checkpoint.

New real-PG checks: no consent means no extractor call; opt-in collection, normalized dedupe, independent-session recall, cross-customer isolation, export, expiry exclusion and physical purge, opt-out erasure, feature-off behavior, a newly constructed NLU instance receiving saved preferences in its answer prompt, and concurrent revocation while extraction is paused (no late reinsertion). Controlled HTTP tests verify authenticated id routing, strict bool/extra-field rejection, feature gating and missing-auth rejection. Privacy regression checks error logs carry no customer/provider text.

Migration tests for timestamp replay now target their own terminal timestamp revision instead of replaying later unrelated create-table migrations. They still execute the original zone-required and instant-preservation assertions.

No paid provider calls were made. Extraction and response transport are controlled in memory tests. No new frontend is edited, so no visual surface is claimed verified. Ruff/mypy not configured/installed, not run.

## Remaining, not completion claims

- No frontend consent/export/delete UI yet. Controls are authenticated API-only.
- V1 is English explicit preference collection, with a narrow vocabulary. Brand, size, broader budget/use-case preferences and learned personality/behavior remain outside v1.
- Existing behavior engine is untouched. This does not certify its existing data lifecycle or sensitive-inference behavior.
- Delete/export cover v1 preferences only, not legacy Milvus facts, recent chat history, orders, backups or logs. The delete endpoint states that scope. No deletion of existing data was performed by this work.
- General answer generation consumes preference context. Full learned-answer quality, every special response branch, production traffic and browser/worker deployment acceptance remain unproven.
- Dev is enabled after pull/restart/migration, but no customer is opted in automatically. Production remains disabled by default.
- Whole-platform readiness remains blocked on broader integration acceptance.
