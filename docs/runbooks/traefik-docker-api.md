# Docker provider compatibility

Pinned official Traefik3.7.19 (13November2026), registry manifest digest includes
linux/amd64 for Intel Macs and linux/arm64 for Apple Silicon. This replaces3.0,
whose Docker client pins API1.24. Newer Docker engines reject older APIs;
upstream fixed negotiation in3.6.1.3.7.19 also includes later security updates.
No daemon minimum is lowered, no Docker TCP socket exposed, no API version
forced. Production TLS/redirect/dashboard restrictions remain unchanged.

The user's screenshot proves repeated provider/daemon errors, but the response
reason is blank. Therefore API mismatch is a grounded candidate, not a confirmed
Mac-specific root cause. Obtain `docker version` and
`docker logs airdeliver-reverse-proxy --tail 20` if the problem persists.

After verified merge, from repository root, with existing .env.dev:

```sh
git pull
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev pull reverse-proxy
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up -d --no-deps --force-recreate reverse-proxy
docker logs airdeliver-reverse-proxy --tail 30
```

This restarts only the proxy, no volumes/databases. Docker-provider discovery
and actual HTTP routing are tested in disposable Docker CI; the user's own
Docker Desktop socket/context has not been directly tested. Full application
routes can still fail for app health/network/labels even if provider connects.
A mounted Docker socket is privileged access despite the read-only mount; this
change does not claim socket isolation or a full production proxy audit.

Official sources:
- https://github.com/traefik/traefik/pull/12256
- https://github.com/traefik/traefik/releases/tag/v3.7.19
- https://github.com/traefik/traefik/security/advisories/GHSA-p956-6gvv-mxqp

## Combined-development router labels

Compose merges label lists by label key; a partial API rule override retained
production websecure and letsencrypt settings. Development now uses `!override`
for complete local API/web HTTP labels. Grafana's proxy router is disabled only
in dev. Production TLS, cert resolver, middleware and monitoring auth remain.
The Docker integration now extracts the actual combined Compose labels and
proxy command, and checks separate web `/` and API `/api/v1/health` routes.
Probe backends verify routing, not the full Next.js/API application.
After pull, recreate affected services, not just proxy:

```sh
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up -d --no-deps --force-recreate reverse-proxy api web grafana
```

Open `http://localhost/`. Inspect `http://localhost/api/v1/health` for actual API
health. Do not use HTTPS locally. Mac confirmation remains needed after restart.

## Worker probe is not the API probe

The shared API image probes8000, but the worker runs its own health server on8081.
Compose now overrides the worker probe to `http://localhost:8081/health` for both
production and combined development. This reports infrastructure liveness only.
`http://localhost:8081/ready` reports full worker readiness and can still return
503 for real startup dependencies. Missing real payment gateway configuration
continues to fail fast and restart the worker; the probe fix does not hide it.
