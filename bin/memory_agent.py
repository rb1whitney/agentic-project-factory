#!/usr/bin/env python3
"""
Always-On Memory Agent Utility (v2.0)
Manages a persistent local SQLite database containing session metrics,
agent interactions, derived insights, entity graphs, and user preferences
across the Agentic Project Factory.

Triple-Layer Hybrid Stack:
  Layer 1 (Core/RAM)  - Managed by @skill-episodic-memory (context paging)
  Layer 2 (Recall/Disk) - interactions + insights tables (this file)
  Layer 3 (Graph/Relational) - entities + relationships tables (this file)
  + User Preferences - behavioral preference tracking
"""

import datetime
import re
import sqlite3
import sys

DB_PATH = "memory.db"

# -- Extraction patterns for consolidation pipeline --

# Relationship patterns: "X requires Y", "X uses Y", etc.
RELATIONSHIP_PATTERNS = [
    (r"(\b[A-Z][\w\s-]+\b)\s+requires\s+(\b[A-Z][\w\s-]+\b)", "requires"),
    (r"(\b[A-Z][\w\s-]+\b)\s+uses\s+(\b[A-Z][\w\s-]+\b)", "uses"),
    (r"(\b[A-Z][\w\s-]+\b)\s+impacts?\s+(\b[A-Z][\w\s-]+\b)", "impacts"),
    (r"(\b[A-Z][\w\s-]+\b)\s+migrated?\s+to\s+(\b[A-Z][\w\s-]+\b)", "migrated_to"),
    (r"(\b[A-Z][\w\s-]+\b)\s+depends?\s+on\s+(\b[A-Z][\w\s-]+\b)", "depends_on"),
    (r"(\b[A-Z][\w\s-]+\b)\s+enforces?\s+(\b[A-Z][\w\s-]+\b)", "enforces"),
    (r"(\b[A-Z][\w\s-]+\b)\s+configures?\s+(\b[A-Z][\w\s-]+\b)", "configures"),
    (r"(\b[A-Z][\w\s-]+\b)\s+blocks?\s+(\b[A-Z][\w\s-]+\b)", "blocks"),
    (r"(\b[A-Z][\w\s-]+\b)\s+replaces?\s+(\b[A-Z][\w\s-]+\b)", "replaces"),
    (r"(\b[A-Z][\w\s-]+\b)\s+extends?\s+(\b[A-Z][\w\s-]+\b)", "extends"),
]

# Preference indicators
PREFERENCE_PATTERNS = [
    r"(?:always|prefer|default\s+to|switch\s+to|use)\s+(.+)",
    r"(?:never|avoid|don't|do\s+not)\s+(.+)",
]

# Entity extraction: capitalized multi-word names, agent names, tool names
ENTITY_PATTERN = re.compile(
    r"\b(?:"
    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"  # Multi-word proper nouns
    r"|@\w[\w-]+"  # Agent/skill references
    r"|[A-Z][A-Z_]{2,}"  # Acronyms (IAM, OIDC, OTLP, etc.)
    r"|(?:bin|tools)/[\w./]+"  # Tool paths
    r"|\.agent/[\w./]+"  # Agent config paths
    r"|memory\.db"  # Known artifacts
    r"|conductor/[\w./]+"  # Conductor paths
    r")\b"
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # WAL not available (e.g., read-only FS)
    conn.execute("PRAGMA foreign_keys=ON")
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

    # 2. Interactions table (Recall Layer)
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

    # 3. Insights table (Recall Layer)
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

    # 4. Entities table (Graph Layer)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """)

    # 5. Relationships table (Graph Layer)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS relationships (
        rel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        predicate TEXT NOT NULL,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES entities (entity_id),
        FOREIGN KEY (target_id) REFERENCES entities (entity_id),
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """)

    # 6. User Preferences table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        pref_id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        source TEXT DEFAULT 'manual',
        updated_at TEXT NOT NULL
    )
    """)

    # Indexes for high-performance querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_category ON insights (category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions (session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_source ON relationships (source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_target ON relationships (target_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON entities (name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pref_key ON user_preferences (key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_timestamp ON insights (timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions (timestamp)")

    conn.commit()
    conn.close()


def record_start(session_id):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
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
    """Mark session COMPLETED and trigger consolidation pipeline."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
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

    # Trigger consolidation pipeline
    _consolidate_session(session_id)


def add_interaction(session_id, request, response, tokens=0):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
    # Truncate to 500 chars max for storage efficiency
    request_trunc = request[:500] if len(request) > 500 else request
    response_trunc = response[:500] if len(response) > 500 else response
    cursor.execute(
        """
    INSERT INTO interactions (session_id, timestamp, request, response, tokens_used)
    VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, now_str, request_trunc, response_trunc, tokens),
    )
    conn.commit()
    conn.close()
    print("Interaction logged.")


def add_insight(session_id, category, insight_text, impact_score=1.0):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
    cursor.execute(
        """
    INSERT INTO insights (session_id, timestamp, category, insight_text, impact_score)
    VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, now_str, category, insight_text, impact_score),
    )
    conn.commit()
    conn.close()
    print("Insight captured.")


def set_preference(key, value, source="manual"):
    """Set or update a user preference (upsert)."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
    cursor.execute(
        """
    INSERT INTO user_preferences (key, value, source, updated_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        source = excluded.source,
        updated_at = excluded.updated_at
    """,
        (key, value, source, now_str),
    )
    conn.commit()
    conn.close()
    print(f"Preference set: {key} = {value}")


# -- Consolidation Pipeline --


def _classify_entity(name):
    """Classify entity type based on naming patterns."""
    if name.startswith("@"):
        return "agent"
    if "/" in name:
        return "path"
    if name == name.upper() and len(name) >= 3:
        return "acronym"
    if name == "memory.db":
        return "artifact"
    return "concept"


def _get_or_create_entity(cursor, session_id, name, timestamp):
    """Get existing entity_id or create new entity. Returns entity_id."""
    cursor.execute("SELECT entity_id FROM entities WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row["entity_id"]
    entity_type = _classify_entity(name)
    cursor.execute(
        "INSERT INTO entities (session_id, name, type, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, name, entity_type, timestamp),
    )
    return cursor.lastrowid


def _extract_entities(text):
    """Extract entity names from text using pattern matching."""
    matches = ENTITY_PATTERN.findall(text)
    # Deduplicate and clean
    seen = set()
    entities = []
    for m in matches:
        m_clean = m.strip()
        if m_clean and m_clean.lower() not in seen and len(m_clean) > 2:
            seen.add(m_clean.lower())
            entities.append(m_clean)
    return entities


def _extract_relationships_from_text(text):
    """Extract (subject, predicate, object) triples from text."""
    triples = []
    for pattern, predicate in RELATIONSHIP_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            subj = match.group(1).strip()
            obj = match.group(2).strip()
            if len(subj) > 2 and len(obj) > 2:
                triples.append((subj, predicate, obj))
    return triples


def _extract_preferences_from_text(text):
    """Extract preference key-value pairs from interaction text."""
    prefs = {}
    # "always use X" / "prefer X" / "default to X" / "switch to X"
    for match in re.finditer(
        r"(?:always\s+use|prefer|default\s+to|switch\s+to)\s+[\"']?([^\"'\n,.]+)[\"']?", text, re.IGNORECASE
    ):
        val = match.group(1).strip()
        if len(val) > 2:
            # Derive key from context
            key = _derive_preference_key(val, text)
            prefs[key] = val

    # "never X" / "avoid X" / "don't X"
    for match in re.finditer(r"(?:never|avoid|don't|do\s+not)\s+[\"']?([^\"'\n,.]+)[\"']?", text, re.IGNORECASE):
        val = match.group(1).strip()
        if len(val) > 2:
            key = _derive_preference_key(val, text)
            prefs[key] = f"NEVER: {val}"

    return prefs


def _derive_preference_key(value, context):
    """Derive a preference key from value and surrounding context."""
    val_lower = value.lower()
    if any(kw in val_lower for kw in ["model", "claude", "gemini", "opus", "sonnet", "flash"]):
        return "model_preference"
    if any(kw in val_lower for kw in ["branch", "git", "commit"]):
        return "git_workflow"
    if any(kw in val_lower for kw in ["format", "style", "prose", "markdown"]):
        return "output_style"
    if any(kw in val_lower for kw in ["review", "audit", "check"]):
        return "review_depth"
    if any(kw in val_lower for kw in ["test", "tdd", "unit"]):
        return "testing_preference"
    if any(kw in val_lower for kw in ["emoji", "icon"]):
        return "emoji_policy"
    # Fallback: slugify value
    slug = re.sub(r"[^a-z0-9]+", "_", val_lower)[:40].strip("_")
    return f"user_pref_{slug}"


def _consolidate_session(session_id):
    """Run the full consolidation pipeline over a completed session.

    Extracts entities, relationships, and preferences from all
    interactions logged during the session.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch all interactions for this session
    cursor.execute(
        "SELECT request, response, timestamp FROM interactions WHERE session_id = ?",
        (session_id,),
    )
    interactions = cursor.fetchall()

    if not interactions:
        print(f"Consolidation: No interactions found for session {session_id}. Skipping.")
        conn.close()
        return

    now_str = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
    entity_count = 0
    rel_count = 0
    pref_count = 0

    # Also include insights text for entity/relationship extraction
    cursor.execute(
        "SELECT insight_text FROM insights WHERE session_id = ?",
        (session_id,),
    )
    insight_rows = cursor.fetchall()

    # Build combined text corpus from interactions + insights
    all_text_blocks = []
    for row in interactions:
        all_text_blocks.append(row["request"])
        all_text_blocks.append(row["response"])
    for row in insight_rows:
        all_text_blocks.append(row["insight_text"])

    combined_text = "\n".join(all_text_blocks)

    # Phase 1: Extract and store entities
    entity_names = _extract_entities(combined_text)
    for name in entity_names:
        _get_or_create_entity(cursor, session_id, name, now_str)
        entity_count += 1

    # Phase 2: Extract and store relationships
    triples = _extract_relationships_from_text(combined_text)
    for subj, predicate, obj in triples:
        src_id = _get_or_create_entity(cursor, session_id, subj, now_str)
        tgt_id = _get_or_create_entity(cursor, session_id, obj, now_str)
        # Check for duplicate relationship
        cursor.execute(
            "SELECT rel_id FROM relationships WHERE source_id = ? AND target_id = ? AND predicate = ?",
            (src_id, tgt_id, predicate),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO relationships (source_id, target_id, predicate, session_id, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (src_id, tgt_id, predicate, session_id, now_str),
            )
            rel_count += 1

    # Phase 3: Extract and store preferences (auto-detected only; never overwrite manual)
    for row in interactions:
        prefs = _extract_preferences_from_text(row["request"])
        for key, val in prefs.items():
            # Check if a manual preference exists -- never overwrite manual with auto
            cursor.execute("SELECT source FROM user_preferences WHERE key = ?", (key,))
            existing = cursor.fetchone()
            if existing and existing["source"] == "manual":
                continue
            cursor.execute(
                """
            INSERT INTO user_preferences (key, value, source, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
                (key, val, f"auto:{session_id}", now_str),
            )
            pref_count += 1

    conn.commit()
    conn.close()

    print(f"\nConsolidation complete for session {session_id}:")
    print(f"  Entities extracted:      {entity_count}")
    print(f"  Relationships extracted:  {rel_count}")
    print(f"  Preferences detected:    {pref_count}")


# -- Query Functions --


def query_insights(query_str):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
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


def query_graph(entity_name):
    """Find all relationships involving an entity."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Find entities matching the query
    cursor.execute(
        "SELECT entity_id, name, type FROM entities WHERE name LIKE ?",
        (f"%{entity_name}%",),
    )
    entities = cursor.fetchall()

    if not entities:
        print(f"No entities found matching '{entity_name}'.")
        conn.close()
        return

    print(f"\n--- GRAPH QUERY: '{entity_name}' ---")
    print(f"Matching entities: {len(entities)}\n")

    for ent in entities:
        print(f"[{ent['type'].upper()}] {ent['name']} (id:{ent['entity_id']})")

        # Outbound relationships (this entity -> other)
        cursor.execute(
            """
        SELECT r.predicate, e.name as target_name, e.type as target_type, r.timestamp
        FROM relationships r
        JOIN entities e ON r.target_id = e.entity_id
        WHERE r.source_id = ?
        ORDER BY r.timestamp DESC
        """,
            (ent["entity_id"],),
        )
        outbound = cursor.fetchall()

        # Inbound relationships (other -> this entity)
        cursor.execute(
            """
        SELECT r.predicate, e.name as source_name, e.type as source_type, r.timestamp
        FROM relationships r
        JOIN entities e ON r.source_id = e.entity_id
        WHERE r.target_id = ?
        ORDER BY r.timestamp DESC
        """,
            (ent["entity_id"],),
        )
        inbound = cursor.fetchall()

        if outbound:
            for rel in outbound:
                print(f"  -> {rel['predicate']} -> [{rel['target_type'].upper()}] {rel['target_name']}")
        if inbound:
            for rel in inbound:
                print(f"  <- {rel['predicate']} <- [{rel['source_type'].upper()}] {rel['source_name']}")
        if not outbound and not inbound:
            print("  (no relationships)")
        print()

    conn.close()


def query_preferences():
    """Display all stored user preferences."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value, source, updated_at FROM user_preferences ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No user preferences stored.")
        return

    print("\n--- USER PREFERENCES ---")
    for row in rows:
        print(f"  {row['key']}: {row['value']}")
        print(f"    Source: {row['source']} | Updated: {row['updated_at']}")
    print()


def show_recent(hours=24):
    """Show insights and interactions from the last N hours."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(hours=hours)).isoformat()

    # Recent insights
    cursor.execute(
        """
    SELECT insight_text, category, impact_score, timestamp, session_id
    FROM insights
    WHERE timestamp >= ?
    ORDER BY impact_score DESC, timestamp DESC
    """,
        (cutoff,),
    )
    insights = cursor.fetchall()

    # Recent interactions
    cursor.execute(
        """
    SELECT request, response, tokens_used, timestamp, session_id
    FROM interactions
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
    LIMIT 20
    """,
        (cutoff,),
    )
    interactions = cursor.fetchall()

    print("\n================================================")
    print(f"  MEMORY RECALL: Last {hours} hours")
    print("================================================")

    if insights:
        print(f"\nInsights ({len(insights)}):")
        for row in insights:
            print(f"  [{row['category'].upper()}] (Score: {row['impact_score']})")
            print(f"    > {row['insight_text']}")
            print(f"    {row['timestamp']}")
    else:
        print(f"\nNo insights in last {hours}h.")

    if interactions:
        print(f"\nInteractions ({len(interactions)}):")
        for row in interactions:
            req_short = row["request"][:80] + "..." if len(row["request"]) > 80 else row["request"]
            res_short = row["response"][:80] + "..." if len(row["response"]) > 80 else row["response"]
            print(f"  Q: {req_short}")
            print(f"  A: {res_short}")
            print(f"    Tokens: {row['tokens_used']} | {row['timestamp']}")
    else:
        print(f"\nNo interactions in last {hours}h.")

    print("================================================\n")
    conn.close()


def show_stats():
    """Enhanced summary with graph and preference counts."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM sessions")
    sess_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM interactions")
    inter_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM insights")
    ins_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM entities")
    ent_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM relationships")
    rel_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM user_preferences")
    pref_cnt = cursor.fetchone()["cnt"]

    # Active sessions
    cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE status = 'ACTIVE'")
    active_cnt = cursor.fetchone()["cnt"]

    print("\n================================================")
    print("   ALWAYS-ON MEMORY: SYSTEM HEALTH")
    print("================================================")
    print(f"  Sessions:        {sess_cnt} (active: {active_cnt})")
    print(f"  Interactions:    {inter_cnt}")
    print(f"  Insights:        {ins_cnt}")
    print(f"  Graph Entities:  {ent_cnt}")
    print(f"  Graph Relations: {rel_cnt}")
    print(f"  Preferences:     {pref_cnt}")
    print("================================================")

    # Category breakdown
    cursor.execute("""
    SELECT category, COUNT(*) as cnt
    FROM insights
    GROUP BY category
    ORDER BY cnt DESC
    """)
    cats = cursor.fetchall()
    if cats:
        print("\nInsights by Category:")
        for row in cats:
            print(f"  * {row['category'].capitalize()}: {row['cnt']}")

    # Top insights
    cursor.execute("""
    SELECT insight_text, category, impact_score
    FROM insights
    ORDER BY impact_score DESC
    LIMIT 5
    """)
    top = cursor.fetchall()
    if top:
        print("\nTop 5 High-Impact Insights:")
        for i, row in enumerate(top, 1):
            print(f"  {i}. [{row['category'].upper()}] (Impact: {row['impact_score']})")
            print(f"     > {row['insight_text']}")

    # Entity types
    cursor.execute("""
    SELECT type, COUNT(*) as cnt
    FROM entities
    GROUP BY type
    ORDER BY cnt DESC
    """)
    etypes = cursor.fetchall()
    if etypes:
        print("\nGraph Entities by Type:")
        for row in etypes:
            print(f"  * {row['type']}: {row['cnt']}")

    # Preferences
    cursor.execute("SELECT key, value FROM user_preferences ORDER BY updated_at DESC LIMIT 5")
    prefs = cursor.fetchall()
    if prefs:
        print("\nUser Preferences:")
        for row in prefs:
            print(f"  * {row['key']}: {row['value']}")

    print("================================================\n")
    conn.close()


def show_summary():
    """Legacy summary command -- redirects to stats."""
    show_stats()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 bin/memory_agent.py <command> [args]\n"
            "\n"
            "Commands:\n"
            "  init                              Initialize/upgrade database schema\n"
            "  start <session_id>                Start a new session\n"
            "  complete <session_id>             Complete session + run consolidation\n"
            "  add-interaction <sid> <req> <res> [tokens]  Log an interaction\n"
            "  add-insight <sid> <cat> <text> [score]      Capture an insight\n"
            "  set-preference <key> <value>      Set a user preference\n"
            "  query <str>                       Search insights by keyword\n"
            "  query-graph <entity>              Find entity relationships\n"
            "  query-preferences                 Show all user preferences\n"
            "  recent [hours]                    Show last N hours (default 24)\n"
            "  stats                             Full system health report\n"
            "  summary                           Alias for stats\n"
        )
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        init_db()
        print("Database initialized/upgraded.")
    elif cmd == "start":
        if len(sys.argv) < 3:
            print("Error: Missing session ID.")
            sys.exit(1)
        record_start(sys.argv[2])
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Error: Missing session ID.")
            sys.exit(1)
        record_complete(sys.argv[2])
    elif cmd == "add-interaction":
        if len(sys.argv) < 5:
            print("Error: Usage: add-interaction <session_id> <request> <response> [tokens]")
            sys.exit(1)
        tokens = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        add_interaction(sys.argv[2], sys.argv[3], sys.argv[4], tokens)
    elif cmd == "add-insight":
        if len(sys.argv) < 5:
            print("Error: Usage: add-insight <session_id> <category> <insight_text> [score]")
            sys.exit(1)
        score = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
        add_insight(sys.argv[2], sys.argv[3], sys.argv[4], score)
    elif cmd == "set-preference":
        if len(sys.argv) < 4:
            print("Error: Usage: set-preference <key> <value>")
            sys.exit(1)
        set_preference(sys.argv[2], sys.argv[3])
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Error: Missing query string.")
            sys.exit(1)
        query_insights(sys.argv[2])
    elif cmd == "query-graph":
        if len(sys.argv) < 3:
            print("Error: Missing entity name.")
            sys.exit(1)
        query_graph(sys.argv[2])
    elif cmd == "query-preferences":
        query_preferences()
    elif cmd == "recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        show_recent(hours)
    elif cmd == "stats":
        show_stats()
    elif cmd == "summary":
        show_summary()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
