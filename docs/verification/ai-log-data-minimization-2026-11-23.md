# AI log data minimization

Backend-only Python3.13/FastAPI logging patch. Same public methods, responses,
provider/router/memory behavior, retention and customer collection. No files or
features deleted. No dependency/model/retrieval change, spend or migration.
Frontend/browser modules N/A.

Confirmed defect: support session persistence, search/visual failures and route
success logged raw session/name/query/provider errors as structured LogRecord
fields. Background fact extraction logged customer fact_preview and raw provider
exceptions. Default formatter hides extra fields but structured log exporters
can retain them. Three tests inspecting full vars(LogRecord), not only rendered
text, failed before the change.

Invariant: operational events retain operation/intent/error type or fact length,
not raw customer content or provider exception bodies. Replace those targeted
fields with bounded non-content diagnostics. Existing fact storage semantics
unchanged; this does not approve lifelong profiling or fix retention/consent.
Broad log scrubber was not chosen because capture minimization is smaller and
keeps predictable per-event fields. Other modules still require audit.

Verification: baseline682pass2skip; three new tests fail before, full685pass2skip
20existing warnings after on disposable PostgreSQL19/real Redis7 inherited
checks. Tests exercise actual logger records on controlled provider/cache errors,
not a real external provider call; no spend. Compileall/diff before checkpoint.
Linter/typechecker NOT RUN, not installed/configured. External log exporter
configuration and historical log purge NOT RUN, no deletion performed.

BE G1 PASS signatures/contracts unchanged;G2/G3 N/A;G4 PASS targeted capture
minimization, not platform-wide privacy certification;G5 no new resources;
G6 tests/compile PASS,lint/typecheck NOT RUN;G7 targeted diagnostics retained;
G8 PASS scope honesty. BE traps1/2/3/4/5/6 N/A;7 PASS no eager initialization;
8 PASS targeted private-field removal, wider privacy audit pending.
System verdict READINESS_BLOCKED pending remaining privacy/security/live and
memory-consent work. Rollback code only, would revive logged content. Existing
historical logs are not modified by this patch.
