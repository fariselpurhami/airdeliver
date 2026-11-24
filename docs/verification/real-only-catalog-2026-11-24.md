# Real-only customer catalog surfaces

Synthetic rows are excluded by both known markers, attributes._seed_dataset and ADL-DEMO-v1 SKU prefix. Storefront filters before pagination, suggestions/featured exclude them, support publication drops them, cart add/review and checkout reject them, shared hybrid filtering and NLU/voice publication prevent synthetic cards. Stored catalog rows, saved carts and order history remain unchanged. Existing synthetic cart lines may be removed, but not checked out.

ActualPG test verifies pagination returns a real row despite earlier synthetic rows, and all original rows/markers remain. Existing actual supportHTTP test now verifies synthetic/inactive/deleted rows are withheld while the read-only catalog inspector can still find stored synthetic data. Diagnostic identity serializer remains for history/audit, not synthetic offer admission.

No local-owner deletion executed. Owner-controlled cleanup must use an existing database backup and validated restore first. Prefer quarantine export plus inactive state rather than irreversible delete where order foreign keys/history exist. A reversible owner cleanup procedure is still pending; do not run a blanket delete.

Local complete suite1227passed5skipped, with preexisting actualRedis burst admission test failure only. No assertions weakened. This does not certify every integration surface or owner data cleanup.
