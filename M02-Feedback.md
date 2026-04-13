# M02 Evaluation Feedback

## Acceptance Criteria Assessment

### 1. Pipeline reads PDFs and text files from input directory without errors

**Status: functional**

- `app/main.py:10-17` — defines `INPUT_DIR = Path("data/input")` and `list_input_files()` which uses `rglob("*")` to find `.pdf` and `.txt` files.
- `app/pipeline/ingest.py:9-27` — `extract_pdf_text()` uses `pypdf.PdfReader` to read PDF files page-by-page.
- A sample PDF is present in `data/input/`: `2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.pdf`.
- Extracted text output exists in `data/extracted/`.

**Issue:** `main.py:5` imports `extract_text` from `app.pipeline.ingest`, but that function does not exist in `ingest.py` — only `extract_pdf_text` and `save_extracted` are defined. This means `main.py` (the M02 pipeline entry point) would crash on import with an `ImportError`. The M03 pipeline modules (`chunk.py`, `embed.py`, `retrieve.py`, `orchestrate.py`) work with a different code path that does not use `main.py`, so the M03 path likely works, but the original M02 `main.py` is broken as committed.

---

### 2. Relevant metadata is extracted and stored correctly for at least 90% of documents

**Status: functional**

- `app/main.py:31-44` — extracts `doc_id` (SHA-256 hash of path), `file_size`, `modified_time`, `file_name`, and `file_type`, then calls `upsert_document()`.
- `app/pipeline/store_postgres.py:9-25` — `upsert_document()` inserts into a `documents` table with columns: `doc_id`, `source_path`, `file_name`, `file_type`, `file_size_bytes`, `modified_time`.
- Metadata fields cover filename, size, modification time, file type, and source path. Author/title/keywords (mentioned in the requirements as examples) are not extracted from PDF internal metadata, but the basics are covered.

---

### 3. Text extraction from PDFs works correctly (for 80% of documents)

**Status: functional**

- `app/pipeline/ingest.py:9-27` — uses `pypdf.PdfReader` to iterate over all pages and extract text with `page.extract_text()`.
- Evidence of successful extraction: `data/extracted/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.txt` exists as output.
- pypdf is a reasonable library for text-based PDFs; scanned/image PDFs would not be handled (no OCR capability like Tesseract).

---

### 4. Tokenization, stop word removal, and punctuation/special character removal work as expected

**Status: completed**

- `app/pipeline/chunk_clean.py:7-20` — `chunk_text()` performs character-based chunking with configurable `chunk_size=1200` and `overlap=200`.
- `app/pipeline/chunk_clean.py:23-28` — `clean_and_tokenize()`:
  - Lowercases text
  - Removes non-alphanumeric characters via regex `[^a-z0-9\s]`
  - Splits on whitespace
  - Filters out NLTK English stopwords and single-character tokens
- `app/pipeline/chunk_clean.py:31-32` — `tokens_to_clean_text()` rejoins tokens into clean text.
- NLTK stopwords corpus is used (`from nltk.corpus import stopwords`).

---

### 5. Vector embeddings are generated successfully for each text chunk

**Status: functional**

Two embedding approaches are present in the codebase:

1. **M02 path (Ollama):** `app/main.py:56` calls `generate_embedding(clean_text)` imported from `app.pipeline.embed`. However, the current `embed.py` uses SentenceTransformers (`all-MiniLM-L6-v2`), not Ollama. The README describes the M02 path as using Ollama with `nomic-embed-text`, but the code no longer contains the Ollama HTTP call — it was replaced by the M03 SentenceTransformers approach. The `generate_embedding` function referenced in `main.py` does not exist in the current `embed.py`.

2. **M03 path (SentenceTransformers):** `app/pipeline/embed.py:28-44` — `build_embeddings()` uses `SentenceTransformer("all-MiniLM-L6-v2")` to encode chunk texts with normalized embeddings. Evidence of success: `data/index/embeddings.npy` and `data/index/meta.jsonl` exist.

**Issue:** The M02 `main.py` references `generate_embedding` which is not defined in the current `embed.py`. The working embedding path is through the M03 modules.

---

### 6. The chosen database is set up and functioning correctly

**Status: functional**

- `docker-compose.yml` — defines a PostgreSQL 16 service using the `pgvector/pgvector:pg16` image with persistent volume (`pgdata`), exposed on port 5433.
- `app/pipeline/store_postgres.py:6` — connects to `postgresql://m02:m02pass@localhost:5433/m02db`.
- README documents the database schema with two tables: `documents` and `chunks` (with `VECTOR(768)` column).
- The README reports 267 chunks stored successfully.

---

### 7. Extracted data (metadata and vector embeddings) is written to the database without errors

**Status: functional**

- `app/pipeline/store_postgres.py:9-25` — `upsert_document()` uses `INSERT ... ON CONFLICT DO UPDATE` for safe idempotent writes.
- `app/pipeline/store_postgres.py:27-48` — `upsert_chunk()` stores `chunk_id`, `doc_id`, `chunk_index`, `text_clean`, and `embedding` (cast to `::vector`).
- The README claims 267 chunks were processed with zero insertion errors.

---

### 8. Architecture diagram shows required components

**Status: completed**

The file `Architecture diagram.png` is present and shows a linear flow:

1. Input Directory (`data/input`)
2. Ingestion Module (file discovery + metadata)
3. Text Extraction Module (PDF/Text reader)
4. Chunking Module (`chunk_text` with size + overlap)
5. Cleaning & Tokenization (stopwords + punctuation removal)
6. Vector Embedding Module (Ollama: nomic-embed-text)
7. PostgreSQL + pgvector (Docker container)
8. Output Storage (documents + chunks tables)

All required components from the acceptance criteria are represented.

---

## Containerization

**Partially containerized.** The PostgreSQL/pgvector database runs in a Docker container (defined in `docker-compose.yml`). The Python application itself is **not** containerized — there is no `Dockerfile` for the app. The pipeline is run directly on the host.

---

## Major Frameworks Used

| Framework/Library | Purpose |
|---|---|
| pypdf | PDF text extraction |
| NLTK | Stopword removal and text cleaning |
| psycopg | PostgreSQL database driver |
| pgvector (PostgreSQL extension) | Vector storage and similarity search |
| sentence-transformers | Embedding generation (M03 path) |
| numpy | Embedding array operations |
| Streamlit | Chat UI (M03 addition) |
| Docker / Docker Compose | Database containerization |
| Ollama | Embedding generation (M02 path, referenced in README/diagram) |

---

## Summary

| Criterion | Status |
|---|---|
| 1. Read PDFs/text files | functional |
| 2. Metadata extraction | functional |
| 3. Text extraction from PDFs | functional |
| 4. Tokenization & cleaning | completed |
| 5. Vector embeddings generated | functional |
| 6. Database set up | functional |
| 7. Data written to database | functional |
| 8. Architecture diagram | completed |

**Key issues found:**

1. **Broken imports in `main.py`:** The M02 entry point (`app/main.py`) imports `extract_text` (line 5) and `generate_embedding` (line 8) which do not exist in the current codebase. The file would fail on import. This suggests the code was refactored for M03 and the original M02 `main.py` was not kept in sync.

2. **No Dockerfile for the application:** Only the database is containerized. A Dockerfile for the Python pipeline would make the solution fully reproducible.

3. **`batch_query.py` is non-functional:** The `answer_question()` function (line 19-22) raises `NotImplementedError` with a placeholder message. The `results.jsonl` file confirms all three queries failed with this error. The function was never wired to the actual `answer_query` from `orchestrate.py`.

4. **`requirements.txt` is incomplete:** Lists only `pypdf`, `nltk`, and `requests`. Missing: `psycopg`, `sentence-transformers`, `torch`, `numpy`, `streamlit` — all of which are needed to run the full pipeline.
