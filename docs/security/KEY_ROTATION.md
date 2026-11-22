# Key Rotation & Secrets Remediation Runbook

Committed secrets were found in the repository history (`.env`, `apps/api/.env`,
`apps/web/.env.local`, `secrets/*`). Treat every value in those files as compromised.

## Step 1 - Rotate every key at its provider (do these FIRST)

| Provider | Keys to rotate | Where |
|---|---|---|
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, publishable key if desired | dashboard.stripe.com -> Developers -> API keys (roll key); Webhooks -> re-sign secret |
| Groq | `GROQ_API_KEY` | console.groq.com -> API Keys -> revoke + create |
| ElevenLabs | `ELEVENLABS_API_KEY` (agent ID is not secret but review) | elevenlabs.io -> Profile -> API Keys |
| Tavily | `TAVILY_API_KEY` | app.tavily.com -> API Keys |
| Hugging Face | `HF_TOKEN` | huggingface.co -> Settings -> Access Tokens |
| M-Pesa (Safaricom) | `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY` | developer.safaricom.et/.ke -> app credentials |
| PayPal | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | developer.paypal.com -> Apps & Credentials |
| Ngrok | `NGROK_AUTHTOKEN` | dashboard.ngrok.com -> Your Authtoken |
| App JWT secrets | `SECRET_KEY`, `REFRESH_SECRET_KEY`, `INTERNAL_API_TOKEN`, `NEXTAUTH_SECRET`, `AUTH_SECRET` | generate new random 32+ char strings locally (invalidates all sessions - expected) |
| PostgreSQL | `POSTGRES_PASSWORD`, superuser `FIRST_SUPERUSER_PASSWORD` | change role password / redeploy with new secret |
| RabbitMQ | `RABBITMQ_PASS`, `RABBITMQ_COOKIE` | change user password / redeploy |
| OpenSearch | `OPENSEARCH_PASS`, `OPENSEARCH_ADMIN_PASSWORD` | security plugin / redeploy |
| MinIO | `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | minio console / redeploy |
| Redis | `REDIS_PASSWORD` | redeploy |
| Grafana / Traefik | `GRAFANA_PASSWORD`, `TRAEFIK_DASHBOARD_PASS_HASH` | redeploy with new values |
| VAPID | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | regenerate pair (`npx web-push generate-vapid-keys`); note: existing push subscriptions break |

## Step 2 - Verify git no longer tracks secret files

```
git rm --cached .env apps/api/.env apps/web/.env.local
git rm -r --cached secrets/
```

(the repo's `.gitignore` now ignores `.env`, `.env.*` except `*.example`, and `secrets/`)

## Step 3 - Purge from history (coordinate before running - rewrites history)

Use git-filter-repo (preferred over filter-branch):

```
pip install git-filter-repo
git clone --mirror <repo-url> airdeliver-mirror
cd airdeliver-mirror
git filter-repo --invert-paths \
  --path .env \
  --path apps/api/.env \
  --path apps/web/.env.local \
  --path secrets
# then force-push the rewritten mirror back and have every clone re-clone:
git push --force --all
git push --force --tags
```

After a force-push: everyone (including Vercel and any servers) must re-clone or
`git fetch --all && git reset --hard origin/main`. Open PRs/branches based on old
history must be rebased.

Note: GitHub caches PR/commit views; contact GitHub Support to scrub cached views
if the repo ever held production secrets (it did). Rotation (Step 1) is what actually
protects you - the purge only stops casual browsing of history.
