# Canonical API commands

Run these from `backend/api`, using its existing virtual environment. Root maintenance wrappers have been retired with owner approval. Helper implementations are retained in `tools/`; do not run reset, repair, seed or sync commands merely to test packaging.

| Purpose | Canonical command |
| --- | --- |
| Message worker | `python -m app.services.orchestration.worker_entrypoint` |
| Demo catalog generator | `python -m tools.seed_ultra_scale` |
| Database helper | `python -m tools.create_db` |
| Database/table helper | `python -m tools.create_db_and_tables` |
| Milvus repair helper | `python -m tools.fix_milvus` |
| Password hash helper | `python -m tools.hash_password` |
| Initialization helper | `python -m tools.init_data` |
| Milvus reset helper | `python -m tools.nuke_milvus_v2` |
| Database reset helper | `python -m tools.reset_db` |
| Search synchronization helper | `python -m tools.sync_search` |

These names document entrypoints, not approval to execute them. Some helpers are destructive or have older assumptions. Migrations remain the schema owner. Existing approval gates, environment selection and provider/payment restrictions remain unchanged.

Compose and Kubernetes invoke the worker module directly. The worker implementation is byte-identical to its previous root path. The immutable move manifests remain unchanged; tests account only for the reviewed canonical seeder import and documentation path changes.

`debian.sources` was removed because the tracked repository, Dockerfiles and CI had no consumer. No maintenance implementation, model, migration, data fixture, certificate or requirements export was deleted in this step.
