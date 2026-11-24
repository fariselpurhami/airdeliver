# Strict consented preference extraction

The active preference extractor now uses the existing strict model adapter.
A valid empty JSON object remains a valid no-preference result. Provider failure,
blank output, malformed JSON and non-object JSON remain typed failures, not
successful empty extraction. Cancellation propagates. No new provider request,
retry, category, consent bypass, inferred trait or persistence policy is added.

Twelve new tests drive the actual FreeLLM adapter, including real PostgreSQL
collection across sessions with consent off/on, success, empty, failure and
cancellation. Failure/cancel commit no preference; another user remains empty.
Existing consent/dedupe/expiry/revoke/race HTTP and SQL tests retained. This closes
one adapter gap in CAP44/46, not all memory/behavior lifecycle or live acceptance.
No owner-machine action, model download, provider call or Granite change.
