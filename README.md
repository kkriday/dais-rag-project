# Document Pipeline (M02 + M03)

This repository now supports both:
- `M02`: PDF/TXT ingestion, cleaning, embedding, and PostgreSQL+pgvector storage
- `M03`: retrieval + chat + batch query evaluation on persisted local index files

## What Was Fixed

The evaluation blockers were addressed:
- `app/main.py` import errors fixed by adding backward-compatible APIs:
  - `extract_text()` in `app/pipeline/ingest.py`
  - `generate_embedding()` in `app/pipeline/embed.py`
- `app/batch_query.py` is now wired to the real query path (`app.pipeline.answer_query`) and no longer raises `NotImplementedError`
- `requirements.txt` now includes required runtime dependencies (`psycopg`, `sentence-transformers`, `torch`, `numpy`, `streamlit`, etc.)
- application containerization added (`Dockerfile` + `app` service in `docker-compose.yml`)
- pipeline package imports are lazy (`app/pipeline/__init__.py`) to avoid unnecessary import-time failures
- `nltk` stopwords loading is auto-healed in `chunk_clean.py`

## Project Structure

```text
project10/
├── app/
│   ├── main.py
│   ├── chat_app.py
│   ├── batch_query.py
│   └── pipeline/
│       ├── ingest.py
│       ├── chunk_clean.py
│       ├── chunk.py
│       ├── embed.py
│       ├── retrieve.py
│       ├── orchestrate.py
│       ├── store_postgres.py
│       └── __init__.py
├── data/
│   ├── input/
│   ├── extracted/
│   ├── chunks/
│   └── index/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── questions.jsonl
└── README.md
```

## Prerequisites

- Python 3.11+ (project has been used with 3.14)
- Docker + Docker Compose

## Setup

```bash
cd /Users/kridaysmacair/project10
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## M02: Run Ingestion -> DB (pgvector)

### 1) Start PostgreSQL

```bash
docker compose up -d postgres
```

### 2) Create extension and tables

```bash
docker exec -it pg_m02 psql -U m02 -d m02db -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec -i pg_m02 psql -U m02 -d m02db <<'SQL'
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  source_path TEXT,
  file_name TEXT,
  file_type TEXT,
  file_size_bytes BIGINT,
  modified_time TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT REFERENCES documents(doc_id),
  chunk_index INTEGER,
  text_clean TEXT,
  embedding VECTOR(384)
);
SQL
```

### 3) Run pipeline

```bash
python -m app.main
```

### 4) Verify writes

```bash
docker exec -it pg_m02 psql -U m02 -d m02db -c "SELECT COUNT(*) AS documents FROM documents;"
docker exec -it pg_m02 psql -U m02 -d m02db -c "SELECT COUNT(*) AS chunks FROM chunks;"
```

## M03: Build Local Index + Query

### 1) Extract PDF to text

```bash
python -c "from app.pipeline.ingest import extract_pdf_text, save_extracted; doc=extract_pdf_text('data/input/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.pdf'); print(save_extracted(doc), doc['num_pages'])"
```

### 2) Chunk extracted text

```bash
python -c "from app.pipeline.chunk import chunk_extracted_txt, save_chunks_jsonl; c=chunk_extracted_txt('data/extracted/2024_Home_Depot_ESG_Report_8.15.24.2_vF.2.txt'); print(len(c), save_chunks_jsonl(c))"
```

### 3) Build embeddings index

```bash
python -c "from app.pipeline.embed import build_and_save_index; print(build_and_save_index())"
```

### 4) Run chat app

```bash
python -m streamlit run app/chat_app.py
```

### 5) Run batch evaluation

```bash
python -m app.batch_query --in questions.jsonl --out results.jsonl --top-k 5
```

## Full App Container Run (Optional)

```bash
docker compose up --build app
```

## Verification Commands For Submission

Use these to show exactly what changed:

```bash
git status --short
git diff -- app/pipeline/ingest.py app/pipeline/embed.py app/pipeline/chunk_clean.py app/pipeline/__init__.py app/batch_query.py requirements.txt docker-compose.yml Dockerfile README.md
```

Use these to show it works:

```bash
python -m app.batch_query --in questions.jsonl --out results.jsonl --top-k 3
head -n 3 results.jsonl
```
