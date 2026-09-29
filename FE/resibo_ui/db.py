"""SQLite persistence for cases and their sealed exhibits.

The rest of the app keeps working with plain dicts in `data.CASES`; this
module is only responsible for making those survive a restart.
"""

import os
import pickle
import sqlite3

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "resibo.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    number    TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    examiner  TEXT,
    place     TEXT,
    badge     TEXT,
    tone      TEXT,
    opened    TEXT,
    exhibits  INTEGER,
    flags     INTEGER,
    chain     TEXT,
    status    TEXT,
    done      INTEGER,
    base_dir  TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL REFERENCES cases(number) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    path        TEXT NOT NULL,
    size        INTEGER,
    digest      TEXT,
    sealed_at   TEXT
);

-- Everything else the UI shows (pipeline-stage illustrations: detected
-- people, face crops, gait results, audit history, and so on) lives here
-- too, one row per named value, instead of as literals in the source.
CREATE TABLE IF NOT EXISTS reference_data (
    key   TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
"""


def connect():
    """Open the database, making sure its schema exists first.

    The schema is (re)applied on every connection, not just once at startup:
    `CREATE TABLE IF NOT EXISTS` is cheap and idempotent, and this way the
    database self-heals if the file is ever missing, empty, or replaced
    underneath the app - instead of every query failing with
    "no such table" until the app is restarted.
    """
    conn = sqlite3.connect(PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def init():
    """Create the tables if this is a fresh database."""
    connect().close()


def seed_if_empty(cases):
    """Load the sample cases in on first run, so the demo still has data."""
    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        if count:
            return
        for case in cases:
            _insert_case(conn, case)
        conn.commit()
    finally:
        conn.close()


def load_cases():
    """All cases, in the order they were opened, as plain dicts."""
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM cases ORDER BY rowid").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _insert_case(conn, case):
    # A real upsert, not INSERT OR REPLACE: that variant deletes the old row
    # first, which cascades through evidence.case_number's foreign key and
    # wipes every exhibit already sealed for this case.
    conn.execute(
        "INSERT INTO cases "
        "(number, name, examiner, place, badge, tone, opened, exhibits, flags, "
        " chain, status, done, base_dir) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(number) DO UPDATE SET "
        "name=excluded.name, examiner=excluded.examiner, place=excluded.place, "
        "badge=excluded.badge, tone=excluded.tone, opened=excluded.opened, "
        "exhibits=excluded.exhibits, flags=excluded.flags, chain=excluded.chain, "
        "status=excluded.status, done=excluded.done, base_dir=excluded.base_dir",
        (case["number"], case["name"], case.get("examiner", ""),
         case.get("place", ""), case.get("badge", ""), case.get("tone", ""),
         case.get("opened", ""), case.get("exhibits", 0), case.get("flags", 0),
         case.get("chain", ""), case.get("status", ""), case.get("done", 0),
         case.get("base_dir", "")))


def insert_case(case):
    """Persist one newly sealed case."""
    conn = connect()
    try:
        _insert_case(conn, case)
        conn.commit()
    finally:
        conn.close()


def insert_evidence(case_number, entries):
    """Persist the sealed exhibits (name, path, size, digest) for one case."""
    conn = connect()
    try:
        conn.executemany(
            "INSERT INTO evidence (case_number, name, path, size, digest, sealed_at) "
            "VALUES (?,?,?,?,?,datetime('now'))",
            [(case_number, e["name"], e["path"], e["size"], e["digest"])
             for e in entries])
        conn.commit()
    finally:
        conn.close()


def evidence_for(case_number):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM evidence WHERE case_number = ? ORDER BY id", (case_number,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_case(case_number):
    conn = connect()
    try:
        conn.execute("DELETE FROM cases WHERE number = ?", (case_number,))
        conn.commit()
    finally:
        conn.close()


def delete_evidence(evidence_id):
    """Remove one sealed exhibit."""
    conn = connect()
    try:
        conn.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
        conn.commit()
    finally:
        conn.close()


# --- Reference data ---------------------------------------------------------
# A generic key/value store for everything that isn't a case or an exhibit:
# the pipeline-stage illustrations every screen reads (detected people, face
# crops, gait results, audit history...). Values are pickled rather than
# JSON-encoded so tuples and dicts round-trip exactly - several screens tell
# a styled table cell from a plain one by checking `isinstance(cell, tuple)`,
# which a JSON round-trip (which only knows lists) would silently break.

def seed_reference_if_empty(defaults):
    """Load the sample reference data in on first run only."""
    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM reference_data").fetchone()[0]
        if count:
            return
        conn.executemany(
            "INSERT INTO reference_data (key, value) VALUES (?, ?)",
            [(key, pickle.dumps(value)) for key, value in defaults.items()])
        conn.commit()
    finally:
        conn.close()


def get_reference(key, default=None):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT value FROM reference_data WHERE key = ?", (key,)).fetchone()
        return pickle.loads(row["value"]) if row is not None else default
    finally:
        conn.close()


def set_reference(key, value):
    """Persist one named value, replacing it if it already exists."""
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO reference_data (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, pickle.dumps(value)))
        conn.commit()
    finally:
        conn.close()
