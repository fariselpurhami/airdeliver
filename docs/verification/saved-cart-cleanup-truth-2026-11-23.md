# Saved cart cleanup outcome, 2026-11-23

Saving a list committed the database first, then used best-effort Redis deletion and claimed active cart empty. It now uses required deletion. If that post-commit cleanup cannot be confirmed, it explicitly says the saved list was recorded but active-cart clearing is uncertain, asks to refresh before saving again, and emits neither empty-cart preview nor full-success claim. Existing database commit and list representation are preserved. No automatic repeat save.

Local733passed3skipped20existing warnings, full migrated PG19 suite. New controlled post-commit transport-failure test verifies exactly one commit, no fake rollback of committed work, retained cart, and honest partial outcome. Existing isolated real Redis transport tests pass. Cross-store atomicity/save idempotency remain unresolved, not certified. No paid calls or deleted features.
