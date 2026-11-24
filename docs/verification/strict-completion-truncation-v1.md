# Strict completion output-budget truth

The additive strict text/JSON adapter now rejects a provider length finish even
when its returned body is valid JSON or readable text. A complete JSON prefix
can omit later targets or constraints, so syntax alone cannot certify completion.
The original non-strict adapter remains unchanged. Existing strict sales adapter
already enforced this condition and is not weakened or replaced.

Actual adapter tests verify plain/JSON rejection, legacy compatibility, normal
stop success, global-intent safe fallback with no partial target list and query
optimizer retention of the original customer request.29focused tests pass. No
extra inference or review call, provider execution or voice/cart fallback change.
Typed success is still not model semantic or whole-group acceptance.
