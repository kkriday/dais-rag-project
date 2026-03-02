from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List

from .retrieve import retrieve_context, RetrievedChunk


def ingest_corpus(corpus_path: str, *, stores: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    M03 ingestion orchestrator (MINIMAL placeholder).

    Later this should:
    - load PDFs/texts from corpus_path
    - extract text + metadata
    - chunk
    - embed + index into vector store
    - persist doc/chunk metadata into a doc store

    For now it returns a status dict so the function exists and your app can wire to it.
    """
    return {
        "status": "ok",
        "message": "ingest_corpus is scaffolded. Next: implement ingest->chunk->embed->store.",
        "corpus_path": corpus_path,
    }


def answer_query(query: str, *, stores: Optional[Dict[str, Any]] = None, k: int = 5) -> Dict[str, Any]:
    """
    M03 chat entrypoint (MINIMAL).

    - Retrieves top-k context chunks
    - Returns a basic answer + sources (chunk/doc/page)

    Later: plug in your LLM to synthesize an answer grounded in retrieved text.
    """
    chunks: List[RetrievedChunk] = retrieve_context(query, k=k, stores=stores)

    # Minimal placeholder "answer" so you can demo end-to-end wiring.
    if not chunks:
        answer = "I couldn’t find relevant context yet (retrieval is still being wired)."
        sources = []
    else:
        combined_text = "\n\n".join([c.text for c in chunks])
        answer = f"""Based on the retrieved document sections:

    {combined_text}
    """
        sources = [
            {
                "doc_id": c.doc_id,
                "chunk_id": c.chunk_id,
                "page": c.page,
                "score": c.score,
            }
            for c in chunks
        ]

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "k": k,
    }
