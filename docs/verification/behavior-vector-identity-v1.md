# Worker behavior vector identity

The existing worker enrichment path now accepts only exact positive integer
product IDs and one matching returned Milvus row with a finite bounded numeric
vector. It does not coerce string, boolean or fractional IDs into other products,
accept another returned product, or leak backend payloads in failure logs. Valid
worker action metadata and input immutability remain. No new event, training,
consent, profile or provider/model action, no namespace rewrite or Granite change.

Nineteen new actual worker/Milvus-return tests cover coercion rejection, wrong/
multiple row identity, nonfinite/malformed vectors, valid enrichment and private
error diagnostics. Existing worker seam and ingress tests pass. This validates
identity/data handling, not consent lifecycle unification or semantic model quality.
