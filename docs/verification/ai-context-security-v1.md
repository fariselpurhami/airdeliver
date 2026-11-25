# Referenced context privilege boundary

Security review found generate_response promoted referenced context into its system message for legacy callers, while strict callers already isolated it. Both modes now serialize that context into the user data payload. Caller-authored system policy is unchanged. No keyword jailbreak classifier or alternate model logic is introduced. Original source move manifest remains immutable; a separate reviewed evolution hash pins the one changed module.

Offline regression covers strict and legacy adapters with dictionary/list/text contexts and checks actual outbound role payloads. This verifies structural isolation, not immunity to prompt injection or output disclosure. Secrets should never be supplied as model context. Output disclosure protection, route-wide coverage, authentication/tenant boundaries and load readiness remain separate work. No provider request, migration, spending or activation.
