# Additive typed model outcome adapter

Existing generate_response remains backward-compatible, including legacy empty-string fallback. New generate_response_strict opts into typed missing-model, empty/invalidJSON and provider failures. It preserves text formatting, token budget and cancellation and does not send the strict flag to the provider. This is a migration seam, not proof every legacy caller has migrated. Ordinary HTTP and shared sales already use strict transport. Raw provider exception bodies/tracebacks removed from the two shared wrapper error logs; exception class remains.

12targeted tests passed with controlled transport. No provider calls. Legacy callers remain a documented partial gap rather than silently changing voice/cart fallbacks.
