# Dashboard payment truth

Additive admin-only no-store payment-metrics API. Server aggregates the full selected paid_at UTC window, not latest100order rows. Currency groups remain separate, no conversion or USD inference. Exact currency code stays visible. Per-order amounts are cast to decimal cents before summing historical float storage; no claim of recovered precision, settlement, net revenue or refunds.

Paid timestamp is authoritative for this report, not created_at or fulfillment status. Future/unpaid/out-of-window rows excluded. Paid records without timestamp are reported as all-time exclusions; invalid/nonfinite/negative/unsupported-large amounts or invalid currency in the window are counted separately. Complete means all eligible SQL rows in that window, not complete provider settlement history. UTC truncation is independent of database session timezone.

Dashboard uses new recorded-payment panel and full-window buckets, preserves original chart and stats API/methods in source for compatibility. No mixed-currency total or hardcoded dollar activity display. Ordering-users-today label states what legacy count actually means and midnight is now UTC. No fake platform ONLINE or live feed claim. Error/stale snapshot and explicit retry visible; no automatic payment retry. Periodic read refresh is60seconds.

Real PostgreSQL test includes151USD orders, EUR separately, unpaid delivered order, missing paid time, old/future payment and invalid currency/negative/NaN/infinity. Admin-only HTTP/no-store/range validation and database timezone checks pass. Full web36suites197tests and TypeScript pass. Two independently collected backend partitions passed1085/1skip and1388/27skips; collection parity shifted after the new file, so do not sum as one unique full-suite count. Exact-head full CI is mandatory.

Actual new component pixels inspected at390mobile and1440desktop with success/two-currency/exclusion and failure/retry states. No horizontal overflow. These are fixture previews, not actual account financial data or complete authenticated browser journey. Full dashboard/browser acceptance remains before release; no provider/payment calls or migration activation.

Grouped amounts and both exclusion counters now use one UNION ALL SQL statement, so one MVCC snapshot covers the complete report without changing the authentication session's isolation. Real PostgreSQL execution and one-query assertion pass.

Full actual dashboard page rendered at390/1440 with fixture admin session/data and decorative WebGL background disabled, not a live authentication integration. Inspected layout, wrapping, currency context and no horizontal overflow. Visual inspection caught animated counters displaying intermediate values; active KPI display now shows exact server values immediately, preserving the old animation method dormant. These fixture pixels supplement, not replace, end-to-end auth/network acceptance.
