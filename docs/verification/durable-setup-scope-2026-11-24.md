# Durable reviewed setup scope

Reviewed literal setup component requirements now persist separately in owner-bound session memory, with three-component/eight-feature and string-length limits. A later setup plan that omits assignments cannot silently reapply a component's feature globally or forget it. New assignments union prior ones. A component identity change or over-bound union withholds publication rather than dropping scope. The existing literal independently reviewed explicit constraint replacement clears both shared and scoped constraints. Ordinary additional requests do not clear either.

Stored scope is previously reviewed state, not fresh model authority. It is not reclassified as source facts, saved preferences or compatibility evidence. Different owner/session isolation and deferred publication retain their existing behavior. Anonymous sessions retain the existing caller-controlled session boundary, not a stronger identity guarantee. Per-component exclusions and non-setup multi-target scope remain separate.

Tests include serialized memory into a new service instance, actual two-turn HTTP/PostgreSQL/Redis where the second planner omits scope, mismatching component identity withholding, and explicit replacement versus addition preserving/clearing stored scope. No provider calls, deployed verification or owner-machine actions.
