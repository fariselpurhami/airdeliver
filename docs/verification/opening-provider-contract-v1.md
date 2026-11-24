# Opening copy contract and safe provider diagnostics

Owner logs on 2026-11-24 establish that all four pools passed catalog eligibility (4/10/10/10), but copy did not pass: Personalized failed exact field evidence validation, Bestsellers received a provider BadRequestError, and Trending/Deals exceeded the 12-second writer/review deadline. They do not establish a quota failure, the precise invalid field/value, or the provider's 400 subcode.

## Changes

- The active lifestyle adapter supplies all ten selected cards to both writer and reviewer. Previously it silently supplied five while the upstream opening selection could publish ten.
- Writer instructions now state the exact field names already enforced by the existing validator. No normalization of unverified claims into supported facts was added.
- An OPENING_INSIGHT exact-field failure can trigger one model-authored repair within the original 12-second total deadline. It must pass the same exact-field validator and independent reviewer. Other guard failures remain failures. The existing empty-results numeric repair is preserved.
- The active FreeLLM transport now observes the process/event-loop/model cooldown already used by the other provider path. A 429 with no valid Retry-After creates at least a 60-second cooldown; a valid reset is respected. Waiting callers check again after acquiring their existing concurrency semaphore. Already-in-flight calls are not recalled. This is not cross-worker or organization-wide quota admission.
- Provider failure type, HTTP status, safe model identifier and an allowlisted error code survive the production JSON formatter. Retry attempt/type and bounded quota metadata are visible without exception text, prompt content, raw provider bodies, failed model output or unrestricted headers. Unknown error codes become unclassified.
- Fixture guard failures preserve their safe reason instead of becoming an anonymous ValueError.

The independent reviewer is defense in depth, not mathematical entailment proof. No provider schema fallback, unreviewed product prose, fixed product prose, model switch, larger opening deadline, migration or deployment is included. The exact historical 400 cause cannot be recovered from these logs. New diagnostics make a future owner-run failure more specific; they do not prove it will succeed.

## Verification

Disposable PostgreSQL 19 migrations through repository head and actual Redis: 1520 passed, 24 skipped. Focused diagnostics suite: 7 passed.

The local-HTTP cases use the real Groq SDK with native strict ShoppingDraft and GroundingReview schemas, ten actual serialized catalog cards, one rejected field claim, one repaired draft, and both accepted and rejected independent verdicts. They do not call Groq or evaluate a real model. Cross-instance cooldown tests establish that a second transport does not make a provider request while a long cooldown is active. Production JsonFormatter tests establish that allowlisted subcodes remain visible without raw messages. Live model quality, precise historical request rejection, and UI delivery receipt remain unverified.
