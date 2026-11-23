# Memory export cache control, 2026-11-23

Self-only memory export now explicitly sends Cache-Control:no-store so preferences are not intentionally retained by HTTP caches. Existing route test asserts the header and authenticated-id scope. Local733passed3skipped20existing warnings on full migrated PG19 suite. This is a response-cache control, not deletion of browser copies or backup records. No category/retention expansion or provider calls.
