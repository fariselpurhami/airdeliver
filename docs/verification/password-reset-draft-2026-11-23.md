# Password recovery, implementation draft, NOT READY TO MERGE

Owner requested full real Forgot password. Adds request/confirm HTTP endpoints and matching public pages. Random32byte credentials, SHA256 credential hashes,20minute expiry, one-use user/token row locks, supersedes earlier links. Fixed configured HTTPS origin, fragment token removed from address bar by UI. DB-shared HMAC quota keys, IP+email limits, generic accepted response for present/absent/inactive/quotas; validation does not echo secrets. Auth version increment revokes access/refresh and pre-reset socket tickets. NextAuth revalidates backend session. Existing password change also increments version.

SMTP TLS adapter and encrypted durable outbox. Worker is explicit opt-in command, not API background fire-and-forget. Attempts capped5, pending expired payloads scrubbed, sent payloads cleared. Encrypted retry payload derived with domain-separated key from mounted application secret. No console token delivery. External delivery is at-least-once, an SMTP acceptance followed by DB commit failure can duplicate an email, but token redemption remains single-use. Worker checked every60seconds when separately started.

## Gates, not completed

- New migration2c9e410bb712 depends on HELD cart1b8de657a098. No owner migration run. User model auth_version is schema-dependent even with PASSWORD_RESET_ENABLED=false. DO NOT MERGE OR ROLL OUT before deliberate migration plan and approval.
- No public origin/sender/SMTP credentials configured. No real email sent or provider contacted. Need controlled sender domain, SPF/DKIM/DMARC verification and authorized live delivery smoke. Worker deployment/lifecycle not added or activated.
- Cross-process socket revocation checks added to relay and5second voice guard, but complete real multi-process socket lifecycle test is still missing. Do not claim full session invalidation certification.
- NextAuth now checks /users/me each session read, fails closed on transport failure. Review latency, outage UX and load before readiness.
- Account enumeration timings need external adversarial evaluation, fixed350ms floor is not a proof of indistinguishability.
- Retention/cleanup for old hashes/audit/quota rows and operator retry/dead-letter monitoring policy need finishing. No deletes were added.
- Delivery failure user-support path, password-strength policy against current project baseline, send-notification-on-reset choice and security review still open.

## Evidence so far

Disposable migrated PostgreSQL reset boundary tests9passed before later SMTP/refresh cases; full backend latest1016passed4skipped, one Redis load test failed (100success18rate-limited instead of50, admission timeouts). Exact isolated retry2passed. Earlier full checkpoint1011passed4skipped. Do not present failing full run as green.115frontend tests22suites, TypeScript and production build pass. Production-preview390px/desktop reset/request pages inspected, screenshot fixtures only. No live provider/payment/Groq/email call. Existing voice tests extended with user lookup because ticket validation now checks real user version.

This PR is implementation progress, not production-ready delivery. Preserve all gates and finish tests/review before requesting merge.

## Follow-up review

Privacy: request/confirm routes use no-store/no-referrer/noindex; proxy overwrites the internal recovery marker and root layout omits analytics on recovery pages. Actual production-preview headers and absence of analytics scripts checked. Fragment capture uses one-time ref to survive React StrictMode. Focused reset+auth checks23passed before worker refinement below.

Outbox concurrency refinement: worker now locks user before delivery, matching request/reset lock order; worker2 skips a user being delivered, reset waits then invalidates. Individual delivery transactions, not one SMTP batch-wide transaction. Test uses independent real PostgreSQL sessions, blocked fixture sender and concurrent reset; verifies one sender, second worker skip, successful reset with no deadlock. Final fifth failure scrubs encrypted retry payload and records delivery_exhausted. Focused reset HTTP/DB/session14passed after this refinement. SMTP remains a test double; no provider request.

PR19 Motion14 merged separately424741db1a23ef2a3ce3e2bafb3fbc4abc0e2337, post-main frontend+guard green. Reset draftdb08468 frontend+guard green, backend matrix pending at review; this additional worker change needs fresh CI.

Password-change stale-auth race closed: reload the user under user-first row lock, recheck current password, then increment version. A stale already-authenticated request cannot overwrite a password that reset just changed. Hashing/verifying moved off event loop for this endpoint. Real PostgreSQL test proves stale request401 and legitimate subsequent change version2. Current focused reset HTTP/DB/session15passed.

Socket refinement: relay authorization now uses a separate short-lived database session instead of sharing the receive loop's session. Voice watcher fails closed on database errors/timeouts rather than silently dying with the media socket alive. Real loopback WebSocket test with independent real PostgreSQL reset transaction verifies1008 closure within the5second guard interval and lock cleanup. Companion watcher-outage test verifies1011 closure. Still not a multiprocess deployment/load proof; media orchestrator is provider-free fixture.

Local limiter diagnosis: uncommitted plugin experiment using8 instead of32 simultaneous cold Redis connections yields1020passed4skipped for the complete migrated suite. Original32 gives1019passed4skipped and32Redis timeouts. No repository limiter changes and no assertions/timeouts relaxed. This is a lead about cold connection fanout/backpressure, not production throughput proof.
