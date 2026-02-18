import os
import psycopg
from typing import Sequence

# Mac connects to Docker container via localhost:5433
DB_URL = os.getenv("DATABASE_URL", "postgresql://m02:m02pass@localhost:5433/m02db")


def upsert_document(doc_id: str, source_path: str, file_name: str, file_type: str,
                    file_size_bytes: int, modified_time_iso: str) -> None:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (doc_id, source_path, file_name, file_type, file_size_bytes, modified_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                  source_path = EXCLUDED.source_path,
                  file_name = EXCLUDED.file_name,
                  file_type = EXCLUDED.file_type,
                  file_size_bytes = EXCLUDED.file_size_bytes,
                  modified_time = EXCLUDED.modified_time
                """,
                (doc_id, source_path, file_name, file_type, file_size_bytes, modified_time_iso),
            )

def upsert_chunk(
    chunk_id: str,
    doc_id: str,
    chunk_index: int,
    text_clean: str,
    embedding: Sequence[float],
) -> None:
    # pgvector accepts a string like: [0.1,0.2,...]
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chunks (chunk_id, doc_id, chunk_index, text_clean, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET
                  text_clean = EXCLUDED.text_clean,
                  embedding = EXCLUDED.embedding
                """,
                (chunk_id, doc_id, chunk_index, text_clean, vec_str),
            )