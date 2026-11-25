# Provider chain budget audit, open acceptance gate

## Scope and measure

Offline fixtures invoke the actual prompt builders with mocked transport. Numbers below use shared_provider_admission.estimated_tokens plus existing output caps, not a tokenizer or billed usage. Successful provider responses reconcile reservations to actual usage. Requests with unknown outcome retain their reservation. The rolling ledger is shared across workers by model, not a per-message allocation.

| Current evidence fixture | Router | Writer | Independent review | Turn sum | Plus next empty-history router |
|---|---:|---:|---:|---:|---:|
| Empty current results | 3528 | 1246 | 807 | 5581 | 9109 |
| One catalog card, four-phase | 3528 | 3504 | 2448 | 9480 | 13008 |
| Three catalog cards, four-phase | 3528 | 3752 | 2697 | 9977 | 13505 |
| Ten catalog cards, four-phase | 3528 | 4623 | 3568 | 11719 | 15247 |

Fixture customer question is an English headphones search, short empty brief, no history or extra research, with small listed local card facts. Real history, multilingual text, many specs, research or concurrent traffic add cost. These sums do not imply every turn is rejected: prior completed calls can reconcile below their caps before the next reservation. They do prove that individual-request checks alone cannot guarantee a whole-turn plus immediate-follow-up experience within7200.

## Safe reduction in this branch

Remove image, SKU and duplicated seed marker attributes from writer/reviewer model prose evidence only. Their public cards and local validators remain unchanged. All claimable facts, names, category, exact specifications, price/currency/price status, relation, stock/evidence kind and availability qualification remain. Both independent passes receive the same evidence. This is a small reduction, not the main solution.

## Remaining work

- Consolidate repeated task/safety prose into compact equivalent writer and independent reviewer contracts, with an explicit requirement coverage matrix and regression tests. Do not remove independent review or evidence checks.
- Measure representative complete actual chains including research and consented history, plus multi-turn and concurrent reservations. Keep caps and models unchanged unless the owner later chooses otherwise.
- Do not replace synchronous foundations with delayed/priority flow or deterministic product prose. Do not shrink the ten-card opening contract.
- Do not call unclassified400 solved. Safe structural error shape and exact output shape need an owner-run reproduction; no live provider call is authorized here.
- A whole-turn preflight must not simply reject turns whose reserved caps exceed7200, since reconciliation may make the real sequence fit. It needs an honest design and offline failure tests before use.

No production, throughput, quota or provider-adherence certification is made by these fixtures.

## Task-scoped contract pass

The next pass keeps the broad original prompt constants in source and uses versioned mode-specific contracts for non-no-match writer/reviewer calls. Shared evidence requirements are stated once per call; separate reviewer rejection authority remains. Four-phase and human voice requirements are integrated rather than appended as overlapping blocks. No-match keeps its existing compact path. An explicit obligation matrix in test_compact_copy_contracts covers source/injection, exact claims, stock/synthetic, no side effects, hard constraints, privacy/tone, alternatives, task attribution, reply style and exceptions. This tests contract presence, not model understanding.

Same one-card fixture writer2580+review2075=4655, down from5952 before prose projection and contract compaction. Router3528 makes whole turn8183; immediate next router11711. The remaining rolling-budget issue is not closed, and live quality/variety must still be evaluated with owner-approved provider runs. No instruction authorizes a claim that more prompt text alone means stronger behavior.

Local regression detail:166 focused tests passed with actual disposable Redis and migrated PostgreSQL19, including staged HTTP/history, gifts, cart follow-ups, provider errors and logging. Split-file regression second partition1272passed/22skipped. First partition1154passed/6skipped/23failures, all23 log-capture assertions empty; the same provider/router/source logging files passed50/50 separately and in the166 boundary run. This indicates order-dependent logger/test interaction, not a certified clean full run. Exact complete CI remains mandatory; no failing log assertions were removed or weakened.

The log-capture cause was found: Alembic env.py used fileConfig's default disable_existing_loggers=true. In-process migration tests could silence service loggers created before migration. Explicitly preserving existing loggers fixes the production-relevant diagnostic gap, not only the test. The first full-collected partition then passed1180tests/6skips, with1294deselected in the complementary partition; no log assertions changed. Existing second partition1272pass/22skip remains from before this additive logger fix. A regression contract guards the explicit setting. Fresh full exact-head CI is still required.
