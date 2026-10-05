"""Short SQLite transactions with explicit cleanup and concurrent reader support."""

from contextlib import contextmanager
from pathlib import Path
from time import monotonic, sleep

import config
import sqlite3


@contextmanager
def connection(database_path=None):
    path = Path(config.DB_PATH if database_path is None else database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=config.SQLITE_BUSY_TIMEOUT_SECONDS)
    try:
        db.row_factory = sqlite3.Row
        db.execute(
            f"PRAGMA busy_timeout = {int(config.SQLITE_BUSY_TIMEOUT_SECONDS * 1000)}"
        )
        db.execute("PRAGMA foreign_keys = ON")
        deadline = monotonic() + config.SQLITE_BUSY_TIMEOUT_SECONDS
        while True:
            try:
                if db.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                    db.execute("PRAGMA journal_mode = WAL")
                break
            except sqlite3.OperationalError as exc:
                code = getattr(exc, "sqlite_errorcode", 0) & 255
                if (
                    code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                    or monotonic() >= deadline
                ):
                    raise
                sleep(min(0.05, max(0, deadline - monotonic())))
        with db:
            yield db
    finally:
        db.close()
