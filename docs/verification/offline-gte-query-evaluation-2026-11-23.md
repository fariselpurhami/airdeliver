# Offline GTE query prompt evaluation, prepared, not measured

The pinned model card recommends a query instruction and unprompted documents:
https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct/raw/a9af15a6372d7d6b25e9fb07c2ccb9e1fe645644/README.md

`apps/api/scripts/evaluate_gte_query_prompt.py` compares the current raw query contract with the pinned model's built-in `query` prompt. It reuses one set of unprompted document vectors, alternates query mode order, and reports recall@k, MRR@k, NDCG@k and p50/p95 query encode latency. Both modes use cosine scores. It hashes the fixture and prompt and records the fixed revision. Reports omit raw texts, but do contain fixture IDs; use synthetic IDs and keep output private if IDs reveal catalog/customer context.

Input: a UTF-8 JSON object with nonempty `documents` (`id`, `text`) and `queries` (`id`, `text`, `relevant_ids`). IDs must be unique strings and relevant IDs must exist in the documents. Labels must be human-reviewed. Include Egyptian Arabic, English, mixed-language queries, complements and alternatives with useful distractors. Use the same document text as the real catalog index when measuring applicability. A convenient tiny fixture or self-labeled results cannot establish quality for the full catalog.

From apps/api, with already-cached pinned GTE weights:

```sh
python -m scripts.evaluate_gte_query_prompt --fixture /private/catalog-eval.json --out /private/gte-ab.json
```

The runner forces offline Hugging Face and Transformers mode, local-files-only loading, and no remote Python code. Missing weights or unavailable safe loading is a blocker, not permission to download or enable remote code. It does not call external inference providers, query the database, modify indexes, create accounts or change runtime query prompting.

Ten harness tests use controlled two-dimensional vectors only. They test metric arithmetic, shared document encoding, mode order, fixture validation, bad vectors and missing query prompts. They are NOT GTE inference or relevance evidence. This machine has MiniLM cached but no GTE weights; no real model run was attempted. Small-fixture timing excludes document encoding and model load and is not a production SLA. Review per-query regressions, sample breadth and repeated warmed runs before any production decision. No permanent prefix switch is made.
