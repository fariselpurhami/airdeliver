# Harrier controlled switch, prepared not activated

Owner selected Harrier without a GTE quality comparison on2026-11-24. This is
not a measured win over GTE. Default remains gte-v1. Pull alone changes no space.

## Bound contract

PRODUCT_TEXT_PROFILE=harrier-v1 selects microsoft/harrier-oss-v1-0.6b,
revision f9b9dc8d367d443f2479d27aa5d8d2850c0774ee,1024dimensions and separate
product, intent, memory and OpenSearch names ending harrier_v1. Visual SigLIP
stays unchanged. Query and memory embeddings use official instruction and L2.
Product documents use existing importer serialization and L2, no instruction.
Benchmark vectors are NOT reused as live catalog vectors.

Source model contract: https://huggingface.co/microsoft/harrier-oss-v1-0.6b

## Owner staging, no activation yet

1. Preserve existing SQL backup and its index/preflight. Readable archive is
   not a full restore. Old indexes/cache remain untouched, not claimed backed up.
2. Update code only after exact-head checks and merge. Build new image using
   normal base+dev Compose configuration. Do NOT run migrator/upgrade-head.
3. Run scripts/migrate_harrier_catalog.py default dryrun in owner seeder image.
   It reads SQL in read-only transaction and all GTE memory through iterator;
   outputs count, fixture subset, model contract and content-bound SHA. No model
   load or writes in dryrun. All1100SQLrows are indexed preserving IDs, not
   reseeded. Current catalog filters still control eligibility.
4. Before apply, stop new writes to source memory/catalog. Dryrun SHA is checked
   again on apply, but it cannot prevent writes after that snapshot. Keep this
   quiet period until activation. Review1100count, memory count and SHA.
5. Apply exact reviewed SHA and expected count. Both repositories use existing
   additive upsert/schema code, no drops. Memory target starts empty and keeps
   original user_id/text/timestamp plus source_memory_id. Target memory uses
   auto-generatedIDs so future normal inserts still work. Nonempty target
   memory blocks automatic retry to avoid duplicates/stale facts.
6. Build confirms sink upserts and flushed/refreshed final counts. This is NOT
   semantic quality, full identity readback or live acceptance. On partial failure
   DO NOT activate. Do not delete candidate data automatically.
7. Activation commands/receipt verification are a separate owner checkpoint;
   keep GTE default until the candidate report is reviewed. Recreate API/worker
   with --no-deps to avoid held migrations. Verify profile/revision/collections,
   startup readiness, card rendering and real Arabic follow-up answers.
8. Rollback selects gte-v1 and restarts same services; all old data remains.
   Facts learned after activation are NOT automatically reverse-migrated, so
   rollback after new writes needs reconciliation rather than pretending parity.
9. No cache/index deletion is in this PR. Exact preview, backups/restore route
   and explicit final approval are required later. SQL1100rows are never deleted.

## Scope and limits

No owner-machine action, provider calls, hosted inference or model download was
performed by the author. Static intents hydrate via existing startup path under
the selected model. Existing memory names never mix dimensions. Legacy sync keeps
its GTE implementation and refuses Harrier because its document serialization
differs from importer; use migration tool instead. Harrier uses256token cap in
API and importer so memory re-encoding and runtime have the same policy. CI demonstrates
code contracts only, not deployment, throughput, ranking or production parity.

Harrier loader resolves the already-downloaded pinned HF snapshot and verifies
manifest file sizes/weight SHA before loading locally. No fallback model/download.
Query-only256token policy is shared with migrated memories. Product documents
explicitly use empty prompt to avoid default query-instruction leakage.

English evidence: scripts/summarize_embedding_languages.py rescans the existing
saved rankings only. It validates full original catalog SHA and query coverage,
then separates English text from Arabic-script and SKU-only queries. Dataset has
no language labels; this explicit grouping is reported, not implied ground truth.
No new inference or download. Selection/activation is on hold for owner's review
of the newly prioritized English-only evidence, not a new demand for GTE baseline.
