# Cart recommendation AMQP acceptance harness, 2026-11-23

Added dedicated disposable RabbitMQ3.13.7 CI service pinned to registry-observed manifest digest e582c0bc7766f3342496d8485efb5a1df782b5ce3886ad017e2eaae442311f69. New AMQP test declares a UUID quorum queue on the actual application exchange/routing key, invokes cart add with the real RabbitMQService publisher, consumes the persistent event, executes the real recommendation worker handler, acknowledges delivery and checks no replayed cart mutation. Catalog and cart persistence are controlled in this seam test; separate tests exercise real PostgreSQL/Redis. No full distributed transaction/cluster durability claim.

Local717passed3skipped20existing warnings: new AMQP test is explicitly skipped because no local RabbitMQ runtime is installed. CI must execute it against the dedicated service before merge; an unexecuted acceptance harness is not a passing acceptance result. No external user broker accessed, no paid provider calls.
