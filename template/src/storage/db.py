"""
SQLite storage for chat history (bonus: saved conversations) and analytics.

Three tables:
  conversations(id, username, title, created_at)
  messages(id, conversation_id, role, content, refused, seconds, input_tokens,
           output_tokens, search_query, sources_json, created_at)
  student_courses(username, program, code)      the course tracker's ticks
Assistant messages carry the answer's metadata, which is exactly what the analytics page reads.
"""

import json
import sqlite3
import uuid
from datetime import datetime

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY, username TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, content TEXT NOT NULL,
    refused INTEGER, seconds REAL, input_tokens INTEGER, output_tokens INTEGER,
    search_query TEXT, sources_json TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE TABLE IF NOT EXISTS student_courses (
    username TEXT NOT NULL, program TEXT NOT NULL, code TEXT NOT NULL,
    PRIMARY KEY (username, program, code));
"""

SOURCE_FIELDS = ("n", "citation", "doc_title", "section_title", "section_path", "page_start", "page_end",
                 "url", "kind", "text", "scores")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --- conversations ---------------------------------------------------------------

def create_conversation(username: str, title: str) -> str:
    conv_id = uuid.uuid4().hex
    with _connect() as c:
        c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (conv_id, username, title[:60], _now()))
    return conv_id


def list_conversations(username: str, limit: int = 30) -> list[dict]:
    with _connect() as c:
        rows = c.execute("SELECT * FROM conversations WHERE username = ? ORDER BY created_at DESC LIMIT ?",
                         (username, limit)).fetchall()
    return [dict(r) for r in rows]


def delete_conversation(conv_id: str, username: str) -> None:
    with _connect() as c:
        c.execute("DELETE FROM conversations WHERE id = ? AND username = ?", (conv_id, username))


# --- messages ------------------------------------------------------------------

def add_user_message(conv_id: str, content: str) -> None:
    with _connect() as c:
        c.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
                  (conv_id, content, _now()))


def add_assistant_message(conv_id: str, result: dict) -> None:
    d = result["debug"]
    sources = [{k: s.get(k) for k in SOURCE_FIELDS} for s in d["retrieved"]]
    with _connect() as c:
        c.execute(
            """INSERT INTO messages (conversation_id, role, content, refused, seconds, input_tokens,
               output_tokens, search_query, sources_json, created_at) VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conv_id, result["answer"], int(result["refused"]), d["seconds"], d["tokens"]["input"],
             d["tokens"]["output"], d["search_query"],
             json.dumps({"sources": [] if result["refused"] else sources, "debug": {
                 k: d[k] for k in ("question", "search_query", "best_cosine", "threshold", "refused_by_gate", "seconds", "tokens")},
                 "retrieved": sources, "cited": result.get("cited", []), "personal": result.get("personal", False),
                 "followups": result.get("followups", [])}, ensure_ascii=False),
             _now()))


def get_messages(conv_id: str) -> list[dict]:
    with _connect() as c:
        rows = c.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conv_id,)).fetchall()
    messages = []
    for r in rows:
        m = {"role": r["role"], "content": r["content"]}
        if r["role"] == "assistant" and r["sources_json"]:
            m["details"] = json.loads(r["sources_json"])
        messages.append(m)
    return messages


# --- course tracker ------------------------------------------------------------

def get_passed(username: str, program: str) -> set[str]:
    with _connect() as c:
        rows = c.execute("SELECT code FROM student_courses WHERE username = ? AND program = ?",
                         (username, program)).fetchall()
    return {r["code"] for r in rows}


def set_passed(username: str, program: str, codes: set[str]) -> None:
    with _connect() as c:
        c.execute("DELETE FROM student_courses WHERE username = ? AND program = ?", (username, program))
        c.executemany("INSERT INTO student_courses VALUES (?, ?, ?)", [(username, program, x) for x in sorted(codes)])


# --- analytics -------------------------------------------------------------------

def stats() -> dict:
    with _connect() as c:
        row = c.execute("""
            SELECT COUNT(*) AS answers, COALESCE(AVG(refused), 0) AS refusal_rate, COALESCE(AVG(seconds), 0) AS avg_seconds,
                   COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens
            FROM messages WHERE role = 'assistant'""").fetchone()
        convs = c.execute("SELECT COUNT(*), COUNT(DISTINCT username) FROM conversations").fetchone()
    return {**dict(row), "conversations": convs[0], "users": convs[1]}


def questions_per_day() -> list[dict]:
    with _connect() as c:
        rows = c.execute("""SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS questions
                            FROM messages WHERE role = 'user' GROUP BY day ORDER BY day""").fetchall()
    return [dict(r) for r in rows]


def recent_answers(limit: int = 500) -> list[dict]:
    """Each assistant answer joined with the question that preceded it."""
    with _connect() as c:
        rows = c.execute("""
            SELECT a.created_at, q.content AS question, a.search_query, a.refused, a.seconds,
                   a.input_tokens + a.output_tokens AS tokens
            FROM messages a JOIN messages q ON q.id = (
                SELECT MAX(id) FROM messages WHERE conversation_id = a.conversation_id AND role = 'user' AND id < a.id)
            WHERE a.role = 'assistant' ORDER BY a.id DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]
