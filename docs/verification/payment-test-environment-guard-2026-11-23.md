# Explicit payment integration-test environment

Mark combined PostgreSQL/Redis payment snapshot tests as requiring TEST_POSTGRES_DSN, matching their disposable database fixture contract. Running pytest without that environment skips3cases rather than failing on a missing variable. CI and the full disposable local harness still supply it and execute the tests. No application runtime change.
