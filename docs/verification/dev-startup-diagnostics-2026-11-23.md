# Development reload diagnostics

Observed user checks: two HTTP failures fell within reload-to-startup-complete intervals, around 103 and 107 seconds. Following startup, root and health returned 200 in milliseconds. This strongly supports reload/startup wait for these episodes, not proof of every future timeout's cause. Total startup includes imports, dependency setup, model loading and embedding warmup; it is not a measurement of embedding inference alone.

Dev uvicorn uses one serving child with --reload. The probe executes as a separate process with a fresh SQL pool. Its successful SQL queries cannot establish HTTP process readiness. The model load is submitted to an executor, but lifespan awaits its completion before serving begins.

Development-only process-bound lifecycle markers now record starting, ready and stopping under /tmp. Markers contain PID, Linux process start identity and fixed state only. Dead processes and reused PIDs are ignored. The probe reports before/after lifecycle state and calls an HTTP error still-starting only when a matching live process reports starting. Missing markers remain unknown, never inferred from a timeout. Import failures before marker initialization, a process stuck after readiness, shutdown windows, and shared-resource contention can still produce unknown outcomes. Diagnostic writes are best-effort and disabled outside development. Markers are not an authenticated health API or production readiness authority.

After this checkpoint's first pull, the old process cannot create the new marker until it reloads, so the very first transition can still report unavailable. Later reloads provide the marker early in app import. Wait for startup completion and rerun, do not disable warmup.

An optional `docker-compose.acceptance.yml` final override preserves dev configuration but omits reload for a deliberate acceptance session. It is not enabled by default and has not been applied to the user's stack. Code changes then require an explicit API restart. If the user chooses it, include it after base and dev files and use --no-deps for API-only recreation to avoid the inherited migrator upgrade-head dependency. Keep the same project and env flags. No container recreation is performed by this change.

No production startup/readiness behavior, models, migration or provider configuration is changed. Tests cover real current /proc identity, stale/corrupt markers, disabled production writes, diagnostic I/O failure and timeout labels with and without a starting marker.
