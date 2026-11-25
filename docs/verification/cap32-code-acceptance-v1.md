# CAP-32: removal recovery code acceptance

Audit found the active code already implements the intended safe lifecycle;
this change expands actual-boundary acceptance rather than inventing another
implementation. No production logic needs replacement for the reviewed scope.

Active chain: confirmed AICartService.handle_remove_from_cart persistence,
optional CartRecommendationEvent with explicit customer reason, WorkerRuntime
_cart_recommendation_observed, current-SQL CartSalesService, shared model writer
and independent review, then current cart and SQL evidence recheck before UI.
The mutation path does not invoke a model or search. Confirmation is operational
copy after persistence, not sales prose. Optional follow-up failure does not
undo a removal, re-add an item, assert a motive or manufacture replacement copy.

The preserved nested removal-copy and heuristic alternative-reason functions
remain unreachable because alternatives is explicitly empty before their
branch. CAP44's AST tripwire guards this. The original bundling and older worker
bodies remain deliberately not traffic-wired. No methods/files were deleted.

Actual PostgreSQL19/Redis/worker publication tests now cover both added and
removed cases for success, candidate price/stock/activity/relation/deletion,
cart changes including re-add during advice, review rejection, offline, timeout
and cancellation. Additional removal-only cases cover cart exclusions, deleted
anchor, changed anchor category/price and changed candidate currency. They
assert no UI suggestion on stale/failed evidence and no cart mutation. Successful
removal propagates only the explicit reason to optional advice. No inference of
financial/personality traits or automatic alternative addition is permitted.

All2153collected cases covered in disposable PostgreSQL19/realRedis splits:
1073passed/3skipped plus1075passed/4skipped, two bootstrap cases duplicated.
77focused actual-boundary/transport/persistence cases pass. This is code
acceptance subject to exact-head CI and merge. Real concern interpretation,
alternative usefulness, final UI pixels and owner runtime remain parked. No
provider calls, owner-machine actions, held migration activation or spending.
