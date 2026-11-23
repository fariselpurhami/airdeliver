# Standalone web security lock correction

The repository has a root workspace lock for CI and an app-local lock for the Docker context. The security checkpoint updated only the root. Docker mounts apps/web at /app, so its frozen install correctly refused the stale app-local lock. This correction updates that lock without deleting it, disabling frozen checks, removing volumes, or changing existing entrypoints.

The app-local lock is a pnpm-managed multi-document file that also carries package-manager metadata. It was regenerated with pnpm12.6.0 in an isolated standalone directory, preserving that metadata and its existing overrides. Root lock unchanged. Standalone frozen install, 107 tests/19 suites, TypeScript and production build pass. CI now explicitly repeats the standalone-context frozen install/test/build instead of validating only the root workspace. No owner-machine install/restart executed.

After approval/merge: pull the correction, repeat the previously approved frozen install, stop on error, then apply the web-only recreation and verify the running Next version. No --no-frozen-lockfile, volume deletion or API restart needed.
