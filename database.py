import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "jersey_sales.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jerseys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT NOT NULL,
                player_name TEXT NOT NULL DEFAULT '',
                size TEXT NOT NULL,
                initial_stock INTEGER NOT NULL,
                current_stock INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jersey_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                sold_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (jersey_id) REFERENCES jerseys(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
