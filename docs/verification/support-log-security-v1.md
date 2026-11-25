# Support endpoint private logging boundary

Support route service logs already minimized customer content, but the HTTP endpoint still attached client-selected session identifiers, cache exception bodies and full provider exceptions/traceback objects to raw LogRecords. A custom JSON formatter dropping those fields is not sufficient if another handler/exporter sees the records.

Remove private session/client key and exception payloads at the log call source. Preserve event names, severity, safe error type, correlation ID, user ID and counts. Existing response shape, rate-limit availability policy, routing, session ownership and customer-facing behavior are unchanged. No keyword behavior replacement, provider request, migration or activation.

Offline tests inspect the entire raw LogRecord, not only the formatter output, for rate-limit failures, blocked requests and hard-fault support response. Other route/error/logging paths remain separate review work.
