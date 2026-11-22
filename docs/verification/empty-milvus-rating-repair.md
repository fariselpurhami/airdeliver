# Explicit empty missing-rating repair

Evidence: inspector on user's machine reports the exact shared text collection,
id/vector1536/price/category, no rating, dynamic=true, auto_id=false, COSINE HNSW,
row_count0. WorkerRuntime.ensure_milvus_schema creates precisely that shape.
API/seeder creators include rating. Worker bootstrap now includes it too.
Existing collections remain unchanged until an explicit maintenance action.

The repair defaults to read-only. Apply requires the exact collection name,
known mismatched schema, empty stats, flush plus strong count0, and explicit
confirmation that all writers are stopped. Refuses nonempty or unknown shapes.
There is no atomic Milvus count-and-drop operation, so maintenance exclusivity is
required; flags are attestations, not an automatic distributed lock. No other
collection, PG row, OpenSearch index or storage volume is touched.

After CI merge, get explicit user approval before these commands. From root:

```bash
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev stop api api-worker api-seeder
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev run --rm --no-deps --entrypoint /opt/venv/bin/python api-seeder -m scripts.repair_empty_product_collection --collection airdeliver_products_sota_v4 --apply-empty-repair --confirm-writers-stopped
```

Expected: repair=empty_missing_rating_recreated, missing_required_fields=[],
writes_performed=true, statistics.row_count0. If any refusal/error occurs, stop,
report output; do not weaken guards or rerun drop blindly. The script never
loads GTE. Recreate worker/API containers later so processes load patched code;
do not merely restart a worker running code baked into an old image. Rebuilds
are separate and should be timed with the user's local model/RAM workload.

On success, the17product seeder can populate the repaired target from cached GTE.
Do not start API/worker simultaneously with seeding on constrained memory until
that workload is complete. If create fails after an empty drop, data remains
unchanged but target may be absent: ordinary canonical bootstrap can create it,
not another forced drop. Preserve logs and resolve before resuming traffic.
