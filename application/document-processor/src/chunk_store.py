import psycopg2
from config import require_db_config, EMBEDDING_DIMENSIONS

def get_connection():
    return psycopg2.connect(**require_db_config())

def ensure_table_exists():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                bucket TEXT NOT NULL,
                object_key TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding vector({int(EMBEDDING_DIMENSIONS)}),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # Tables created before embeddings existed won't have the column yet.
        cur.execute(
            f"ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector({int(EMBEDDING_DIMENSIONS)});"
        )
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS document_chunks_unique_chunk
            ON document_chunks (bucket, object_key, chunk_index);
        """)
        conn.commit()
        cur.close()
        print("Table ready: document_chunks")
    finally:
        conn.close()

def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

def save_chunks(bucket: str, key: str, chunks: list[str], embeddings: list[list[float]]):
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk/embedding count mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings."
        )

    conn = get_connection()
    try:
        cur = conn.cursor()
        # Replace, don't append — makes reprocessing the same file safe.
        # Delete and inserts share one transaction: all or nothing.
        cur.execute(
            "DELETE FROM document_chunks WHERE bucket = %s AND object_key = %s;",
            (bucket, key),
        )
        for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                "INSERT INTO document_chunks (bucket, object_key, chunk_index, chunk_text, embedding) "
                "VALUES (%s, %s, %s, %s, %s::vector);",
                (bucket, key, index, chunk, _to_vector_literal(vector)),
            )
        conn.commit()
        cur.close()
        print(f"Saved {len(chunks)} chunk(s) with embeddings for {bucket}/{key}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
