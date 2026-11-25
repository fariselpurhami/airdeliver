# Demo catalog seeding on PostgreSQL 19

`backend/api/tools/seed_ultra_scale.py` remains the catalog generator. Migrations own the schema. The seeder checks the migrated columns and timestamp types instead of creating a conflicting standalone products table.

## Data contract

- USD prices use PostgreSQL `NUMERIC(10,2)` and `Decimal`, with two decimal places.
- Names, stock, ratings, variants and image links are demo data, not merchant offers. Descriptions say this explicitly. Authenticity and verified-photography claims are not generated.
- The seed and ordinal determine each record independently. Changing batch size, stopping, or restarting does not change later generated records. Demo timestamps are explicitly fixed at January 1, 2026 UTC.
- A versioned, seed-specific SKU namespace identifies the demo dataset. Existing catalog IDs do not determine whether generation is skipped. PostgreSQL assigns IDs.
- Existing SKUs and inventory edits are preserved. Replays read the actual stored rows and reconcile indexes using their real database IDs. A failed index write can be repaired by rerunning.
- No table, collection or index is automatically dropped. Existing vector dimensions are checked and mismatches fail clearly.
- Explicitly disabled backends are reported as disabled. A configured backend failure does not produce a successful completion, including when continuing other batches after an error.

The API and seeder share the text model, 1536 dimensions, collection name and pinned default model revision through `app/core/catalog_contract.py`. A custom model needs its actual dimension and an isolated collection, not the API's collection. The catalog seeder populates text search. It does not claim to generate visual embeddings from illustrative images.

## Commands

From the repository root, after the combined development setup has created `.env.dev` and migrations have succeeded:

```sh
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev --profile tools run --rm api-seeder
```

For a 16 GB Intel Mac, run model-heavy API/worker inference separately from this one-off job. The default batch is 16, embedding batch 1, CPU threads 2, max sequence length 256 and PostgreSQL pool 2 with no overflow. The seeder has its own network attachment and no longer requires the API process to stay running. It still needs PostgreSQL, the successful migrator, Milvus and OpenSearch for the default indexed mode. The 1.5B model itself requires several GB of memory. Small batches do not remove that weight-memory requirement, and a full-stack Mac memory benchmark is not claimed.

To populate PostgreSQL only, explicitly disabling both search backends and avoiding model loading:

```sh
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev --profile tools run --rm --no-deps -e MILVUS_ENABLED=false -e OPENSEARCH_ENABLED=false api-seeder
```

The second command assumes the database is already up and migrated. It does not build or repair search indexes. Rerun the normal indexed command later to reconcile them. Set `SEED_TARGET_COUNT`, `SEED_BATCH_SIZE` and `SEED_RANDOM_SEED` locally to change generation. Reusing the same seed identifies the same demo dataset; changing it intentionally creates a different dataset without deleting the old one.

Populated legacy naive timestamps require a verified `LEGACY_TIMESTAMP_TIMEZONE`. New empty databases need no historical conversion decision. Do not infer a legacy timezone from your location. A new follow-up migration fixes the Product model's previously mismatched timestamp columns; already-aware columns are not reinterpreted.

## Verification scope

Native PostgreSQL tests cover 1,000 rows, USD/JSONB/UTC types, unrelated high catalog IDs, rerun safety, preserving inventory edits, index-failure recovery, and the actual CLI. A separate smoke test uses a real small 384-dimensional model, not fake vectors. CI also has a real Milvus/OpenSearch round-trip test with that small model in isolated indexes. Check its actual run result before calling that path verified. These tests do not claim a full default-GTE model benchmark or full-platform production certification.
