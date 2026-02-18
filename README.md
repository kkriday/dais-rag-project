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
