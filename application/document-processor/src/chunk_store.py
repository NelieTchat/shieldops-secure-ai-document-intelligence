import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_table_exists():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY,
            bucket TEXT NOT NULL,
            object_key TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Table ready: document_chunks")

def save_chunks(bucket: str, key: str, chunks: list[str]):
    conn = get_connection()
    cur = conn.cursor()
    # Replace, don't append — makes reprocessing the same file safe.
    cur.execute(
        "DELETE FROM document_chunks WHERE bucket = %s AND object_key = %s;",
        (bucket, key),
    )
    for index, chunk in enumerate(chunks):
        cur.execute(
            "INSERT INTO document_chunks (bucket, object_key, chunk_index, chunk_text) VALUES (%s, %s, %s, %s);",
            (bucket, key, index, chunk),
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Saved {len(chunks)} chunk(s) for {bucket}/{key}")
