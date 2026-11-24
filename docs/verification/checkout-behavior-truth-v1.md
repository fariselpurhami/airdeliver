# Checkout event is not completed purchase

The original worker confirm-order handler now emits the existing checkout action
for checkout initiation, not buy. Actual completed conversion handler keeps buy.
This preserves action breadth and weights without telling behavioral history that
a failed/unpaid checkout was a completed purchase. No checkout/cart/payment logic,
new collection, model, inference, consent or event transport is added.

Two actual handler tests cover downstream checkout success/failure. Both assert
only checkout signal while the original checkout call and failure propagation
remain. Existing conversion test still asserts buy only on conversion. This is
telemetry meaning, not proof of payment completion or behavior lifecycle closure.
