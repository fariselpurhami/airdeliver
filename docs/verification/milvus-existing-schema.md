# Existing collection mismatch, read-only diagnosis

The1536-dimensional GTE model loaded on the user's machine. The seeder rejected
an existing collection because at least one of id/vector/price/rating/category
was absent. Dimension validation ran first and passed. The previous error did
not name the missing field, so actual collection inspection is required before
claiming its origin. The immediately previous seeder943825b and historical API
creators declared all five required fields, so neither alone proves that origin.

After this checkpoint is on main, from the project root:

```bash
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev exec -T api /opt/venv/bin/python -m scripts.inspect_product_collection
```

This reads the currently mounted API source and existing Milvus metadata/stats.
It does not download/load GTE, rebuild images, restart services, seed rows, create
or delete any collection, or print token values. Report missing_required_fields,
fields, auto_id, enable_dynamic_field, indexes and statistics. Keep the original
collection until an explicit migration/reindex has been reviewed and authorized.

If the schema is incompatible, safest release path is a separately named new
collection built from authoritative PostgreSQL products and matching pinned GTE
vectors, validated against row identities/counts/search quality before an explicit
API read-target switch. Preserve the old collection for rollback. A seeder-only
collection rename is insufficient because the API read target must match. No
migration or target switch is implemented or authorized by this diagnostic.

CI diagnostic run45078367209 passed Seaweed but RustFS hit the known OpenSearch
disk high-watermark403 before schema creation. Cache-only cleanup was insufficient
on that hosted runner. CI now additionally removes unused preinstalled Android
and.NET SDKs, guarded to GitHub-hosted jobs only. No application volumes/images
or production watermarks are removed/relaxed. Diagnostic remains unmerged until
the exact updated checkpoint passes both jobs.
