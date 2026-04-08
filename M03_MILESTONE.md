# M03 Milestone — Agentic Prototype

## 1. Document Pipeline

### How it works

**Document type:** PDF and plain-text (`.pdf`, `.txt`) files from a local input directory (`data/input/`).

**Pipeline stages:**

1. **Ingestion** (`app/pipeline/ingest.py`) — Reads PDFs page-by-page using `pypdf` and extracts raw text per page with page markers. Saves full extracted text to `data/extracted/<doc_id>.txt`.
2. **Chunking** (`app/pipeline/chunk.py`) — Reads the extracted `.txt` files and splits them into overlapping character-based chunks (`max_chars=1200`, `overlap=150`) while preserving the page number of each chunk.
3. **Cleaning & Tokenization** (`app/pipeline/chunk_clean.py`) — Lowercases, removes punctuation/special characters, strips NLTK English stopwords, and rejoins tokens into clean text.
4. **Embedding** (`app/pipeline/embed.py`) — Encodes each chunk using `SentenceTransformer("all-MiniLM-L6-v2")` with normalized embeddings. Saves `data/index/embeddings.npy` and `data/index/meta.jsonl`.
5. **Storage** (`app/pipeline/store_postgres.py`) — Upserts document metadata into the `documents` table and chunk text + embedding vector into the `chunks` table in PostgreSQL + pgvector.
6. **Orchestration** (`app/pipeline/orchestrate.py`) — `ingest_corpus()` wires the above stages end-to-end. `answer_query()` handles retrieval and response generation.

**Output format:**
- `data/extracted/` — plain `.txt` files (one per document)
- `data/chunks/chunks.jsonl` — JSONL with fields: `chunk_id`, `doc_id`, `page`, `text`
- `data/index/embeddings.npy` — NumPy float32 array of shape `(N, 384)`
- `data/index/meta.jsonl` — JSONL with chunk metadata
- PostgreSQL: `documents` and `chunks` tables (with pgvector `VECTOR(384)` column)

### How to run the pipeline

**Prerequisites:** Docker running, Python dependencies installed.

```bash
# 1. Start the database
docker compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full pipeline
python -m app.main
```

Place PDF or text files in `data/input/` before running.

---

## 2. Chat Interface

### How it works

The chat interface is a **Streamlit web app** (`app/chat_app.py`). Users type questions in a chat input box; the app calls `answer_query()` from `app.pipeline`, which:
1. Encodes the query using `SentenceTransformer`.
2. Performs cosine similarity search over the pre-built embeddings index (`data/index/embeddings.npy`).
3. Returns the top-k most relevant chunks as context, along with source metadata (doc ID, page, similarity score).

The response is displayed in a conversational chat format. Sources are shown in a collapsible expander.

### How to run the chat

```bash
streamlit run app/chat_app.py
```

Then open **http://localhost:8501** in your browser.

---

## 3. Batch Query Interface

### How it works

The batch interface (`app/batch_query.py`) reads a JSONL file of questions, runs each through `answer_query()`, and writes results (answer, sources, latency) to an output JSONL file. Each input row must have a `question` field and optionally an `id` field.

**Input format (`questions.jsonl`):**
```json
{"id": "q1", "question": "What are the sustainability goals?"}
{"id": "q2", "question": "What is the carbon reduction target?"}
```

**Output format (`results.jsonl`):**
```json
{"id": "q1", "question": "...", "answer": "...", "sources": [...], "latency_ms": 120}
```

### How to run batch queries

```bash
python -m app.batch_query --in questions.jsonl --out results.jsonl --top-k 5
```

Results are saved to `results.jsonl`. Each row contains the question, generated answer, retrieved source chunks, and latency in milliseconds.
