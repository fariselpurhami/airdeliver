# Product-status source compatibility audit

Observed November 26, 2026. Read-only official-source research, not product or UI acceptance.

The current inactive status contract is safe against many unsupported claims, but its successful synthetic cases do not yet demonstrate compatibility with real product releases. Four official pages expose publication dates, effective dates and regions in different forms. No production registry, pin or status routing was activated.

## Evidence

| Official source | Observed shape | Implication |
| --- | --- | --- |
| Apple MacBook Air M5 announcement | Article datePublished is day-only with a trailing Z; dateModified is a separate full instant. The body distinguishes preorder and planned availability. | Do not invent a publication time or treat a schedule as actual release. |
| Apple multi-product availability update | Day-only datePublished, a different dateModified, several model families in the title and body, and relative availability language tied to the article day. | Exact model and effective-date bindings require source-aware evidence. A family mention does not bind every variant. |
| Samsung global Galaxy S26 availability | Full datePublished with +09:00. Its UTC date is the prior day. dateModified precedes datePublished on the current page. Regional availability exceptions remain in a footnote. | Search date and page date are not necessarily contradictory. Modification cannot silently replace publication; global wording is not a promise for each market. |
| Samsung Japan Galaxy S26 announcement | Day-only publication metadata. Japanese body gives a Japan-specific planned date different from the global release page. | Localized parsing and market scope are required. A global date must not overwrite the Japan schedule. |

URLs in the row order above:

- https://www.apple.com/newsroom/2026/03/apple-introduces-the-new-macbook-air-with-m5/
- https://www.apple.com/newsroom/2026/03/macbook-neo-iphone-17e-ipad-air-with-m4-and-more-are-now-available/
- https://news.samsung.com/global/samsung-galaxy-s26-series-and-galaxy-buds4-series-now-available-worldwide
- https://news.samsung.com/jp/galaxy-s26-launch

Original HTML was inspected in addition to fetched readable text. The compact source-shapes.json records observed canonical URLs, raw date metadata and snapshot hashes. Hashes are integrity evidence only. These snapshots are not approved application inputs and are not merchant inventory checks.

## Current code boundaries

1. ExtractedStatus requires an effective ISO instant verbatim in the quoted body. None of the four readable pages supplies an effective release instant in that format. A successful ISO-only synthetic case cannot certify natural-language launch pages.
2. VerifiedStatusSource requires full aware publication instants. Date-only publication cannot honestly be turned into an exact midnight timestamp without adding unsupported precision.
3. The resolver deliberately applies freshness to original publication as well as observation. A newly fetched historical release confirmation therefore stays unverified under a short freshness window. This must remain distinct from evidence that a product never existed or has not launched.
4. A product released in the past, current regional availability, continued manufacturing and merchant stock are different claims. Current code never certifies stock.
5. Empty search/catalog results cannot establish nonexistence. Source text and search-provided metadata cannot authenticate their own publisher, exact model or market.

## Next implementation slice

Keep existing paths unchanged. First add a precision-preserving source adapter boundary whose output remains nonpublishable until source-specific checks bind canonical host, exact model, publication precision, effective date and market. Date-only data needs explicit date/range semantics, not a fabricated instant. Relative terms must resolve against the original article date, never retrieval date. Separate historical release confirmation from current availability freshness. Test representative synthetic source shapes before plugging the adapter into the inactive reviewed path. Production registry entries, active semantic routing and full HTTP/UI acceptance remain separate work.

No model or Tavily requests, spending, migrations or production-data access were used for this audit. The four-source sample is a targeted compatibility check, not broad publisher coverage.
