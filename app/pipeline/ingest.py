from pathlib import Path
from pypdf import PdfReader


def extract_text_from_txt(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def extract_text(file_path: Path) -> str:
    if file_path.suffix.lower() == ".txt":
        return extract_text_from_txt(file_path)
    elif file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError("Unsupported file type")