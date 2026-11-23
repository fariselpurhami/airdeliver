# Secret history cleanup and prevention

Owner-approved rewrite updated all 80 existing branch refs atomically, protected
by old-SHA leases. No branches/tags were deleted and no visibility change was
made. A private mirror and bundle were retained outside the repository.

Historical real-config paths `.env`, `apps/api/.env`, `apps/web/.env.local`,
`drone_client/.env` and `secrets/` were removed. Identified credential copies were
replaced elsewhere. A generated config bytecode file containing embedded copies
was also removed. Local ignored configuration remains untouched. Source,
workflows and examples at main were unchanged by the rewrite.

A fresh remote mirror was checked: 3,568 reachable blobs, no removed paths and no
exact matches for 22 identified long credential candidates. Scanner findings in
fixed test identities, schema examples, placeholder Kubernetes data and vendored
model documentation were individually reviewed. A fingerprint-specific ignore
list covers those historical false positives, not whole files or secret rules.

A checksum-pinned scanner workflow now checks reachable checkout history and
redacts all detected values. A synthetic provider-token negative control was
rejected. This does not prove all unknown secret formats or private data absent.
No provider credential was tested for validity. GitHub caches, old commit URLs,
Actions logs/artifacts, forks and prior clones are outside the rewrite. Rotate
exposed credentials even when used only for testing. Old clones must not push
removed history back. Preserve ignored local config and use a fresh clone.
