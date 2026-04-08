# M04 Milestone — Evaluation Framework Baseline

## 1. Evaluation Test Set Execution

### Test Set Description

- **Total items:** 50 questions
- **Format:** JSONL — each line is a JSON object with `id`, `question`, and `expected_keywords` fields
- **Source document:** 2024 Home Depot ESG Report (single PDF, 110+ pages)
- **Coverage:** Questions span all major report sections — carbon emissions, sustainability pillars, forestry, water, circularity, chemistry, associate programs, community investments, financial disclosures, governance
- **File:** `data/eval_questions.jsonl`

### How It Was Run

The evaluation set was run against the batch interface (`app/batch_query.py`). Each question is routed through `answer_query()` in `app/pipeline/orchestrate.py`, which:
1. Performs semantic similarity retrieval (top-5 chunks via `retrieve.py`)
2. Passes the retrieved context to **Ollama llama3.1** to synthesize a grounded answer

```bash
python -m app.batch_query --in data/eval_questions.jsonl --out data/eval_results.jsonl --top-k 5
```

Results (answer, sources, latency) were written to `data/eval_results.jsonl`.

---

## 2. Quantitative Performance Analysis

### Metrics Used

| Metric | Definition |
|--------|-----------|
| **Keyword Recall** | Fraction of expected keywords found in the synthesized answer. Measures whether the LLM correctly incorporated key facts from retrieved chunks. |
| **Top Similarity Score** | Cosine similarity of the top-ranked retrieved chunk (0–1). Measures retrieval confidence. |
| **Latency (ms)** | End-to-end response time per query including retrieval + LLM generation. |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total questions | 50 |
| Average keyword recall | **74.68%** |
| Average top similarity score | **0.645** |
| Average latency | **~15,859 ms** (~16s per query via local Ollama) |
| High recall queries (≥ 80%) | **27 / 50 (54%)** |
| Low recall queries (< 40%) | **10 / 50 (20%)** |

### Per-Query Breakdown (Selected)

| ID | Question (abbreviated) | Keyword Recall | Top Similarity |
|----|------------------------|---------------|---------------|
| q01 | Scope 1 & 2 targets | 1.00 | 0.754 |
| q02 | Five environmental pillars | 1.00 | 0.645 |
| q03 | What is SBTi? | 1.00 | 0.590 |
| q04 | Scope 3 Category 11 goal | 1.00 | 0.686 |
| q16 | Veterans support | 1.00 | 0.768 |
| q18 | Disaster relief | 1.00 | 0.763 |
| q38 | Diversity & inclusion | 1.00 | 0.767 |
| q07 | Water conservation goals | 0.33 | 0.724 |
| q28 | Home Depot Foundation | 0.33 | 0.606 |
| q32 | UN SDGs alignment | **0.00** | 0.656 |
| q36 | Number of stores | 0.33 | 0.723 |
| q41 | Neonicotinoids approach | 0.33 | 0.542 |
| q42 | White roofing program | **0.00** | **0.414** |
| q47 | Scope 2 market-based figures | 0.33 | 0.695 |
| q48 | Formaldehyde reduction | **0.00** | 0.539 |

---

## 3. Error Analysis & Failure Identification

### Failure Categories

#### Category A — LLM Paraphrasing / Keyword Mismatch (5 queries: q07, q28, q37, q39, q47)

The LLM synthesizes correct answers but uses different wording than the expected keywords. For example, q07 expects "WaterSense" but the LLM describes water-saving products without using that exact brand name. q47 expects "market-based" but the LLM may say "location-based" or describe the figure differently.

**Root cause:** The LLM rephrases content rather than quoting exact terms. Keyword recall underestimates actual answer quality here — the information is present but expressed differently.

---

#### Category B — Terminology / Abbreviation Gaps (2 queries: q32, q41)

q32 (UN SDGs) and q41 (neonicotinoids) — the document uses these terms but the relevant chunks are not consistently retrieved in the top-5. q32 expects "UN SDG" and "Sustainable Development Goals" but the retrieved chunks describe ESG programs without prominently featuring the SDG label. q41 expects "neonicotinoids" but the LLM avoids repeating technical chemical names.

**Root cause:** Semantic search retrieves conceptually related content but the exact technical terms aren't prominent in the top-ranked chunks.

---

#### Category C — Low Retrieval Coverage / Sparse Content (2 queries: q42, q48)

q42 (white roofing, sim=0.414) and q48 (formaldehyde reduction, sim=0.539) both have very low similarity scores. These topics appear only briefly in the document — one or two sentences within broader sections. The embeddings index lacks a focused chunk for these topics.

**Root cause:** Character-based chunking merges these brief mentions into larger chunks dominated by surrounding text. The signal is diluted, resulting in weak retrieval and the LLM unable to find specific details.

---

#### Category D — Specific Numeric / Factual Lookup (1 query: q36)

q36 asks for the number of Home Depot stores. The retrieved chunks describe store operations broadly rather than returning a specific count. The LLM correctly notes stores exist but doesn't state a number because it wasn't clearly present in the retrieved context.

**Root cause:** Specific numeric facts in tables and appendices get split by character chunking, separating numbers from their labels. The retriever returns narrative chunks rather than the table row containing the count.

---

### Latency Note
Average latency of ~16 seconds per query is entirely due to local Ollama llama3.1 inference. Retrieval itself takes ~5–10ms. In production, a faster model or API-hosted LLM would reduce this significantly.

---

## 4. Improvement Strategy Proposals

### Strategy 1 — Hybrid Retrieval: Semantic + BM25 (Addresses: Categories B, C)

**What to change:** Add a BM25 keyword search layer alongside the existing cosine similarity retrieval in `retrieve.py`. Combine both rankings using Reciprocal Rank Fusion (RRF). BM25 will handle exact term matching for technical words (neonicotinoids, WaterSense, UN SDGs, market-based).

**Why it is expected to help:** Semantic search retrieves conceptually related chunks but misses exact token matches for rare technical terms and abbreviations. BM25 excels at exact keyword lookup. The hybrid approach covers both semantic intent and lexical precision.

**How impact will be measured in M05:** Re-run the 50-question eval after adding BM25. Track improvement in keyword recall for Category B queries (q32, q41) and Category C low-similarity queries (q42, q48). Target: raise average recall from 74.68% to above 82%.

---

### Strategy 2 — Sentence-Boundary Aware Chunking (Addresses: Categories C, D)

**What to change:** Replace character-based chunking in `chunk_clean.py` with sentence-boundary chunking using `nltk.sent_tokenize`. Apply a smaller chunk size for pages that are primarily tables or appendices (detected by low text density), keeping numeric rows intact.

**Why it is expected to help:** The current 1,200-character chunks break sentences and table rows mid-entry, separating numbers from their labels and diluting the signal for brief mentions. Sentence-aware chunks keep facts coherent. Table-specific chunking preserves numeric rows as complete units.

**How impact will be measured in M05:** Re-index the corpus with the new chunking strategy and re-run the eval. Track improvement in top similarity scores for currently weak queries (q42 sim=0.414) and in keyword recall for numeric-fact queries (q36, q47, q49).

---

### Strategy 3 — Upgraded LLM Model (Addresses: Categories A, B)

**What to change:** Swap `llama3.1` for a larger on-premises model via Ollama (e.g., `llama3.1:70b` or `mistral:7b-instruct`) and add an explicit instruction in the prompt to preserve exact technical terms, brand names, and abbreviations from the source text rather than paraphrasing.

**Why it is expected to help:** The current llama3.1 model paraphrases content and drops exact keywords (Category A failures). A larger model with a refined prompt ("preserve exact terms from the context") would retain technical vocabulary like "WaterSense", "UN SDGs", "market-based emissions", and "neonicotinoids" in its output.

**How impact will be measured in M05:** Compare keyword recall for Category A queries (q07, q28, q37, q39, q47) before and after the model/prompt change. Also measure whether average latency improves or degrades and whether answer quality improves qualitatively.
