# Explicit unknown catalog prices: UI

The carousel and product details now display `Price unverified` for absent,
invalid, negative, nonfinite or explicitly unknown prices, instead of `$0.00`.
A genuine listed zero remains `$0.00`. Unknown-price carousel ADD is disabled;
inspection remains available. No cart/checkout pricing is inferred from this UI.

Verification: 73 Jest tests across 10 suites, TypeScript noEmit and Next production
build passed locally. Component integration tests check disabled ADD and details.
Chrome inspected a rendered real carousel test DOM with compiled application CSS:
unknown price text fits beside disabled ADD; a second listed-zero card shows
$0.00 and enabled ADD. Images are mocked in this preview, not an authenticated
or deployed product page. No production deployment or provider calls.
