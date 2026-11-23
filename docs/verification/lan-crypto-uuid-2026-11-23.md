# HTTP LAN UUID crash

Shared cryptographic UUIDv4 helper uses native randomUUID when present, otherwise 16 getRandomValues bytes with RFC v4 version/variant. No Math.random/date fallback. Missing secure entropy fails closed. Replaced every application randomUUID use, including landing order/copy action traces, store message/session IDs, checkout request IDs and server trace IDs.

Similar API audit: crypto.subtle SHA256 remains a secure-context requirement for checkout fingerprinting. This patch gives a clear secure-connection error before any payment request, rather than an undefined-method TypeError or a weak/custom hash fallback. It does not make payment checkout over insecure HTTP safe or claim it works. Microphone getUserMedia and service worker/push already have capability guards; they still need browser-supported secure context for actual use. No permission bypass or fake provider behavior.

Proof: full frontend 128 tests/24 suites, tsc and production build. Tests pin native/fallback/bit format/no-entropy paths, 1000 real crypto fallback UUIDs and secure-digest refusal. Real Chromium opened an intercepted RFC1918 HTTP origin with isSecureContext=false, randomUUID undefined and getRandomValues available. Clicking a button with the compiled actual helper generated a valid UUID without error. This is actual insecure-origin helper proof, not a claim of full phone/assistant/provider end-to-end acceptance.

No backend change, migration, provider call, machine operation or deployment. Parent handles per-PR merge approval.
