import json
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH
from utils.database import connection


@contextmanager
def get_connection():
    with connection(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        yield db


def save_history(event_type, title, payload):
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO history (event_type, title, payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, title, json.dumps(payload, ensure_ascii=False), created_at),
        )
        return cursor.lastrowid


def list_history(limit=50):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, event_type, title, created_at
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_history(item_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, event_type, title, payload, created_at
            FROM history
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    return result
