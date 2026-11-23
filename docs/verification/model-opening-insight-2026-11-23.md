# Model opening and Insight restoration

November 23, 2026. Builds on the shared sales boundary and gift-budget incident repair.

## Current path

The existing opening personal/bestseller/trending/deals pools, diversity selection, freshness and staged streaming are retained. Active row prose now calls FreeLLMService.generate_lifestyle_matrix, which uses the shared model writer and independent review. Introduction and Insight are two separately displayed model-written paragraphs. The old lifestyle generator and old row-copy implementation remain explicitly named legacy methods with their characterization tests.

Row labels are selection-pool names, not verified claims about measured sales, trends, discounts, luxury or personal tastes. The model cannot turn those labels into assertions. No customer language is available to this entrypoint yet, so concise English is explicit.

Opening cards are limited to five per row, active positive local inventory, non-demo, known price. Current card snapshots are frozen before model work and compared with fresh PostgreSQL rows before UI publication. Changed facts withhold stale copy/cards. The current shared schema bounds five cards; the old larger row-size configuration is preserved. Local stock is never supplier-stock verification.

Writer/reviewer failure is not replaced with fixed sales prose. Failed rows are withheld; if no row can be generated, a labeled operational notice is sent. Only rows actually streamed are marked seen by default, so model failure does not silently exhaust unseen selections. Legacy candidate-marking logic remains behind an explicit default-off configuration.

Each nonempty row uses up to two model calls, writer and reviewer, within a 12-second total row budget; up to four rows run concurrently, under the existing provider admission control and 75-second matrix deadline. No live model call was made during development. Real account latency, provider spend/limits and bilingual prose quality remain unverified.

## Verification

Actual NLU opening entrypoint, FreeLLMService adapter, disposable PostgreSQL19 current rows, real Redis and UI publication tested. Cases: two-paragraph success, material evidence, price changing during generation, demo-only/empty rows, offline provider, review rejection and malformed one-paragraph output. Existing deadline/transport tests retained. Former editorial/lifestyle tests explicitly characterize the preserved legacy methods rather than stand in for the new path.

No dependency, schema or image changes. No migration rollout, owner-machine execution or provider calls.
