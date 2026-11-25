# Account dialog behavior verification

The real profile route continues to call authenticated API endpoints for profile save, password change and paginated order history. No fixture transport or account data is included in runtime code.

## Verified locally

- Fresh disposable PostgreSQL19migrated from empty. Real ASGI HTTP request handling and real database commits for profile fields and password hash replacement.
- Self-profile input forbids privilege, activation, password and email injection. Dedicated current-password verification remains required for password changes.
- Wrong current password401, short new password422, old password rejected after successful replacement. Anonymous self-service requests401.
- Existing database-backed order ownership/detail and paginated history tests passed. Other owners' detail is hidden. Currency preserved and history no-store.
- Frontend tests cover changed-field-only save, cancel, busy/duplicate prevention, save failure, password checks/autocomplete/visibility, order currency/tracking/pagination, error vs empty distinction, named dialogs, focus trap/Escape/return focus.
- Actual components rendered at1440and390pixels for approved before/after previews. Visual fixtures are external to repository and are not production acceptance.

## Limits

Authentication in the persistence test uses a dependency-supplied disposable user, not a real OAuth/session flow. Anonymous refusal is tested without that override. No owner's profile/password/database was changed. No provider/payment service called. Deployment, browser-to-owner-backend acceptance, password-session revocation policy and broader production/load certification are not established by this patch.
