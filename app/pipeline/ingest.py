from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from pypdf import PdfReader


def extract_pdf_text(pdf_path: str) -> Dict[str, Any]:
    """
    Extract raw text per page from a PDF.
    Returns dict with doc_id and pages list.
    """
    path = Path(pdf_path)
    reader = PdfReader(str(path))

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text})

    return {
        "doc_id": path.stem,
        "source_path": str(path),
        "num_pages": len(pages),
        "pages": pages,
    }


def save_extracted(doc: Dict[str, Any], out_dir: str = "data/extracted") -> str:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Save as one big txt for now (simple)
    txt_file = out_path / f"{doc['doc_id']}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        for p in doc["pages"]:
            f.write(f"\n\n--- PAGE {p['page']} ---\n\n")
            f.write(p["text"])

    return str(txt_file)
