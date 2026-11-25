# Compact reviewed inference, first repair

## Preserved

Synchronous opening/chat execution, all ten opening cards in each active row, strict required row/field identities, array/text bounds, local evidence validation, independent model review and fail-closed publication. No model switch, token-cap increase, automatic provider retry for malformed output, real provider/payment calls or quota claim.

## Changes

- Encode shared opening product evidence once with exact per-row ID references. Conflicting evidence for the same ID fails before inference. All original evidence fields remain present.
- Supply the exact required opening shape, explicitly distinguishing output claim arrays from input card lists. This addresses ambiguity behind missing-required/overlong-array reports without accepting those invalid outputs.
- Remove JSON Schema title annotations only. Descriptions, constraints, required properties and additionalProperties restrictions remain.
- Compact JSON whitespace on shopping writer/reviewer/repair inputs. No evidence facts, question, history or constraints removed.
- Log a safe error-body shape for unclassified errors, limited to known structural booleans and allowlisted code/type values. Never log arbitrary keys, error text, customer text or failed generation.

## Offline evidence

Four rows each retain the same ten products. Shared catalog contains ten rather than forty records. Actual prompt/schema estimator plus unchanged output caps: writer3750 + review1671 =5421 for this fixture. The old repeated-card encoding is over twice the size of the compact evidence input. This is not tokenizer usage or a whole-session quota guarantee. Unique products and larger specs can still exceed available capacity, and concurrent/prior calls share the same rolling ledger.

Focused suite60passed/1environment skip. Full fresh disposable PostgreSQL19/pgvector:2121passed/274skipped. Tests reject missing required output keys, eleven claims, duplicate keys, conflicting IDs, ungrounded claims and negative review. Both writer and independent reviewer see the same evidence snapshot.

## Still unverified

No live generation was run. Provider adherence to the clearer exact shape and unclassified400 cause remain unverified. Existing safe diagnostics must be used on an owner-run reproduction after merge. This patch reduces overhead but does not establish that router + research + shopping + review + immediate next router all fit a single rolling7200 window. No whole-platform production certification.
