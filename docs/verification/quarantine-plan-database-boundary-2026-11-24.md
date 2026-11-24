# Quarantine planning boundary

ActualPG19test creates a separate disposable database clone and proves same-database refusal, matching snapshot/count acceptance, private exclusive manifest, archive fingerprint binding and changed product count refusal without manifest publication. Existing apply/rollback/stale/concurrent state test retained. Two tests passed.

This clone test is NOT an archive restore test and does not certify archive provenance. Existing DockerCIbackup test actually pg_dumps/restores and checks one sentinel row; comprehensive full-schema/data recovery comparison remains open. Owner tool still never executed on owner data. Final owner batch must not imply these prerequisites have already occurred.
