from __future__ import annotations

import os
import re
import requests
from typing import Any, Dict, List, Optional

from .retrieve import retrieve_context, RetrievedChunk

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

_QUESTION_PREFIX = re.compile(
    r"^(what is|what are|what were|what was|how does|how do|how did|how many|"
    r"describe|explain|what|how|why|when|where|who|which)\s+",
    re.IGNORECASE,
)
_DOC_NAMES: Dict[str, str] = {
    "2024_Home_Depot_ESG_Report_8.15.24.2_vF.2": "Home Depot 2024 ESG Report",
    "Lowes_2024_Annual_Report_Website_compressed": "Lowe's 2024 Annual Report",
    "Mohawk_2024_Impact_Report_compressed": "Mohawk 2024 Impact Report",
}


def _friendly_name(doc_id: str) -> str:
    return _DOC_NAMES.get(doc_id, doc_id)


_FILLER = {
    "the", "a", "an", "of", "in", "at", "for", "to", "and", "or", "by",
    "with", "about", "its", "their", "your", "our", "this", "that", "on",
    "from", "as", "is", "are", "was", "were", "be", "been", "s",
    "does", "do", "did", "has", "have", "had", "get", "gets",
    "use", "uses", "make", "makes", "operate", "operates",
}


def _expand_queries(query: str) -> List[str]:
    """Return 2-3 query variants for multi-query retrieval without calling an LLM."""
    queries = [query]

    keyword_q = _QUESTION_PREFIX.sub("", query).strip()
    if keyword_q and keyword_q.lower() != query.lower():
        queries.append(keyword_q)

    tokens = [
        re.sub(r"[^\w']", "", w)
        for w in keyword_q.lower().split()
    ]
    tokens = [t for t in tokens if t and t not in _FILLER and len(t) > 2]
    if len(tokens) >= 2:
        entity_q = " ".join(tokens[:6])
        if entity_q not in queries:
            queries.append(entity_q)

    return queries


def _llm_synthesize(query: str, context: str) -> str:
    prompt = (
        "You are a precise analyst answering questions about corporate documents.\n"
        "Use ONLY the context below. Each section is labeled [Source: <doc>, Page <n>].\n\n"
        "Rules:\n"
        "1. Preserve exact numbers, percentages, brand names, abbreviations, and technical terms "
        "as they appear (e.g. ‘42%’, ‘MT CO2e’, ‘SBTi’, ‘WaterSense’, ‘neonicotinoids’).\n"
        "2. Write the answer in clean, flowing prose or a concise bullet list. "
        "Do NOT include any page numbers, document names, or source references anywhere in the answer.\n"
        "3. For multi-part answers, use a numbered or bulleted list.\n"
        "4. If the answer is not in the context, respond exactly: "
        "’I could not find that information in the provided documents.’\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[LLM unavailable: {e}]"


def ingest_corpus(corpus_path: str, *, stores: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Full pipeline: PDF/TXT → extract → chunk → embed → save flat-file index.
    Also upserts into PostgreSQL via store_postgres when the DB is available.
    """
    from pathlib import Path
    from .ingest import extract_pdf_text, save_extracted
    from .chunk import chunk_extracted_txt, save_chunks_jsonl
    from .embed import build_and_save_index

    corpus = Path(corpus_path)
    files: List[Any] = (
        [corpus]
        if corpus.is_file()
        else sorted(list(corpus.rglob("*.pdf")) + list(corpus.rglob("*.txt")))
    )

    if not files:
        return {"status": "error", "message": f"No PDF or TXT files found in {corpus_path}"}

    processed = []
    for f in files:
        if f.suffix.lower() == ".pdf":
            doc = extract_pdf_text(str(f))
        else:
            doc = {
                "doc_id": f.stem,
                "source_path": str(f),
                "num_pages": 1,
                "pages": [{"page": 1, "text": f.read_text(encoding="utf-8", errors="ignore")}],
            }
        txt_path = save_extracted(doc)
        chunks = chunk_extracted_txt(txt_path)
        out_path = f"data/chunks/{f.stem}_chunks.jsonl"
        save_chunks_jsonl(chunks, out_path)
        processed.append({"doc_id": doc["doc_id"], "num_chunks": len(chunks), "chunk_file": out_path})

        # Optional: persist to PostgreSQL if available
        if stores is not None:
            try:
                from .store_postgres import upsert_document, upsert_chunk
                from .embed import generate_embedding
                from .chunk_clean import clean_and_tokenize, tokens_to_clean_text
                import hashlib
                doc_id = hashlib.sha256(str(f.resolve()).encode()).hexdigest()
                upsert_document(doc_id, str(f.resolve()), f.name, f.suffix.lower().lstrip("."), f.stat().st_size, "")
                for i, c in enumerate(chunks):
                    clean = tokens_to_clean_text(clean_and_tokenize(c.text))
                    upsert_chunk(f"{doc_id}_{i}", doc_id, i, clean, generate_embedding(clean))
            except Exception:
                pass

    index_summary = build_and_save_index()

    return {
        "status": "ok",
        "documents_processed": len(processed),
        "documents": processed,
        "index": index_summary,
    }


def answer_query(
    query: str,
    *,
    stores: Optional[Dict[str, Any]] = None,
    k: int = 8,
    doc_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Multi-query hybrid retrieval → LLM synthesis with inline source citations.
    Generates 2-3 query variants, merges results by best RRF score, passes
    source-labeled context to the LLM.

    doc_filter: if set, restricts retrieval to a single document's chunks.
    """
    queries = _expand_queries(query)

    merged: Dict[str, RetrievedChunk] = {}
    for q in queries:
        for chunk in retrieve_context(q, k=k * 2, stores=stores, doc_filter=doc_filter):
            if chunk.chunk_id not in merged or chunk.score > merged[chunk.chunk_id].score:
                merged[chunk.chunk_id] = chunk

    top_chunks = sorted(merged.values(), key=lambda c: c.score, reverse=True)[:k]

    # Guarantee every known document has at least one chunk in context —
    # only when no filter is active (single-doc filter intentionally narrows scope).
    represented = {c.doc_id for c in top_chunks}
    for doc_id in ([] if doc_filter else _DOC_NAMES):
        if doc_id in represented:
            continue
        # Try to find the best chunk for this doc from the wider merged pool first
        doc_chunks = sorted(
            [c for c in merged.values() if c.doc_id == doc_id],
            key=lambda c: c.score, reverse=True,
        )
        if not doc_chunks:
            # Fall back: targeted retrieval using the doc's friendly name as a hint
            targeted = retrieve_context(
                f"{query} {_friendly_name(doc_id)}", k=4, stores=stores
            )
            doc_chunks = sorted(
                [c for c in targeted if c.doc_id == doc_id],
                key=lambda c: c.score, reverse=True,
            )
        if doc_chunks:
            # Swap out the lowest-scoring chunk to keep total at k
            top_chunks[-1] = doc_chunks[0]
            top_chunks = sorted(top_chunks, key=lambda c: c.score, reverse=True)
            represented.add(doc_id)

    if not top_chunks:
        return {"query": query, "answer": "I could not find relevant information in the documents.", "sources": [], "k": k}

    # Build a system note listing every document in the index so the LLM
    # is always aware of what's loaded, even if a doc isn't in the top-k chunks.
    all_doc_ids = sorted({c.doc_id for c in merged.values()})
    all_names = [_friendly_name(d) for d in all_doc_ids]
    if len(all_names) < len(_DOC_NAMES):
        # Ensure every known document is mentioned even if retrieval missed it
        known = [n for n in _DOC_NAMES.values() if n not in all_names]
        all_names = sorted(set(all_names) | set(known))
    doc_list_note = "Documents loaded in this system: " + ", ".join(all_names) + "."

    context_parts = [
        f"[Document: {_friendly_name(c.doc_id)}, Page {c.page}]\n{c.text}"
        for c in top_chunks
    ]
    answer = _llm_synthesize(query, doc_list_note + "\n\n" + "\n\n".join(context_parts))

    sources = [
        {"doc_id": c.doc_id, "chunk_id": c.chunk_id, "page": c.page, "score": c.score}
        for c in top_chunks
    ]

    return {"query": query, "answer": answer, "sources": sources, "k": k}
