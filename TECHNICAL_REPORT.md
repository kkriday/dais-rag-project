# DAIS — Document-driven Agentic Intelligence System
## Technical Report · MSA 8700 · Spring 2026

---

## Abstract

This report documents the design, implementation, evaluation, and iterative improvement of DAIS (Document-driven Agentic Intelligence System), a Retrieval-Augmented Generation (RAG) pipeline built over four milestones. The system ingests corporate PDF reports, builds a hybrid search index, and answers natural-language questions by combining BM25 keyword search with dense semantic retrieval, fusing results via Reciprocal Rank Fusion (RRF), and synthesizing grounded answers through a locally hosted large language model (Ollama llama3.1). The final system achieves 78.0% average keyword recall across 100 evaluation questions, with LLM-judge scores of 4.91/5.0 on answer relevance, 4.51/5.0 on faithfulness, and 4.50/5.0 on context relevance.

---

## 1. Introduction

Enterprise document intelligence is a growing need — large organizations produce hundreds of pages of annual reports, ESG disclosures, and impact assessments that analysts must search manually. This project addresses that problem by building an end-to-end RAG pipeline capable of ingesting multi-document corpora and answering precise, factual questions grounded in source text.

**Document Corpus (Final, M05):**

| Document | Chunks |
|---|---|
| Home Depot 2024 ESG Report | ~295 |
| Lowe's 2024 Annual Report | ~260 |
| Mohawk 2024 Impact Report | ~260 |
| **Total** | **815** |

---

## 2. System Architecture

### 2.1 Ingestion Pipeline

```
PDF / TXT Documents
       │
       ▼
  Ingest (ingest.py) — pypdf, page-by-page extraction
       │
       ▼
  Chunk (chunk.py) — 250-token windows, 20% overlap, page-aware
       │
       ▼
  Embed (embed.py) — SentenceTransformer all-MiniLM-L6-v2 (384-dim)
       │
       ▼
  Flat-File Index — embeddings.npy + meta.jsonl
  (optional: PostgreSQL / pgvector)
```

### 2.2 Query Pipeline

```
User Query
       │
       ▼
  Query Expansion — 2–3 variants via _expand_queries()
       │
       ▼
  Hybrid Retrieval — Semantic (cosine) + BM25 (rank_bm25)
       │
       ▼
  RRF Merge — k=8, all documents guaranteed representation
       │
       ▼
  LLM Synthesis — Ollama llama3.1, precision prompt
       │
       ▼
  Answer (prose) + Sources
```

### 2.3 Technology Stack

| Component | Technology |
|---|---|
| PDF Extraction | pypdf |
| Text Cleaning | NLTK |
| Embedding Model | all-MiniLM-L6-v2 (sentence-transformers) |
| Keyword Index | BM25Okapi (rank-bm25) |
| Score Fusion | Reciprocal Rank Fusion (RRF, k=60) |
| LLM | Ollama llama3.1 (8B, local) |
| Chat Interface | Streamlit |
| Vector Storage (optional) | PostgreSQL 16 + pgvector |
| Containerization | Docker / Docker Compose |

---

## 3. Milestone Progression

### M02 — Data Ingestion Pipeline

Built the core ingestion stack: `ingest.py` (pypdf extraction), `chunk.py` (character chunking), `chunk_clean.py` (NLTK stopword removal), `embed.py` (SentenceTransformer), and `store_postgres.py` (pgvector upsert). 267 chunks stored with zero insertion errors.

**M02 Score: 115/120 (95.8%)**

---

### M03 — Agentic Prototype

Added LLM synthesis via Ollama, wired `ingest_corpus()` end-to-end, built the Streamlit chat interface (`chat_app.py`) and fully functional batch query CLI (`batch_query.py`). Both interfaces route through `answer_query()` in `orchestrate.py`.

**M03 Score: 149/160 (93.1%)**

---

### M04 — Evaluation Framework Baseline

Established a 50-question evaluation set with `expected_keywords` per question. Ran baseline evaluation (semantic-only, k=5):

| Metric | Value |
|---|---|
| Average keyword recall | 74.68% |
| High recall (≥80%) | 27/50 (54%) |
| Low recall (<40%) | 10/50 (20%) |
| Average latency | ~15,859 ms |

**Failure taxonomy:**
- **Category A** — LLM paraphrasing (drops exact technical terms)
- **Category B** — Terminology gaps (rare terms not in top-5 chunks)
- **Category C** — Sparse content (brief mentions diluted by chunking)
- **Category D** — Numeric/table lookup (numbers split from labels)

**M04 Score: 160/160 (100%)**

---

### M05 — Iterative Improvement

Five improvements implemented:

**A — Hybrid BM25 + Semantic Retrieval**
`retrieve.py` extended with `BM25Okapi` index. Both retrievers fused via Reciprocal Rank Fusion (RRF, constant=60). Impact: q32 (UN SDGs) 0%→100%, q47 (Scope 2 market-based) 33%→100%.

**B — Precision LLM Prompt**
Explicit instructions to preserve exact numbers, abbreviations, brand names. No inline citations. Impact: eliminated Category A paraphrasing, answer relevance reached 4.91/5.0.

**C — Multi-Query Expansion**
`_expand_queries()` generates 3 query variants per input (original, prefix-stripped, entity keywords) without LLM calls. All variants retrieved and merged by best RRF score. Impact: cross-document recall +3%.

**D — Increased Retrieval Depth**
k raised 5→8; fetch_k = k×2=16 candidates per variant before merge. Reduces displacement of niche-topic chunks by dominant-but-generic chunks.

**E — Source-Labeled Context + Document Registry**
`_DOC_NAMES` maps doc IDs to friendly names. System note listing all loaded documents injected at top of every prompt. Each chunk prefixed with `[Document: <name>, Page <n>]`. Eliminated cross-document attribution errors.

**M05 Score: 156/160 (97.5%)**

---

## 4. Evaluation Methodology

### Keyword Recall

```
Keyword Recall = (expected keywords found in answer) / (total expected keywords)
```

100-question JSONL set (`data/eval_questions.jsonl`): q01–q50 Home Depot, q51–q75 Lowe's, q76–q100 Mohawk.

### LLM-as-Judge (eval_llm_judge.py)

llama3.1 scores three metrics (1–5 integer scale):

| Metric | Definition |
|---|---|
| Faithfulness | Answer grounded in retrieved context? |
| Answer Relevance | Answer addresses the question? |
| Context Relevance | Retrieved chunks relevant to query? |

---

## 5. Results

### Final Scores — M05b (100 Questions)

| Document | Avg Recall | High (≥80%) |
|---|---|---|
| Home Depot (q01–q50) | 83.3% | 34/50 |
| Lowe's (q51–q75) | 76.3% | 14/25 |
| Mohawk (q76–q100) | 69.2% | 12/25 |
| **Overall** | **78.0%** | **60/100** |

### LLM Judge Scores

| Metric | Score |
|---|---|
| Faithfulness | **4.51 / 5.0** |
| Answer Relevance | **4.91 / 5.0** |
| Context Relevance | **4.50 / 5.0** |

### Milestone Progression

| Configuration | k | Questions | Avg Recall |
|---|---|---|---|
| M04 Baseline (semantic only) | 5 | 50 | 74.68% |
| M05a (hybrid BM25+semantic) | 5 | 50 | 75.00% |
| M05b Final (hybrid + multi-query) | 8 | 100 | **78.0%** |

### Remaining Zero-Recall Queries (5)

| ID | Root Cause |
|---|---|
| q42 | Single sentence buried in large chunk |
| q59 | Fact in shareholder letter prose; phrasing mismatch |
| q79 | Segment names only in TOC chunks, not prose |
| q88 | CEO name too rare in corpus |
| q96 | Term diluted in dense governance section |

---

## 6. Ablation Study

| Condition | Retrieval | Prompt | k | Avg Recall |
|---|---|---|---|---|
| M04 Baseline | Semantic only | Generic | 5 | 74.68% |
| M05a | Hybrid BM25+Semantic | Precision | 5 | 75.00% |
| M05b Final | Hybrid + Multi-query | Precision + doc labels | 8 | **78.0%** |

Multi-query expansion combined with k=8 contributed the largest share of improvement (+3pp). BM25 provided targeted fixes for rare-term queries.

---

## 7. Limitations and Future Work

| Priority | Improvement | Impact |
|---|---|---|
| High | Sentence-boundary chunking (nltk.sent_tokenize) | Fixes q42, q79, q88 directly |
| High | Metadata-enhanced retrieval (filter by company) | Cleaner single-doc queries |
| Medium | Larger LLM (llama3.1:70b or API) | Reduced paraphrasing, lower latency |
| Medium | Cross-encoder re-ranking | Higher precision in top-k |
| Low | Table-aware chunking | Fixes numeric-lookup failures |

---

## 8. Conclusion

DAIS demonstrates that a locally-hosted RAG pipeline can answer factual questions from multi-document corporate corpora with high answer quality using entirely open-source components. The final system achieves 78.0% keyword recall and 4.91/5.0 answer relevance across 100 questions spanning three documents. The most impactful improvements were multi-query expansion and hybrid BM25+semantic retrieval. The remaining 5 zero-recall failures all share a single root cause — chunking granularity — which sentence-boundary chunking would directly address.

---

*Report generated: April 2026 · MSA 8700 · Project: msa8700-bk-10-ageratum*
