# Support response lifetime fence

26November2026. Separate one-defect PR, based on main05b95d32. No merge or rollout.

## Reproduction

Actual Zustand store, deferred mocked fetch, resetChat then resolve old response:
2red tests (old success and old error append into the reset conversation),1passing
unchanged-conversation control. Initial test syntax typo ran0tests, corrected
before the meaningful red run. Same red reproduced on unchanged main basis.
No cart reset, server erase, real customer data, network provider or database call
was executed: cart/reset command methods are stubbed in this test.

## Smallest preserving change

Add a monotonic local conversation generation, increment it during existing
resetChat, capture it at support request start, check it after fetch, after body
parsing and in catch before modifying current messages. No existing routing,
server state, writer/review, card/action contract or timeout is replaced. Does not
cancel/replay native or provider work. Success, HTTP error and network failure
from a previous visible conversation cannot append after reset. A response
accepted before reset is removed by existing reset behavior.

## Actual verification

- Focused actual store/card/reconnect slice17passed before final contrast addition.
- Full Jest42suites223tests passed; includes reset during body parsing, new current
  reply surviving late old reply, two resets and old rejected request not changing
  a new pending processing state.
- TypeScript noEmit passed before final test-only contrast addition; repeated at
  final commit preparation.
- No layout/style change. Actual store state is inspected; no mounted visual UI,
  real-browser reset, server erasure or cross-device acceptance is claimed.
- Full exact-head hosted CI pending. Green tests alone do not authorize merge or
  product quality acceptance. Server same-session lost-update and swallowed
  persistence outage remain separate unresolved gaps in PR266.
