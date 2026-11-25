# Documentation ownership stage

Twelve loose documentation files move to architecture, development, runbooks
and decisions. Each original byte is preserved, with SHA256 identities in the
adjacent JSON manifest. Original document URLs/paths remain relative symlinks.
Root README references use canonical paths, and docs/README.md indexes actual,
nonempty areas. Historical verification receipts and catalog media stay put.

Four focused ownership/content/reference tests pass. No source behavior,
containers, services, databases, deployment configuration or provider/payment
calls change. Full exact-head CI remains the merge gate.
