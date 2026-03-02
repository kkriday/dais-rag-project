"""
Pipeline package exports.

These are the stable entrypoints the rest of the app should import:
- ingest_corpus: documents -> internal stores
- retrieve_context: query -> top-k chunks
- answer_query: chat -> answer + sources
"""

from .retrieve import retrieve_context, RetrievedChunk
from .orchestrate import ingest_corpus, answer_query

__all__ = [
    "ingest_corpus",
    "retrieve_context",
    "answer_query",
    "RetrievedChunk",
]
