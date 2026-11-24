# Granite candidate, not activated

Owner confirmed Granite candidate on2026-11-24 after English-only offline
summary: tiny synthetic draft sample near tied, Granite faster/lower measured
memory on owner's benchmark. Arabic is not planned soon. Harrier stays available.
Neither candidate is a proven production ranking winner over GTE.

Granite contract: ibm-granite/granite-embedding-311m-multilingual-r2,
44399559930365213510b1ee2eb15ded83374f0e,768dimensions, empty query prompt,
L2normalization,256token cap. Separate product, intent, memory and OpenSearch
names ending granite_v1. GTE remains default and every old store stays intact.
Official source https://huggingface.co/ibm-granite/granite-embedding-311m-multilingual-r2
Manifest already pinned/downloaded through owner benchmark. Snapshot manifest/SHA
verified locally before load, no hosted inference or implicit download.

Same owner migration tool now accepts --profile granite-v1 on BOTH dryrun/apply.
Profile selects full target contract before imports. ExistingHarrier profile and
default CLI behavior retained. Content digest binds target profile; HarrierSHA
cannot authorizeGranite write. All1100SQLIDs preserved, source memory copied to
separate collection, original data unchanged. See Harrier switch runbook for
quiet snapshot/build/activation, partial-state and rollback requirements.

Additive code costs no hosted/provider money. OwnerCPU/disk/RAM still needed to
buildGraniteindexes. Previous1000doc synthetic timing is not a promise for actual
1100row importer+memory migration. No model/index cache deletion in this PR.

Actual SKU-only embedding recall@10was0for both candidates in offline test.
This is not proof of failure of actual hybrid search. Exact SKU lookup needs its
own SQL/keyword route, not assumed solved by embedding model choice.

Verification: freshprocess real profile/engine/seeder wiring768andempty prompt,
three disjoint namespaces, previousHarrier contracts andmigrationtests retained.
CI is not owner deployment, ranking quality, fullDR or production acceptance.
