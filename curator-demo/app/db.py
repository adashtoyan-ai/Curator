"""КУРАТОР — доступ к БД (демо на SQLite, без внешней инфраструктуры)."""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("CURATOR_DB", os.path.join(os.path.dirname(__file__), "..", "curator.db"))


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL DEFAULT 'citizen',
    phone TEXT UNIQUE,
    first_name TEXT, last_name TEXT,
    birth_date TEXT, region_code TEXT,
    coordinator_id INTEGER
);
CREATE TABLE IF NOT EXISTS citizen_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE, title TEXT, level TEXT, region_code TEXT
);
CREATE TABLE IF NOT EXISTS user_categories (
    user_id INTEGER, category_code TEXT,
    UNIQUE(user_id, category_code)
);
CREATE TABLE IF NOT EXISTS measures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT, title TEXT, description TEXT,
    measure_type TEXT, level TEXT, region_code TEXT,
    authority TEXT, amount REAL,
    eligibility TEXT, required_documents TEXT,
    version INTEGER DEFAULT 1, is_current INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id INTEGER, coordinator_id INTEGER,
    title TEXT, life_event TEXT, status TEXT DEFAULT 'draft',
    answers TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, citizen_id INTEGER,
    measure_id INTEGER, measure_version INTEGER,
    coordinator_id INTEGER, status TEXT DEFAULT 'submitted',
    expected_amount REAL, created_at TEXT
);
CREATE TABLE IF NOT EXISTS rule_eval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, measure_id INTEGER,
    score INTEGER, category TEXT, evaluated_at TEXT
);
CREATE TABLE IF NOT EXISTS case_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, event TEXT, actor TEXT, status TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, text TEXT, is_read INTEGER DEFAULT 0, created_at TEXT
);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def jload(s):
    return json.loads(s) if s else None


def jdump(o):
    return json.dumps(o, ensure_ascii=False)
