# Display recency and behavior history boundary

Successfully published legacy search cards now update the existing opening
freshness repository, not only a parallel legacy seen set. Search publication is
required before scheduling seen writes; an unconfirmed UI send cannot mark cards
as displayed. Existing legacy set still dual-writes validated IDs for compatibility.
Opening/search canonical sorted timestamps now prune expired entries and have a
retentionTTL at least the configured cooldown, preventing unbounded retainedIDs.

BehaviorEngine exposes a narrow record_product_exposure method: shared recency
plus existing behavior seenIDs, with no vector embedding, price inference,
financialtier/persona, neural training or preference writes. NLU uses it only
after successful display; missing/failed optional behavior adapter falls back to
canonical recency. Existing track_interaction path remains separate. Do not union
old behavior events into display recency: cart/discard/buy events are not proof a
card was shown, and oldsets lack eventtimestamps. No migration/backfill/deletion.
No broad new implicitmemory/profile recording was enabled to claim parity.

ActualRedis tests cover search/opening sharedrecency, ownerisolation, positiveint
IDs only, legacyreader compatibility, sortedset pruning/TTL, behavior exposure
without register/track calls. Existing cooldown tests preserve historicalset while
reopening eligible products after cooldown. RequiredUIpublication gets a transport
capture update; full productionSDK+SQL pipeline coverage is separately pending in
PR119. This is scoped displayhistory unification, not a complete learnedbehavior
or consentlifecycle certification. Realprofilequality and liveacceptance remain.
