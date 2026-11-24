# Product-query robustness boundaries, revision 1

## Live evidence driving this change

The owner observed main `8db4825`: opening provider completed but the text failed `writer_format`; empty laptop retrieval repeated three hybrid cycles; shopping generation then received a provider TPM rejection. A byte upper-bound in diagnostics is not an actual token count. These observations do not establish a broken keyword index, global inventory absence, or a measured latency guarantee.

## Changed boundaries

- Opening batch returns explicit `introduction` and `insight` strings, not a text field whose delimiter must be guessed. Both must be nonempty single paragraphs. The application joins them with a blank line. Existing identity, evidence, number, synthetic-fixture and independent review gates remain. Safe allowlisted reasons now survive structured logging.
- A limit30 empty search is not repeated with the identical query at limit10. Broad search is retained only when broadening changes the normalized query. SQL sessions remain sequential, candidates stay capped, and all displayed facts still come from fresh SQL rows.
- Empty eligible-card results use a small model-authored no-match writer and independent review. No canned shopping answer replaces the model. Current customer constraints are supplied intact. No general product examples or global stock claims are permitted. Provider failure still produces an operational system notice.
- The router no longer receives its full schema twice. Strict schema stays on the native response-format boundary. Compact semantic rules preserve literal targets, language/spelling tolerance, scope, explicit cart review, gift/setup behavior and hard constraints. Original long instructions remain in source as legacy reference.
- General shopping rules are compacted without removing the independent reviewer or deterministic validator. Stage output caps: router768, shopping640, review256, four-row opening1000 tokens. Complex outputs may be withheld rather than published partially.
- Redis admission coordinates both native API and FreeLLM worker adapters per model: shared request lock, rolling60-second estimated input/output reservations, actual-usage reconciliation, persistent unknown-cost reservations and shared429cooldown. Only random reservation IDs and numeric usage enter Redis. Configured Redis errors fail closed. Without Redis configured, existing local serialization remains, not cross-process coordination.
- Per chat turn, at most6 provider transport admissions and16000 estimated reserved tokens, including optional preference collection. The default shared rolling budget is8000, configurable with `PROVIDER_TPM_BUDGET`. These are protective ceilings, not a promise that six calls or a complete turn can fit within8000TPM.

## Coverage matrix

| Query/failure class | Expected behavior | Actual test boundary |
|---|---|---|
| Empty/unsupported local category | Scoped no-match, model-authored, reviewed, no recommendations | Shared response service, six varied empty queries, transport captures |
| Partial/multi-target/comparison/specs | Keep each target separate; unknown evidence stays unknown | Existing staged PostgreSQL HTTP tests, changed-price and missing-target cases |
| Hard budget/RAM/size/material/exclusions | Missing evidence cannot satisfy a requirement; no silent relaxation | Existing literal constraint, strategy, SQL and setup tests |
| Ambiguous/recipient-only gift | Clarify missing fields, diverse exploratory cards only under owner gift policy | Existing discovery and gift-browse tests |
| Accessories/setup | No unsupported compatibility or complete-system promise | Existing cart advice/setup/publication tests |
| Misspellings, multilingual, indirect needs | Semantic routing, retain literal customer identity | Existing real SDK mocked-transport routing tests |
| Non-product requests | Scope-safe response, no catalog/provider continuation | Existing SDK routing/dispatch tests |
| Injection/untrusted evidence | No authority gained; invalid claims withheld | Existing evidence/claim/privacy tests and strict schema contracts |
| Very long input/output | Contract/reservation/deadline bounds; fail closed, no truncation presented as complete | Oversize reservation, output schema length tests; existing HTTP input validation |
| Quota429/cooldown | No immediate blind burst; shared cooldown and unknown-cost reservation | Real Redis clients and existing real SDK local HTTP429 tests |
| Slow semantic embedding | Keyword starts independently; native gate remains held; bounded semantic timeout | Existing delayed-native encoder tests |
| Invalid writer/reviewer output | Operational notice, no cards or generated unsafe prose | Empty-path invalid references/length/review tests plus existing validators |
| Cross-process concurrency/Redis outage | One shared model request; fail closed on configured Redis failure | Two independent Redis clients, both native adapters, cancellation/outage tests |
| Opening format | Two explicit fields assembled, independent review and fresh publication | Updated batch and real PostgreSQL/Redis publication tests |

## Limits and acceptance still needed

This is not exhaustive language or product comprehension coverage. Controlled model outputs test orchestration and enforcement, not whether a live model interprets every unknown query correctly. The ASCII/UTF-8 reservation calculation is an estimate, not the Groq tokenizer. Provider framing, hidden reasoning and other clients may differ. Shared admission reduces bursts; it cannot guarantee no429, that an arbitrary opening+turn fits8000TPM, or a few-second response. Limits across different model names or processes outside this Redis namespace are not coordinated. Unknown-cost reservations remain until the rolling window expires. Model review is defense in depth, not formal proof of entailment.

No live provider calls or owner-machine execution were used for verification. New caps/prompt changes require owner live opening and representative chat tests after rollout. Real inventory coverage, keyword-index health, external facts, multilingual model quality, CPU performance after Granite cutover, concurrency load, provider availability and production deployment acceptance remain separate checks. Old models/indexes and held migrations are untouched.

## Verification record

Split full-suite run against disposable PostgreSQL19 and Redis: first partition786passed20skipped, second806passed4skipped. The second partition repeats two SQLite compiler setup tests, so the unique full-suite result is1590passed24skipped. Final focused rerun51passed. No external provider/model request made. Earlier interrupted all-in-one runs are not counted as passing runs. Canonical55 live acceptance remains unchanged.
