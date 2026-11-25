# CAP-30: broader consented memory and explicit full reset

shopping-v3 requires a new explicit opt-in. Existing v1/v2 facts remain readable
but cannot authorize expanded learning. The current request always wins. Twenty
supported shopping categories replace the three-category-only contract:18finite
product/shopping vocabularies and current-catalog-supported brand/category values.
At most eight source-validated first-person affirmative facts per turn. Negation,
third-party/quoted/instruction and sensitive-source checks fail closed. No health,
identity, financial situation or free-form personality records are introduced.
The taxonomy is bounded, not universal understanding. Literal extraction gates
remain English-only; multilingual meaning/quality is explicitly unverified.
The existing SQL owner/consent lock and generation protect every commit. No90-day
expiry or arbitrary lifetime fact-count eviction. Recall context remains bounded.

A separate self-only full-reset endpoint/button names saved preferences,
shopping behavior, derived profiles, recent personalized context and shown history.
Account/cart/orders are untouched. Redis generation advances before deletion;
a persistent reset-pending barrier blocks writes/replies until cleanup succeeds.
Bounded erase serialization prevents concurrent reset completion reopening a
barrier. Missing/failed stores return503/incomplete, never full-delete success.
Retry is explicit. New requests after confirmed reset may create fresh short-term
context; old stamped writes cannot. Redis outage fails closed.

Exact Redis owner key inventory:behavior prefix streams/price/seen/active/ghost,
DNA exact/versioned profile, owner-hashed HTTP sessions, retained chat/seen,
canonical freshness set and shown_at. No wildcard can cross owner boundaries.
Legacy Milvus deletion checks all three configured profile memory collections and
known v2 memory collection with integer owner filter, flush and strong read-back.
Tests use a controlled Milvus transport, not a deployed Milvus acceptance claim.
The legacy public vector fact APIs no longer permit unconsented insert/recall;
original implementation remains dormant. No customer traffic path invokes it.
No physical deletion claim is made when vector storage is unavailable.

Behavior learning now requires canonical shopping-v3 consent before native
embedding, queue staging/drain and ghost commit. SQL row lock plus stamped Redis
atomic command script prevent learning-off, off/on and reset races. Existing
histories remain usable when learning is off. Confirmed display recency is not
preference inference, and receives the same reset generation fence. HTTP and
retained chat/DNA/exposure writes are fenced. An erased in-flight personalized
HTTP answer is withheld rather than saved or published. Original methods retained
dormant for source continuity. No held migration/runtime is activated.

Full2312collected backend cases covered on fresh PostgreSQL19/realRedis splits:
768pass2skip,768pass3skip,771pass2skip, with two bootstrap duplicates. Focused
SQL/Redis reset races, mounted owner scope, stale native/queue generation and
partial vector cleanup tests pass. Frontend7cases pass, including uncertain full
cleanup, explicit confirmation, separate learning-off and erase. Mobile430px
controls inspected:readable wrapping, no overflow/overlap. Exact-head CI and
unchanged-main fast-forward remain required. No real provider/model-quality,
owner-machine or live merchant execution was performed. Code20/20 is separate
from whole0/20 and canonical35preserved20partial0lost. No production-ready claim.
