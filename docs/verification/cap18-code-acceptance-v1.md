# CAP-18: long-term saved-memory lifecycle code acceptance

Owner decisions on November 25: memory off stops learning, but saved preferences
remain usable. Erasing preferences is a separate explicit action. Memory is
long-term rather than an automatic 90-day window. Broader behavior collection
and full-personalization erasure are CAP30, not claimed by this group.

shopping-v2 is an explicit long-term opt-in for the existing literal preference
scope. Old v1 grants are readable but cannot authorize new collection. Existing
unexpired records gain long-term storage only on explicit new-policy enable.
No schema migration: the existing nonnullable indexed timestamp uses a documented
9999-12-31 UTC no-automatic-expiry sentinel. Expired old rows are never revived.
The UI states that newly enabled memory is long-term, learning-off still uses
saved facts, and the current erase button erases saved preferences only, not
chat/orders. Broader categories are not silently enabled here. Feature flag
still defaults off. Original SQL lifecycle method bodies retained dormant.

Off and erase both change SQL generation. Pending extraction cannot commit after
either action, or after off then on. Erase updates consent and deletes rows in
one transaction. Recall ignores the learning bit but still joins canonical owner
and accepted policy. Deleted/expired/unknown-policy facts cannot reach current
or retained reply paths. Tests that previously called off to mean erase now
exercise the distinct erase method. Independent learning-off tests prove recall
and no new provider extraction. Current customer text continues to win.

Recent conversation remains bounded (HTTP five turns/one hour, retained NLU
24 hours). Behavior streams/active dimension/seen are bounded with 24-hour TTL,
ghost one hour, DNA five minutes, price history 20 entries with no invented TTL.
These remain distinct caches, not newly granted long-term inferred profiling.
Full reset and pending queue/native generation fences are explicitly CAP30 work.
No whole-group/model-quality/owner-runtime acceptance is earned by code tests.

19 focused real SQL lifecycle cases,23 mounted HTTP/bootstrap cases and six frontend cases pass. All2292 collected backend cases covered on three fresh PostgreSQL19/realRedis runs:762pass2skip,761pass3skip,764pass2skip with two bootstrap duplicates. Two new mounted off-during-reply variants then passed in the focused23 run. Mobile error
preview inspected at 430px: wrapped copy, separate controls, disabled uncertain
mutations, readable no-overflow panel. Full backend and exact-head CI release
receipts are required before merge. No live owner/provider calls were made.
