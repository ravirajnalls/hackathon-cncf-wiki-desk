"""SQLite episodic + operational memory."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "memory.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whop_id TEXT UNIQUE,
            topic TEXT NOT NULL,
            paid_at TEXT,
            delivered_at TEXT,
            cost_usd REAL DEFAULT 0,
            delivery_url TEXT,
            status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            speaker TEXT,
            year TEXT,
            ingested_at TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            video_id UNINDEXED,
            t_start UNINDEXED,
            t_end UNINDEXED,
            text
        );

        CREATE TABLE IF NOT EXISTS studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT,
            version TEXT,
            terac_id TEXT,
            score REAL,
            n INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT DEFAULT (datetime('now')),
            decision TEXT,
            reason TEXT,
            expected TEXT,
            outcome TEXT
        );
    """)
    return conn


def log_decision(decision: str, reason: str, expected: str, outcome: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO decisions (decision, reason, expected, outcome) VALUES (?, ?, ?, ?)",
            (decision, reason, expected, outcome),
        )


def record_order(whop_id: str, topic: str, paid_at: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO orders (whop_id, topic, paid_at) VALUES (?, ?, ?)",
            (whop_id, topic, paid_at),
        )
        # The buyer may supply the topic after the first poll
        if topic and topic != "unknown":
            conn.execute("UPDATE orders SET topic = ? WHERE whop_id = ?", (topic, whop_id))


def get_order(whop_id: str):
    with get_db() as conn:
        return conn.execute("SELECT * FROM orders WHERE whop_id = ?", (whop_id,)).fetchone()


def set_order_status(whop_id: str, status: str):
    with get_db() as conn:
        conn.execute("UPDATE orders SET status = ? WHERE whop_id = ?", (status, whop_id))


def mark_delivered(whop_id: str, delivery_url: str, cost_usd: float):
    with get_db() as conn:
        conn.execute(
            """UPDATE orders SET delivered_at = datetime('now'), delivery_url = ?, cost_usd = ?, status = 'delivered'
               WHERE whop_id = ?""",
            (delivery_url, cost_usd, whop_id),
        )


def pending_orders():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE status = 'pending' ORDER BY paid_at"
        ).fetchall()


def video_ingested(video_id: str) -> bool:
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,)).fetchone() is not None


def record_video(video_id: str, title: str, speaker: str, year: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO videos (video_id, title, speaker, year, ingested_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (video_id, title, speaker, year),
        )


def search_chunks(query: str, limit: int = 10):
    with get_db() as conn:
        return conn.execute(
            """SELECT video_id, t_start, t_end, text FROM chunks
               WHERE chunks MATCH ? LIMIT ?""",
            (query, limit),
        ).fetchall()
