# Paid-scale engineering target

The design target is hundreds of thousands to millions of registered users on verified paid provider capacity. Registered users are not simultaneous requests. A published250KTPM plan is a starting profile, never a claim it serves that population. Scale planning needs measured active concurrency, actual complete-chain usage, response latency, traffic bursts, organization/model quotas and approved cost envelope.

## Non-negotiable invariants

- Preserve synchronous opening/chat foundations, literal evidence, all public cards, independent review and existing per-turn/output caps. No silent downgrade or unreviewed model prose.
- Account activation and paid traffic remain owner-controlled. Safe existing deployment guards stay until verified plan settings are supplied.
- Distributed admission must bound global concurrency, waiting and per-principal activity. A single user must not occupy every active/waiting slot. Waiting is within the current request deadline, not a deferred answer redesign.
- Redis authoritative cross-process state. Paid profile with unavailable/missing Redis fails closed, never falls back to unbounded local traffic.
- Usage reconciliation preserves unknown/failed reservations, uses actual successful numeric usage, and never erases other workers. Provider header values may reduce local allowance or impose cooldown, never silently increase configured capacity.
- Respect Retry-After and existing outer deadlines. No retry storm or retry before provider reset. Cancellation clears queue/leases but unknown charge stays reserved.
- Numeric metering and early80/95percent alerts carry no prompts/customer identifiers. Cost is a configured rate estimate, not billing or spend authorization. Missing input/output breakdown means unknown cost, not zero cost.
- Capacity exhaustion becomes a human, honest, state-preserving response using existing approved operational fallback. No claims an order/payment changed on failed inference.

## Acceptance boundaries

Offline real Redis multi-process-equivalent clients must test concurrent users, same-user floods, bounded FIFO waiting, deadlines/cancellation, backend outage, unknown costs, out-of-order headers, request/day vs request/minute units, configured limits and early alerts. Existing API/full matrix regression required. Actual provider limits and real high-volume throughput/latency/quality remain owner-run acceptance gates; code/tests cannot certify unlimited availability.

Engineering checkpoints:1operating contract;2distributed fairness/admission;3header+usage reconciliation;4metering+alerts;5offline concurrent fault acceptance;6exact-head regression/rollout evidence. No deployment/provider call/subscription has been performed.


## First bounded implementation

Paid profiles now wrap each provider invocation in a shared bounded active/queue gate, preserving deterministic cart/tracking paths. Request principal is carried by ContextVar from both existing budgeted entrypoints; non-conversation internal work shares one conservative principal. Queue is FIFO between admitted principals; same principal overlap is withheld, not allowed to flood the queue. Defaults8active/64queued/2second wait, hard120second lease bound, all explicit engineering starting values and not throughput certification. Crashed leases expire; cancellation removes entries. Paid-without-Redis fails closed. Free deployment guard remains compatible.

This gate is per provider invocation, not a durable full-turn reservation or a fair scheduler across a user's multi-stage chain. Existing shared per-model serialization still limits provider throughput. Neither is hidden as solved scale. Further work must address whole-chain atomic capacity, observed headroom and model-concurrency safety without relaxing review/caps. The opening/chat synchronous contract is unchanged.

64focused real Redis/PostgreSQL and transport/profile/formatter tests pass at this checkpoint, including8distinct concurrent users, same-principal overlap, queue overflow, cancellation/deadline cleanup, outage fail-closed and identity-context propagation. These do not simulate millions of active requests or certify latency.
