# Opening quota and copy correction

Owner log2026-11-24: worker became healthy,34cards selected across4pools. Three
writer-evidence failures and one12s timeout withheld all rows. Groq120b reported
8000TPM,2405remaining,retry13s. This proves real rate limiting, not attribution of
5595used/reserved tokens to a particular call. No usage records existed.

Prior4sequential chains needed8writer/review calls, up to12with repair. Each
FreeLLMcap1200, sum9600or14400output cap before prompts. Not actual consumption.
Writer rules8227English bytes and reviewer2998bytes repeated per row plus cards
and schemas. Chat also shares120b and may invoke routing, search planning,
writer/review, research. One user question is not one provider call.

## Changes

Keep foundations and individual row adapter. Current FreeLLM-backed NLU opening
uses one compact four-row writer and one independent batch review, all34(or up
to40)cards represented. Per-row identity/evidence/numeric/claim validation and
currentSQLpublication guard stay. Two paragraphs per row, no fixed substitute.
No repair burst for batch. Any bad row fails whole batch closed. This means
availability remains imperfect; no reduction in evidence strictness.

Output caps1600batch and512review, total2112versus9600prior eight caps. Caps are
NOT measured usage. Leave room for GPT-OSS reasoning, use official supported low
reasoning effort for these bounded stages, not a blanket model change. Source:
https://console.groq.com/docs/api-reference
Provider default is medium; allowed GPT-OSS efforts low/medium/high.

Shared process/model lock now covers FreeLLM and neural-core actual invocations,
not just cooldown. It prevents concurrent sends in one process, not quota across
API/workerprocesses or multiple accounts. No organization-wide TPM guarantee.
Existing retry-after/deadline handling stays. Log successusage numeric prompt,
completion,total tokens with model/stage and input byte upper bound, no raw text.
An absent usage field is absent, never fabricated zero.

No paid account, provider call or owner execution. Free-tier restrictions remain.
Later improve distributed quota priority if real numeric usage shows need. Do
not claim this alone guarantees immediate chat while opening is running. Owner
must verify successful four-row screenshot and follow-up response after rollout.

Canonical55ledger unchanged: source preservation is not live acceptance. No
production/parity claim, no heldPR/deletion/migration activation.
