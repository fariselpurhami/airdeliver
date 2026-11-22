# Product consultation policy/data boundary

## Reconnaissance and invariant

Backend AI orchestrator, Python3.13, existing Groq SDK and bounded completion
wrapper. Public consult_on_product/history signatures, provider admission/retry/
token budgets, product consultation feature, style instructions and response
string preserved. No model/prompt-name/retrieval embedding change, reseed,
retention change, file/feature deletion or paid-provider request.

Confirmed defect: sanitized conversational history admitted system roles;
consult_on_product interpolated product fields, customer question and fetched
web excerpts into the system message. Those sources are data, not policy.
On provider failure, fallback claimed immediate dispatch and quality without
inventory/shipping evidence. Four new regressions failed before the change.

Invariant: server policy alone occupies system messages. History allows only
user/assistant turns, malformed entries ignored. Product/web/customer inputs
are bounded serialized user data with explicit untrusted-reference treatment;
web excerpts cannot establish this store's availability/price/policies. Advisor
feature/style and catalog search logic retained. Failure reports inability to
assess and catalog identity/category without inventing dispatch/compatibility.

Alternative was textual delimiters inside a system message only. Structural
role separation is stronger and directly testable, but is NOT an injection-proof
barrier for an LLM. A paid/model behavior evaluation would require approval.

## Verification and gates

Baseline677pass2skip. New first4tests4fail before changes. After five new tests,
full682pass2skip20existing warnings, including migrated PostgreSQL19 and actual
Redis7 tests inherited from prior checkpoint. Added role/malformed-history/
external-marker/system-message and failure-claim tests. Actual installed Groq
SDK sends an HTTP request to a local loopback server; captured wire JSON proves
message role layout and parsed answer. This is not a real Groq/model inference
or semantic/jailbreak evaluation. No external API call or spend.
Compileall and diff checks before checkpoint; backend lint/typechecker NOT RUN,
not installed/configured. Browser/a11y modules N/A, no frontend change.

BE G1 PASS preserved public contracts;G2/G3 N/A no accounting/CAS mutation;
G4 PASS structural role isolation for this method only, broad injection/security
posture not certified;G5 existing byte/token/deadline/provider controls retained;
G6 executed tests/compile PASS,lint/typecheck NOT RUN;G7 existing error telemetry,
no data lifecycle change;G8 PASS scoped evidence. BE traps1/2/3/4/5 N/A;
6 PASS no new cancellation/lease/network semantics;7 PASS no eager clients;
8 PASS export parity/data bounds, broader privacy audit remains.

Verdict READINESS_BLOCKED for the platform, not production qualification.
Other generation paths interpolate untrusted context and need the same audit;
unvalidated generated factual claims still require grounding. Existing
consultation web search provider behavior is unchanged, not run externally.
Rollback code only. No database migration or cache reset required.
