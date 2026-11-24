# Research fact/source identity types

Source indexes now require exact JSON integers, not booleans, numeric strings
or floats that Pydantic could otherwise coerce. Quote/label/statement and target
coverage entries require strings. The existing optional null-statement
normalization remains: null becomes empty so the exact quote is displayed.
No lookup, model, quota, source policy or semantic-review rule changes.

Nine actual answer_product_question boundary tests show malformed extraction
returns are withheld before review even when a positive review is queued. Valid
integer source0 and the existing nullable statement remain accepted. This is
mechanical identity/type evidence, not a proof that a source supports a claim.
