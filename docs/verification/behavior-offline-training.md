# Offline behavior candidates

Run inside apps/api with the project Python environment:

```bash
python -m scripts.train_behavior --help
python -m scripts.train_behavior --dataset /path/interactions.jsonl \
  --config /path/architecture.json --output /path/new-candidate-v1.pt \
  --model-version candidate-v1 --epochs 3 --batch-size 8 --threads 1
```

The config must be explicit OmniNetConfig JSON, including supported_dims and a
compatible architecture. Do not use a full-size model until CPU/RAM capacity is
measured. This is offline CPU training, never a startup job or API request.
Use a new output path in a job-owned directory for each run, and one writer per
output directory. Existing outputs are rejected. Candidate writes are atomic;
checkpoint and metrics JSON are separate writes, not one transaction.

Each JSONL record has subject_id (pseudonymous), embedding_source (model@revision),
source (real or synthetic), and4to256 events. Each event contains a globally
unique event_id, stable item_id, known action, positive numeric timestamp and a
finite vector. Events must be time ordered. One dataset has one embedding source
and dimension. Do not invent events, claim synthetic interactions are real, or
include direct personal identifiers. Secure the dataset locally; the job never
uploads it. Current limits:512MiB input,10000 records,16MiB per line. These are
format bounds, not a safe RAM guarantee after tensor/list expansion.

Subjects are stably partitioned70/15/15 using a hash, so training, validation and
test users do not overlap. Tiny datasets may have empty splits and are rejected.
Both positive and explicit discard outcomes need real training batches with at
least two distinct target items per batch. Historical context excludes target
and future events. The best validation epoch is evaluated once on the test set.

Outputs: tensor-only checkpoint with version/data fingerprint/provenance and a
.metrics.json report. Warm starts require matching architecture, action mapping,
embedding revision and split contract. Optimizer state is not resumed, so a warm
start is a new fine-tuning job, not an exact interrupted-job resume.

All candidates have production_approved=false. No serving config, live model or
production approval is changed. NDCG/MRR measure single next-positive-item ranking
against distinct items in the held-out snapshot, not the production catalog.
This is not evidence of revenue lift, calibrated confidence, personalization
quality or real-user generalization. Synthetic tests prove mechanics only. Real
consented event capture, dataset governance, representative evaluation, capacity
limits and an independent release decision remain required.
