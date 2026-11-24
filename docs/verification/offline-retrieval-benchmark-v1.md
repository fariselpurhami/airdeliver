# Offline fixture retrieval benchmark preparation

Owner evidence: completed importer final output confirmed1000Milvus/1000OpenSearch,
fixtureSHA4bcaf87eaae246f4c7e61dcf254f231a7aacb83c87281b2ae6fee05e46a189e9.
Screenshot displayed roughly22m8s whole apply, not isolated embedding throughput.
Exit status not captured. No claim of measured retrieval quality.

## Prepared, not run against a model

- fixtures/retrieval_eval/queries_v1.json:140assistant-authored DRAFT queries,
 20percategory,70dev/70test. Exact4/paraphrase4/constraints4/Arabic4/typo2/no-match2.
 Every qrel is derived from fixture fields and requires human review. Not independent
 real-customer labels. Test split is proposed locked holdout after adjudication,
 not a claim nobody has inspected its source.
- scripts/evaluate_fixture_retrieval.py: pure file scorer. Requires exact catalogSHA,
 complete split rankings, known unique SKUs and explicit draft-label override.
 MacroRecall@10/20/50,nDCG@10,MRR@10(bykind),hard-constraintviolations,
 no-matchfalsepositives,p50/p95elapsedtimes. Never outputs acceptance_pass=true.
- scripts/run_cached_fixture_retrieval.py: owner-only exact dense reference with
 explicit existing local path and --run-local-model optin. HF/Transformersoffline,
 local_files_only, trust_remote_code=false. NO model/index/provider run by agent.
 No persistence of vectors or store writes. No GGUF/ONNX/modernarchitecture
 compatibility claim: this first runner is SentenceTransformer CPU only.
- scripts/check_fixture_index_counts.py: optional read-only count of SQLfixtureIDs
 present inMilvus/OpenSearch, no embeddingload/schema/create/refresh. Missingstores
 fail, nevercreate. Searchvisibilitycanlag30seconds.

## Owner commands after this PR ships, not executed here

Read-only counts:

```sh
python3 scripts/dev_compose_quiet_volumes.py exec -T api python scripts/check_fixture_index_counts.py
```

Pure scorer, from apps/api, requires owner-produced ranking file:

```sh
python scripts/evaluate_fixture_retrieval.py --rankings /path/to/local-rankings.json --split dev --allow-draft
```

Ranking schema:
`{"catalog_sha256":"full SHA","rankings":{"query-id":{"skus":["known SKU"],"latency_ms":12.0}},"metadata":{"model_revision":"exactcommit","mode":"recorded actual retriever"}}`.
All70queryIDs ofselectedsplitrequired, including emptylists for abstentions.
No production IDs guessed fromSKU, no hidden model calls. Latency may be omitted,
but scorer then reports missing samples rather than inventing time.

## Next stages, not claimed done

1 Human review Arabic/English queries and complete relevantSKUsets; annotategraded
 relevance0/1/2. Currentlabelsgrade2onlyand narrowtype-equivalence. Constraints,
 no-matchandparaphrase relevance need adjudication. Fixtures are synthetic.
2 Baseline actual stores direct retrieval withoutGroq/Tavily/router/copy. Current
 prepared dense runner is exact cosine reference, NOTMilvusANN/OSBM25appmeasurement.
 Add read-only exporter for BM25/Milvus/currentfusion/RRF candidates with full
 currentSQLfilters before comparing productionquality. Do not treat exactcosine
 reference as storefitness/timeoutproof.
3 Approved model changes only after clear measured gains. Candidates updated to
 GraniteR2IntelINT8,Harrier0.6B,conditionalGemma2text-onlylicense/runtimecheck;
 Qwen3control. JinaNCexcludedcommercialno-spend. Currentrunnerdoesnotautomatically
 support thesequantizedbackends. No downloads, reindexing or external calls approved.
4 Pin tokenizer,pooling,instructions,normalization/modelrevision. Needseparate
 versionedindexperembeddingmodel; no1536indexreuseacrossmodels. Rerankonlycanreuse.
5 Budget: measure50representativeitems afterapproval; warm1000estimate20times
 measured50batchtimeplusstartup/indexI/O, notextrapolate22minuteapplydirectly.
 Measurequeryp50/p95,timeoutcount,peakRSS/hostswapandcoldstartupseparately.
6 Compare pairedlockedtestmetricsandArabicstrata, notMTEBglobalrank. Candidate
 fusion/reranker mustnotviolatehardfilters. No-matchalways-top50referencewill
 correctlyshowfalsepositives, not pretendcalibratedabstention.

## Gate notes

Additive scripts/data/tests only. No endpoint/DBschema/auth/payment/frontendchange.
FEgatesN/A. BEG1 strictinputfiles;G2/G3effectsN/A;G4nodownload/remote-code;
G5boundedthreads/batch/contextintheoptionalrunner;G6puremath/filetests;
G7explicitmetadata/limits;G8draft/no-live/partialimplementationlabels.
No productionqualification. Existingmodel/cacheandownerfilesystemnotaccessed.
No scripts/models from external community cards executed.
