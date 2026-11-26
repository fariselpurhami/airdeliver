# Support session atomic commit

26November2026. Based on main05b95d32, separate defect fix. No deployment/merge.

## Red first

3real temporary Redis cases failed on original source: two independent support
service instances sharing anonymous/authenticated session both published replies
from the same snapshot; read outage still called the model. Controlled local
probe previously showed2expected turns/1stored. Redis is isolated loopback process,
synthetic state only, no migrations/real data/provider calls.

## Boundary

Capture exact raw Redis snapshot with owner reset generation, compute against that
snapshot, then one Lua execution checks reset-pending/generation and raw equality
before SET+TTL. No global/local lock, silent merge, queue or model retry. Stale
loser gets an honest retry notice, not an answer based on outdated constraints.
Required raw read distinguishes missing from outage. Unconfirmed write cannot
publish ordinary response. Existing direct helper path is retained for historical
callers; actual public support handle installs the strict request-local boundary.

This is optimistic concurrency, not an exactly-once delivery promise. A cancelled
request or lost Redis response can have committed. Tests retain the committed
turn and never automatically replay it. Sequential intentional identical customer
messages remain separate turns. Client retries are not silently deduplicated.
Redis execution is the linearization point, not a guarantee that network bytes
reach a browser before a later reset. Existing owner publication and frontend
reset-response fences remain separate obligations.

## Tests and limits

-15initial temporary Redis/service/mounted HTTP cases passed. Later cases add
  response loss after commit, cancellation after commit, reset between precheck
  and actual Lua, intentional identical input followup.
-75related tests passed17SQL-dependent skipped; adapted minimal unit cache doubles
  to exercise raw snapshots rather than adding insecure production fallbacks.
-86state/provenance tests passed before final two race cases.
-Full local run exceeded120second command budget before completion. A fail-fast
  retry stopped at existing mixed Redis+SQL cart test requiring absent
  TEST_POSTGRES_DSN:1failed483passed71skipped. Not app defect or full-suite pass.
-Source-evolution receipt preserves original move/logging manifests and checks
  baseline then current digest. Full hosted exact-head SQL/storage CI required.
-No distributed cluster/Redis Cluster claim: the existing cache design uses one
  Redis instance; owner/session keys are not hash-tag colocated for Cluster Lua.
-No provider quality, UI layout, owner acceptance or production rollout claimed.

Final focused preparation:169tests passed, including19real temporary Redis/service/
HTTP cases, existing support/visual/session contracts and provenance checks.

## Adversarial identical-history follow-on

b0c60d90 all5hosted checks green; backend2821passed3skipped. Before acceptance,
new real-Redis saturated-history test exposed that content-equality CAS can see
identical serialized bytes after a new turn. Red1failed19passed. Added opaque
per-commit revision nonce to the stored snapshot, separate from customer memory
fields. Both unchanged semantic history revision and concurrent identical-turn
one-winner tests now pass. Existing model schema ignores this storage-only field;
it is never supplied as customer/claim evidence.171focused tests now pass including
21temporary real Redis/service/HTTP cases. Full new-head CI required again.

Typed-corruption follow-on: valid JSON with invalid stored role previously fell
back to fresh context and could overwrite lost constraints. New actual Redis case
red1failed21passed; strict public support hydration now rejects typed corruption
before inference rather than silently resetting. Direct historical helper behavior
is retained outside the public strict boundary.172focused tests pass,22real
Redis/service/HTTP cases. New source receipt current digest updated, baseline kept.

Final-publication follow-on: reset finishing immediately after successful commit
was another red boundary1failed22passed. Owner generation is now rechecked after
optional preference collection, immediately before service return, in addition to
the atomic precommit fence.173focused pass,23real Redis/service/HTTP cases. There
can still be a reset after the final service check while bytes are in transit;
client conversation-generation suppression is the separate browser obligation.

## Hosted CI receipt for 03d6f627

All 5 hosted checks passed on exact head 03d6f627 (backend job
https://github.com/fariselpurhami/airdeliver/actions/runs/45770247347/job/139740892493).
Prior green heads baa963af and b0c60d90 are superseded by the later follow-ons.
This is CI evidence only, not a quality, rollout or owner acceptance claim.
Related client fence (PR269, head aa042223): actual store bundled into a React
harness and run in Chrome at 390 and 1280 widths showed stale reply absent after
reset. This is not a full production overlay or real server erase test.
