# Clear cart concurrency boundary

Clear now uses a required snapshot read plus compare-and-delete, instead of an
unconditional delete that could erase a concurrently added item. After existing
pending-order cleanup it publishes a fresh current snapshot, rather than an
unconditional empty cart that could hide an item added during DB cleanup.
Existing order cancellation logic is preserved.

Real Redis regressions cover concurrent addition before compare/delete and a new
item arriving during slow order cleanup. Full local suite: 840 passed, 4 skipped,
20 existing warnings. Legacy frames still lack canonical revision ordering;
prepared SQL revision routing remains held for cutover review. Clear is not yet
journal-idempotent across redelivery. No deployment or production DB application.
