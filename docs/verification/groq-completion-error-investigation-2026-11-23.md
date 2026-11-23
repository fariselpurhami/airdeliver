# Request5 400 investigation, 2026-11-23

No provider request was made for this investigation. Five reservations remain consumed, three remain. This change supplies no sixth-request entry point and never resets any ledger.

## Confirmed request

`filter_and_recommend` sends system and user messages, brain model120b, temperature0.2, top_p0.9, max_tokens1000, response_format json_object. The acceptance wrapper caps max_tokens at256 and disables SDK/service retries. No stop, reasoning_effort, reasoning_format, include_reasoning, tools, n, or stream field is sent. An offline test now exercises that exact method to the mocked SDK call and asserts every field.

Groq1.7's APIError stores decoded data in `body`; it does not expose code/type/param attributes. Prior metadata looked at code attributes, losing codes from actual SDK exceptions. The shared sanitizer now reads only fixed allowlisted code/type/param values from the decoded dictionary, including nested error dictionaries. It never emits the message, failed_generation, prompt, raw body or arbitrary strings. Unknown fields get a local redaction label. Request IDs retain their constrained grammar. Old response metadata fields remain.

## Findings and hypotheses

Groq's model page lists JSON Object Mode and JSON Schema Mode for120b. The API reference describes max_tokens as deprecated in favor of max_completion_tokens, not unsupported. Temperature0.2 and top_p0.9 are within documented ranges. There is no demonstrated invalid outgoing parameter from the evidence available.

Hypothesis: JSON generation validation failed, possibly because256 output tokens are insufficient for reasoning plus the requested JSON. Another hypothesis is server-side request validation. BadRequestError alone cannot distinguish them. No raw error payload was retained in the owner output, so this patch cannot recover request5's specific error retroactively.

Do not add reasoning_format: the GPT-OSS-specific reasoning documentation says it is unsupported. Generic reasoning examples are not model-specific evidence. Do not silently enlarge the approved token cap or retry. A future explicitly approved one-shot should use this sanitizer and preserve all five ledgers; a documented max_completion_tokens migration or low-effort experiment is a separate behavior change, not a proven fix for this400.

## Sources inspected

- https://console.groq.com/docs/model/openai/gpt-oss-120b
- https://console.groq.com/docs/api-reference
- https://console.groq.com/docs/reasoning
- https://console.groq.com/docs/structured-outputs
- Locked local Groq1.7 APIError/APIStatusError implementation and actual SDK fake-transport contract tests.

## Verification

Full local suite:921passed,4skipped,20warnings. The AMQP-dependent cases remain covered by CI. Tests cover real SDK BadRequestError objects, nested and flat dictionaries, malicious/unrecognized field values, no sensitive text output, production recommendation parameter capture, one reservation and no retry.
