# Optional memory SQL failure isolation

A failed optional recall query now rolls back the failed PostgreSQL transaction
before returning recent context, so later shopping queries do not inherit an
aborted session. Development memory flag can now be explicitly disabled through
Compose interpolation; its existing true default is unchanged. This does not
make absent memory endpoints available, create tables or apply a migration.

Real PostgreSQL regression deliberately queries a missing optional table, invokes
the recall fallback and proves the same session can execute SELECT 1 afterward.
Full local suite: 850 passed, 4 skipped, 20 existing warnings. No user database,
provider spend, deployment, migration or memory category expansion performed.
