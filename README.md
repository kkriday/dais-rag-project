# DAIS — Document AI System (M02 → M05)

A multi-agent pipeline that ingests corporate PDF/TXT documents, builds a
hybrid BM25 + semantic search index, and answers natural-language questions
via an LLM (Ollama llama3.1).

## Project Structure

```text
project10/
├── app/
│   ├── main.py              # Full pipeline runner (ingest → embed → store)
│   ├── chat_app.py          # Streamlit chat interface
│   ├── batch_query.py       # Batch evaluation runner
│   └── pipeline/
│       ├── ingest.py        # PDF/TXT text extraction
│       ├── chunk.py         # Page-aware character chunking
│       ├── chunk_clean.py   # Stopword removal + tokenization
│       ├── embed.py         # Sentence-transformer embeddings
│       ├── retrieve.py      # Hybrid BM25 + semantic retrieval (RRF)
│       ├── orchestrate.py   # Multi-query answer synthesis via Ollama
│       ├── store_postgres.py# pgvector storage
│       └── __init__.py
├── data/
│   ├── input/               # Place PDFs/TXTs here
│   ├── extracted/           # Plain-text output per document
│   ├── chunks/              # JSONL chunk files per document
│   ├── index/               # embeddings.npy + meta.jsonl
│   ├── eval_questions.jsonl # 100-question evaluation set
│   └── eval_results*.jsonl  # Evaluation outputs
├── docker-compose.yml       # PostgreSQL + Ollama services
├── Dockerfile
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- **Ollama** — required for LLM answer synthesis

  Install from https://ollama.com, then pull the model:
  ```bash
  ollama pull llama3.1
  ```
  Ollama must be running (`ollama serve`) before starting the chat or batch
  query interfaces. Alternatively, use the Docker Compose service (see below).

## Setup

```bash
git clone <repo-url>
cd <repo-directory>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running with Docker Compose (Recommended)

Starts PostgreSQL (pgvector) and Ollama together:

```bash
docker compose up -d
```

Then pull the LLM model inside the Ollama container:

```bash
docker exec ollama_service ollama pull llama3.1
```

## M02: Ingest Documents → PostgreSQL/pgvector

### 1. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 2. Create extension and tables

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

### 3. Place PDFs in `data/input/` and run pipeline

```bash
python -m app.main
```

### 4. Verify writes

```bash
docker exec -it pg_m02 psql -U m02 -d m02db -c "SELECT COUNT(*) FROM documents;"
docker exec -it pg_m02 psql -U m02 -d m02db -c "SELECT COUNT(*) FROM chunks;"
```

## M03: Build Index + Chat + Batch Query

### Option A — Full pipeline in one call

```python
from app.pipeline.orchestrate import ingest_corpus
result = ingest_corpus("data/input/")
print(result)
```

### Option B — Step by step

```bash
# 1. Extract, chunk, and build embeddings index
python -m app.pipeline.embed

# 2. Start chat interface
streamlit run app/chat_app.py
# → open http://localhost:8501

# 3. Run batch evaluation
python -m app.batch_query --in data/eval_questions.jsonl --out data/eval_results.jsonl --top-k 8
```

## M04 / M05: Evaluation

```bash
# Run all 100 evaluation questions
python -m app.batch_query --in data/eval_questions.jsonl --out data/eval_results_m05_full.jsonl --top-k 8
```

Results include `answer`, `sources`, and `latency_ms` per question.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1` | Model name to use |
| `DATABASE_URL` | — | PostgreSQL connection string |
