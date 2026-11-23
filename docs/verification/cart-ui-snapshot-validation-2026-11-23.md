# Validate cart snapshots before UI replacement

A shared strict parser now protects both cart-page HTTP refresh and websocket
cart hydration. It rejects null/boolean/blank/negative/nonfinite prices, duplicate
product lines, invalid IDs/quantities and unknown price status. Listed zero is
retained. Invalid response preserves the current cart; malformed high revisions
cannot advance the UI ordering floor. No new visual layout is introduced.

Local verification: 90 tests across 12 frontend suites, TypeScript noEmit and Next
production build pass. Includes malformed high-revision preservation regression.
No deployment or external provider calls.
