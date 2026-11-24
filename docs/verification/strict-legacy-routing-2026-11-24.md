# Strict legacy routing callers

Two read-only legacy NLU callers now select the existing strict production model adapter when available: global intent extraction and query optimization. Older injected adapters without the strict method keep their existing generate_response contract. Legacy fallback behavior is retained. No voice/cart callers, inference-selected mutations or model persona policy were changed.

Typed provider/configuration/empty-output failures reach the caller's existing fallback. Native cancellation propagates. Global intent fallback logging now records exception class and fallback flag only, without customer preview, raw exception body or traceback. The safe query optimizer diagnostics remain unchanged.

Tests exercise the actual strict adapter with controlled completion success, provider failure and cancellation; verify input query retention and unchanged old adapter support. This is two migrated callers, not complete strict transport migration, semantic route acceptance or removal of the retained heuristic fallback. No live provider calls or owner actions.
