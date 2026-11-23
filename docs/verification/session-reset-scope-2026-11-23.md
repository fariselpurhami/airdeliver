# Session reset scope wording, 2026-11-23

Recent session reset previously claimed all memory cleared, although durable customer preferences intentionally persist and cache deletion is best effort. Copy now says recent reset requested, saved preferences unchanged, order records not erased, and cart state must confirm completion. It also preserves transparency about existing cart-clear behavior potentially cancelling pending orders. No execution behavior or deletion scope widened.

Full migrated PG19 suite732passed3skipped before final wording clarification; targeted reset test passed afterward. No provider calls. One new regression checks no blanket durable-memory erase claim and no new persistent-memory delete keys. No claim of atomic cache reset or changed pending-order policy.
