# RAG Benchmark Report

**Variants tested:** 6
**Queries per variant:** 252

## Overall Comparison

| Retriever | recall@3 | recall@5 | recall@10 | precision@3 | precision@5 | mrr | hit_rate@5 | latency_ms |
|---|---|---|---|---|---|---|---|---|
| baseline_hybrid | 0.6865 | 0.7262 | 0.8492 | 0.2262 | 0.1437 | 0.6205 | 0.7183 | 334.2645 |
| baseline_semantic | 0.9167 | 0.9444 | 0.9722 | 0.3029 | 0.1873 | 0.8779 | 0.9365 | 327.2494 |
| chunked_512 | 0.381 | 0.5516 | 0.7579 | 0.1243 | 0.1087 | 0.3206 | 0.5437 | 339.2343 |
| baseline_hybrid+rerank_flashrank | 0.6429 | 0.6746 | 0.7381 | 0.2116 | 0.1333 | 0.5932 | 0.6667 | 1941.6841 |
| chunked_parent_child | 0.7381 | 0.8095 | 0.9087 | 0.2434 | 0.1603 | 0.5852 | 0.8016 | 341.7386 |
| baseline_semantic+rerank_flashrank | 0.9167 | 0.9444 | 0.9722 | 0.3029 | 0.1873 | 0.8779 | 0.9365 | 1936.0928 |

## Winners

- **recall@3**: baseline_semantic (0.9167)
- **recall@5**: baseline_semantic (0.9444)
- **recall@10**: baseline_semantic (0.9722)
- **precision@3**: baseline_semantic (0.3029)
- **precision@5**: baseline_semantic (0.1873)
- **mrr**: baseline_semantic (0.8779)
- **hit_rate@5**: baseline_semantic (0.9365)
- **latency_ms**: baseline_semantic (327.2494)

## Per-Category Breakdown

### baseline_hybrid

- **natural_language** (n=50): recall@3=0.8, precision@3=0.2667, recall@5=0.8, precision@5=0.16, hit_rate@5=0.8, recall@10=0.84, mrr=0.72, latency_ms=333.5092
- **exact_lookup** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=0.99, latency_ms=336.5732
- **partial_description** (n=50): recall@3=0.8, precision@3=0.2667, recall@5=0.8, precision@5=0.16, hit_rate@5=0.8, recall@10=0.92, mrr=0.6867, latency_ms=332.292
- **misspelled** (n=50): recall@3=0.46, precision@3=0.1533, recall@5=0.54, precision@5=0.108, hit_rate@5=0.54, recall@10=0.84, mrr=0.3984, latency_ms=333.5716
- **ambiguous** (n=50): recall@3=0.36, precision@3=0.12, recall@5=0.48, precision@5=0.096, hit_rate@5=0.48, recall@10=0.64, mrr=0.3323, latency_ms=333.9036
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=371.085

### baseline_semantic

- **natural_language** (n=50): recall@3=0.98, precision@3=0.3267, recall@5=0.98, precision@5=0.196, hit_rate@5=0.98, recall@10=1.0, mrr=0.9153, latency_ms=328.795
- **exact_lookup** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=1.0, latency_ms=322.547
- **partial_description** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=0.93, latency_ms=338.4722
- **misspelled** (n=50): recall@3=0.98, precision@3=0.3267, recall@5=0.98, precision@5=0.196, hit_rate@5=0.98, recall@10=0.98, mrr=0.98, latency_ms=324.447
- **ambiguous** (n=50): recall@3=0.62, precision@3=0.2067, recall@5=0.76, precision@5=0.152, hit_rate@5=0.76, recall@10=0.88, mrr=0.5994, latency_ms=322.1846
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=322.285

### chunked_512

- **natural_language** (n=50): recall@3=0.28, precision@3=0.0933, recall@5=0.5, precision@5=0.1, hit_rate@5=0.5, recall@10=0.78, mrr=0.2655, latency_ms=354.7416
- **exact_lookup** (n=50): recall@3=0.78, precision@3=0.26, recall@5=0.9, precision@5=0.18, hit_rate@5=0.9, recall@10=1.0, mrr=0.6425, latency_ms=332.8564
- **partial_description** (n=50): recall@3=0.44, precision@3=0.1467, recall@5=0.7, precision@5=0.14, hit_rate@5=0.7, recall@10=0.94, mrr=0.3822, latency_ms=337.951
- **misspelled** (n=50): recall@3=0.24, precision@3=0.08, recall@5=0.44, precision@5=0.088, hit_rate@5=0.44, recall@10=0.7, mrr=0.2161, latency_ms=326.5964
- **ambiguous** (n=50): recall@3=0.14, precision@3=0.0467, recall@5=0.2, precision@5=0.04, hit_rate@5=0.2, recall@10=0.36, mrr=0.1098, latency_ms=343.9802
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=340.385

### baseline_hybrid+rerank_flashrank

- **natural_language** (n=50): recall@3=0.8, precision@3=0.2667, recall@5=0.8, precision@5=0.16, hit_rate@5=0.8, recall@10=0.88, mrr=0.7237, latency_ms=2206.6618
- **exact_lookup** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=0.99, latency_ms=1791.4522
- **partial_description** (n=50): recall@3=0.8, precision@3=0.2667, recall@5=0.82, precision@5=0.164, hit_rate@5=0.82, recall@10=0.86, mrr=0.6835, latency_ms=1822.8848
- **misspelled** (n=50): recall@3=0.28, precision@3=0.0933, recall@5=0.32, precision@5=0.064, hit_rate@5=0.32, recall@10=0.44, mrr=0.2869, latency_ms=1288.9756
- **ambiguous** (n=50): recall@3=0.32, precision@3=0.1067, recall@5=0.42, precision@5=0.084, hit_rate@5=0.42, recall@10=0.5, mrr=0.3056, latency_ms=2554.7078
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=3035.14

### chunked_parent_child

- **natural_language** (n=50): recall@3=0.74, precision@3=0.2467, recall@5=0.86, precision@5=0.172, hit_rate@5=0.86, recall@10=0.98, mrr=0.5922, latency_ms=358.4498
- **exact_lookup** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=0.8767, latency_ms=332.951
- **partial_description** (n=50): recall@3=0.92, precision@3=0.3067, recall@5=0.96, precision@5=0.192, hit_rate@5=0.96, recall@10=0.98, mrr=0.7779, latency_ms=351.0274
- **misspelled** (n=50): recall@3=0.66, precision@3=0.22, recall@5=0.76, precision@5=0.152, hit_rate@5=0.76, recall@10=0.9, mrr=0.4274, latency_ms=329.679
- **ambiguous** (n=50): recall@3=0.36, precision@3=0.12, recall@5=0.46, precision@5=0.092, hit_rate@5=0.46, recall@10=0.68, mrr=0.275, latency_ms=336.157
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=352.455

### baseline_semantic+rerank_flashrank

- **natural_language** (n=50): recall@3=0.98, precision@3=0.3267, recall@5=0.98, precision@5=0.196, hit_rate@5=0.98, recall@10=1.0, mrr=0.9153, latency_ms=2129.2154
- **exact_lookup** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=1.0, latency_ms=2018.0268
- **partial_description** (n=50): recall@3=1.0, precision@3=0.3333, recall@5=1.0, precision@5=0.2, hit_rate@5=1.0, recall@10=1.0, mrr=0.93, latency_ms=1833.7888
- **misspelled** (n=50): recall@3=0.98, precision@3=0.3267, recall@5=0.98, precision@5=0.196, hit_rate@5=0.98, recall@10=0.98, mrr=0.98, latency_ms=1713.9034
- **ambiguous** (n=50): recall@3=0.62, precision@3=0.2067, recall@5=0.76, precision@5=0.152, hit_rate@5=0.76, recall@10=0.88, mrr=0.5994, latency_ms=1942.6072
- **workflow_template** (n=2): recall@3=1.0, precision@3=0.0, recall@5=1.0, precision@5=0.0, hit_rate@5=0.0, recall@10=1.0, mrr=0.0, latency_ms=3009.155