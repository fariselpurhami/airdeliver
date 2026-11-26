# Product identity and release-status truth, preparation v1
25 November 2026

## Why the current path is not enough
The active research method validates exact quotes and exact-model coverage, then independently reviews them. This is stronger than model memory, but its normalized source rows contain URL and text only. A stale page can be quoted exactly and still mislead about a release today. No active release-status policy currently separates announcement, planned release, actual release, regional availability and merchant stock.

The old unreviewed methods remain preserved under their explicit legacy names. Their product-reality prose is not a source of truth, and active reviewed wrappers do not call them for final answers. No old file or logic was deleted in this work.

## Required distinctions
- Canonical model and variant identity, including manufacturer, region and edition. Similar names are not interchangeable.
- Catalog presence means only that a local row exists. It does not establish real-world identity or current merchant stock.
- Source-backed announcement is not a release. A future dated schedule is planned, not guaranteed. A passed planned date without actual confirmation remains unconfirmed.
- A recent source fetch is not a recent assertion. Preserve publication/update time and the effective date, with timezone and region. A search snippet's claimed date is untrusted metadata, not verified source dating.
- No results means unverified, never nonexistent, fake, impossible or unreleased. Fiction may be explored as fiction only when the premise is explicitly hypothetical or supported by evidence, not guessed from an unfamiliar name.
- Manufacturer identity binding must come from a verified publisher registry or approved canonical source, not a page's self-description, a familiar hostname substring or a model verdict.
- Conflicting current official sources remain conflicting unless an explicit, verified supersession relation settles them. Never silently choose whichever search result ranks first.
- Release truth is distinct from preorder, shipping date, buyable region, seller availability and warehouse quantity.

## Added offline preparation contract
`product_status_policy.py` accepts trusted normalized evidence, with exact identity, publisher binding, observed/published/effective instants, region and typed assertion. It returns only evidence-bounded states. There is no nonexistent state and it never returns confirmed merchant stock. All18 offline temporal/identity/source tests pass after an initial missing-module red.

This resolver is deliberately not active yet. Its boolean identity/official fields must never be filled directly from source prose or an LLM. A typed model cannot authenticate its own inputs. The sample six-hour freshness window in tests is an explicit test policy, not an accepted production SLA. Old, stable historical evidence needs separate support for historical claims; current launch claims need current confirmation. No Tavily or provider call was made for these tests.

## Integration work still required
1. Preserve raw source identifiers, fetched time, verified publication/update time, redirected canonical URL and region from the source adapter. Do not invent missing dates.
2. Establish publisher identity and exact model binding independently, including official announcements/support pages and explicit linked press materials. Unverified social/review pages can be attributed but cannot establish official status.
3. Extend structured fact extraction with typed status assertions and date/region/source references, exact quote validation, and an independent temporal/status review. Prevent ordinary specification facts from smuggling in global existence or current-release claims.
4. Route launch/existence questions from current semantic intent. No brittle product-name blacklist, no static list of future models, no provider/model knowledge substituted for source evidence.
5. Render replies by question and evidence state: lead with the useful answer or precise uncertainty, dated source-qualified support, what it means for the customer's choice, and one relevant next step. No repeated boilerplate, fictional supply-chain stories, false fraud alarms or forced alternative sale.
6. Test active HTTP/orchestrator research paths with controlled sources: newly released today, yesterday, tomorrow schedule, canceled launch, region mismatch, same-name variants, old page freshly fetched, source disagreement, source outage, fictional user premise and malicious page instructions. Then bounded approved live probes and actual UI renders.

## Example meaning, not an approved fixed template
A failed search can support: no reliable confirmation was found in that search, and the exact model/manufacturer link is the next useful check. It cannot support: this product does not exist or has not launched.

An official scheduled launch can support: the manufacturer lists a planned release on a specific date in a specific region, checked at a stated time. It cannot support: shipping now or guaranteed available tomorrow.

A dated official launch page can support actual release status for its exact model/region. It cannot establish stock at a selected merchant.

## Acceptance still open
No claim of zero hallucinations, superiority over other AI, completed active integration, live research certification or user-approved final answer quality. The owner specifically requires further work beyond the first correct-but-repetitive backpack result. Preserve that bar.

## Exact publisher-host configuration preparation

An inactive `publisher_binding.py` now supplies application-configured exact HTTPS host binding, with no shipped publisher entries. Initial collection failed because the module was absent; the implementation rejects suffix impersonation, URL credentials, alternate ports, wildcard/public-root/IP configuration, control characters, encoded controls and unconfigured sibling hosts. Duplicate configured hosts fail closed. Binding an unrelated page on a known publisher still establishes only publisher origin, never exact product identity, source date, status assertion, or redirected destination. The final fetched URL must be checked independently; no HTTP/redirect is performed by this helper.

This is the registry mechanism, not a verified real-world registry or active status integration. Current normalized source rows preserve locally observed time and retain provider publication metadata only with an explicit unverified label. Verified dates, exact model binding, approved publisher configuration, typed extraction/review and active HTTP/UI acceptance remain open. No provider, Tavily, account or stock access was used.

## Future-effective status correction

Two additional test-first failures showed that the inactive resolver treated a future discontinuation as already discontinued and a future-effective announcement as current. It now returns scheduled_discontinuation for the first and unverified for the second. Differing effective schedules conflict rather than silently choosing a date. This does not activate the resolver or establish source authenticity. It keeps the evidence contract honest before wiring it to answers.

## Trusted metadata to typed status binding, offline integration step

`status_claim_binding.py` now joins a reviewed extracted status to the exact source quote, configured publisher host, trusted exact-model binding, source-adapter region and verified publication/observation times. It never accepts publisher identity, region or publication date from the extracted object. The effective ISO instant must occur verbatim in the exact quote; natural-language date interpretation is deliberately not implemented. The result feeds the existing temporal resolver. Eleven new binding cases plus temporal/publisher cases pass54offline tests, including forged quotes/dates, wrong host/model/region, missing typed source metadata, absent review and freshly fetched old publications.

This remains inactive preparation. The reviewed flag is an internal caller prerequisite, not proof supplied by a source. Trusted source metadata must come from a verified adapter, which is not implemented for real publishers here. A positive model review is not mathematical entailment, and configured origin does not establish assertion meaning by itself. No real registry entry, fetch, Tavily/provider call, semantic launch routing or HTTP/UI status publication has been activated. These tests were added alongside this new adapter, not claimed as a prior failing implementation reproduction.

## Inactive reviewed status pipeline

A test-first missing-module failure preceded `reviewed_product_status.py`, which now connects bounded extraction, exact quote/model/date-source preflight, a separate four-criterion status review and temporal resolution over typed verified sources. Eight new cases cover positive reviewed release, each negative review, forged quote before review, empty-source uncertainty without a model call and cancellation propagation. Combined62 status/publisher/binding cases pass offline. No active route calls this pipeline, and no source fetch or real model/provider call was made. The preflight builds an internal evidence object only for validation; it is not published or treated as a reviewed result before the second stage succeeds. Verified real publisher/date/model adapters and active semantic routing/HTTP/UI remain missing; an internal type/boolean is not source authentication.

## Preflight is separate from review, and invalid clocks fail before inference

Three new regressions failed first: preflight called the reviewed binder before the reviewer, and invalid application clock/age values reached both inference stages before failing. A new validation-only API now returns no evidence and is used for preflight. The reviewed binder is reached only after a positive independent verdict. The application clock is validated before inference. Additional extraction/review outage and shared-deadline cancellation tests confirm no partial draft is returned. Combined69 focused cases pass offline. This refines only the inactive pipeline; no real source adapter, provider call or active path was added.

## Reject malformed adapter metadata before inference

Seven further red cases showed that the dataclass annotation alone did not enforce adapter metadata. Naive observation/publication times, empty region/model sets, duplicate model keys, mutable list identity bindings and non-text content could reach inference or fail with an unrelated exception. Source shape is now validated before either stage. This validates structure only, never source authenticity; verified publisher/date/model extraction remains unimplemented for real pages.145 combined status/binding/publisher/source-evolution cases pass offline. No provider or source fetch was used.

## Request-local publisher configuration snapshot

A further test-first failure showed publisher configuration could change during the independent review await and silently rebind the final evidence to a different publisher. The inactive pipeline now takes a validated independent registry snapshot before inference.225 combined focused tests pass. This is request consistency, not verification of a real publisher registry, and the active product research flow is unchanged.
