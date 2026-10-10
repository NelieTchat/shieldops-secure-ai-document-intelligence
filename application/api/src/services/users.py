import uuid

from psycopg2 import errors

from db import get_connection

class UsernameTaken(Exception):
    pass

def create_user(username: str, password_hash: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) "
                "RETURNING id::text, username;",
                (username, password_hash),
            )
        except errors.UniqueViolation:
            conn.rollback()
            raise UsernameTaken()
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return {"id": row[0], "username": row[1]}
    finally:
        conn.close()

def get_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id::text, username, password_hash FROM users WHERE username = %s;",
            (username,),
        )
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2]}

def get_by_id(user_id: str) -> dict | None:
    try:
        uuid.UUID(user_id)
    except ValueError:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id::text, username FROM users WHERE id = %s;", (user_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if row is None:
        return None
    return {"id": row[0], "username": row[1]}
