import os
import psycopg2

# No defaults on purpose: a missing database setting must stop the service. It must
# never fall back to a guessable password, or to a local socket (an empty host).
DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", ""),
    port=os.environ.get("DB_PORT", ""),
    dbname=os.environ.get("DB_NAME", ""),
    user=os.environ.get("DB_USER", ""),
    password=os.environ.get("DB_PASSWORD", ""),
)
_DB_ENV_NAMES = dict(host="DB_HOST", port="DB_PORT", dbname="DB_NAME", user="DB_USER", password="DB_PASSWORD")


def require_db_config() -> dict:
    """Return connection settings, or raise naming the missing variables (never values)."""
    missing = [_DB_ENV_NAMES[key] for key, value in DB_CONFIG.items() if not value]
    if missing:
        raise RuntimeError("Missing required database settings: " + ", ".join(missing))
    return {**DB_CONFIG, "port": int(DB_CONFIG["port"])}

def get_connection():
    return psycopg2.connect(**require_db_config())

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
