#!/usr/bin/env python3
"""
Always-On Memory Agent Utility
Manages a persistent local SQLite database containing session metrics,
agent interactions, and derived insights across the Agentic Project Factory.
"""

import datetime
import sqlite3
import sys

DB_PATH = "memory.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT NOT NULL
    )
    """)

    # 2. Interactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        request TEXT NOT NULL,
        response TEXT NOT NULL,
        tokens_used INTEGER,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """)

    # 3. Insights table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insights (
        insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        category TEXT NOT NULL,
        insight_text TEXT NOT NULL,
        impact_score REAL DEFAULT 1.0,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """)

    # Indexing for high-performance querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_category ON insights (category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions (session_id)")

    conn.commit()
    conn.close()


def record_start(session_id):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        """
    INSERT OR REPLACE INTO sessions (session_id, start_time, status)
    VALUES (?, ?, ?)
    """,
        (session_id, now_str, "ACTIVE"),
    )
    conn.commit()
    conn.close()
    print(f"Session {session_id} marked ACTIVE.")


def record_complete(session_id):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        """
    UPDATE sessions
    SET end_time = ?, status = ?
    WHERE session_id = ?
    """,
        (now_str, "COMPLETED", session_id),
    )
    conn.commit()
    conn.close()
    print(f"Session {session_id} marked COMPLETED.")


def add_interaction(session_id, request, response, tokens=0):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        """
    INSERT INTO interactions (session_id, timestamp, request, response, tokens_used)
    VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, now_str, request, response, tokens),
    )
    conn.commit()
    conn.close()
    print("Interaction logged successfully.")


def add_insight(session_id, category, insight_text, impact_score=1.0):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        """
    INSERT INTO insights (session_id, timestamp, category, insight_text, impact_score)
    VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, now_str, category, insight_text, impact_score),
    )
    conn.commit()
    conn.close()
    print("Insight captured successfully.")


def query_insights(query_str):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    # Simple case-insensitive matching
    cursor.execute(
        """
    SELECT i.insight_text, i.category, i.impact_score, i.timestamp, s.session_id
    FROM insights i
    JOIN sessions s ON i.session_id = s.session_id
    WHERE i.insight_text LIKE ? OR i.category LIKE ?
    ORDER BY i.impact_score DESC, i.timestamp DESC
    """,
        (f"%{query_str}%", f"%{query_str}%"),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"No insights found matching '{query_str}'.")
        return

    print(f"\n--- DISCOVERED INSIGHTS FOR '{query_str}' ---")
    for row in rows:
        print(f"[{row['category'].upper()}] (Score: {row['impact_score']}) (Session: {row['session_id'][:8]})")
        print(f"  > {row['insight_text']}")
        print(f"  Date: {row['timestamp']}\n")


def show_summary():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM sessions")
    sess_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM interactions")
    inter_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM insights")
    ins_cnt = cursor.fetchone()["cnt"]

    print("\n================================================")
    print("      ALWAYS-ON MEMORY SUMMARY PLATFORM")
    print("================================================")
    print(f"Total Sessions Captured:     {sess_cnt}")
    print(f"Total Interactions Logged:   {inter_cnt}")
    print(f"Total Insights Cataloged:    {ins_cnt}")
    print("================================================")

    cursor.execute("""
    SELECT category, COUNT(*) as cnt
    FROM insights
    GROUP BY category
    ORDER BY cnt DESC
    """)
    print("\nInsights by Category:")
    for row in cursor.fetchall():
        print(f"  * {row['category'].capitalize()}: {row['cnt']}")

    cursor.execute("""
    SELECT insight_text, category, impact_score
    FROM insights
    ORDER BY impact_score DESC
    LIMIT 5
    """)
    print("\nTop 5 High-Impact Insights:")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. [{row['category'].upper()}] (Impact: {row['impact_score']})")
        print(f"     > {row['insight_text']}")
    print("================================================\n")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 bin/memory_agent.py [init | start <session_id> | "
            "complete <session_id> | add-interaction <session_id> <req> <res> "
            "[tokens] | add-insight <session_id> <cat> <text> [score] | "
            "query <str> | summary]"
        )
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        init_db()
        print("Database initialized.")
    elif cmd == "start":
        if len(sys.argv) < 3:
            print("Error: Missing session ID.")
            sys.exit(1)
        record_start(sys.argv[3]) if len(sys.argv) > 3 else record_start(sys.argv[2])
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Error: Missing session ID.")
            sys.exit(1)
        record_complete(sys.argv[2])
    elif cmd == "add-interaction":
        if len(sys.argv) < 5:
            print("Error: Missing arguments.")
            sys.exit(1)
        tokens = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        add_interaction(sys.argv[2], sys.argv[3], sys.argv[4], tokens)
    elif cmd == "add-insight":
        if len(sys.argv) < 5:
            print("Error: Missing arguments.")
            sys.exit(1)
        score = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
        add_insight(sys.argv[2], sys.argv[3], sys.argv[4], score)
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Error: Missing query string.")
            sys.exit(1)
        query_insights(sys.argv[2])
    elif cmd == "summary":
        show_summary()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
