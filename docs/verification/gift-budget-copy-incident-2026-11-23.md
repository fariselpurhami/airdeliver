# Gift budget/copy incident regression

November 23, 2026. Owner reported that a recipient-only gift request clarified successfully, but an explicit jewelry / birthday / 1000 dollar follow-up returned the generic grounded-copy notice. Owner logs on PR35 show router HTTP200, route, writer HTTP200, then neural_core.shopping.copy_withheld. No reviewer request appears. This narrows the live failure to writer schema or evidence validation; it does not establish the exact rule.

## Definite source defects repaired

- Literal English dollar/dollars/US dollars was not accepted as explicit USD currency evidence; only USD and $ were. The router instructions had the same gap.
- The independent numeric validator treated customer budget numerals in prose as product-field claims. A natural reference to a 1000 dollar budget could fail even when the card evidence was valid.
- Failure logging used arbitrary extras which the configured formatter discards. The shared boundary now logs safe stage/reason/candidate-count/mode/intent as formatted scalar message text. Stages distinguish writer provider/schema/evidence and reviewer provider/schema/verdict. Private provider messages, prompts and prose are never included.

Budget allowance is narrow: the grounded cap must appear in a budget-labelled phrase. It does not authorize a product price, spec, different number or currency conversion. Existing field/reviewer gates remain. Empty eligible results are explicitly handled as a normal model-written no-match response within the retrieved results, not a promise of invented alternatives or global unavailability.

## Verification

1131 passed, 4 skipped against disposable migrated PostgreSQL19 and real Redis, on unchanged rerun after the pre-existing concurrent Redis limiter load test failed in the first full run. No tests weakened. Includes the owner's actual two-turn structure through the real support orchestrator, exact dollar-word grounding, a current eligible jewelry card, over-cap/out-of-stock exclusion, safe budget narration, rejection of product-price/spec misuse, empty-result model response, and failure metadata surviving both configured log formats.

No provider call was made. The precise live PR35 validation reason cannot be recovered retroactively because its logs omitted that data. New diagnostics make any remaining live failure identifiable without exposing model prose. No deployment, migration rollout or owner-machine operation was executed.
