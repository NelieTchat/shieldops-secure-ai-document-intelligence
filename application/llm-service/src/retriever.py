import psycopg2
from config import require_db_config, TOP_K_MAX, MAX_DISTANCE

def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

def retrieve_chunks(query_vector: list[float], top_k: int, key_prefix: str) -> list[dict]:
    if not 1 <= top_k <= TOP_K_MAX:
        raise ValueError(f"top_k must be between 1 and {TOP_K_MAX}.")
    # Always scope to a folder. The trailing slash stops one prefix from matching another.
    if not key_prefix or not key_prefix.endswith("/"):
        raise ValueError("key_prefix must be a non-empty folder prefix ending in '/'.")

    literal = _to_vector_literal(query_vector)
    conn = psycopg2.connect(**require_db_config())
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bucket, object_key, chunk_index, chunk_text,
                   embedding <=> %s::vector AS distance
            FROM document_chunks
            WHERE embedding IS NOT NULL
              AND starts_with(object_key, %s)
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (literal, key_prefix, literal, top_k),
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    return [
        {
            "bucket": bucket,
            "key": key,
            "chunk_index": chunk_index,
            "text": text,
            "distance": float(distance),
        }
        for bucket, key, chunk_index, text, distance in rows
        if float(distance) <= MAX_DISTANCE
    ]
