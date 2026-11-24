# Opening HTTP outcome and deadline

The modern web client requests opening suggestions through authenticated POST `/ai-ordering/session/suggestions`. The API runs NLU inline and streams UI events through Redis. This path is not the worker's queued WELCOME_INTENT route.

Confirmed code gap: the frontend aborted this request after30seconds, while the backend matrix permits75seconds. False HTTP outcomes were explicitly suppressed as best-effort hydration. Thus an API/connection failure could leave only the static greeting with no explanation. This is a plausible failure mechanism, NOT a diagnosis of the owner's screenshot without current API logs. Worker fixture flags do not prove API fixture flags or code execution.

The opening-only HTTP deadline is now90seconds. Cart/payment deadlines remain30seconds. A failed/aborted opening response shows a neutral operational message explaining uncertain completion, possible late cards and no repeated reopening. No automatic retry, model call, product prose substitute, synthetic card or eligibility bypass was added. A successful HTTP response is still not treated as proof that cards rendered; delivery acknowledgement remains separate work.

Verification:174frontend tests across31suites, TypeScript and production build pass. Added opening/cart timeout coverage and a single-attempt visible failure regression. Actual ChatMessage component was rendered and inspected at390px width; neutral info text wraps legibly without clipping. This isolated render verifies message layout, not the full owner's page or live websocket delivery. No backend/provider/model executed. No owner restart instruction until exact latest-head CI is green and merged.
