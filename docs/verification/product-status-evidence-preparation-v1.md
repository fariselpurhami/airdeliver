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

## Additional unchanged-boundary verification

Eight additional passing cases verify cancellation during review never returns preflight evidence, numeric/string/null verdicts cannot coerce to approval, invalid count/deadline bounds call no inference, and caller source-list replacement across writer await cannot swap the frozen evidence supplied to review. These verify existing fail-closed boundaries rather than claim new product behavior.233 combined focused cases pass offline. Active source adapters/routing remain open.

## Active source URL spelling hardening

Ten red cases showed the existing source URL gate accepted raw controls/whitespace/backslashes, encoded control/backslash sequences and malformed DNS labels. The gate now rejects those ambiguous spellings before source extraction; valid query strings, encoded spaces in paths, punycode labels and explicit443 remain allowed. An actual answer_product_question case verifies malformed links cause zero inference and no source publication. This is active URL-input hardening only, not active release-status integration or SSRF certification. No network fetch/provider was executed. The separate source-evolution receipt was updated, preserving immutable historical manifests.248 combined focused cases are covered by the full selection; the final targeted URL/source-evolution run passes99cases.

## Active-path audit and mounted HTTP rejection matrix

Source audit confirms the alarming historical reality/retention prompt bodies are retained only in legacy_unreviewed methods. Existing AST closure guards reject active calls into those bodies and active reads of their unsafe policy symbols. No deletion or rewrite of preserved foundations was performed. Those source strings are application data, never instructions for this work.

The mounted HTTP/PostgreSQL/Redis research fallback matrix now includes malformed source URL, forged exact quote and negative independent review for comparison/specifications/consultation. It requires no source publication after forgery/rejection, zero catalog fallback after a nonempty-but-rejected extraction, and scoped constraint-preserving fallback for a bad source URL. Local74 companion tests pass;24 HTTP cases skip because no migrated disposable PostgreSQL is configured locally. The new nine HTTP cases require actual disposable-CI execution before being claimed verified. No new migration or active status route was added.

## Publication cannot occur after observation

Two test-first failures showed an impossible metadata ordering could still resolve to released: a claimed source publication later than the time it had already been observed. The inactive adapter now rejects this before inference and the temporal resolver independently filters it. Both clocks being individually recent is insufficient.250 combined offline cases pass. This does not infer release from a date or activate a real source adapter.

## Mounted HTTP matrix CI receipt

Exact head8e631b3d completed all five check classes for push and PR. Seaweed backend logged2917passed3skipped with the disposable migrated PostgreSQL DSN and Redis enabled, so the24-case mounted research matrix was not silently skipped as locally. Nine added cases cover malformed source URLs, forged supporting quotes and negative independent review across comparison/specifications/consultation. Source evidence: https://github.com/fariselpurhami/airdeliver/actions/runs/45733598871/job/139621376667 . These controlled completions prove those active rejection/fallback boundaries, not actual-model product-status truth or release acceptance. Fresh CI is still required after later changes.

## Writer and independent source review receive the same scoped input

A new offline regression failed because source extraction received recent customer-only context and consented preference scope, while its independent reviewer received only the current question, targets and source excerpts. A follow-up such as whether a material suits the previously stated use therefore lacked the same task constraints during review. The existing reviewer now receives the exact same bounded payload as the writer, including the existing intent-only/non-factual scopes. No new data source or preference inference was added and product facts still come only from the quotes.251 focused tests pass;19 PostgreSQL-dependent companion cases skip locally. The mounted research matrix now asserts retained customer context and preference scope reach source review; actual disposable-CI verification is still required. Independent review is not a guarantee of natural-language entailment.

## Evidence-window provenance, without larger model budgets

Four new tests initially failed because packed excerpts did not report their selected input slice and both model passes lacked an explicit omitted-context limit. The unchanged contiguous-window selection now records application-owned character offsets, supplied-input length and truncation. These describe the supplied excerpt only, never a complete original page; incoming similarly named metadata is overwritten. Source text remains an exact substring and the same byte budget applies. Writer and reviewer are told omitted context is not evidence of absence or global release status.255 focused cases pass, including English/Arabic exact-slice and same-payload review checks. The end-to-end fixture was corrected to stay inside the existing6000character acquisition limit, not by relaxing that limit. No network/provider call, model budget change or source completeness claim.

## Exact-snapshot integrity bridge, not automatic metadata verification

A test-first missing-module failure preceded an inactive pinned_status_source bridge. It accepts an application-owned separately reviewed pin: exact final URL, publisher identity, SHA256 of the supplied text, publication instant, region and exact model keys. It rejects changed content/URL, publisher mismatch, malformed digest and metadata before any status inference. The unchanged extraction/independent-review/temporal pipeline can then consume the exact matching snapshot. Thirteen new synthetic cases pass;268 combined focused cases pass.

No real pins ship, no page fetch is performed, and this is not a source-specific metadata verifier. A hash can prove consistency with a pin but cannot establish the pin's correctness. Publication/model/region must still be independently reviewed from primary evidence, and changed pages require new review rather than automatic hash refresh. This is a bounded integrity mechanism for a future reviewed-source workflow, not completion of the missing real-world adapter or active semantic routing. No provider call or runtime activation occurred.

## Real-source shape audit and date-precision preparation

The four-source compatibility audit is recorded in
`product-status-real-source-compatibility-v1.md`, with original HTML metadata
shapes in `product-status-source-shapes-v1.json`. It demonstrates why the
existing synthetic ISO-in-quote path is not yet a real-source adapter.

The new inactive `source_date_precision.py` preserves a supplied publication
value as either a calendar day or an aware instant. It never invents midnight,
a source timezone, a model, market or release assertion. Day-only values with
publisher-style trailing Z remain day-only. Unsupported relative/natural-language
values and unknown offsets fail closed. Source-specific selection and metadata
authentication are still absent; no existing caller uses this parser.

Test-first result: missing-module collection failure, then 27 cases passed.
Two further regressions showed Python normalizes invalid offset minutes; explicit
minute validation fixed both. Final new-file result29pass, combined focused
result297pass. No real source was fed into the model or published as status.

## Original-HTML candidate boundary, still unverified

`source_metadata_candidates.py` parses bounded supplied HTML only, never fetches.
It retains canonical URL candidates without following them, collects explicit
NewsArticle datePublished and meta-name-date values, excludes Organization/Product
and modified-date fallback, preserves ambiguity, and caps input at256KiB, depth16
and32metadata candidates. Invalid date values remain absent. No result is a
VerifiedStatusSource: publisher/model/market/status authentication is still absent.

Test-first missing module, then21pass. Two malformed-Unicode boundary regressions
failed and were fixed; final25newcases,322combinedfocusedpass. Replay against the
four previously captured original HTML snapshots produced the observed source
publication values without inventing instants: Apple two day-only values, Samsung
global aware+09:00instant, Samsung Japan day-only. Sizes117823..233095bytes stayed
inside the existing bound. This replay tests extraction compatibility, not trust,
real-time status, model reasoning or merchant inventory. No source-specific
metadata acceptance policy or production caller has been added.

### Malformed/ambiguous metadata follow-up

Additional original-HTML boundary tests reproduced9failures:3valueless attributes
raised AttributeError,3duplicate JSON fields silently selected the last value,
and3duplicate HTML attributes did the same. The parser now ignores valueless
attributes, ignores tags with duplicate attributes and rejects duplicate-key
JSON objects without publishing partial values.12newcases pass,37candidate-parser
cases total,334combinedfocusedpass. All4captured official HTML replays retain
expected publication values. A deterministic10000malformed-attribute sample had
no uncaught parser errors; this is not a fuzzing or security certification.
Full local backend2470pass/536skip, with unavailable-service skips, not CI parity.

## Active source-link numeric-host and empty-userinfo correction

A source URL audit reproduced12failing cases: abbreviated/octal/hex browser-style
IPv4 spellings passed as DNS names, and explicit empty userinfo passed the active
URL check. The smallest correction rejects all-numeric address-token host labels
and any supplied username/password component, including empty ones. The inactive
publisher host boundary applies the same numeric-host rejection. Ordinary DNS,
numeric sublabels and punycode controls still pass.19newunit cases pass.

The mounted comparison/specification/consultation fallback matrix adds both
numeric-host and empty-userinfo cases across all3tasks. Locally353focusedpass and
30DB/service cases skip; those30require actual disposable PostgreSQL/Redis CI.
Immutable historical manifests are unchanged; the source-evolution receipt records
the active URL maintenance hash. This is a link-identity shape check, not DNS
resolution, redirect validation, SSRF certification or real-provider execution.

## Direct binder boundary audit

Five red direct-entry cases found metadata preflight depended on the reviewed
orchestrator: empty region, duplicate exact-model keys, publication after
observation, oversized text, and a naive observation clock. Four were accepted
by the direct binder; the naive clock failed only later with a different gate.
The public normalizer now invokes the same existing validate_status_source guard
before publisher/quote/date binding.190focused status/source tests pass, preserving
all old rules and inactive status. This does not authenticate source metadata or
supply the still-missing real publisher/date/model/market adapter.
