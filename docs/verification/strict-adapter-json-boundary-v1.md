# Strict completion JSON ambiguity boundary

The retained generate_response_strict JSON-object mode now uses the same bounded
unique-key object decoder as structured stages. Invalid objects, duplicates,
nonfinite constants and excessive raw size are typed StructuredOutputError, not
valid empty preference results. Plain-text mode and the historical non-strict
adapter remain compatible. No old method/body removed, no fallback scheduling,
provider/model/cap changes, new inference stage or owner-machine step.

Nine new actual adapter/preference tests cover duplicate override, nested keys,
NaN/Infinity, arrays/null/size, plain text and non-strict legacy shape retention.
This is syntactic validation, not semantic preference approval or broader trait
collection. Consent gates and narrow shopping categories remain unchanged.
