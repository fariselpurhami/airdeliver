# Shared HTTP limiter boundary

Public `limiter` remains the same decorated-route entry point. `USE_REDIS=true` selects the existing credential-escaped CoreSettings Redis URL and a dedicated `airdeliver:http` key prefix. There is no additional service or paid dependency. `USE_REDIS=false` explicitly retains memory mode, suitable for tests/single-process development, not shared quotas.

SlowAPI ASGI middleware now enforces the existing100/minute default on undecorated HTTP endpoints. Existing auth/users/ordering decorators retain their stricter limits. Root health is exempt so orchestration probes do not consume quota or fail on Redis outage. WebSocket message controls remain their separate existing implementation, unchanged. Redis failures return503 with Retry-After1, not a false successful admission or silently divided per-worker quota. Socket connect/read timeout0.25seconds bounds each backend operation; this installed SlowAPI library uses synchronous storage, so Redis stall impact is bounded per operation but is not a fully async distributed admission system.

## Proxy trust contract

The key uses ASGI request.client only. It never reads X-Forwarded-For, Forwarded or X-Real-IP. The ASGI server, not arbitrary HTTP clients, owns proxy-header validation. Uvicorn/Gunicorn's FORWARDED_ALLOW_IPS must be restricted to known immediate proxy IPs/networks and direct API access blocked in deployment. Never use wildcard trust. This patch does not guess Docker subnet/proxy addresses or broaden trust. Until the actual proxy topology is verified, multiple real clients may share a proxy quota. The local tests prove spoofed headers cannot change the key when they reach the app directly, not that a deployed upstream is configured correctly.

## Verification

Full local942passed4skipped20warnings. Actual disposable Redis tests prove independent limiter instances share quota, client isolation, expiry recovery, backend outage503 on decorated and default paths, and health availability. Memory HTTP tests prove default429, existing decorated429 and exemption. No deployment, credential change, migration or provider call.
