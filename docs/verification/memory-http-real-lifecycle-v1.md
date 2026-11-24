# Mounted memory self-service with actual SQL

An actual mounted HTTP lifecycle now covers strict opt-in, post-consent collection,
no-store export, ignored foreign owner selectors, separate owner deletion,
revocation, physical fact removal and re-enable without resurrecting old facts.
Auth is controlled only at its dependency, not replaced inside the service. The
existing19focused route/SQL/consent-generation cases pass together.

This adds no runtime behavior, data migration, policy vocabulary or collection.
Scope remains shopping-v1 preferences. Recent conversation/history, order records
and separately retained behavior caches are not represented as deleted here.
No live deployment, security certification or global privacy closure is claimed.
