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


def extract_text(path_like: str | Path) -> str:
    """
    Backward-compatible helper used by the M02 pipeline entrypoint.
    Supports .pdf and .txt inputs and returns full extracted text.
    """
    path = Path(path_like)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        doc = extract_pdf_text(str(path))
        return "\n\n".join(p["text"] for p in doc["pages"])

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type for extraction: {path}")

if __name__ == "__main__":
    from chunk import chunk_extracted_txt, save_chunks_jsonl

    PDF_PATHS = [
        "data/input/Lowes_2024_Annual_Report_Website_compressed.pdf",
        "data/input/Mohawk_2024_Impact_Report_compressed.pdf",
    ]

    for pdf in PDF_PATHS:
        doc = extract_pdf_text(pdf)
        txt_path = save_extracted(doc)
        print(f"Extracted: {txt_path}")

        chunks = chunk_extracted_txt(txt_path)
        save_chunks_jsonl(chunks, f"data/chunks/{Path(pdf).stem}_chunks.jsonl")
        print(f"{len(chunks)} chunks saved")
