# Same-customer product follow-up context, 2026-11-23

## Actual path and changes

Server-side Redis chat history already existed, with a 24-hour TTL and 30-event cap. Intent routing already received it. The search optimizer did not receive it, final history save ran in a background task, and the general product answer placed history/catalog/customer text in the system role.

Additive changes: optimizer receives bounded history for reference resolution; completed answer history is awaited before process_message returns; the existing response-policy sections remain but dynamic catalog/history/question/profile/web content moves to a JSON user message. Static policy says history is data, never instructions, and old assistant claims are not current product evidence.

## Executed

697 passed, 2 skipped, 20 existing warnings on full migrated disposable PostgreSQL 19 suite, including isolated real Redis7 tests.

New integration test runs two actual NLU process_message turns with no frontend-supplied history, a real disposable Redis server, the installed Groq SDK, and a local HTTP responder. First question names Atlas Headphones, second asks about its price. Captured requests prove that the previous product and answer reach intent routing, optimizer and answer generation, and the emitted second carousel retains product id7. Different customer id gets no history. TTL is checked. Dynamic product text is absent from the system messages.

This is an application/transport integration test, not full deployed browser-to-RabbitMQ-to-worker acceptance. The scripted local responder validates context, not learned pronoun resolution or answer quality. Catalog retrieval and user-profile lookup are controlled. No paid provider call occurs. The test fails against the old plain-text request contract, then passes with the structured/context-aware contract. Do not interpret that as a real-model accuracy measurement.

## Remaining

History is keyed by customer id, not independent conversation id: tabs/devices for the same customer share a recent timeline. Persistent customer preference memory is a separate feature under development. Live provider quality, complete browser/websocket transport, and full multi-worker ordering remain unproven. No ruff/mypy run. Whole-platform readiness remains blocked on other acceptance work.
