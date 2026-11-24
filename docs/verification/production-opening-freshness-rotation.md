# Production opening freshness rotation

The opening uses a per-user, per-product24-hour cooldown, not membership in a forever-seen set. `OPENING_PRODUCT_COOLDOWN_SECONDS` defaults to86400 and accepts60..604800. It works in production without enabling demo preview.

Only successfully streamed product rows get a last-shown timestamp in an additive Redis sorted set. The existing seen set and its prior TTL behavior are preserved. No history reset, deletion or reseeding is performed. Existing history entries without timestamps are eligible, rather than being hidden indefinitely. A product becomes eligible again after its timestamp ages beyond the cooldown; a later successful display refreshes its timestamp. Recently shown products remain excluded from all opening pools, including personalized recall.

For bestsellers/trending/deals, each bounded pool blends up to50 ranked rows and50 eligible rows ordered using a new server-generated nonce. Existing brand/category diversity and row shuffle then select at most5. The exploratory half can reach beyond a fixed ranked top100. This provides variation, not a guarantee that every refresh yields disjoint rows or that each catalog product is shown equally often. The database orders eligible rows for this query; large-catalog query cost needs production measurement.

Production still rejects seeded demo products and requires current active, positive-stock catalog rows. No ranking is evidence of real popularity, suitability, merchant availability or discounts. Model-written introduction/Insight still needs the existing review boundary. Dev demo preview is separate and remains explicitly labeled synthetic.

If the entire eligible real catalog was shown within the cooldown, the opening can honestly have no fresh rows until the cooldown ends. It does not silently waive the cooldown or clear history. The default follows the requested daily cycle, rather than requiring100 never-seen products.

Tests use actual Redis with a controlled clock to verify cooldown expiry, later re-show, timestamp refresh, user isolation and preserved legacy membership. Actual PostgreSQL tests verify nonce-driven pool variation beyond the ranked top100 while preserving eligibility and bounded results. Existing Redis publication/current-row and model-review tests remain in place.

After merge and final checks, existing combined API/worker recreate is sufficient. No migration or seed is needed. The default cooldown requires no environment change. The optional dev demo flag does not enable production demo offers.
