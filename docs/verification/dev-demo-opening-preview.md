# Withdrawn demo-preview behavior

This preview was withdrawn at the owner's request. The flag is no longer supported and cannot enable synthetic opening cards. The historical note below is retained for audit only, not operating instructions. Do not run its commands. No catalog data or history was deleted.

<details><summary>Historical implementation, withdrawn</summary>

# Local demo opening preview

`DEV_DEMO_CATALOG_PREVIEW` defaults to false. It only takes effect when `APP_ENV=development`. Production and staging ignore a true flag. This is a local UI/model-copy test mode, not a merchant catalog or live offer.

Preview keeps `seeded_demo` evidence, `demo` stock status and synthetic-price/stock warnings in the card. The opening row has an explicit demo-preview notice. Existing UI disables adding demo cards to a cart. Model writer/review receives the synthetic-data warning; normal grounding/review still applies and may withhold a row.

Opening pools still prefer unseen eligible rows. Only when every opening pool is empty and history is nonempty, preview performs one bounded repeat without exclusions. It does not clear history. Homepage has a bounded SQL repeat after unseen retrieval is exhausted. Turning preview off restores the normal real-catalog exclusion policy without catalog changes.

From repository root, after pulling the merged version, opt in for the recreate command:

```bash
DEV_DEMO_CATALOG_PREVIEW=true python3 scripts/dev_compose_quiet_volumes.py up -d --no-deps --no-build --force-recreate api api-worker web
```

This preserves the established combined Compose files/project/env selection. It does not run migrations, seeding, storage recreation or model/provider tests. Hard-refresh the chat afterward. The explicit environment assignment applies to this command only; repeat it for later recreates that should retain preview, or set the non-secret flag in the existing development environment file. To turn off, use the same recreate command with `DEV_DEMO_CATALOG_PREVIEW=false`.

The flag does not enable provider credentials or waive model-copy review. Cards may still be withheld on provider/review failure. Four rows are not guaranteed when the underlying eligible pools are empty.

</details>
