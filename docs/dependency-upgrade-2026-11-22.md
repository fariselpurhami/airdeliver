# Dependency upgrade — 2026-11-22

Authorized by Faris: upgrade torch and all libraries to latest, with
before/after model smoke tests and per-package changelog.

## Version changes (poetry.lock diff)

| Package | Before | After |
| --- | --- | --- |
| cuda-bindings | — | 13.5.0 |
| cuda-pathfinder | — | 1.9.1 |
| cuda-toolkit | — | 13.2.2 |
| fastapi | 0.141.1 | 0.165.0 |
| numpy | 2.5.3 | 2.5.5 |
| nvidia-cublas | — | 13.10.1.6 |
| nvidia-cuda-cccl | — | 13.3.5.0.6 |
| nvidia-cuda-nvrtc | — | 13.5.37 |
| nvidia-cudnn-cu13 | — | 9.26.0.51 |
| nvidia-cusparselt-cu13 | — | 0.8.1 |
| nvidia-nccl-cu13 | — | 2.30.7 |
| nvidia-nvshmem-cu13 | — | 3.7.2 |
| opentelemetry-api | — | 1.45.2 |
| sentence-transformers | 6.1.0 | 6.3.0 |
| sqlmodel | 0.0.46 | 0.0.50 |
| starlette | 1.3.1 | 1.10.0 |
| stripe | 15.6.1 | 17.1.0 |
| torch | 2.7.1 | 2.15.0+cpu |
| torchaudio | 2.6.0+cpu | 2.11.1+cpu |
| torchvision | 0.21.0+cpu | 0.29.2+cpu |
| transformers | 5.17.0 | 5.24.0 |
| triton | 3.3.1 | 3.9.0 |
| uvicorn | 0.53.0 | 0.54.0 |

Note: the `nvidia-*`/`cuda-*` entries exist in the lock only for non-Linux
platform markers (the win32 torch fallback); the Linux deployment installs
`torch==2.15.0+cpu` from the PyTorch CPU index, which has no CUDA deps.

## Constraints changed in pyproject.toml

- torch `>=2.4.0` (locked 2.6.0) -> `^2.15.0` (linux: `2.15.0+cpu` via pytorch-cpu source)
- transformers `5.17.0` -> `^5.24.0`
- sentence-transformers `6.1.0` -> `^6.3.0`
- numpy `2.5.3` -> `^2.5.5`
- fastapi `^0.141.1` -> `^0.165.0`
- uvicorn `^0.53.0` -> `^0.54.0`
- sqlmodel `^0.0.46` -> `^0.0.50`
- stripe `^15.6.1` -> `^17.1.0` (previous "FROZEN" note superseded by owner directive)
- torchvision `0.21.0` -> `0.29.2` (cpu build on linux)
- torchaudio `2.6.0` -> `2.11.1` (cpu build on linux)

## Verification

- Backend suite in fresh py3.13 poetry env: **205 passed** (excludes
  tests/test_behavior_engine.py — see RAM note).
- Model smoke test (`apps/api/scripts/smoke_behavior.py`): real
  all-MiniLM-L6-v2 embeddings hashed before (torch 2.6.0) and after
  (torch 2.15.0) — **identical hashes, identical cosine matrix and
  nearest-neighbor ranking**; BehaviorEngine register_interaction +
  get_user_profile flow works, profile keys unchanged.
  Run: `poetry run python scripts/smoke_behavior.py --out /tmp/after.json --compare /tmp/before.json`
- torch 2.15 import RSS: 222 MB (torch 2.6 was 377 MB) — lighter.
- linux/amd64 wheel availability: proven by installation on linux x86_64
  (this CI sandbox) and `poetry export` emits
  `--extra-index-url https://download.pytorch.org/whl/cpu` so Docker
  builds on Intel Mac (linux/amd64 VM) resolve the +cpu wheels.

## NOT verified (sandbox limits)

- tests/test_behavior_engine.py in the poetry env: the suite process is
  OOM-killed on the 2 GB sandbox (OmniNet allocates ~300 MB of weights;
  total RSS exceeds the limit). The engine itself is verified working
  under the new deps via the smoke script above; run the file on any
  machine with >= 4 GB free RAM to get a green badge.
- stripe 15.6.1 -> 17.1.0 spans two major releases. All mocked payment
  tests pass; live Stripe API calls (checkout session creation, webhook
  handling) should be smoke-tested once against the Stripe sandbox
  before production traffic.
