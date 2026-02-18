import re
from typing import List
from nltk.corpus import stopwords

STOPWORDS = set(stopwords.words("english"))

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def clean_and_tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens


def tokens_to_clean_text(tokens: List[str]) -> str:
    return " ".join(tokens)