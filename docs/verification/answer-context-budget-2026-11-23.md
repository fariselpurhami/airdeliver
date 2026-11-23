# Structured answer context budget, 2026-11-23

The generic LLM wrapper sliced every prompt to3000characters. A large product/inquiry followed by history could therefore lose the history/stock metadata and leave invalid JSON, despite correct call-site wiring. Structured conversation envelopes now use the existing14000character context budget, bound depth/list/dict/string sizes, and shrink longest values until valid JSON fits. This preserves shorter late history/availability fields instead of slicing blindly. Plain prompts retain the existing3000character behavior.

Executed:727passed3skipped20existing warnings on full migrated PG19 suite. Two new tests validate long catalog/inquiry bodies cannot silently slice off JSON context and that the actual wrapper sends valid JSON with late history/availability intact in the user role. No paid calls. AMQP test still locally skipped, CI required. This is bounded application input behavior, not a real-model recall/quality guarantee.
