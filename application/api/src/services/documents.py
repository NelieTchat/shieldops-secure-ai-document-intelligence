import json
import re
import uuid
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from psycopg2 import errors

import config
from db import get_connection

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

@lru_cache(maxsize=1)
def _s3():
    return boto3.client("s3", region_name=config.AWS_REGION)

@lru_cache(maxsize=1)
def _sqs():
    return boto3.client("sqs", region_name=config.AWS_REGION)

def validate_filename(filename: str) -> str:
    """Return the lowercase extension, or raise ValueError."""
    name = filename.strip()
    if not name or len(name) > 255:
        raise ValueError("Invalid file name.")
    if "/" in name or "\\" in name or ".." in name or _CONTROL_CHARS.search(name):
        raise ValueError("Invalid file name.")
    extension = ("." + name.rsplit(".", 1)[-1]).lower() if "." in name else ""
    if extension not in config.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed: {allowed}")
    return extension

def build_object_key(owner_id: str, doc_id: str, extension: str) -> str:
    # The owner is part of the key; the user-supplied file name never is.
    return f"{config.UPLOAD_PREFIX}/{owner_id}/{doc_id}{extension}"

def create_document(owner_id: str, filename: str, size_bytes: int) -> dict:
    extension = validate_filename(filename)
    doc_id = str(uuid.uuid4())
    object_key = build_object_key(owner_id, doc_id, extension)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (id, owner_id, filename, object_key, size_bytes) "
            "VALUES (%s, %s, %s, %s, %s);",
            (doc_id, owner_id, filename.strip(), object_key, size_bytes),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return {"id": doc_id, "filename": filename.strip(), "object_key": object_key,
            "size_bytes": size_bytes}

def get_owned(owner_id: str, doc_id: str) -> dict | None:
    """Return the document only if this user owns it; otherwise None."""
    try:
        uuid.UUID(doc_id)
    except ValueError:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id::text, filename, object_key, size_bytes FROM documents "
            "WHERE id = %s AND owner_id = %s;",
            (doc_id, owner_id),
        )
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if row is None:
        return None
    return {"id": row[0], "filename": row[1], "object_key": row[2], "size_bytes": row[3]}

def _pipeline_state(conn, keys: list[str]):
    received: set[str] = set()
    chunks: dict[str, int] = {}
    if not keys:
        return received, chunks
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT object_key FROM ingestion_status WHERE object_key = ANY(%s);",
            (keys,),
        )
        received = {row[0] for row in cur.fetchall()}
    except errors.UndefinedTable:
        conn.rollback()  # the pipeline tables do not exist yet
    try:
        cur.execute(
            "SELECT object_key, count(*) FROM document_chunks "
            "WHERE object_key = ANY(%s) GROUP BY object_key;",
            (keys,),
        )
        chunks = {row[0]: row[1] for row in cur.fetchall()}
    except errors.UndefinedTable:
        conn.rollback()
    cur.close()
    return received, chunks

def status_for(key: str, received: set[str], chunks: dict[str, int]) -> str:
    if chunks.get(key, 0) > 0:
        return "processed"
    if key in received:
        return "received"
    return "awaiting_ingestion"

def list_documents(owner_id: str) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id::text, filename, object_key, size_bytes, created_at "
            "FROM documents WHERE owner_id = %s ORDER BY created_at DESC;",
            (owner_id,),
        )
        rows = cur.fetchall()
        cur.close()
        received, chunks = _pipeline_state(conn, [row[2] for row in rows])
    finally:
        conn.close()
    return [
        {
            "id": row[0],
            "filename": row[1],
            "size_bytes": row[3],
            "status": status_for(row[2], received, chunks),
            "created_at": row[4],
        }
        for row in rows
    ]

def presign_upload(object_key: str) -> dict:
    if not config.DOCUMENTS_BUCKET:
        raise RuntimeError("DOCUMENTS_BUCKET is not set.")
    return _s3().generate_presigned_post(
        Bucket=config.DOCUMENTS_BUCKET,
        Key=object_key,
        Conditions=[["content-length-range", 1, config.MAX_UPLOAD_BYTES]],
        ExpiresIn=config.PRESIGNED_URL_EXPIRES_SECONDS,
    )

def object_exists(object_key: str) -> bool:
    if not config.DOCUMENTS_BUCKET:
        raise RuntimeError("DOCUMENTS_BUCKET is not set.")
    try:
        _s3().head_object(Bucket=config.DOCUMENTS_BUCKET, Key=object_key)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise

def send_upload_event(object_key: str) -> None:
    """Sandbox-only shim: send the S3-style event ingestion-service expects."""
    if not config.INGESTION_QUEUE_URL or not config.DOCUMENTS_BUCKET:
        raise RuntimeError("INGESTION_QUEUE_URL and DOCUMENTS_BUCKET must be set.")
    body = {"detail": {"bucket": {"name": config.DOCUMENTS_BUCKET},
                       "object": {"key": object_key}}}
    _sqs().send_message(QueueUrl=config.INGESTION_QUEUE_URL, MessageBody=json.dumps(body))
