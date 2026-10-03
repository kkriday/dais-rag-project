# DAIS: Document AI Question-Answering System

DAIS is a retrieval-augmented generation (RAG) system that answers natural-language
questions about long corporate reports. It ingests PDFs, indexes them with hybrid
keyword and semantic search, and uses a locally hosted LLM to write answers grounded
in the source text, with page-level citations.

It was built and evaluated on three 2024 corporate reports (Home Depot ESG,
Lowe's Annual Report, Mohawk Impact Report): 815 indexed passages in total.

![Architecture diagram](Architecture%20diagram.png)

## Results

Evaluated on a hand-built set of 100 questions, each with expected answer keywords:

| Metric | Score |
|---|---|
| Answer relevance (LLM judge) | **4.91 / 5** |
| Faithfulness to sources (LLM judge) | **4.51 / 5** |
| Context relevance (LLM judge) | **4.50 / 5** |
| Average keyword recall | **78%** (up from a 74.7% semantic-only baseline) |

The biggest gains came from adding BM25 keyword search alongside semantic search
and from query expansion. For example, a question about "Scope 2 market-based"
emissions went from 33% to 100% recall once exact-term matching was added.
The full write-up, including ablations and failure analysis, is in
[TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).

## How it works

**Ingestion**
1. **Extract:** pull text from each PDF page by page with `pypdf`.
2. **Chunk:** split each page into ~1,200-character passages with overlap, keeping the page number.
3. **Embed:** encode passages with the `all-MiniLM-L6-v2` sentence-transformer (384-dim).
4. **Index:** save embeddings and metadata to a flat-file index; optionally store them in PostgreSQL + pgvector.

**Answering a question**
1. **Query expansion:** generate 2–3 rephrasings of the question (no LLM call needed).
2. **Hybrid retrieval:** score passages with both cosine similarity and BM25.
3. **Reciprocal Rank Fusion:** merge the two rankings and keep the top 8 passages,
   making sure each loaded document is represented.
4. **Grounded generation:** Llama 3.1 (via Ollama) answers using only the labeled
   passages, preserving exact numbers and terms.
5. **Citations:** the answer is returned with its source document, page, and relevance score.

**Evaluation**
- Batch runner over the 100-question set, recording answers, sources and latency.
- Keyword recall against expected terms per question.
- LLM-as-judge scoring of faithfulness, answer relevance and context relevance.

## Tech stack

| Area | Tools |
|---|---|
| Language | Python 3.11 |
| Document processing | pypdf, NLTK |
| Retrieval | sentence-transformers, rank-bm25, NumPy |
| Vector database | PostgreSQL 16 + pgvector |
| LLM | Llama 3.1 8B served locally with Ollama |
| Interface | Streamlit chat app |
| Infrastructure | Docker, Docker Compose, GitLab CI |

## Features

- Streamlit chat interface with an expandable source panel per answer
- Filter answers to a single document or search across all of them
- Handles several numbered questions in one message
- Runs fully locally: no paid APIs, no data leaves the machine
- Reproducible batch evaluation and LLM-judge scripts

## Project structure

```text
app/
├── chat_app.py          # Streamlit chat interface
├── batch_query.py       # Batch question runner for evaluation
├── eval_llm_judge.py    # LLM-as-judge scoring
├── main.py              # Ingestion into PostgreSQL/pgvector
└── pipeline/
    ├── ingest.py        # PDF/TXT text extraction
    ├── chunk.py         # Page-aware chunking
    ├── chunk_clean.py   # Stopword removal and tokenization
    ├── embed.py         # Embeddings and flat-file index
    ├── retrieve.py      # Hybrid BM25 + semantic retrieval (RRF)
    ├── orchestrate.py   # Query expansion and answer synthesis
    └── store_postgres.py# pgvector storage
data/
├── input/               # Source PDFs
├── chunks/              # Chunked passages (JSONL)
├── index/               # embeddings.npy + meta.jsonl
├── eval_questions.jsonl # 100-question evaluation set
└── eval_*results*.jsonl # Evaluation outputs
```

## Running it locally

**Requirements:** Python 3.11+, Docker, and [Ollama](https://ollama.com).

```bash
git clone https://github.com/kkriday/dais-rag-project.git
cd dais-rag-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.1
```

The repo already includes a built index for the three sample reports, so you can
start the chat app straight away:

```bash
streamlit run app/chat_app.py
```

Then open http://localhost:8501.

### Index your own documents

Put PDFs or text files in `data/input/`, then run:

```python
from app.pipeline.orchestrate import ingest_corpus
ingest_corpus("data/input/")
```

### Run the evaluation

```bash
python -m app.batch_query --in data/eval_questions.jsonl --out data/eval_results.jsonl --top-k 8
python -m app.eval_llm_judge --results data/eval_results.jsonl --out data/eval_judge_results.jsonl
```

### Optional: PostgreSQL + pgvector

`docker compose up -d` starts PostgreSQL (pgvector) and Ollama in containers.
`python -m app.main` then writes documents and embedded chunks into the database.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1` | Model used for answers and judging |
| `DATABASE_URL` | local Docker Postgres on port 5433 | PostgreSQL connection string (only needed for pgvector storage) |

## Next steps

- Sentence-boundary chunking, to fix the remaining misses where a fact is buried in a large passage
- Cross-encoder re-ranking for higher precision in the top results
- Table-aware extraction for numeric lookups
