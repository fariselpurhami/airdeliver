# Preserve canonical cart line order

Prepared canonical add now replaces an existing line in place instead of moving
it to the end when refreshing price/quantity. This matches the existing active
cart behavior. Real PostgreSQL regression checks a two-line cart and refreshed
first line. Full local suite 849 passed, 4 skipped, 20 existing warnings.
No runtime cutover, schema application or deployment.
