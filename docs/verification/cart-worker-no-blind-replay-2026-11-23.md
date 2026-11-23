# Do not replay an uncertain cart mutation

Worker generic transient retry previously replayed CartPersistenceError. A write can have committed while its reply was lost, so replaying an add can duplicate quantity. Cart persistence uncertainty now rejects without automatic requeue and best-effort notifies the customer to refresh before retrying. Other transient work keeps its existing bounded retry policy.

Real disposable Redis regression commits a cart write, then deliberately loses its response. The actual AICartService raises its persistence error through the worker wrapper; the stored quantity stays one and no retry publication occurs. Controlled tests cover notification outage and unchanged generic retry. Full local PostgreSQL19/Redis suite748 passed,3 skipped,20 existing warnings. Message wrapper is controlled here, not actual AMQP delivery. Existing CI broker acceptance covers a separate recommendation seam, not this retry test.

This does not supply mutation idempotency or guarantee a notification reaches a disconnected customer. A cart operation may remain unconfirmed, intentionally requiring authoritative refresh. Broker-level redelivery after process loss still needs durable mutation IDs/idempotency. No automatic retry is safer than blindly doubling a possibly committed add.
