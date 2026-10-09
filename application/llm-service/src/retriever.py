import psycopg2
from config import DB_CONFIG, TOP_K_MAX

def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

def retrieve_chunks(query_vector: list[float], top_k: int) -> list[dict]:
    if not 1 <= top_k <= TOP_K_MAX:
        raise ValueError(f"top_k must be between 1 and {TOP_K_MAX}.")

    literal = _to_vector_literal(query_vector)
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bucket, object_key, chunk_index, chunk_text,
                   embedding <=> %s::vector AS distance
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (literal, literal, top_k),
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
    ]
