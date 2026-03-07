import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "audit.db")


def get_read_only_connection():
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
        check_same_thread=False,
        timeout=10
    )

    conn.row_factory = sqlite3.Row
    return conn


def get_write_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=10
    )

    # Improve concurrency + safety
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.row_factory = sqlite3.Row
    return conn