# Source research diagnostics

Owner retest at10:21 routed the exact specifications question successfully, but sourceanswerreturnedgenericunknown. Prior code suppressed missingkey andHTTPerrors as emptylists, while quote/review/schemaerrors onlyloggedValueError. It was impossible to infer which stage failed from the screenshot or that log alone. This change does not claim the model does not exist, that a key is missing on the owner's machine, or that a correct source was wrongly rejected.

New safe logs:

* `product_knowledge.lookup cause=missing_key returned=0 accepted=0` before anyHTTP request when credentialabsent.
* `product_knowledge.lookup cause=authentication|rate_limit|provider_server|provider_request status_code=...`, no bodies/keys/URLs/customerquery.
* `product_knowledge.lookup cause=timeout|connection` for transportfailure.
* `product_knowledge.lookup cause=ok|empty_results|source_policy returned=N accepted=N rejected=N` after source URL/textfilter.
* `product_knowledge.sources accepted=N targets=N lookup_failures=N` beforeextraction.
* `product_knowledge.withheld stage=lookup|extraction_provider|extraction_schema|quote_validation|review_provider|review_verdict cause=... error_type=...` for finalwithhold.

User notices now distinguish researchconfiguration/auth/rate/server/request/connect/timeout, noresults, rejectedURL/text, invalidextractionformat, exactquotevalidation and exactmodel/factreview rejection. Noresults explicitlydoesnotmeannonexistentmodel. Credentialdetails remainadministratoronly; novalues everlogged. Partialtargetoutage canstillreturnindividuallysupportedsiblingevidence withmissingtargetsdisclosed. Catalogfallbackunchanged.

Exactquote membership, exact-modelindependentreview, no merchantavailability and sourceattribution remain. No rejectionruleweakened merelybecause a currentmodelname is plausible. Needownerretest/newstageevidence before furtherfixing retrieval/sourceextractionquality.26focusedtests+fullPG19/Redis1424passed24skipped. ActualHTTPtransport exercised throughinprocessfixtures, no externalresearch/modelprovider request. This is diagnostics andhonestfailurecopy, not proof of liveknowledgecoverage.
