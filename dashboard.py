"""Cloud Native Brain demo dashboard: orders, revenue, Terac clarity, decisions, wiki diff.

  streamlit run dashboard.py
"""

import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DB_PATH = ROOT / "memory.db"
STUDIES_DIR = ROOT / "studies"
PRICE_USD = float(os.environ.get("WHOP_PRICE_USD", "3"))

st.set_page_config(page_title="Cloud Native Brain", page_icon="📚", layout="wide")
st.title("Cloud Native Brain")
st.caption("An agent-run research desk. Customers pay, the agent researches, the wiki gets delivered, "
           "and every order makes the next one better.")


def query(sql: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql_query(sql, conn)
        except Exception:
            return pd.DataFrame()


# Test orders from development are hidden from revenue
orders = query("SELECT whop_id, topic, paid_at, delivered_at, status, delivery_url FROM orders "
               "WHERE whop_id NOT LIKE 'test%' ORDER BY paid_at DESC")
decisions = query("SELECT time, decision, reason, expected, outcome FROM decisions "
                  "WHERE decision != 'test' ORDER BY id DESC")
videos = query("SELECT video_id, title, speaker, year, ingested_at FROM videos ORDER BY ingested_at DESC")
pages = [p for p in (ROOT / "wiki").rglob("*.md")
         if p.relative_to(ROOT / "wiki").as_posix() not in ("index.md", "log.md")
         and "Research" not in p.parts]

delivered = orders[orders["status"] == "delivered"] if not orders.empty else orders


def minutes_to_deliver(df: pd.DataFrame) -> pd.Series:
    paid = pd.to_datetime(df["paid_at"], errors="coerce", utc=True)
    done = pd.to_datetime(df["delivered_at"], errors="coerce", utc=True)
    return (done - paid).dt.total_seconds() / 60


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", f"${len(delivered) * PRICE_USD:,.0f}")
c2.metric("Orders delivered", f"{len(delivered)} / {len(orders)}")
c3.metric("Wiki pages", len(pages))
c4.metric("Talks ingested", len(videos))
if not delivered.empty:
    mins = minutes_to_deliver(delivered).dropna()
    c5.metric("Median delivery", f"{mins.median():.0f} min" if not mins.empty else "—")
else:
    c5.metric("Median delivery", "—")

# ---------- Terac before / after ----------
st.subheader("Human in the loop: Terac clarity study")


def load_round(n: int) -> dict | None:
    p = STUDIES_DIR / f"round{n}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


r1, r2 = load_round(1), load_round(2)
if r1 is None:
    st.info("No Terac study launched yet: `python -m agent.tools.run_terac_study launch --round 1`")
else:
    before = avg([i.get("scores", {}).get("original") for i in r1["items"]])
    after = avg([i.get("scores", {}).get("variant") for i in r2["items"]]) if r2 else None
    win = avg([i.get("variant_win_rate") for i in r2["items"]]) if r2 else None
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Before (original wiki)", before if before is not None else "waiting")
    t2.metric("After (agent rewrite)", after if after is not None else "waiting",
              delta=round(after - before, 2) if before is not None and after is not None else None)
    t3.metric("Prefer the rewrite", f"{win:.0%}" if win is not None else "waiting")
    t4.metric("Panelists", f"{r1.get('n_submissions', 0)} + {r2.get('n_submissions', 0) if r2 else 0}")

    rows = []
    r2_items = {i["section"]: i for i in r2["items"]} if r2 else {}
    for item in r1["items"]:
        rows.append({
            "Section": item["section"],
            "Before": item.get("scores", {}).get("original"),
            "Plain variant (R1)": item.get("scores", {}).get("variant"),
            "After (R2)": r2_items.get(item["section"], {}).get("scores", {}).get("variant"),
            "Top complaint": (item.get("complaints") or [""])[0],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(f"Round 1: {r1.get('status')}"
               + (f" · {r1['dashboard_url']}" if r1.get("dashboard_url") else "")
               + (f" · Round 2: {r2.get('status')}" if r2 else ""))

    style = ROOT / "agent" / "style_guide.md"
    if style.exists():
        with st.expander("Writing rules the agent learned from readers (used in every new compile)"):
            st.markdown(style.read_text(encoding="utf-8"))

# ---------- orders & decisions ----------
left, right = st.columns(2)
with left:
    st.subheader("Orders")
    if orders.empty:
        st.write("No orders yet.")
    else:
        view = orders.copy()
        view["minutes"] = minutes_to_deliver(view).round(1)
        st.dataframe(view[["paid_at", "topic", "status", "minutes", "delivery_url"]],
                     hide_index=True, use_container_width=True)
with right:
    st.subheader("Decision log")
    if decisions.empty:
        st.write("No decisions logged yet.")
    else:
        st.dataframe(decisions, hide_index=True, use_container_width=True, height=320)

# ---------- memory ----------
st.subheader("Memory: the wiki updates itself")
log = subprocess.run(["git", "log", "--oneline", "-15", "--", "wiki"], cwd=ROOT,
                     capture_output=True, text=True).stdout
st.code(log or "No wiki commits yet.", language="text")
latest = subprocess.run(["git", "log", "-1", "-p", "--stat", "--", "wiki"], cwd=ROOT,
                        capture_output=True, text=True).stdout
if latest:
    with st.expander("Latest wiki diff"):
        st.code(latest[:8000], language="diff")
if not videos.empty:
    with st.expander(f"Talks in memory ({len(videos)})"):
        st.dataframe(videos, hide_index=True, use_container_width=True)
