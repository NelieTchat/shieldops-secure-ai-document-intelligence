import os
import psycopg2

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5432")),
    dbname=os.environ.get("DB_NAME", "shieldops"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "localdevpassword"),
)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_table_exists():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_status (
            id SERIAL PRIMARY KEY,
            bucket TEXT NOT NULL,
            object_key TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Table ready: ingestion_status")

def record_status(bucket: str, object_key: str, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ingestion_status (bucket, object_key, status) VALUES (%s, %s, %s);",
        (bucket, object_key, status),
    )
    conn.commit()
    cur.close()
    conn.close()
