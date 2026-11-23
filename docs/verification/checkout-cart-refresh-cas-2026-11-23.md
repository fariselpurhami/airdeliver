# Checkout price-refresh concurrency

Checkout now uses the required Redis read, distinguishing an outage from an empty cart. Catalog price refresh atomically compares the original pre-validation cart before replacing its prices. If another operation changed the cart, or write confirmation fails, checkout stops with refresh-required, without payment provider calls or a stale replacement preview.

Real disposable Redis regression adds a newer cart during catalog lookup and verifies it survives with no payment call. An outage test verifies the cart is not reported empty. Full PostgreSQL19/Redis local suite739 passed,3 skipped,20 existing warnings. Existing successful stale-price refresh and checkout replay tests also pass. Local AMQP skip is covered by CI, not claimed as local proof.

This extends, but does not complete, the snapshot concurrency boundary. Payment completion cleanup, global UI event ordering, distributed cart revisions, and cross-store atomicity remain separate. Snapshot equality is not an exactly-once event protocol.
