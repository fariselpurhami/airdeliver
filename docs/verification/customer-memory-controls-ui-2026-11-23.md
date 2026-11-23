# Customer memory controls UI, 2026-11-23

Added profile controls without removing existing profile features: explanation of opt-in scope/90-day expiry, explicit enable, two-step revoke/erase, server-fetched JSON export in a copyable textarea, refresh and error state. No consent change happens on load. Failure does not invent a successful state, disables new mutations until refresh, and labels any displayed state as last confirmed. Delete copy clearly excludes chat/orders. API paths are self-only, no customer id supplied.

Executed:59frontend tests across8suites, TypeScript check and production Next build. Five new component tests cover explicit enable, second erase confirmation, uncertain outcome refresh gate, JSON export, and initial-load failure. Chrome mobile390 preview inspected for readable scope/retention/error, wrapping controls and no clipping. Preview uses real component DOM/Tailwind, controlled transport. This is not full authenticated profile/browser acceptance or a privacy compliance certification.

No broader categories, personality inference or production activation added. Backend consent/persistence from previous checkpoint is unchanged. No files/features deleted.
