# Repository automation

- dev/: local environment setup, Compose output, read-only volume inventory,
  catalog generation and the existing model download helper.
- ops/: database backup and read-only provider log analysis.
- ci/: exact Python lock inventory and disposable Docker proxy verification.

Historical scripts/<name> commands remain relative symlinks to these owners.
Canonical and historical paths run the same implementation. Model download,
catalog generation and backup helpers are not run as part of layout changes.
Follow the existing owner approval, provider, secret and migration limits.
