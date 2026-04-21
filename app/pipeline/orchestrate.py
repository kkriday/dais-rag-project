from __future__ import annotations

import os
import requests
from typing import Any, Dict, Optional, List

from .retrieve import retrieve_context, RetrievedChunk

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def _llm_synthesize(query: str, context: str) -> str:
    """Call Ollama to synthesize an answer from retrieved context."""
    prompt = (
        f"You are a precise assistant answering questions about a corporate ESG report.\n"
        f"Use ONLY the context below. Preserve exact technical terms, brand names, numbers, "
        f"abbreviations, and proper nouns exactly as they appear in the context "
        f"(e.g. ‘UN SDGs’, ‘WaterSense’, ‘SBTi’, ‘neonicotinoids’, ‘42%’, ‘MT CO2e’).\n"
        f"Give a concise, direct answer. If the answer is not in the context, "
        f"say ‘I could not find that information in the document.’\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[LLM unavailable: {e}]"


def ingest_corpus(corpus_path: str, *, stores: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "ok",
        "message": "ingest_corpus is scaffolded. Next: implement ingest->chunk->embed->store.",
        "corpus_path": corpus_path,
    }


def answer_query(query: str, *, stores: Optional[Dict[str, Any]] = None, k: int = 5) -> Dict[str, Any]:
    """
    Retrieves top-k context chunks then synthesizes a grounded answer via Ollama llama3.1.
    """
    chunks: List[RetrievedChunk] = retrieve_context(query, k=k, stores=stores)

    if not chunks:
        answer = "I could not find relevant information in the documents."
        sources = []
    else:
        combined_text = "\n\n".join([c.text for c in chunks])
        answer = _llm_synthesize(query, combined_text)
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
