# Catalog overlay/card unknown-price consistency

Removed remaining display coercion in catalog ProductCard. Overlay normalization
now carries explicit unknown/listed status, checked by display and both add
entry points. Existing numeric Product contract is preserved for compatibility;
its fallback numeric field is never presented as listed or made addable when
status is unknown. Genuine listed zero still passes. This does not change cart
or checkout pricing and does not claim all external consumers honor the status.

Local: 91 frontend tests, 12 suites, TypeScript and Next production build pass.
Chrome pixel inspection of actual ProductCard test DOM + compiled app CSS at
390px confirms readable unverified price and disabled add button. Preview uses
mocked image/motion plumbing, not a deployed authenticated catalog.
