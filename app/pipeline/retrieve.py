from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

MODEL_NAME = "all-MiniLM-L6-v2"

CHUNKS_DIR = Path("data/chunks")
INDEX_DIR = Path("data/index")
EMB_PATH = INDEX_DIR / "embeddings.npy"


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    page: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None


def _load_chunks_map() -> Dict[str, Dict[str, Any]]:
    chunks = {}
    for path in sorted(CHUNKS_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                chunks[row["chunk_id"]] = row
    return chunks


def _load_meta() -> List[Dict[str, Any]]:
    meta_path = INDEX_DIR / "meta.jsonl"
    if not meta_path.exists():
        return []

    rows = []
    with meta_path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


_model: Optional[SentenceTransformer] = None
_emb: Optional[np.ndarray] = None
_meta: Optional[List[Dict[str, Any]]] = None
_chunks_map: Optional[Dict[str, Dict[str, Any]]] = None
_bm25: Optional[BM25Okapi] = None
_bm25_ids: Optional[List[str]] = None


def _ensure_loaded() -> None:
    global _model, _emb, _meta, _chunks_map, _bm25, _bm25_ids

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    if _emb is None:
        if not EMB_PATH.exists():
            raise FileNotFoundError(f"Embeddings not found. Run build index first: {EMB_PATH}")
        _emb = np.load(str(EMB_PATH)).astype(np.float32)

    if _meta is None:
        _meta = _load_meta()

    if _chunks_map is None:
        _chunks_map = _load_chunks_map()

    if _bm25 is None and _chunks_map:
        chunk_list = list(_chunks_map.values())
        _bm25_ids = [c["chunk_id"] for c in chunk_list]
        tokenized = [c["text"].lower().split() for c in chunk_list]
        _bm25 = BM25Okapi(tokenized)


def retrieve_context(query: str, k: int = 5, *, stores: Optional[Dict[str, Any]] = None) -> List[RetrievedChunk]:
    """
    Hybrid retrieval: combines semantic cosine similarity with BM25 keyword search
    using Reciprocal Rank Fusion (RRF).
    """
    _ensure_loaded()
    assert _model is not None and _emb is not None and _meta is not None
    assert _chunks_map is not None and _bm25 is not None and _bm25_ids is not None

    fetch_k = min(k * 4, len(_meta))

    # --- Semantic scores ---
    q = _model.encode([query], normalize_embeddings=True)
    q = np.asarray(q, dtype=np.float32)
    sims = (_emb @ q[0])
    sem_top_idx = np.argsort(-sims)[:fetch_k]
    sem_chunk_ids = [_meta[int(i)]["chunk_id"] for i in sem_top_idx]

    # --- BM25 scores ---
    bm25_scores = _bm25.get_scores(query.lower().split())
    bm25_top_idx = np.argsort(-bm25_scores)[:fetch_k]
    bm25_chunk_ids = [_bm25_ids[int(i)] for i in bm25_top_idx]

    # --- Reciprocal Rank Fusion ---
    rrf_scores: Dict[str, float] = {}
    for rank, cid in enumerate(sem_chunk_ids):
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (60 + rank + 1)
    for rank, cid in enumerate(bm25_chunk_ids):
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (60 + rank + 1)

    top_ids = sorted(rrf_scores, key=lambda x: -rrf_scores[x])[:k]

    sem_score_map = {_meta[int(i)]["chunk_id"]: float(sims[int(i)]) for i in sem_top_idx}

    results: List[RetrievedChunk] = []
    for cid in top_ids:
        row = _chunks_map.get(cid, {})
        results.append(
            RetrievedChunk(
                chunk_id=cid,
                doc_id=row.get("doc_id", ""),
                page=row.get("page"),
                text=row.get("text", ""),
                score=sem_score_map.get(cid, rrf_scores[cid]),
                meta={"rrf_score": rrf_scores[cid]},
            )
        )

    return results