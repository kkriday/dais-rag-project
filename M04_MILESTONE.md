# M04 Milestone — Evaluation Framework Baseline

## 1. Evaluation Test Set Execution

### Test Set Description

- **Total items:** 50 questions
- **Format:** JSONL — each line is a JSON object with `id`, `question`, and `expected_keywords` fields
- **Source document:** 2024 Home Depot ESG Report (single PDF, 110+ pages)
- **Coverage:** Questions span all major report sections — carbon emissions, sustainability pillars, forestry, water, circularity, chemistry, associate programs, community investments, financial disclosures, governance
- **File:** `data/eval_questions.jsonl`

### How It Was Run

The evaluation set was run against the batch interface (`app/batch_query.py`) using the following command:

```bash
python -m app.batch_query --in data/eval_questions.jsonl --out data/eval_results.jsonl --top-k 5
```

Each question was routed through `answer_query()` in `app/pipeline/orchestrate.py`, which performs semantic similarity retrieval over the pre-built embeddings index and returns the top-5 most relevant chunks as the answer. Results (answer, sources, latency) were written to `data/eval_results.jsonl`.

---

## 2. Quantitative Performance Analysis

### Metrics Used

Since there is no LLM generating free-form answers (retrieval only), the following proxy metrics were used:

| Metric | Definition |
|--------|-----------|
| **Keyword Recall** | Fraction of expected keywords found in the returned answer text. Measures whether retrieved chunks contain the relevant information. |
| **Top Similarity Score** | Cosine similarity score of the top-ranked retrieved chunk (0–1). Measures retrieval confidence. |
| **Latency (ms)** | End-to-end response time per query. |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total questions | 50 |
| Average keyword recall | **84.84%** |
| Average top similarity score | **0.645** |
| Average latency | **1,704 ms** (first query loads model; median ~8 ms) |
| High recall queries (≥ 80%) | **35 / 50 (70%)** |
| Low recall queries (< 40%) | **6 / 50 (12%)** |

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
| q08 | Responsible chemistry | 0.50 | 0.566 |
| q32 | UN SDGs alignment | **0.00** | 0.656 |
| q35 | Paris Agreement | 0.33 | 0.534 |
| q36 | Number of stores | 0.33 | 0.723 |
| q41 | Neonicotinoids approach | 0.33 | 0.542 |
| q42 | White roofing program | 0.67 | **0.414** |
| q48 | Formaldehyde reduction | 0.33 | 0.539 |
| q49 | Carbon baseline year | 0.33 | 0.630 |

---

## 3. Error Analysis & Failure Identification

### Failure Categories

#### Category A — Terminology Mismatch (3 queries: q32, q35, q41)
**Queries:** UN SDGs (q32), Paris Agreement (q35), Neonicotinoids (q41)

The document uses these terms but in a context surrounded by different language. The retrieval system searches by semantic similarity, but when the question uses formal terminology (e.g., "UN Sustainable Development Goals") and the document uses the abbreviation "UN SDGs" mostly in a table or caption context, the relevant chunk is either not retrieved or lacks the expected keywords.

**Root cause:** Keyword-based evaluation penalizes answers where the concept is present but phrased differently. The retrieved chunks for q32 contained ESG program descriptions but the abbreviation "UN SDG" appeared on a different chunk that wasn't top-ranked.

---

#### Category B — Numerical/Specific Fact Retrieval (2 queries: q36, q49)
**Queries:** Number of stores (q36), Carbon emissions baseline year (q49)

For q36, the expected keyword "stores" appears in many chunks broadly (not specifically a count), so the top chunks retrieved describe store operations rather than stating the number of locations. For q49, "2020" and "base year" appear in emissions-related chunks but the specific phrasing "baseline" was not used in the document.

**Root cause:** Specific numeric facts are scattered across tables and appendix sections. Character-based chunking breaks table rows mid-entry, splitting numbers from their labels. The retriever cannot distinguish between "2020" as a year reference versus "2020 base year."

---

#### Category C — Low Similarity Score / Sparse Coverage (1 query: q42)
**Query:** White roofing program (q42, top sim = 0.414)

The white roofing program is mentioned only briefly in the document (one or two sentences within a broader energy efficiency section). The embedding index doesn't have a dedicated chunk for it, so similarity scores are very low.

**Root cause:** The document covers this topic too briefly for character-based chunking to create a strong, focused chunk. The retrieval confidence (0.414) is below the threshold where results are reliable.

---

#### Category D — Partial Recall (8 queries: q08, q11, q30, q33, q39, q40, q45, q50)
These queries retrieved relevant chunks but missed 1–2 expected keywords. Most of these keywords appeared in different chunks that ranked just outside the top-5.

**Root cause:** `k=5` retrieval window is insufficient for topics that span multiple scattered sections. Increasing `k` or using a summarizing LLM would likely recover the missing keywords.

---

### Latency Anomaly
Query q01 showed **83,282 ms** latency versus a median of ~8 ms. This is because q01 was the very first query and triggered model loading (SentenceTransformer initializes lazily on first call). All subsequent queries used the cached model.

---

## 4. Improvement Strategy Proposals

### Strategy 1 — Add an LLM Synthesis Layer (Addresses: Categories A, B, D)

**What to change:** Wire an LLM (Ollama with `llama3` or similar on-premises model) into `answer_query()` in `orchestrate.py`. After retrieving the top-k chunks, pass them as context to the LLM with a prompt asking it to synthesize a direct answer to the question.

**Why it is expected to help:** Currently the "answer" is raw concatenated chunk text. An LLM would resolve terminology differences (e.g., recognizing that "UN SDGs" = "UN Sustainable Development Goals"), extract specific numeric facts from context, and produce a coherent response instead of a wall of text.

**How impact will be measured in M05:** Re-run the same 50-question eval set after adding the LLM layer. Compare keyword recall scores before and after. Expect low-recall queries (q32, q35, q36, q41, q48, q49) to improve significantly.

---

### Strategy 2 — Semantic + Keyword Hybrid Retrieval (Addresses: Categories B, C)

**What to change:** Add a BM25 keyword search layer alongside the existing cosine similarity retrieval in `retrieve.py`. Final ranking combines both scores (e.g., RRF — Reciprocal Rank Fusion).

**Why it is expected to help:** Cosine similarity retrieves conceptually related chunks but misses exact matches for specific numbers, acronyms, or proper nouns (e.g., "2020 base year", "UN SDGs", "neonicotinoids"). BM25 excels at exact token matching. Combining both covers semantic and lexical gaps.

**How impact will be measured in M05:** Compare top similarity scores and keyword recall for Category B and C failures before and after. Track whether previously low-scoring queries (q42 sim=0.414) improve.

---

### Strategy 3 — Improved Chunking Strategy (Addresses: Categories B, C)

**What to change:** Replace pure character-based chunking with sentence-boundary-aware chunking (e.g., using `nltk.sent_tokenize` or `spaCy`). Additionally, add a smaller chunk size for table/appendix pages (where numeric data is dense) and a larger chunk size for narrative sections.

**Why it is expected to help:** Character chunking breaks sentences and table rows mid-entry, separating numbers from their labels. A 1,200-character chunk that starts in the middle of a table row will have no meaningful context. Sentence-aware chunking keeps facts intact and improves retrieval precision for specific numeric queries.

**How impact will be measured in M05:** Re-index the corpus with the new chunking strategy and re-run the full 50-question eval. Track improvement in keyword recall for q36 (store count), q49 (baseline year), and other numeric-fact queries.
