import sqlite3
import json
from datetime import datetime

DB_PATH = "kno_tic.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT    NOT NULL,
            risk_score  INTEGER NOT NULL,
            category    TEXT    NOT NULL,
            result_json TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    try:
        conn.execute("ALTER TABLE analyses ADD COLUMN feedback TEXT DEFAULT NULL")
        conn.commit()
    except Exception:
        pass
    conn.close()


def save_analysis(content: str, result: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO analyses (content, risk_score, category, result_json, created_at) VALUES (?,?,?,?,?)",
        (
            content,
            result.get("risk_score", 0),
            result.get("category", "desconocido"),
            json.dumps(result, ensure_ascii=False),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    if row_id is None:
        raise RuntimeError("Failed to insert analysis row")
    return row_id


def save_feedback(analysis_id: int, value: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE analyses SET feedback = ? WHERE id = ?",
        (value, analysis_id),
    )
    conn.commit()
    conn.close()


def get_history(search: str = "", category: str = "") -> list:
    conn = sqlite3.connect(DB_PATH)
    query = """SELECT id, risk_score, category, content, created_at, result_json, feedback
               FROM analyses WHERE 1=1"""
    params = []
    if search:
        query += " AND content LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY id DESC LIMIT 50"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "risk_score": r[1],
            "category": r[2],
            "preview": r[3][:60] + "..." if len(r[3]) > 60 else r[3],
            "date": r[4],
            "full_content": r[3],
            "result": json.loads(r[5]),
            "feedback": r[6],
        }
        for r in rows
    ]


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    if total == 0:
        conn.close()
        return {"total": 0, "phishing_percent": 0, "top_tactic": None}

    threat_count = conn.execute(
        "SELECT COUNT(*) FROM analyses WHERE risk_score >= 60"
    ).fetchone()[0]

    all_results = conn.execute("SELECT result_json FROM analyses").fetchall()
    category_rows = conn.execute(
        "SELECT category, COUNT(*) FROM analyses GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()

    indicator_counts: dict[str, int] = {}
    for (raw,) in all_results:
        for ind in json.loads(raw).get("indicators", []):
            t = ind.get("type", "otro")
            indicator_counts[t] = indicator_counts.get(t, 0) + 1

    top_tactic = max(indicator_counts, key=lambda k: indicator_counts[k]) if indicator_counts else None
    by_category = {row[0]: row[1] for row in category_rows}

    return {
        "total": total,
        "phishing_percent": round(threat_count / total * 100),
        "top_tactic": top_tactic,
        "by_category": by_category,
    }
