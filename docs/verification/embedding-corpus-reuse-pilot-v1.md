# Offline document-vector reuse and timed pilot

Additive benchmark-only improvement after the owner's two-document smoke showed substantial baseline CPU cost. No production model/index/configuration changed. No pretrained model downloaded or owner-machine command executed by the implementation work.

## Reuse contract

Full benchmark runs now persist normalized document vectors to the isolated benchmark output directory under document-vectors-v1/<bindingSHA>. Binding includes exact model revision AND SHA of local safetensors/config/tokenizer/pooling files, exact catalog SHA, ordered SKUs, composed-document text SHA, document prompt, dtypefloat32, CPU/eager attention, seq256, batch1, threads2 and installed torch/transformers/sentence-transformers/numpy versions. Query prompt is intentionally excluded: query instructions cannot change document embeddings when document prompt and model are identical.

A first full GTE run writes a completed NumPy array and manifest, then renames the completed directory. The instructed GTE control reuses those verified vectors, but still loads the same model and computes its own70query embeddings. This saves a second1000document encode, not the model memory, startup or query cost. Dev and held-out queries can share a corpus without training on either query set. Candidate models never share vectors. Full benchmark artifacts already created under PR137 did NOT persist vectors and cannot magically supply a corpus cache.

Read verifies contract, fileSHA, dtype, shape, current model dimension, finite/nonzero unit vectors; allow_pickle=False. Mismatch/corruption fails, no automatic overwrite/deletion. Different settings produce a different key, never silent reuse. Partial cache files remain isolated and are not treated as completed results. SHA binding detects unintended changes, not a malicious actor rewriting both data and manifests. Hashing baseline7.1GB adds disk reads each run, reported as overhead rather than model encoding time.

## Pilot

The owner runner gains pilot --pilot-docs20..50. It picks deterministic category-spread fixture documents, spaced within categories, rather than contiguous variants. Each document is encoded individually with the same CPUfloat32/eager/seq256/batch1/two-thread settings as the full run. Reports every duration, first-document warmup separately through the raw list, remaining median/p95, peakRSS and a1000document corpus-only mean extrapolation. It loads the real local model, so the same8GiB tools limit and host-memory check apply. No query quality metric, no query execution, no vector persistence or index writes in pilot.

The projection is NOT an upper bound, not a completion-time promise, and excludes queries, later thermal throttling, swap and host contention. Category coverage is not a statistically representative customer workload. A20document baseline pilot could still take several minutes or longer; the owner chooses the downtime window. Existing2document smoke is not repurposed as a speed benchmark.

## Owner sequence after merge

Do NOT restart an active candidate run or pull code while it is still reading benchmark scripts. Finish or stop it deliberately first. Existing candidate score/ranking artifacts remain valid under their disclosed old method, but are never overwritten by this revision.

1 Pull only when no benchmark process is running:

```sh
git pull --ff-only
```

2 Pause duplicate model services, no dependencies/data changes:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py stop api api-worker
```

3 Run one20document GTE pilot inside existing8GiB/2CPU tools service, not6GiB API. No downloads/hosted inference:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py pilot --model baseline-current --pilot-docs 20
```

4 Restart on success OR failure, then send full pilot JSON/error before scheduling a long run:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py up -d --no-deps api api-worker
```

Stop if preflight reports low memory, process fails/OOM or progress cost is unacceptable. Do not raise limits blindly. Existing artifact/partial refusal requires inspection before a retry, never a blind delete.

## Later planned baseline window, not automatic

Pause model services again as above, then current-query baseline full run (1000docs+70queries). First completion persists the verified corpus:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model baseline-current
```

Only after its success, instructed control reuses matching vectors automatically. It prints Verified document vectors reused; document encoding skipped. If absent, do not assume reuse occurred; send output:

```sh
AIRDELIVER_ENV_FILE=.env.dev python3 scripts/dev_compose_quiet_volumes.py run --rm --no-deps -T --entrypoint python api-seeder scripts/owner_embedding_benchmark.py run --model baseline-instructed
```

Restart services after either failure or both successes using step4. No parallel model runs. Pure-file comparison remains the same command after all4profiles complete. Baseline pilot and candidate-only scores cannot establish a replacement winner. Synthetic DRAFT labels, current-store/exporter gap, held-out review and backup-first controlled switch remain unchanged.

## Verification

Focused tests exercise pure cache integrity/mismatch/reorder/model-byte/package/settings behavior and a real tiny offline Qwen2 CLI first encode, second query-prompt reuse and20document pilot. Tiny Qwen3/ModernBERT smoke continues to exercise architecture loading. No pretrained model execution or hosted request occurred. Full-suite/CI results are recorded in the PR, not a production or real-model quality claim.

Local verification split to stay within process runtime budget:1536passed24skipped for the complete PG19/Redis suite excluding the15-case owner-runner module; that module passed15cases separately (31passed when combined with16cache cases). All tests covered, no combined single-run count claimed. An initial combined invocation was interrupted by the execution timeout, not a test assertion; it was not treated as a pass.
