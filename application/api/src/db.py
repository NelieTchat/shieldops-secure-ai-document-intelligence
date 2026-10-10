import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_tables():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY,
                owner_id UUID NOT NULL REFERENCES users(id),
                filename TEXT NOT NULL,
                object_key TEXT NOT NULL UNIQUE,
                size_bytes BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS documents_owner_idx ON documents (owner_id);"
        )
        conn.commit()
        cur.close()
        print("Tables ready: users, documents")
    finally:
        conn.close()
