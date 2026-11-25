# Independent provider quota axes

Optional owner-verified limits add RPM, RPD, TPD, input TPM and output TPM to the existing shared total TPM guard. All five settings default to unset. No provider quota, plan, spending or deployment setting is activated by this change. Existing free/developer plan defaults and six-call turn guard remain unchanged.

Settings: `PROVIDER_RPM_BUDGET`, `PROVIDER_RPD_BUDGET`, `PROVIDER_TPD_BUDGET`, `PROVIDER_ITPM_BUDGET`, `PROVIDER_OTPM_BUDGET`. Each configured limit is a positive integer, at most one billion. Never copy a plan name into a numeric quota or infer a limit from response prose. Configure only numbers verified for the actual provider/model/account. The ledger uses the existing model namespace, not a claim of cross-model account aggregation.

A single Redis script checks all enabled dimensions and observed token/request headroom before any reservation debit. Minute and daily windows remain independent. Request counts reserve one per attempt. Input/output amounts are conservative estimates until numeric usage is observed. Failed, cancelled and unknown attempts retain their estimates; known usage reconciles live entries. Reservations are not a billing record or a tokenizer measurement.

Cleanup is bounded to128 expired entries per dimension per attempt. An unresolved backlog denies admission rather than scanning an entire day in one Redis operation. Missing/evicted accumulators with surviving reservations fail closed. Configured axes without a shared ledger fail closed. Redis keys contain numeric usage and opaque request identifiers, never customer prompts or response text.

Observed request headroom remains a distinct counter and is decremented on admission. Later larger response values cannot raise the current observation before expiry. This is conservative local coordination, not proof of authoritative global provider state.

Offline evidence uses real disposable Redis and stubbed provider responses. Tests cover each independent dimension, concurrent callers, atomic rejection, separate expiry windows, cancellation, accumulator eviction, bounded backlog and reconciliation. No real provider calls, payments or migrations were made. Real account limits and high-volume production acceptance remain owner-side checks. Throughput/serialization, external alert delivery and durable billing are separate stages, not closed by this patch.
