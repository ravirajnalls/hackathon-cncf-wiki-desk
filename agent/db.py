"""SQLite episodic + operational memory."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "memory.db"
LOG_FILE = Path(__file__).parent.parent / "wiki" / "log.md"


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
    export_decision_log()


def export_decision_log(limit: int = 200):
    """Mirror the decisions table into wiki/log.md so it's visible in git and on the site."""
    def cell(value) -> str:
        return str(value or "").replace("|", "/").replace("\n", " ")[:160]

    with get_db() as conn:
        rows = conn.execute(
            "SELECT time, decision, reason, expected, outcome FROM decisions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    lines = [
        "# Decision Log", "",
        "Every choice the agent makes, with its reason, what it expected and what happened. Newest first.", "",
        "| Time (UTC) | Decision | Reason | Expected | Outcome |",
        "|------|----------|--------|----------|---------|",
    ]
    lines += [f"| {cell(r['time'])} | {cell(r['decision'])} | {cell(r['reason'])} | "
              f"{cell(r['expected'])} | {cell(r['outcome'])} |" for r in rows]
    LOG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
