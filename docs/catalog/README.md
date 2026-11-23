# AirDeliver reviewed SKU evidence pack, v1.0

## Start here

This is an authoring and review contract, not a fabricated merchant catalog. There are no partner feeds today. Unknown facts stay null. The filled example is synthetic, draft, and permanently rejected by the import eligibility check. Do not turn its synthetic flag off to make a real catalog.

Files:
- sku-enrichment.schema.json: machine-readable JSON Schema.
- sku-enrichment.synthetic.json: filled illustrative row, not importable.
- sku_enrichment.py: strict runtime validator and pure dry-run merge planner.
- plan_sku_enrichment.py: CLI validation or read-only current-database plan, no write mode.

## Evidence and review workflow

1. Identify exact catalog SKU. Do not use product name similarity as identity.
2. Record real source type, URL, title, capture time with timezone, section/page locator, supporting excerpt, content SHA256 and permission/license basis. A hash records bytes; it does not prove a claim is true. The validator never fetches source URLs.
3. Add only facts that source supports: material, style, use, size system/available sizes/fit notes, authoritative description, compatibility, rating value plus count. Ratings use a five-point scale. Leave unknown sections null or lists empty.
4. For every claim link evidence_ids to the row's evidence records. For every relation record exact target SKU, direction, scope and supporting evidence. Compatibility is not inferred from complement status.
5. A human checks factual support, SKU match, currentness and permission, then records reviewer, timezone-aware reviewed_at and approved status. Product and relation reviews are independent. Schema-valid does not mean human-verified.
6. Validate first. Only nonsynthetic, approved rows and approved relations qualify for a dry-run import plan. Unknown source/target SKUs and conflicting existing attributes are rejected.
7. Inspect dry-run output and hash. It says writes=0. Applying changes is not implemented or authorized by this pack. A future apply must use a separately reviewed transaction/CAS plan and fresh current-state validation.

## Running inside apps/api

Use the repository's existing Python environment:

    python -m scripts.plan_sku_enrichment ../../docs/catalog/sku-enrichment.synthetic.json --schema-only

That proves authoring shape only. Running the same synthetic file without --schema-only must reject it.

For a real reviewed manifest:

    python -m scripts.plan_sku_enrichment /path/to/reviewed.json --validate-only
    python -m scripts.plan_sku_enrichment /path/to/reviewed.json

The second command reads current SKU/attributes in a READ ONLY transaction with statement/lock timeouts and returns a merge plan, never a write. Maximum file size8MiB,10000 source rows,20000 referenced SKUs. Do not send credentials in a manifest.

## Relationship contract

On candidate B, a complement relation targeting SKU A means B is a complement FOR anchor A. A future approved import would encode A in B.attributes.complement_for_skus as a JSON string list, matching the existing conservative complement gate. There is no inferred inverse, transitivity or semantic matching. Alternative and compatibility evidence are retained in enrichment_v1, but no new alternative/compatibility runtime policy is silently enabled. Existing unrelated attributes are preserved, conflicting values require explicit review.

## How this feeds rich factual cards

The proposed recommendation-copy gate derives auditable clauses from current catalog fields: explicit listed prices, bounded ratings, current-set price/rating comparisons and exact supplied material/style/use. A verified anchor is required for reference deltas. Attribute statements are labeled as catalog claims, not independently certified facts. Description, size/fit and compatibility are not parsed into inferred prose. Before any real data apply, reviewer evidence and conflict rules must be enforced; existing catalog fields are not automatically authenticated by this pack.

## Human-labeled quality evaluation plan

Build at least60 reviewed cases before calling quality proven:20 removal alternatives,20 complementary-addition cases and20 sparse/conflicting/multicurrency/adversarial cases. Split by SKU family so holdout products never leak into prompt tuning. Each case includes exact catalog snapshot/hash, explicit user need, anchor if relevant, allowed IDs, prohibited IDs, source-backed fact assertions, expected abstention and two independent reviewer labels with disagreement resolution.

Report separate metrics: factual-claim precision (target no unsupported claims in accepted output), selected-ID validity, relation-evidence precision, request relevance graded0-4, diversity without constraint violation, useful detail graded0-4, readability/RTL layout and abstention correctness. Never roll safety failures into an average style score. Keep baseline and post-change outputs, commands and failure examples. Synthetic tests prove contracts, not merchant truth or user preference fit.

## Verification and limits

Full local965passed4skipped20warnings at pack preparation. Unit tests cover shape, duplicate keys/SKUs, missing evidence, unreviewed/synthetic rejection, unknown SKUs, direction, conflict rejection, nonmutation and file bounds. Real database read-only CLI path has not yet been executed against the owner's live catalog. No provider calls, database writes, source fetching, migrations or deployment performed. This pack is a candidate contract pending CI and parent review, not production qualification.
