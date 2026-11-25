# Existing API maintenance helpers

These are the original maintenance implementations, not automatic startup work.
They can create/reset databases, change catalog/search state, call configured
services or print a password hash. Do not run them during layout verification.
The legacy API-root filenames remain compatibility import/CLI entrypoints.
Canonical CLI form from backend/api: python -m tools.<module>.

Two original file-relative path expressions retain their pre-move meaning.
The create_db_and_tables model-discovery expression had a suspicious parent
before this move. It is deliberately preserved rather than silently repaired.
That behavior needs a separate functional review before operational use.
