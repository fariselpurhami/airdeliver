# Behavior queue-drain boundary

Consolidation now validates packets before choosing Redis keys, encoding tensors
or scheduling inference. Exact positive owner/item IDs, supported dimensions,
known action index, finite fresh timestamp, float32-safe finite tensor entries
and optional nonnegative finite price are required. A malformed packet is skipped
without suppressing a later valid packet in the same batch. Inference is scheduled
only after a valid encoded event was queued for persistence.

Actual Redis tests check no stream/history/profile-side work for invalid packets,
then valid persistence, retention and one owner-bound inference callback. Existing
real tensor/queue and small offline training tests remain passing. No new event
collection, inferred persona activation, checkpoint approval or consent policy.
This is one retained behavior boundary, not whole-group lifecycle completion.
