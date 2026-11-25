# Product detail overlay, bounded design acceptance

2026-11-25. The owner approved before/after renders, with a borderless requirement.

## Active view

- Shared by Explore, products and the assistant carousel, with responsive sizing.
- Borderless black glass, anchored close button, readable product-first hierarchy.
- Compact phone view, two-column desktop view, scrollable short-screen content.
- No synthetic 4.8 rating, SKU ornament or made-up description in the active view.
- Catalog rating is shown only when supplied and valid, never for synthetic products.
- Missing prices stay unverified. Synthetic fixtures, inactive and exhausted products cannot submit from this view. The backend remains authoritative for inventory and eligibility.
- Quantity is bounded by available inventory when supplied, at most 99.
- Add uses the existing authenticated API and a mutation UUID. The action disables while pending and after an uncertain or accepted result. HTTP acceptance is explicitly not a confirmed cart update. No automatic retries, local cart mutation or automatic checkout.
- View cart uses the existing route. Ask about this sends only after an explicit click, through the existing assistant store.
- Image credits and licenses are retained with an optional borderless treatment, including expanded credits. Other callers keep their existing treatment.
- Initial close focus, focus loop, Escape and focus restoration are covered. Keyboard focus indicators remain on interactive controls, not decorative card/panel borders.
- The original component and its methods remain dormant in the same file for source continuity.
- Next development indicator is disabled through supported config, not by hiding runtime error UI.

## Verification

- Full frontend suite: 34 suites, 188 tests passed. TypeScript no-emit passed.
- Eight product design tests cover fixture restrictions, request quantity/double clicks, uncertain results, eligibility guards, supplied rating/currency/detail, explicit assistant action, keyboard focus/Escape and product change reset.
- Actual React component rendered with compiled Tailwind CSS at 390x844, 1440x1000 and 320x568. Both standard sizes inspected. Small phone scroll path inspected separately. Cards/panels have no decorative borders.
- This does not claim a real merchant checkout, live provider quality, owner-device browser acceptance, or whole-platform production readiness. No live provider or payment called. No migration or held PR activated.
- Backend CI path filters now include shared product detail/cart wiring and its test. This prevents a UI-only commerce mutation change from skipping the required rustfs/seaweed matrix.
