# Opening provider backpressure

Opening now serializes its four writer/reviewer chains instead of launching four chains at once. Retrieval and overall matrix deadline are unchanged. Rate retry honors numeric/date Retry-After and retry-after-ms. When requested reset exceeds remaining caller budget, it does not retry early or extend the deadline. No admission slot is held during backoff.

ActualSQL opening test asserts only one copy chain active and four rows streamed. Controlled provider tests cover429delay/reset beyond deadline, malformed headers, HTTP-date, cancellation and original deadline. No provider calls. Account-wide rate quotas can still prevent copy; this reduces avoidable bursts, not a guarantee of quota availability.

Full suite1231passed5skipped, with known actual Redis admission burst failure only. No assertions weakened. New targeted tests pass.
