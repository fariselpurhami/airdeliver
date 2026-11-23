# Strict checkout cart identifiers and quantities

Independent checkout hydration now requires actual integer product IDs within PostgreSQL BIGINT and actual integer quantity1-99. It does not coerce numeric strings/floats into a different type or pass oversized IDs into database lookups. The existing id/product_id alias remains supported. Valid existing integer carts are unchanged.

Seven tests stop invalid payloads before catalog lookup, order insert or provider call. Full disposable PostgreSQL19/Redis suite781 passed,4 skipped,20 existing warnings. This closes a type/range boundary, not all checkout fraud or payment correctness.
