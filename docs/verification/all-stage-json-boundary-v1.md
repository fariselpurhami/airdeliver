# Shared structured return boundary

Every caller of infer_schema now rejects duplicate object keys at any depth,
nonfinite numeric constants, nonobjects, excessive nesting and oversized raw
objects before stage schema parsing. This includes router, writer and independent
review returns from native and injected adapters. Provider strict JSON schema does
not replace runtime validation. Original valid raw text is preserved for the
existing per-stage schema diagnostics. Cancellation still propagates.

Twenty new shared-boundary and actual router/copy tests cover both adapter paths,
duplicate intent overrides, nested duplicates, NaN/Infinity, object bounds, valid
return retention and cancellation. Copy diagnostics distinguish a malformed JSON
return from provider failure. This is syntactic evidence hardening, not semantic
truth, multilingual quality or provider security certification. No new model call,
quota change, reduced independent review, owner restart or Granite action.
