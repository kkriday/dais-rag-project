from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    page: Optional[int]
    text: str


_PAGE_RE = re.compile(r"--- PAGE (\d+) ---")


def chunk_extracted_txt(txt_path: str, *, max_chars: int = 1200, overlap: int = 150) -> List[Chunk]:
    """
    Takes the saved extracted txt with PAGE markers and returns chunks.
    Simple char-based chunking with overlap, carrying the current page number.
    """
    path = Path(txt_path)
    doc_id = path.stem

    raw = path.read_text(encoding="utf-8", errors="ignore")

    # Split into segments that start at page markers
    parts = raw.split("\n\n--- PAGE ")
    chunks: List[Chunk] = []
    chunk_idx = 0

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # part looks like: "3 ---\n\n<text...>"
        m = re.match(r"(\d+)\s---\s*\n\n(.*)", part, flags=re.DOTALL)
        if m:
            page = int(m.group(1))
            text = m.group(2).strip()
        else:
            page = None
            text = part.strip()

        if not text:
            continue

        # chunk within this page
        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_id = f"{doc_id}_p{page}_c{chunk_idx}"
                chunks.append(Chunk(chunk_id=chunk_id, doc_id=doc_id, page=page, text=chunk_text))
                chunk_idx += 1

            if end >= len(text):
                break

            start = max(0, end - overlap)

    return chunks


def save_chunks_jsonl(chunks: List[Chunk], out_path: str = "data/chunks/chunks.jsonl") -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    import json
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "page": c.page,
                "text": c.text,
            }) + "\n")

    return str(out)
