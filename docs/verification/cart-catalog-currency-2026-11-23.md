# Keep catalog currency aligned with USD cart

Add-to-cart now checks the current product currency before writing a USD-only cart. Non-USD or unknown currency is rejected without conversion or dollar-labeled preview. Checkout already performs its independent currency check. Existing USD behavior stays unchanged.

Actual migrated PostgreSQL regression changes a product to EUR in one session and attempts add in a new session. No cart state write, success or preview occurs. Full local PostgreSQL19/Redis suite782 passed,4 skipped,20 existing warnings. Not multi-currency support or a currency-conversion feature. Legacy cached items lacking currency remain subject to checkout's current catalog check.
