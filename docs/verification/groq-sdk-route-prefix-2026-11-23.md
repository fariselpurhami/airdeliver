# Groq SDK1.7.0 acceptance route correction

Three owner-run requests failed404. Budget remains3 consumed/5 remaining; no automatic retry or ledger reset. Earlier manual _prepare_url('/models') check used a different relative path from the actual SDK resource. That check was insufficient and the earlier suggestion endpoint construction was correct was wrong.

Installed/locked Groq1.7.0 AsyncModels.list calls _get('/openai/v1/models'). AsyncCompletions.create calls _post('/openai/v1/chat/completions'). BaseClient._prepare_url concatenates base URL raw path with relative raw path. Our acceptance clients incorrectly set base https://api.groq.com/openai/v1, producing /openai/v1/openai/v1/... in actual method calls. A fake httpx transport now captures and asserts exact outgoing URLs for BOTH actual SDK methods, proving the duplicated-prefix failure locally without network or a usable key. Correct base https://api.groq.com yields the documented single-prefix routes.

All three acceptance clients use the corrected origin base. No production service client behavior changed: that client used SDK defaults. No new ledger continuation or request is enabled, and all previous one-shot ledgers remain exclusive. Correct route does not yet prove model access, successful inference or quota. Any fourth real request needs separate confirmation, successor-ledger reconciliation and CI.
