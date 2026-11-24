# Retained behavior text seam

register_interaction now validates owner identity, finite positive numeric weight,
and bounded nonempty text before invoking the native encoder. Boolean/string IDs,
nonfinite weights and nontext/oversized payloads no longer consume model work or
reach the staging adapter. Encoder failures log exception class only, not private
customer/model error text. Existing valid view/search_hit mapping remains.

Sixteen new tests assert no registry or staging call for invalid inputs and no
private failure value in logs. Existing valid mapping/model-failure and downstream
metadata ingress tests pass:38focused. No caller activation, profile inference,
training, consent-policy change or encoder/model replacement occurs.
