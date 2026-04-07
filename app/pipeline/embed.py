from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple
import json

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"
CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
INDEX_DIR = Path("data/index")
EMB_PATH = INDEX_DIR / "embeddings.npy"
META_PATH = INDEX_DIR / "meta.jsonl"
_MODEL: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def load_chunks_jsonl(path: Path = CHUNKS_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def build_embeddings(rows: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    model = _get_model()
    texts = [r["text"] for r in rows]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype=np.float32)

    meta = [
        {
            "chunk_id": r["chunk_id"],
            "doc_id": r["doc_id"],
            "page": r.get("page"),
            # keep a small preview; full text stays in chunks.jsonl
            "text_preview": (r["text"][:200] + "...") if len(r["text"]) > 200 else r["text"],
        }
        for r in rows
    ]
    return emb, meta


def save_index(emb: np.ndarray, meta: List[Dict[str, Any]]) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(str(EMB_PATH), emb)

    with META_PATH.open("w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m) + "\n")


def build_and_save_index() -> str:
    rows = load_chunks_jsonl()
    emb, meta = build_embeddings(rows)
    save_index(emb, meta)
    return f"saved: {EMB_PATH} (shape={emb.shape}), meta: {META_PATH} (rows={len(meta)})"


def generate_embedding(text: str) -> List[float]:
    """
    Backward-compatible M02 embedding API used by app/main.py.
    Returns a single normalized embedding vector as a Python list.
    """
    model = _get_model()
    emb = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(emb[0], dtype=np.float32).tolist()
