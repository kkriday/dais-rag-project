# M02 – Document Processing Pipeline with Vector Storage

## Overview

This project implements a foundational document processing pipeline that:

- Ingests PDF and text files from a specified input directory
- Extracts raw text
- Chunks text with overlap
- Cleans and tokenizes text (stopword & punctuation removal)
- Generates vector embeddings using a local Ollama server
- Stores metadata and embeddings in PostgreSQL using pgvector

The system is fully on-prem compatible and containerized for database deployment.

---

## Architecture

Input Directory  
→ Ingestion Module  
→ Text Extraction Module  
→ Chunking & Cleaning Module  
→ Embedding Module (Ollama)  
→ PostgreSQL + pgvector (Docker)  

---

## Technologies Used

- Python 3.14
- PostgreSQL 16
- pgvector
- Docker
- Ollama (local embedding model)
- psycopg
- pypdf
- nltk

---

## Project Structure
project10/
│
├── app/
│   ├── main.py
│   └── pipeline/
│       ├── ingest.py
│       ├── chunk_clean.py
│       ├── embed.py
│       └── store_postgres.py
│
├── data/
│   └── input/
│
├──.gitlab-ci.yml
├── Architecture Diagram
├── docker-compose.yml
├── README.md
└── requirements.txt

---

---

## Setup & Execution Instructions

### Step 1 – Start PostgreSQL (pgvector)

If the container does NOT exist:

```bash
docker run -d --name pg_m02 \
-e POSTGRES_USER=m02 \
-e POSTGRES_PASSWORD=m02pass \
-e POSTGRES_DB=m02db \
-p 5433:5432 \
pgvector/pgvector:pg16
```

If the container already exists:

```bash
docker start pg_m02
```

Verify container is running:

```bash
docker ps
```

---

### Step 2 – Enable pgvector Extension

```bash
docker exec -it pg_m02 psql -U m02 -d m02db
```

Inside psql:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

---

### Step 3 – Install Python Dependencies

```bash
pip install -r requirements.txt
```

If needed:

```bash
pip install "psycopg[binary]"
```

---

### Step 4 – Pull Embedding Model (Ollama)

```bash
ollama pull nomic-embed-text
```

---

### Step 5 – Run the Pipeline

```bash
python -m app.main
```

Expected Output:
- Extracted characters
- Created chunks
- Stored chunk X/Y
- Completed successfully

---

### Step 6 – Verify Embeddings Stored

Check total embeddings:

```bash
docker exec -it pg_m02 psql -U m02 -d m02db -c "SELECT COUNT(*) FROM chunks;"
```

Expected result:

```
 count
-------
 267
```

---
## Database Schema

### Documents Table

CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    source_path TEXT,
    file_name TEXT,
    file_type TEXT,
    file_size_bytes BIGINT,
    modified_time TIMESTAMPTZ
);

### Chunks Table

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT REFERENCES documents(doc_id),
    chunk_index INTEGER,
    text_clean TEXT,
    embedding VECTOR(768)
);

---

## Acceptance Criteria Coverage

✔ Reads PDFs and text files from input directory
✔ Extracts metadata (filename, size, modified time)
✔ Extracts text from PDFs
✔ Tokenizes and removes stopwords
✔ Generates embeddings via Ollama
✔ Stores embeddings in PostgreSQL (pgvector)
✔ Database is containerized
✔ GitLab repository connected
✔ GitLab CI pipeline configured

---

## Performance Summary
✔	267 chunks processed successfully
✔	Embedding dimension: 768
✔	Zero insertion errors
✔	Safe upsert handling
✔	Fully containerized database

---

# M03 – Agentic Prototype (DAIS)

## Overview

This project implements a working **Document‑Driven Agentic Intelligence System (DAIS)** prototype.

**M03 deliverables covered:**
- Working multi‑agent pipeline from **documents → internal stores**
- **Chat interface** (Streamlit) wired to the pipeline for basic queries
- **Batch query interface** (minimal CLI) to run automated evaluation queries and write results

At a high level, the system:
1. Ingests PDF documents
2. Extracts text by page
3. Chunks text (with overlap) and persists chunks
4. Builds semantic embeddings (SentenceTransformers) and persists an index
5. Retrieves top‑k relevant chunks via cosine similarity
6. Produces an answer + sources (chunk/doc/page)

---

## Architecture

**Document → Stores → Retrieval → Answer**

- **Ingestion Agent**: PDF → per‑page text
- **Chunking Agent**: text → chunks.jsonl (chunk_id, doc_id, page, text)
- **Embedding Agent**: chunks → embeddings.npy + meta.jsonl
- **Retrieval Agent**: query → semantic top‑k chunks
- **Answer Agent**: composes response from retrieved context + sources

Internal stores created under `data/`:
- `data/extracted/*.txt` (raw extracted text with page markers)
- `data/chunks/chunks.jsonl` (persisted chunks)
- `data/index/embeddings.npy` + `data/index/meta.jsonl` (persisted embedding index)

---

## Technologies Used

- Python 3.x
- Streamlit (chat UI)
- pypdf (PDF text extraction)
- sentence-transformers + torch (semantic embeddings)
- numpy

> Note: Earlier M02 work used PostgreSQL + pgvector + Ollama embeddings. Those are optional/legacy for M03 in this repo.

---

## Project Structure

```text
project10/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── chat_app.py                # Streamlit chat interface
│   ├── batch_query.py             # Batch query interface (CLI)
│   └── pipeline/
│       ├── __init__.py            # Exposes stable entrypoints
│       ├── ingest.py              # PDF extraction
│       ├── chunk.py               # Chunking + JSONL writer
│       ├── embed.py               # Build/save embeddings index
│       ├── retrieve.py            # Semantic retrieval
│       ├── orchestrate.py         # ingest_corpus + answer_query
│       └── store_postgres.py      # (optional/legacy)
│
├── data/
│   ├── input/                     # Put PDFs here
│   ├── extracted/                 # Generated
│   ├── chunks/                    # Generated
│   └── index/                     # Generated
│
├── questions.jsonl                # Batch input (create in project root)
├── results.jsonl                  # Batch output (generated)
├── docker-compose.yml
├── .gitlab-ci.yml
├── README.md
└── requirements.txt
```

---

## Setup

### 1) Activate virtual environment

```bash
cd /Users/kridaysmacair/project10
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt

# If not already installed during M03 steps:
pip install streamlit pypdf sentence-transformers torch numpy
```

---

## Run the M03 Pipeline (End‑to‑End)

> Example PDF used in development:
> `./data/input/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.pdf`

### Step A — Extract PDF to text

```bash
python3 -c "from app.pipeline.ingest import extract_pdf_text, save_extracted; doc = extract_pdf_text('./data/input/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.pdf'); out = save_extracted(doc); print('saved:', out, 'pages:', doc['num_pages'])"
```

Expected: creates `data/extracted/<doc_id>.txt`

### Step B — Chunk extracted text

```bash
python3 -c "from app.pipeline.chunk import chunk_extracted_txt, save_chunks_jsonl; chunks = chunk_extracted_txt('data/extracted/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.txt'); out = save_chunks_jsonl(chunks); print('chunks:', len(chunks), 'saved:', out)"
```

Expected: creates `data/chunks/chunks.jsonl`

### Step C — Build semantic embeddings index

```bash
python3 -c "from app.pipeline.embed import build_and_save_index; print(build_and_save_index())"
```

Expected: creates:
- `data/index/embeddings.npy`
- `data/index/meta.jsonl`

---

## Chat Interface (Streamlit)

Run:

```bash
python3 -m streamlit run app/chat_app.py
```

Open the local URL shown in the terminal (usually `http://localhost:8501`).

---

## Batch Query Interface (Minimal)

### 1) Create `questions.jsonl` in the project root

Example:

```json
{"id":"q1","question":"What are Scope 1 and Scope 2 targets?"}
{"id":"q2","question":"Summarize emissions reduction goals in the report."}
{"id":"q3","question":"What ESG topics are covered under supply chain?"}
```

### 2) Run batch evaluation

```bash
python -m app.batch_query --in questions.jsonl --out results.jsonl --top-k 5
```

Expected: writes `results.jsonl` with `answer`, `sources`, and `latency_ms` per question.

---

## Notes / Known Warnings

- HuggingFace warning about unauthenticated requests / HF_TOKEN: safe to ignore for local use.
- `embeddings.position_ids | UNEXPECTED`: safe to ignore for this model; embeddings still work.

---
