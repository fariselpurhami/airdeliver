# Answer availability metadata, 2026-11-23

Specialized prompts previously labeled every returned product confirmed in-stock and asked the specs answer to confirm availability without supplying stock/price metadata. Added explicit catalog-availability records to general and specialized answer inputs, with active+positive known integer stock required for available_in_catalog, zero/inactive unavailable, missing/invalid status not_verified. ProductAccess.get preserves the difference between absent stock and zero; normalized dump alone defaults missing inventory to0 and omits activity for mappings.

Removed no branch or template. Strengthened active prompt wording to avoid treating catalog presence as availability, delivery or dispatch evidence. Exact-spec path now receives listed price/currency/activity/stock and no longer forces in-stock wording.

Local725passed3skipped20existing warnings, full migrated PG19 suite. Eight new controlled tests cover status truth and exact-spec payload. New AMQP acceptance remains locally skipped and awaits CI. This is prompt/input grounding, not verified generated-answer correctness, live stock reservation or complete prompt cleanup. Existing product selection/hydration remains unchanged. No paid calls, no user stack actions, no model/prefix changes.
