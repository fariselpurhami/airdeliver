# Derive cart aggregates from validated lines

Hydration now recomputes cart total with Decimal from validated line price and quantity. Read-only UI hydration and saved-list Order total no longer trust a stale cached aggregate. Original raw snapshot remains untouched for compare-and-set, so the next mutation/cleanup still detects changes correctly. No cache rewrite on read.

Two tests cover exact multi-line arithmetic with stale total, successful later CAS, and saved-list total from lines. Full disposable PostgreSQL19/Redis local suite770 passed,4 skipped,20 existing warnings. This is aggregate consistency, not current catalog pricing or stock. Checkout still rechecks mutable catalog facts before payment.
