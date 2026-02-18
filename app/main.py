from pathlib import Path
import hashlib
from datetime import datetime, timezone

from app.pipeline.ingest import extract_text
from app.pipeline.chunk_clean import chunk_text, clean_and_tokenize, tokens_to_clean_text
from app.pipeline.embed import generate_embedding
from app.pipeline.store_postgres import upsert_document, upsert_chunk

INPUT_DIR = Path("data/input")


def list_input_files():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR.resolve()}")

    return [p for p in INPUT_DIR.rglob("*") if p.suffix.lower() in [".pdf", ".txt"]]


if __name__ == "__main__":
    files = list_input_files()
    print(f"Found {len(files)} input files:\n")

    for f in files:
        print(f"Processing: {f.name}")

        # 1) Extract text
        text = extract_text(f)

        # 2) Build doc metadata
        doc_id = hashlib.sha256(str(f.resolve()).encode("utf-8")).hexdigest()
        file_size = f.stat().st_size
        modified_time = f.stat().st_mtime
        modified_time_iso = datetime.fromtimestamp(modified_time, tz=timezone.utc).isoformat()

        # 3) Store document row (metadata)
        upsert_document(
            doc_id,
            str(f.resolve()),
            f.name,
            f.suffix.lower().lstrip("."),
            file_size,
            modified_time_iso
        )

        # 4) Chunk text
        chunks = chunk_text(text, chunk_size=1200, overlap=200)
        print(f"  Extracted {len(text)} characters")
        print(f"  Created {len(chunks)} chunks")

        # 5) For each chunk: clean -> embed -> store in pgvector
        for i, chunk in enumerate(chunks):
            tokens = clean_and_tokenize(chunk)
            clean_text = tokens_to_clean_text(tokens)

            embedding = generate_embedding(clean_text)

            chunk_id = f"{doc_id}_{i}"
            upsert_chunk(
                chunk_id,
                doc_id,
                i,
                clean_text,
                embedding
            )

            # progress print
            print(f"  Stored chunk {i+1}/{len(chunks)}")

        print("\nDone with file ✅\n")