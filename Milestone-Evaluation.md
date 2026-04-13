# Milestone Evaluation — msa8700-bk-10-ageratum

**Evaluated on:** 2026-04-07
**Previous evaluation:** N/A

## Summary

This project implements a document processing pipeline (DAIS) that ingests a Home Depot FY2023 ESG Report PDF, extracts text, chunks it, generates embeddings, and supports semantic retrieval. The codebase is modular with separate pipeline modules for ingestion, chunking, cleaning, embedding, retrieval, and orchestration. A Streamlit chat interface is functional, and data artifacts (295 chunks, embeddings) are persisted to disk.

**Key strengths:** The pipeline modules (ingest, chunk, embed, retrieve) are well-structured and functional individually. The architecture diagram is present and clear. Data artifacts demonstrate the pipeline has been executed successfully. The Streamlit chat interface is wired to the retrieval pipeline.

The M02 entry point (`main.py`) has broken imports that prevent it from running. The `batch_query.py` is non-functional (placeholder `NotImplementedError`). The `requirements.txt` is incomplete (missing 5+ critical dependencies). The test set contains only 3 questions (needs 50–100), and all failed. No M04 evaluation framework, quantitative analysis, error analysis, or improvement strategies exist. The "agents" in the pipeline are really sequential pipeline stages without distinct agent roles or LLM-based reasoning — `answer_query` simply concatenates retrieved chunk text without synthesis.

## Evaluation History

| Date | Type | Summary |
|------|------|---------|
| 2026-04-07 | Initial | First evaluation of M02–M04. M02 partially functional with broken main.py. M03 has working chat but broken batch interface. M04 has no evaluation framework. |

## Major Frameworks and Libraries

| Library / Framework | Purpose |
|---|---|
| pypdf | PDF text extraction |
| NLTK | Stopword removal and text cleaning |
| sentence-transformers (all-MiniLM-L6-v2) | Embedding generation (384-dim) |
| numpy | Embedding array operations |
| Streamlit | Chat UI |
| psycopg | PostgreSQL database driver (M02 path) |
| pgvector (PostgreSQL extension) | Vector storage (M02 path) |
| Docker / Docker Compose | Database containerization |

## Detailed Evaluation

### M02 — Data Pipeline, CI/CD Setup

| #   | Criterion                       | Score | Max | Evidence |
|-----|---------------------------------|-------|-----|----------|
| 2.1 | Code Quality                   | 20 | 30 | Pipeline modules are modular and well-organized across `app/pipeline/` (ingest.py, chunk.py, chunk_clean.py, embed.py, retrieve.py, orchestrate.py, store_postgres.py). Naming is consistent. However, `app/main.py:5,7` has broken imports (`extract_text`, `generate_embedding` don't exist in current codebase), and `requirements.txt` lists only 3 of 8+ needed packages. -10 for broken main.py entry point. |
| 2.2 | Pipeline Functionality         | 20 | 30 | Individual pipeline stages work: PDF extraction (`ingest.py`), chunking (`chunk.py` — 295 chunks), embedding (`embed.py` — 295 embeddings in `data/index/`), and PostgreSQL storage (`store_postgres.py`). Data artifacts confirm successful execution. However, the M02 entry point `main.py` crashes on import due to missing functions. The end-to-end M02 pipeline cannot run as committed. -10 for broken orchestration entry point. |
| 2.3 | Architecture Diagram           | 30 | 30 | `Architecture diagram.png` present, showing complete pipeline flow: Input Directory → Ingestion → Text Extraction → Chunking → Cleaning → Embedding → PostgreSQL/pgvector → Output Storage. All key components are represented with clear data flow. |
| 2.4 | Documentation & Reproducibility | 10 | 30 | `README.md` includes setup instructions (6 steps for M02, additional for M03), database schema, and project structure. However, `requirements.txt` is critically incomplete (missing psycopg, sentence-transformers, torch, numpy, streamlit). `-10`. The M02 `main.py` won't run due to broken imports, so following the instructions will fail. `-10`. |
|     | **M02 Subtotal**               | **80** | **120** | |

### M03 — Agentic Prototype

| #   | Criterion                       | Score | Max | Evidence |
|-----|---------------------------------|-------|-----|----------|
| 3.1 | Multi-Agent Pipeline           | 20 | 40 | Pipeline modules exist: ingest (`ingest.py`), chunk (`chunk.py`), embed (`embed.py`), retrieve (`retrieve.py`), orchestrate (`orchestrate.py`). README:238-241 describes five "agents" (Ingestion, Chunking, Embedding, Retrieval, Answer). However, these are sequential pipeline stages, not agents with distinct roles or decision-making. `answer_query` (`orchestrate.py:28-64`) concatenates retrieved text without LLM synthesis — no structured output beyond raw chunk text. `ingest_corpus` (`orchestrate.py:8-25`) is a scaffolded placeholder. -10 for unclear agent roles, -10 for no structured output/LLM synthesis. |
| 3.2 | Document Ingestion & Storage   | 30 | 40 | Extracted text persisted to `data/extracted/*.txt`. Chunks persisted to `data/chunks/chunks.jsonl` (295 records). Embeddings persisted to `data/index/embeddings.npy` (295×384) + `data/index/meta.jsonl`. Data is queryable via `retrieve.py` cosine similarity search. However, `ingest_corpus()` in `orchestrate.py:8-25` is a placeholder that doesn't actually run ingestion. -10 for incomplete ingestion orchestration. |
| 3.3 | Dual Interface Implementation  | 10 | 40 | **Chat interface:** `chat_app.py` is functional — Streamlit UI wired to `answer_query()`, displays answers and sources. **Batch interface:** `batch_query.py:19-22` raises `NotImplementedError` — completely non-functional. `results.jsonl` confirms all 3 queries failed. The batch interface was never wired to `answer_query` from orchestrate.py. -10 for non-functional batch interface, -10 for responses being raw concatenated chunks rather than meaningful synthesized answers. `-10` batch not routed through pipeline. |
| 3.4 | Architecture & Reproducibility | 20 | 40 | Architecture documented in README:232-245 and `Architecture diagram.png`. Repo is well-organized with clear `app/pipeline/` structure. However, `requirements.txt` is incomplete (missing 5+ critical deps), meaning deployment from instructions fails without undocumented `pip install` commands. README:311 acknowledges this with a separate manual install line. -10 for incomplete requirements, -10 for undocumented manual steps needed. |
|     | **M03 Subtotal**               | **80** | **160** | |

### M04 — Evaluation Framework Baseline

| #   | Criterion                              | Score | Max | Evidence |
|-----|----------------------------------------|-------|-----|----------|
| 4.1 | Evaluation Test Set Execution          | 0 | 40 | `questions.jsonl` contains only 3 questions (needs 50–100). `results.jsonl` shows all 3 failed with `NotImplementedError` from the placeholder `answer_question()` in `batch_query.py:19-22`. No successful execution of test set against the system. |
| 4.2 | Quantitative Performance Analysis      | 0 | 40 | No quantitative analysis exists anywhere in the repository. No metrics defined, no summary statistics, no per-query breakdowns. |
| 4.3 | Error Analysis & Failure Identification | 0 | 40 | No error analysis document or artifact exists. The failures in `results.jsonl` are due to the unimplemented placeholder, not actual system errors to analyze. |
| 4.4 | Improvement Strategy Proposals         | 0 | 40 | No improvement strategies are documented anywhere in the repository. |
|     | **M04 Subtotal**                       | **0** | **160** | |

## Score Summary

| Milestone | Score | Max Points | Percentage |
|-----------|-------|------------|------------|
| M02 — Data Pipeline, CI/CD Setup | 80 | 120 | 66.7% |
| M03 — Agentic Prototype | 80 | 160 | 50.0% |
| M04 — Evaluation Framework Baseline | 0 | 160 | 0.0% |
| **Grand Total (M02–M04)** | **160** | **440** | **36.4%** |

## Recommendations

- **Fix `batch_query.py`:** Wire the `answer_question()` function to use `answer_query()` from `app.pipeline.orchestrate` — this is a one-line fix that would unlock the batch evaluation interface needed for M04.
- **Fix `requirements.txt`:** Add all missing dependencies (`psycopg[binary]`, `sentence-transformers`, `torch`, `numpy`, `streamlit`) so the project can be installed and run from scratch.
- **Build M04 evaluation framework:** Create a test set of 50–100 questions with expected answers, execute against the batch interface, define evaluation metrics, and perform quantitative + error analysis.
- **Add LLM synthesis to `answer_query`:** Currently the system just concatenates retrieved chunk text. Integrating an LLM to synthesize answers from retrieved context would make responses meaningful and demonstrate true agentic capability.
