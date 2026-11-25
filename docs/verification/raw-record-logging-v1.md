# S07: application raw-record logging boundary

## Verified reproduction

Synthetic private markers were present in full Python LogRecord dictionaries before the fix, including exception objects/tracebacks, error bodies, customer query/cache-key extras, arbitrary request paths, client command types and rejected voice tickets. This is a raw-record issue even where the configured formatter already omits those fields.

Actual red runs on the pre-fix code: `python -m pytest -q tests/test_raw_route_log_privacy.py` produced 15 failures. `python -m pytest -q tests/test_raw_service_log_privacy.py` against unchanged main 366ce6c5 produced 5 failures. The source guard also failed before the source changes. No real provider calls, model downloads, database writes, payments or voice sessions were used.

## Smallest preserving change

Logging source calls now retain fixed operational stage messages and selected metadata rather than raw exceptions, tracebacks, query/content previews, keys or tickets. The retained StructuredLog legacy entrypoint uses its existing safe metadata boundary. Global HTTP failures record a route template, not an arbitrary request URL path. Errors, retries, gateway failures, socket cleanup and cancellation keep their existing behavior.

Inspected all 20 changed production files with AST comparison after replacing diagnostic statements by placeholders. Their non-diagnostic syntax trees are identical, excluding the fixed router diagnostic reason selection. This is supporting evidence, not a substitute for runtime tests.

Actual focused command: `python -m pytest -q tests/test_raw_logging_source_guard.py tests/test_raw_route_log_privacy.py tests/test_raw_service_log_privacy.py tests/test_ai_log_data_minimization.py tests/test_router_config.py tests/test_response_consumer_integration.py tests/test_paypal_capture_security.py tests/test_paypal_webhook_security.py tests/test_webhook_security.py tests/test_llm_search_log_privacy.py tests/test_logging_config.py tests/test_commerce_safe_diagnostics.py tests/test_payment_orchestrator.py tests/test_payment_completion_seam.py`.

Result: 110 passed, one existing Pydantic configuration warning. Runtime cases include database/cache outages, payment callback retryable status, Redis bridge three retries and propagation, socket auth/setup/listener/receive faults, cancellation propagation, voice ticket rejection and failure cleanup. Voice coverage is logging-only with a controlled orchestrator, not live voice acceptance.

Full exact-head CI and postmerge are pending.

## Limits

The source guard is a tripwire for known unsafe constructs, not general taint analysis. It permits the already-tested quota/error-shape diagnostics and exception class/numeric status metadata. Selected numeric user/order/product IDs, timing, counts and fixed event names remain operational metadata. This is not anonymous telemetry or a zero-PII guarantee. Third-party library logs, access-server/proxy logs, dynamically generated code, infrastructure retention/access policy and real deployed collection need separate review. Historical log copies are unchanged. Removing diagnostic payloads reduces forensic detail; reproduce using synthetic fixtures rather than re-enabling private logging.

Reference mapping: OWASP ASVS logging/data-protection controls and OWASP Logging Cheat Sheet. No certification claimed. Source and run receipts override earlier formatter-only closure language.
