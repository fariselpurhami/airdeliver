# Sanitized provider error metadata, review only

The successor models-list returned NotFoundError/404. Its `not_in_allowlist` label is produced by our sanitizer when SDK error code is absent or not in a fixed set. It is not a Groq account/project/model permission result. A model-specific missing ID cannot alone explain GET /models also returning 404. Underlying routing/account/provider response cause remains unproven.

This branch adds no provider request and does not add a ledger continuation. Existing one-shot command still refuses once the successor file exists. Future error metadata can include response content type from four fixed MIME types and request ID only for constrained req_/greq_ identifier patterns. Everything else becomes unknown/null. No raw body, exception message, request/response headers or credential is printed. This cannot recover bodies discarded by the earlier runs. Missing ID does not prove absence of a provider request. A header ID is useful for support correlation, not trusted identity/authentication.

Tests inject fake responses only. No call, account change or production behavior change. Do not merge or run a new diagnostic until owner approval; request budget remains 2 reserved, 6 remaining.
