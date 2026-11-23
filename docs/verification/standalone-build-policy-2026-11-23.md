# Standalone pnpm build policy

The app-local workspace policy had a literal placeholder for @parcel/watcher rather than a boolean. Root workspace already allowed it. Make the app-local policy explicitly true to match the established root configuration; do not ask the owner to interactively approve arbitrary packages.

It is used by Jest's jest-haste-map, not required to boot Next. The previous standalone validation used --ignore-scripts and therefore missed this policy failure. CI now installs normally, without bypassing scripts, in both contexts. Local standalone pnpm12.6 frozen install ran watcher and resolver install scripts successfully, followed by107 tests, TypeScript and production build. No volume deletion, lock bypass, deployment, or owner-machine action.
