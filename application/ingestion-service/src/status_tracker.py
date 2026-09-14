import psycopg2

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="shieldops",
    user="postgres",
    password="localdevpassword",
)


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_table_exists():
    """Creates the ingestion_status table if it doesn't already exist."""
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
    """Inserts one row recording what happened to a given upload."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ingestion_status (bucket, object_key, status) VALUES (%s, %s, %s);",
        (bucket, object_key, status),
    )
    conn.commit()
    cur.close()
    conn.close()
