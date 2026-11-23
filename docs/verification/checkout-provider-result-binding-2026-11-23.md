# Bind payment handoff to selected provider

Checkout verifies the orchestrator result's provider matches the frozen preferred provider and the supported Stripe/PayPal checkout set before storing a transaction ID or exposing payment tokens. A mismatched/unknown provider result remains unconfirmed, retaining the same durable request for reconciliation. No fallback to a different payment method is invented.

Three real-ORM contract cases simulate wrong/unsupported provider results and assert no persisted transaction/handoff or UI payment intent. Full local PostgreSQL19/Redis suite785 passed,4 skipped,20 existing warnings. Gateway response is controlled, no real provider calls. This guards an adapter contract; it is not provider authentication or a live payment certification.
