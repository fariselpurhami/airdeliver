# Revalidate mutable cart before persistence

Pydantic construction checks do not re-run on normal attribute/list mutation. Existing-line catalog refresh could assign an invalid value then write it despite safe hydration. The write boundary now validates a fresh cart value before arithmetic/CAS. Invalid mutated state preserves previous Redis data and emits no success/preview.

Six tests cover invalid price/quantity/ID assignment and negative catalog refresh of an existing line. Full migrated PostgreSQL19/Redis local suite791 passed,4 skipped,20 existing warnings. These are controlled invalid inputs; database constraints already prevent negative catalog price in normal PostgreSQL rows. Boundary defense remains useful for alternate adapters/model mutation. Not a general security certification.
