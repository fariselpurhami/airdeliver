# CAP-22: cart lifecycle code acceptance

Owner resolved clear semantics on November25: clearing is cart-only on every
path, order cancellation is separate and requires explicit order intent.
Active AICartService clear now compare-and-deletes the current cart snapshot,
then synchronizes current cart state. It never queries/changes pending orders.
This covers authenticated direct endpoint, retained broker/internal/reset path.
Original cancel-pending implementation remains dormant for source continuity.

Retained NLU model CLEAR, exact clear text, internal clear and save commands now
prepare the same owner-bound five-minute snapshot review as current HTTP chat.
They do not publish a mutation merely because a model classified a request.
Negated clear text does not trigger substring interception. Changed/expired/
wrong-owner/already-submitted review fails, consumed-before-effect prevents
uncertain automatic replay. Reviewed save retains its disclosed cancelled Saved
List record behavior and reports cleanup uncertainty honestly. Original NLU
methods are retained dormant with pre_cart_only names. Add/remove exact review
and durable cart tests remain separate evidence; this audit does not activate
the held cart journal migration/runtime. Direct UI clear is an explicit button
command, not model interpretation. Reset's notice now promises no cancellation.

57focused real SQL/Redis lifecycle/persistence cases pass, including owner/race/
replay/uncertain save and old dormant cleanup contracts. New direct clear test
asserts no order SQL access and retained routes keep cart unchanged until review.
All2279collected covered on3fresh PostgreSQL19/realRedis runs757pass2skip,
757pass3skip,760pass2skip with2bootstrap duplicates. Actual language proposal
quality and owner UI/runtime/held migration acceptance remain unverified. Latest
head scan and both storage jobs plus fast-forward required. No live owner calls.
