# Owner embedding benchmark and later switch plan

## Scope

The owner approved local no-spend candidate downloads and benchmark on 2026-11-24. Existing GTE remains active. This adds no application model/index/configuration changes. It does not delete models, reseed SQL, mutate vector indexes or call hosted inference. Static files come from Hugging Face; local model execution is offline, trust_remote_code=False. No community conversion or downloaded Python is executed.

Official selected manifests:

| Profile | Revision | Licence metadata | Selected download |
| --- | --- | --- | --- |
| Harrier0.6B | f9b9dc8d367d443f2479d27aa5d8d2850c0774ee | MIT | 1,208,034,182 bytes |
| Granite311M multilingual R2 | 44399559930365213510b1ee2eb15ded83374f0e | Apache2.0 | 657,906,584 bytes |

Sources: https://huggingface.co/microsoft/harrier-oss-v1-0.6b and https://huggingface.co/ibm-granite/granite-embedding-311m-multilingual-r2 . Sizes from current API manifests, pinned in fixtures/retrieval_eval/models_v1.json. About1.87GB combined download, not a RAM estimate. LFS weights/tokenizer SHA256 and all selected file sizes checked. Cache overhead is additional. MIT/Apache licence metadata is not a legal opinion.

Baseline revision a9af15a6372d7d6b25e9fb07c2ccb9e1fe645644 is already cached under SENTENCE_TRANSFORMERS_HOME, not the default HF Hub directory. Baseline lookup checks both and NEVER downloads it. If missing, stop. Candidate files use separate pinned snapshots. Downloader never loads a model and is safe while the app runs.

## Measurement limits

- CPU float32, eager attention, two threads, batch1, sequence256 for every profile. Exact normalized dense reference over1000synthetic fixture documents, not the active Milvus ANN or OpenSearch BM25/fusion path.
- baseline-current means the current unprompted query POLICY applied to the standardized fixture corpus. It is not a measurement of the active index. baseline-instructed is an important control using the official retrieval instruction without changing model weights.
- Harrier uses its official web_search_query instruction. Granite uses no query instruction. Documents have no instruction. Synthetic metadata is excluded consistently for every profile, so corpus text differs from the current importer serialization and this is disclosed in artifacts.
-140assistant-authored DRAFT labels split70dev/70test, not human-adjudicated customer accuracy. Category/Arabic/constraint strata and related query templates limit conclusions. Top50 has no abstention calibration; no-match false positives are expected and must not be hidden.
- Comparison reports paired descriptive nDCG changes and bootstrap intervals. No automatic promotion. A result may justify further validation, never an automatic production switch. Dev must finish before a separate held-out test command. Human review and actual-store exporter remain open.
- Synthetic tiny Qwen2/Qwen3/ModernBERT offline CLI tests verify executable architecture/pooling/serialization only, not candidate quality or full-weight performance. Actual pinned candidate smoke stages must pass on the owner's image before full runs.

## Resource window

Owner runtime x86_64, reported container-visible host RAM12.61GiB and free disk52.86GiB. API cap6GiB is too low for GTE float32 weights plus runtime. Use existing api-seeder tools service (8GiB,2CPU) with command overridden and --no-deps. No seeding function executes. Pause api/api-worker during model execution to avoid duplicate resident models. Other services keep their data, no compose down or volume flags. If less than8GiB available host RAM, baseline runner stops. Do not raise limits blindly; report memory state. Runtime is not promised. Progress bars show document encoding; output artifacts are written to data/storage/embedding-benchmark-v1, partial failures retained.

Run commands from the usual repository root. Each is separate; stop after any failed command. The image must already exist, as in the successful owner preflight. A missing image could trigger a Docker build, so inspect the local image first if it has not been used.

1 Pull merged code (after CI merge only):

```sh
git pull --ff-only
```

2 Download Granite selected static files (~658MB), no model execution/provider inference:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py download --model granite
```

3 Download Harrier selected static files (~1.21GB), no model execution/provider inference:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py download --model harrier
```

4 Pause model services before the memory-heavy stage, data untouched. The app cannot serve AI while paused:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py stop api api-worker
```

5 Preflight confirms cached baseline/cgroup memory, no model execution/download:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py preflight
```

6 Smoke each actual pinned model separately (two documents/two queries), offline. Stop if any fails:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py smoke --model baseline-current
```

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py smoke --model granite
```

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py smoke --model harrier
```

7 Full DEV runs, sequential processes release RAM between models. No download/index writes/provider inference:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model baseline-current
```

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model baseline-instructed
```

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model granite
```

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model harrier
```

8 Restore services even if a smoke/full run failed, no migration or reseed. Existing API may warm slowly:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py up -d --no-deps api api-worker
```

9 Pure-file DEV comparison, no models/network:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/compare_fixture_benchmarks.py
```

Return comparison JSON and failure output if any, not env/secrets. Test split remains a separate later stage. No script automatically names a winner or switches config.

## Later controlled switch, not authorized by running benchmark

1 Review dev results, resource cost and Arabic/category/constraint/no-match failures. A better instructed baseline may remove the need for a replacement. Human-adjudicate held-out labels and run test without tuning. Measure actual-store behavior before accepting.
2 Verify usable SQL dump, Milvus/OpenSearch backup and restore exercise, cache manifest, exact current revisions/counts and rollback plan. Keep source catalog1000file+SHA and old vectors. Obtain the owner's separate go for the exact destructive operations after preview.
3 Create NEW versioned candidate indexes/collections with correct dimensions and model revision. Harrier1024 and Granite768 cannot be inserted into the current1536space. Index1000fixtures through the same importer under a candidate namespace, without deleting/recreating SQL products or changing product IDs. Verify both search stores, filters and live read-only retrieval.
4 Change active model/revision/dimension/collection/query prompt/normalization in one tested PR, both Compose stacks and all consumers together. Stage and verify new API/worker readiness, compare actual retrieval and rollback before removing old data.
5 Only after acceptance and explicit destructive-step approval, remove exact old cache/index paths from a reviewed manifest. Never wildcard cache directories, never delete shared tokenizer/vision/voice models. Retain backups through agreed rollback window. Complete deletion and rollback availability conflict, so settle retention explicitly before deletion.

### Reference inventory

Literal or shared-constant references in the current tracked source include:
- docker-compose.dev.yml (API/worker/seeder/cache overrides), docker-compose.yml (production inherited runtime revision/cache/worker settings). Production may inherit model choice through shared profile rather than literal model string; audit effective merged config and .env overrides as well.
- apps/api/app/core/catalog_contract.py, apps/api/app/core/ai_profile.py, apps/api/app/core/config.py, apps/api/app/services/ai_commerce_engine.py.
- apps/api/seed_ultra_scale.py, apps/api/sync_search.py, scripts/catalog_synthesizer.py.
- apps/api/scripts/smoke_behavior.py, verify_seed_search_integration.py, repair_empty_product_collection.py, inspect_product_collection.py, evaluate_gte_query_prompt.py, owner_embedding_benchmark.py and fixture benchmark manifests.
- apps/api/tests/test_dev_compose_config.py, test_seed_ultra_scale.py and all contract/dimension/index-loading tests discovered by constants.
- README.md, docs/verification/empty-milvus-rating-repair.md, docs/verification/offline-gte-query-evaluation-2026-11-23.md. Keep historical reports/baseline manifests historically accurate; append the new decision, do not blind-replace history.
- Existing tracked apps/api/app/services/__pycache__/ai_commerce_engine.cpython-311.pyc also matched the literal scan. It is not runtime source to edit; handle stale bytecode separately under the preserve-files rule.

This inventory is a lead, not proof of all transitive references. Re-run literal+constant search and inspect effective Compose/environment/runtime settings at switch time. No old references were changed in this benchmark PR.
