# Canonical consent generation boundaries

A delayed shopping-preference extraction now keeps the original consent changed_at
and requires the same generation under the final SQL row lock. Revoking then
re-enabling consent while extraction waits cannot resurrect work started under
the revoked grant. New extraction after re-enable still works. Recall joins the
canonical enabled/current-policy consent row in the same fact query, so a revoke
or policy change after its preliminary check cannot return stale facts.

Three real PostgreSQL race tests cover revoke/re-enable in-flight extraction and
recall revoked/policy-changed between checks. Existing23 preference/consent tests
remain green. No new collection categories, trait inference, feature activation,
training or model/provider call. Self-service export retains access semantics,
not an inference grant. Broader behavior lifecycle unification remains open.
