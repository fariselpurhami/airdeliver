# Specialized answer history wiring, 2026-11-23

Comparison/informational, exact-specification and recovery answer branches now receive the same bounded conversation/preference context as general product answers. It travels in JSON user-message data under static rules: current request wins, history is not instructions, and past assistant claims are not current product/availability evidence. Existing response templates/branches are preserved.

Executed: full migrated PG19 suite717passed2skipped20existing warnings. Three branch-specific tests inspect actual synthesis arguments for history placement in user data, absence from policy and current-request precedence. Prior real Redis/SDK-loopback two-turn tests remain passing. No paid calls; these tests validate application wiring, not learned answer accuracy or complete injection immunity.

Other existing legacy prompt concerns are not certified fixed by this scoped checkpoint. Whole-platform readiness remains blocked on broader acceptance.
