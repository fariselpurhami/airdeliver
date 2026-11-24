# Legacy optional cart copy boundary

Both shared_sales_followups flag values now use the existing asynchronous
read-only recommendation event. The flag stays accepted for constructor
compatibility, not as a bypass to unreviewed copy. Original bundle entrypoint
enqueues that same event only. Old bundle implementation remains explicitly
legacy_unreviewed, never selected by cart mutation. Original inline removal-copy
helpers remain source continuity only; live mutation sends operational removal
confirmation and optional event, not raw ranked product copy.

Cart persistence/receipt and operational confirmation semantics stay unchanged.
No model/search runs on the mutation path for either flag. Event failures cannot
undo a saved cart. Optional worker already rechecks cart/currentSQL/complement or
alternative relation, generates structured model copy with independent review,
then rechecks after model work. Existing actualPG/Redis/AMQP tests still apply;
new tests exercise both flag values and original bundle compatibilityentrypoint.
No fixed persuasive fallback. Operational removed/added confirmation is separate
from optional sales text. No providercalls, owneractions, schema/state migration,
feature deletion or livequality claim.
