"""
Pipeline package exports.

These are stable entrypoints the rest of the app should import:
- ingest_corpus: documents -> internal stores
- retrieve_context: query -> top-k chunks
- answer_query: chat -> answer + sources

Imports are lazy so modules that only need ingestion/chunking do not fail
when optional retrieval dependencies are not yet installed.
"""

__all__ = ["ingest_corpus", "retrieve_context", "answer_query", "RetrievedChunk"]


def __getattr__(name: str):
    if name in {"ingest_corpus", "answer_query"}:
        from .orchestrate import ingest_corpus, answer_query
        return {"ingest_corpus": ingest_corpus, "answer_query": answer_query}[name]
    if name in {"retrieve_context", "RetrievedChunk"}:
        from .retrieve import retrieve_context, RetrievedChunk
        return {"retrieve_context": retrieve_context, "RetrievedChunk": RetrievedChunk}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
