# JSON logging and shared limiter joint verification

The public JsonFormatter/setup_logging and main.configure_logging entrypoints remain. Main now calls setup_logging using LOG_FORMAT=json by default, with LOG_FORMAT=text available and APP_LOG_LEVEL configurable. Repeated setup replaces rather than duplicates the root handler.

JSON is serialized with json.dumps. Explicit SecretStr configuration values, Bearer credentials, common credential key/value forms and URL userinfo are redacted. Arbitrary log extras and exception messages/tracebacks are not serialized; exception type is retained. Only validated request_id and correlation_id extras are emitted. This reduces accidental provider-payload leakage and changes diagnostic detail intentionally. It is not a claim that arbitrary free-form personal data in every existing log message is removed, nor that independent Uvicorn/Gunicorn/access handlers are uniformly JSON or scrubbed. Broader callsite and server-log audits remain separate work.

The rate limiter uses the existing Redis service with no paid addition, strict default/decorated HTTP checks, no per-worker fallback on shared backend failure and explicit proxy trust caveats in shared-rate-limit-boundary-2026-11-23.md. No deployment/proxy configuration is changed.

Joint local verification with seventh acceptance runner included:951passed4skipped20warnings. Individual branches also passed full CI before integration. Joint CI must pass before main merge. No production model parameter changed, provider request, deployment, migration, credential change or customer-memory widening.
