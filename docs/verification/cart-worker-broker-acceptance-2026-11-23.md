# Actual broker cart uncertainty acceptance

Adds an executable acceptance test combining the pinned disposable CI RabbitMQ quorum queue and actual Redis. A persistent mutation is delivered through actual aio-pika IncomingMessage to the real worker retry wrapper and cart service. Redis commits the add, then the test loses the response. The wrapper processes the message, emits no retry publication, queue has no returned delivery, and persisted quantity is one.

Local suite748 passed,4 skipped,20 existing warnings. The new AMQP test is intentionally skipped locally because this environment has no disposable broker. Its result is pending CI, not proven by local tests. The existing controlled lost-response and generic retry tests still pass. No provider calls, production broker access or deployment. Does not cover worker process loss before acknowledgement or promise exactly-once mutations.
