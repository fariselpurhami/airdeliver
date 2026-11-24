# Product-only routing contract

Owner anchors: `phonemsg-01M868CYG2NVR12T0VMFP5GJBW`. This is an additive routing-policy and dispatch fix, not a keyword replacement for the model or a claim that every possible product question succeeds.

## Confirmed gap and fix

The existing schema had no out-of-scope intent. Its prompt grouped jokes/general casual conversation into SOCIAL_CHAT and that branch invoked another model writer. A model deciding a question was outside shopping therefore had no typed stop. New `OUT_OF_SCOPE` intent returns a short polite product-only notice without another generation, catalog lookup or action. Ordinary product/order/cart/support paths remain. This operational notice is not fixed product-sales prose.

Routing instructions explicitly preserve dialectal Arabic, English misspellings, mixed-language product questions, indirect needs and product-care/usage consultation. Literal identity constraints remain. A spelling rewrite is not product evidence and retains the existing independent query-rewrite review. No new keyword heuristics claim to understand products or classify user intent. Current unrelated requests must not be rescued by an old product context.

## Offline evidence and limits

`tests/test_product_domain_routing.py` drives the actual native Groq SDK, response parser, current schema/grounding and off-topic `handle_message` dispatch with an in-process HTTP fixture transport. Seven pinned product cases cover colloquialArabic, misspelling, mixedArabicEnglish, indirectneed, careconsultation, comparisonwording and specifications. Three pinned off-topic cases show a typed out-of-scope decision does not call a second model/search or display model-authored unrelated prose. This proves that the application can carry these literal spans and enforce a stop after that decision. It does not prove the live model will choose the right decision.

65 focused tests passed, including existing routercause and characterization tests. No external provider call was made. Actual live model understanding, language quality, source accuracy and the owner's schema-failure retest remain acceptance items. A live multilingual eval must use an independently labelled, versioned dataset with held-out paraphrases and record per-case outcomes, not certify unlimited questions from these controlled responses.
