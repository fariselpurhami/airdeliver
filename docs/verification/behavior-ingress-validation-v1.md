# Behavior ingress data validation

Existing behavior telemetry accepts only positive integer owner/product IDs,
finite nonnegative prices and bounded finite numeric vectors. Invalid payloads
cannot start history updates or stage packets. Validation logging records error
type, not raw rejected values. Unknown metadata keys remain ignored as before,
so original worker action metadata stays compatible. No new telemetry collection,
consent grant, profile use, training, inference policy or active route is added.

Twenty actual ingress tests cover invalid ownership/IDs, NaN/Infinity, negative
price, nonnumeric/bool/oversized/empty vectors, malformed metadata and valid packet
plus history updates. Existing real tensor/consolidation and worker seam tests
remain. This does not unify behavior consent/lifecycle or certify learned persona
quality. It narrows failure data handling only; broader lifecycle work is open.
