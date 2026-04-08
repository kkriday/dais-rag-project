# M02 Milestone Notes

## Resubmission Summary

All acceptance criteria have been addressed. The following notes document what was done for each requirement.

---

## Acceptance Criteria

### 1. Pipeline reads PDFs and text files from input directory without errors
**Status: Complete**

- `app/main.py` defines `INPUT_DIR = Path("data/input")` and uses `rglob("*")` to discover `.pdf` and `.txt` files.
- `app/pipeline/ingest.py` — `extract_pdf_text()` uses `pypdf.PdfReader` to read PDFs page by page.
- `extract_text()` was added as a backward-compatible helper (supports both `.pdf` and `.txt`) so that `app/main.py` imports no longer crash with `ImportError`.
- Sample PDF (`2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.pdf`) is present in `data/input/` and extracted output exists in `data/extracted/`.

---

### 2. Relevant metadata is extracted and stored correctly for at least 90% of documents
**Status: Complete**

- `app/main.py` extracts: `doc_id` (SHA-256 hash of path), `file_size`, `modified_time`, `file_name`, `file_type`, and `source_path`.
- `app/pipeline/store_postgres.py` — `upsert_document()` stores all fields in the `documents` table.
- PDF internal metadata (author, title, keywords) is not extracted from the PDF header — the solution uses filesystem metadata instead, which covers the requirements for this milestone.

---

### 3. Text extraction from PDFs works correctly (for 80% of documents)
**Status: Complete**

- `app/pipeline/ingest.py` — `extract_pdf_text()` iterates all pages using `pypdf.PdfReader` and calls `page.extract_text()`.
- Works correctly for text-based PDFs. Scanned/image-only PDFs are not supported (no OCR), which is acceptable for this corpus.
- Extracted output confirmed: `data/extracted/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.txt` exists.

---

### 4. Tokenization, stop word removal, and punctuation/special character removal work as expected
**Status: Complete**

- `app/pipeline/chunk_clean.py`:
  - `chunk_text()` — character-based chunking with `chunk_size=1200` and `overlap=200`.
  - `clean_and_tokenize()` — lowercases text, removes non-alphanumeric characters via regex `[^a-z0-9\s]`, splits on whitespace, filters NLTK English stopwords and single-character tokens.
  - `tokens_to_clean_text()` — rejoins tokens into clean text for embedding.

---

### 5. Vector embeddings are generated successfully for each text chunk
**Status: Complete**

- `app/pipeline/embed.py` — `build_embeddings()` uses `SentenceTransformer("all-MiniLM-L6-v2")` to encode chunk texts with normalized embeddings.
- `generate_embedding()` was added as a backward-compatible single-text embedding function used by `app/main.py`.
- Evidence of success: `data/index/embeddings.npy` and `data/index/meta.jsonl` exist.
- Note: The architecture diagram references Ollama (`nomic-embed-text`) as the original M02 embedding path. The current implementation uses `sentence-transformers` (`all-MiniLM-L6-v2`) which runs locally without requiring an external service, and is compatible with an on-premises deployment.

---

### 6. The chosen database is set up and functioning correctly
**Status: Complete**

- `docker-compose.yml` defines a PostgreSQL 16 service using the `pgvector/pgvector:pg16` image, with a persistent volume (`pgdata`) and exposed on port 5433.
- `app/pipeline/store_postgres.py` connects via `postgresql://m02:m02pass@localhost:5433/m02db`.
- Two tables: `documents` and `chunks` (with `VECTOR(384)` column for embeddings).

---

### 7. Extracted data (metadata and vector embeddings) is written to the database without errors
**Status: Complete**

- `upsert_document()` and `upsert_chunk()` in `app/pipeline/store_postgres.py` use `INSERT ... ON CONFLICT DO UPDATE` for safe idempotent writes.
- 267 chunks stored successfully with zero insertion errors (confirmed in README).

---

### 8. Architecture diagram shows required components
**Status: Complete**

- `Architecture diagram.png` is present and shows all required components:
  - Input Directory → Ingestion Module → Text Extraction → Chunking → Cleaning & Tokenization → Vector Embedding → PostgreSQL + pgvector → Output Storage.

---

## Fixes Applied During Resubmission

| Issue | Fix |
|-------|-----|
| `app/main.py` crashed on import (`extract_text` not found) | Added `extract_text()` to `app/pipeline/ingest.py` |
| `app/main.py` crashed on import (`generate_embedding` not found) | Added `generate_embedding()` to `app/pipeline/embed.py` |
| `batch_query.py` raised `NotImplementedError` | Wired `answer_question()` to `answer_query()` from `app.pipeline` |
| `requirements.txt` missing dependencies | Added `psycopg[binary]`, `pgvector`, `sentence-transformers`, `torch`, `numpy`, `streamlit` |
| No Dockerfile for the Python application | Added `Dockerfile` using `python:3.11-slim` |

---

## Containerization

- The PostgreSQL/pgvector database runs in Docker via `docker-compose.yml`.
- The Python application is containerized via `Dockerfile` (added during resubmission).
- To run the full stack: `docker compose up` starts the database; the app container runs `python -m app.main`.
