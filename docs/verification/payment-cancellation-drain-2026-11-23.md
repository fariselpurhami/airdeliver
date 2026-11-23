# Drain gateway tasks on parent cancellation

The orchestrator owns tasks started with create_task. A parent cancellation while awaiting asyncio.wait previously left them running. It now cancels and awaits every started gateway task before propagating cancellation, preserving existing normal deadline behavior.

A controlled async lifecycle test starts two blocking gateways, cancels the parent, and verifies both finalizers finished with no live gateway task left. Full local migrated PostgreSQL19/Redis suite799 passed,4 skipped,20 existing warnings. No provider calls. Cancellation cannot undo a request a remote provider already accepted, nor stop a blocking SDK thread by itself. Existing durable checkout request/lease still governs reconciliation.
