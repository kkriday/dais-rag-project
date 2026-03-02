from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
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
    """
    Load full chunk text by chunk_id so we can return it after semantic retrieval.
    """
    if not CHUNKS_PATH.exists():
        return {}

    chunks = {}
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
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


def _ensure_loaded() -> None:
    global _model, _emb, _meta, _chunks_map

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


def retrieve_context(query: str, k: int = 5, *, stores: Optional[Dict[str, Any]] = None) -> List[RetrievedChunk]:
    """
    Semantic retrieval using cosine similarity on normalized embeddings.
    """
    _ensure_loaded()
    assert _model is not None and _emb is not None and _meta is not None and _chunks_map is not None

    q = _model.encode([query], normalize_embeddings=True)
    q = np.asarray(q, dtype=np.float32)  # (1, d)

    # cosine similarity since vectors are normalized: sim = dot(q, emb)
    sims = (_emb @ q[0])  # (n,)

    top_idx = np.argsort(-sims)[:k]

    results: List[RetrievedChunk] = []
    for idx in top_idx:
        m = _meta[int(idx)]
        chunk_id = m["chunk_id"]
        row = _chunks_map.get(chunk_id, {})
        results.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                doc_id=m.get("doc_id", row.get("doc_id", "")),
                page=row.get("page"),
                text=row.get("text", ""),
                score=float(sims[int(idx)]),
                meta={"text_preview": m.get("text_preview")},
            )
        )

    return results
