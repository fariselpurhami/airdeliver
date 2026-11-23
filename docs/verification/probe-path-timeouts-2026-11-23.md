# Bounded per-path preflight HTTP checks

Probe records HTTP status or exception class per endpoint, elapsed seconds and
continues after timeout without losing prior DB results. Connect timeout 2s,
read timeout 3s, overall endpoint deadline 4s. It never prints exception contents.
A controlled ReadTimeout test proves next-path continuation and retained DB data.
Full local suite 855 passed, 4 skipped. User stack health timeout was observed,
but its root cause is not established; readiness handler reads DB/Redis and
embedding state, not actual model inference or Milvus search. No provider calls.
