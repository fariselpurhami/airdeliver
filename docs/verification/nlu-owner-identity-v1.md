# Retained NLU owner identity ingress

The actual bus parser now accepts only positive32-bit integers or their canonical
ASCII decimal string representation. It no longer maps true to1or7.9to7. Existing
canonical string bus IDs remain supported. Noncanonical signs, padding, leading
zeros and exponent/decimal notation are rejected before UI, memory or inference.
No owner lookup, token rule, user account or message route is changed.

Twenty-five new parser/process cases plus existing NLU characterization pass:
111focused. Rejected identities cannot read history or send UI from process_message.
This is a narrow identity-coercion boundary, not a full authorization audit.
