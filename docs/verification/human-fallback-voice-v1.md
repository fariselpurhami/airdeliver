# Human fallback and reply voice, bounded acceptance

2026-11-25. Scope: customer-facing failure, withheld, empty and fallback text across the application, plus natural model reply voice. Text first; voice transport is unchanged, only its existing unavailable message changed.

## Inventory and design

A Python AST pass found 258 candidate literals, including logs, exceptions, prompts and historical methods. Manual classification separated customer text from operator diagnostics and dormant code. Files inspected include API auth/users/orders/products/support/memory/health, NLU/opening/research/recommendation/cart/checkout/payment, and web catalog/cart/checkout/orders/tracking/profile/notifications/admin. This is a bounded source audit, not a guarantee that every possible runtime/provider string is covered.

The exact-match customer_status registry preserves historical internal strings and maps only known operational statuses at serialization/publication boundaries. It does not rewrite arbitrary model prose, customer input, nested product descriptions, exception bodies or unknown strings. This matters because two older execution branches use internal status prefixes. No safety branch is changed just to change its display words.

HTTP NeuralCoreResponse and existing recommendation output serializers, plus the NLU publication gateway, use human text. Existing response_kind, confidence, empty products, action, telemetry, failure causes and logs stay intact. Status codes and recovery categories are additive. The registry does not add provider calls or manufacture advice during a provider failure.

## Customer-facing changes

- Removed technical System notice, grounding/schema/router/cognitive narration from known customer statuses. Product research cause remains in logs, while the customer receives a useful next step.
- Natural short no-match voice stays model-written and reviewed. Hard constraints, current-results scope and no-fabricated-product rules are unchanged. Substantive advice keeps its four-phase shape.
- Cart/payment uncertainty remains explicit. No automatic mutation retry or assurance that a payment failed. Removed the unsupported claim that a team was notified. No refund, stock or availability claims were added.
- Account/order/profile/catalog errors and empty states use plain words instead of transmission, warehouse-sync, sector-depleted or integrity jargon. Arbitrary profile exception messages are no longer shown.
- Retry/browse controls are user-driven only. Only known safe status codes get controls. Retry uses the preceding user text, never image data, queued commands or an older status superseded by a newer user message. Unknown codes keep their text but get no retry action. There is no checkout/payment retry control.

## Verification

New coverage checks every exact alias, unknown/non-string/nested data, internal-versus-wire behavior, real NLU publisher envelopes, retained review/empty-card conditions, UI explicit clicks and no calls on render, stale statuses, missing text, images and unknown action categories. Existing cart, payment, owner and evidence tests remain.

Actual component pixels inspected at 390x844 and 1440x1000. Full disposable PostgreSQL19/pgvector suite: 2115 passed,274 skipped (environment-gated). Frontend:35suites,193tests; TypeScript no-emit passed. Exact-head CI receipts are reported with the PR. No real provider, merchant, payment, carrier or owner-stack calls were made. No cap was raised, migration activated or held PR merged. Human live-model tone acceptance remains unverified without an approved bounded provider evaluation.
