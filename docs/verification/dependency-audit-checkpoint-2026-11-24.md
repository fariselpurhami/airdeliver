# Dependency audit checkpoint, 2026-11-24

Baseline: `0dae8849b415bf2e4da4ff0ca0eaac15f2e60d60`. This checkpoint adds a repeatable exact Python lock inventory and a production gap register. It closes the lack of a current registry advisory observation for these lock identities, not the supply-chain or production readiness gap.

## Observations

- Root frontend lock: `pnpm audit --json` returned zero known registry advisory matches, 1,075 dependency entries reported.
- Standalone `apps/web` lock: same command returned zero known registry advisory matches, 1,091 dependency entries reported. Both development and production dependencies were included, not production-only.
- Python Poetry lock contains 155 exact name/version identities including alternative platform versions. `pip-audit 2.10.1`, PyPI service, exact pinned requirements, `--no-deps --disable-pip`, checked 151 entries in the first batch and one additional alternate `networkx` identity in the second batch without known advisory matches. Three exact vendor-build identities were skipped by the service: `torch==2.15.0+cpu`, `torchaudio==2.11.1+cpu`, `torchvision==0.29.2+cpu`. Their base versions were queried separately as lock identities and returned no matches, but that does not clear the exact CPU builds. No version suffix was stripped to manufacture a clean result.
- Lock SHA-256: `bb241c00749fd8c81bfa685408b7db506656bba6ff64d1517ae66d98cced33e8`.

No application dependency was installed, upgraded or resolved by the audit. The audit utility was installed into a separate disposable environment. Only package names/versions were sent to public package-advisory services. No source, credentials, user data, model, customer catalog or provider request was sent.

## Repeatable inventory

From repository root, Python 3.11 or later:

```sh
python3 scripts/python_lock_inventory.py --output-dir /tmp/airdeliver-lock-inventory
```

This records exact versions and artifact hashes, package URLs and source types, without copying repository credentials/URLs. It splits conflicting package versions into separate pinned requirement batches, because pip-audit rejects duplicate package names at different versions. The command itself is entirely offline, does not import application code, and writes only to the supplied output directory. It does not claim installed-runtime attestation or license clearance. Every component's license state remains explicitly unreviewed.

When a reviewed audit utility is available, audit each generated requirements batch with exact versions and no dependency resolution. Preserve failure/skip status, time, scanner version and advisory-service identity. Never count an audit service error or skipped identity as zero findings. An advisory gate, scheduled fresh scans, immutable CI action/image review and native/OS/model inventory are subsequent work, not silently marked complete by this checkpoint.

## Remaining supply-chain and IP work

- Containers/base OS packages, images, GitHub Actions, downloaded model code/weights, native libraries and deployed runtime provenance are not covered by these package-registry queries.
- Public package advisories cannot detect unknown vulnerabilities or establish application exploitability. Zero matches is not a security certificate.
- Lock inventory is not a complete SPDX/CycloneDX runtime SBOM or legal license audit. Python lock files do not carry a reliable complete license declaration. Do not fill missing licenses by guess.
- Repository proprietary terms apply only to rights the owner actually holds. The tracked Qwen implementation carries third-party Apache 2 notices; the two attributed reference photos retain CC-BY-SA 4.0. Models, packages and hosted providers retain their own terms. Registration and contributor provenance are not established by repository text.
- Secret-history cleanup is documented in `secret-history-rewrite-2026-11-23.md`; rotation at every provider remains a separate evidence gate. A green history scan is neither revocation nor proof that old clones/caches are gone.

The [production gap register](production-gap-register.json) is a living release checklist, not a replacement for the canonical 55-capability scoreboard. No production flag is promoted by this checkpoint.
