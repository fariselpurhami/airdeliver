# Read-only running-stack preflight

Script scripts/probe_running_stack.py runs inside an existing API container.
It reads migration/table presence and catalog row count under an explicit
read-only DB transaction, then queries loopback health and unauthenticated memory
export status. Output is counts, table names, revisions and status codes only.
No provider/model inference, migrations, new accounts, consent changes or writes.
This is not a hybrid relevance/latency, consent lifecycle or answer-quality test.

Real migrated PostgreSQL regression plus controlled HTTP transport verifies the
read path and no auth headers. Full local 851 passed, 4 skipped. Actual user's
stack remains untested by this script until run there.
