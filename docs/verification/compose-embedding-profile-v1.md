# Compose model identity and shared cache

Both base and combined dev stacks select the active encoder using
PRODUCT_TEXT_PROFILE and its pinned catalog_contract revision/dimension/namespaces.
The fallback remains gte-v1 for unactivated installations. Owner activation in
.env.dev to granite-v1 remains necessary and is not overwritten by this change.
Legacy GTE code/profile is retained, not active when granite-v1 is selected.

The dev API/worker EMBEDDING_MODEL_PATH hint had a stale GTE default, although the
current encoder factory ignores that setting in favor of the versioned profile.
It now defaults empty; legacy revision hint is no longer unconditionally main.
The dev seeder had an operational GTE override that conflicted with Granite's
namespace validation. Empty optional EMBEDDING_MODEL now selects the active
versioned profile in Settings. Explicit overrides remain checked, never silently
converted. No model switch, downloads, reindexing or owner data changes occur here.

HF_HOME=/data/storage/models_cache/huggingface, HF_HUB_CACHE below its hub folder,
and SENTENCE_TRANSFORMERS_HOME=/data/storage/models_cache/sentence_transformers
remain unchanged. Dev binds host data/storage into /data/storage; base uses its
existing storage volume. Resolved snapshot symlinks can point into blobs in that
same shared cache. Moving or renaming weights is not necessary.

Only docker-compose.dev.yml has runtime hint changes. docker-compose.yml still
correctly forwards the chosen profile and revision. dev-setup, acceptance,
storage-rustfs-ci, storage-seaweed-ci and seed-ci do not choose a competing model
or override these cache paths. Compose config plus fresh-process Settings tests
cover GTE, Granite and Harrier without loading any model. This is config and
boundary evidence, not an owner-machine restart or live semantic-quality claim.
