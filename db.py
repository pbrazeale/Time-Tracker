from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, Iterator, Optional

import sqlite3
from zoneinfo import ZoneInfo


DB_PATH = Path(__file__).resolve().parent / "time_tracker.db"
CENTRAL_TZ = ZoneInfo("America/Chicago")


@dataclass
class WorkSession:
    id: int
    session_date: str
    start_time: str
    end_time: Optional[str]
    notes: Optional[str] = None
    total_hours: Optional[float] = None


@dataclass
class ProjectEntry:
    id: int
    session_id: int
    project_name: str
    category: str
    start_time: str
    end_time: Optional[str]


def _calculate_total_hours(start_iso: Optional[str], end_iso: Optional[str]) -> Optional[float]:
    if not start_iso or not end_iso:
        return None
    try:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
    except ValueError:
        return None
    delta = end_dt - start_dt
    return round(delta.total_seconds() / 3600, 2)


def _row_to_work_session(row: sqlite3.Row) -> WorkSession:
    data = dict(row)
    data.setdefault("total_hours", None)
    return WorkSession(**data)


def _ensure_total_hours_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(work_sessions)")}
    if "total_hours" not in columns:
        conn.execute("ALTER TABLE work_sessions ADD COLUMN total_hours REAL")
    rows = conn.execute(
        """
        SELECT id, start_time, end_time
        FROM work_sessions
        WHERE start_time IS NOT NULL
          AND end_time IS NOT NULL
          AND total_hours IS NULL
        """
    ).fetchall()
    for row in rows:
        total_hours = _calculate_total_hours(row["start_time"], row["end_time"])
        conn.execute(
            "UPDATE work_sessions SET total_hours = ? WHERE id = ?",
            (total_hours, row["id"]),
        )



def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                notes TEXT,
                total_hours REAL
            );

            CREATE TABLE IF NOT EXISTS project_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                category TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                FOREIGN KEY (session_id) REFERENCES work_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1
            );
            """
        )

        _ensure_total_hours_column(conn)

        existing = conn.execute("SELECT name FROM categories").fetchall()
        if not existing:
            conn.executemany(
                "INSERT INTO categories (name, active) VALUES (?, 1)",
                [("Programming",), ("Meetings",), ("Marketing",)],
            )


def get_categories(include_inactive: bool = False) -> list[str]:
    with get_conn() as conn:
        if include_inactive:
            rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
        else:
            rows = conn.execute(
                "SELECT name FROM categories WHERE active = 1 ORDER BY name"
            ).fetchall()
    return [row[0] for row in rows]


def add_category(name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, active) VALUES (?, 1)", (name,)
        )


def set_category_active(name: str, active: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE categories SET active = ? WHERE name = ?",
            (1 if active else 0, name),
        )


def rename_category(old_name: str, new_name: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))
        conn.execute(
            "UPDATE project_entries SET category = ? WHERE category = ?",
            (new_name, old_name),
        )


def get_active_session() -> Optional[WorkSession]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM work_sessions WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
        ).fetchone()
    if row:
        return _row_to_work_session(row)
    return None


def start_session(now: Optional[datetime] = None) -> WorkSession:
    now = now or datetime.now(CENTRAL_TZ)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO work_sessions (session_date, start_time) VALUES (?, ?)",
            (now.date().isoformat(), now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM work_sessions WHERE id = last_insert_rowid()"
        ).fetchone()
    return _row_to_work_session(row)


def end_session(session_id: int, end_time: Optional[datetime] = None) -> None:
    when = (end_time or datetime.now(CENTRAL_TZ)).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT start_time FROM work_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        total_hours = None
        if row:
            total_hours = _calculate_total_hours(row["start_time"], when)
            conn.execute(
                "UPDATE work_sessions SET end_time = ?, total_hours = ? WHERE id = ?",
                (when, total_hours, session_id),
            )
        else:
            conn.execute(
                "UPDATE work_sessions SET end_time = ? WHERE id = ?",
                (when, session_id),
            )



def get_active_project_entry(session_id: int | None = None) -> Optional[ProjectEntry]:
    query = "SELECT * FROM project_entries WHERE end_time IS NULL"
    params: tuple[object, ...]
    if session_id is not None:
        query += " AND session_id = ?"
        params = (session_id,)
    else:
        params = tuple()
    query += " ORDER BY start_time DESC LIMIT 1"

    with get_conn() as conn:
        row = conn.execute(query, params).fetchone()
    if row:
        return ProjectEntry(**row)
    return None


def start_project_entry(
    session_id: int,
    project_name: str,
    category: str,
    start_time: Optional[datetime] = None,
) -> ProjectEntry:
    start = (start_time or datetime.now(CENTRAL_TZ)).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO project_entries (session_id, project_name, category, start_time)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, project_name.strip(), category, start),
        )
        row = conn.execute(
            "SELECT * FROM project_entries WHERE id = last_insert_rowid()"
        ).fetchone()
    return ProjectEntry(**row)


def end_project_entry(entry_id: int, end_time: Optional[datetime] = None) -> None:
    end_ts = (end_time or datetime.now(CENTRAL_TZ)).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE project_entries SET end_time = ? WHERE id = ?", (end_ts, entry_id)
        )


def list_sessions_between(start: date, end: date) -> list[sqlite3.Row]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM work_sessions
            WHERE session_date BETWEEN ? AND ?
            ORDER BY session_date
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return rows


def list_project_entries_between(start: date, end: date) -> list[sqlite3.Row]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT pe.*, ws.session_date
            FROM project_entries pe
            JOIN work_sessions ws ON ws.id = pe.session_id
            WHERE ws.session_date BETWEEN ? AND ?
            ORDER BY pe.start_time
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return rows


def update_session(
    session_id: int,
    session_date: str,
    start_time: str,
    end_time: Optional[str],
    notes: Optional[str] = None,
) -> None:
    total_hours = _calculate_total_hours(start_time, end_time)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE work_sessions
            SET session_date = ?, start_time = ?, end_time = ?, notes = ?, total_hours = ?
            WHERE id = ?
            """,
            (session_date, start_time, end_time, notes, total_hours, session_id),
        )



def delete_session(session_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM work_sessions WHERE id = ?", (session_id,))


def update_project_entry(
    entry_id: int,
    project_name: str,
    category: str,
    start_time: str,
    end_time: Optional[str],
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE project_entries
            SET project_name = ?, category = ?, start_time = ?, end_time = ?
            WHERE id = ?
            """,
            (project_name, category, start_time, end_time, entry_id),
        )


def delete_project_entry(entry_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM project_entries WHERE id = ?", (entry_id,))


def ensure_session_for_date(target_date: date) -> WorkSession:
    """Create a manual session for a given date if one does not exist."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM work_sessions WHERE session_date = ? ORDER BY start_time LIMIT 1",
            (target_date.isoformat(),),
        ).fetchone()
        if row:
            return _row_to_work_session(row)
        now = datetime.combine(target_date, datetime.min.time(), CENTRAL_TZ)
        conn.execute(
            "INSERT INTO work_sessions (session_date, start_time) VALUES (?, ?)",
            (target_date.isoformat(), now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM work_sessions WHERE id = last_insert_rowid()"
        ).fetchone()
    return _row_to_work_session(row)


def add_manual_project_entry(
    session_id: int,
    project_name: str,
    category: str,
    start_time: str,
    end_time: Optional[str],
) -> ProjectEntry:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO project_entries (session_id, project_name, category, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, project_name, category, start_time, end_time),
        )
        row = conn.execute(
            "SELECT * FROM project_entries WHERE id = last_insert_rowid()"
        ).fetchone()
    return ProjectEntry(**row)


def list_all_sessions() -> list[sqlite3.Row]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM work_sessions ORDER BY session_date DESC, start_time DESC"
        ).fetchall()
    return rows


def list_all_project_entries() -> list[sqlite3.Row]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT pe.*, ws.session_date
            FROM project_entries pe
            JOIN work_sessions ws ON ws.id = pe.session_id
            ORDER BY pe.start_time DESC
            """
        ).fetchall()
    return rows


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def sessions_as_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return _rows_to_dicts(rows)


def entries_as_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return _rows_to_dicts(rows)


__all__ = [
    "CENTRAL_TZ",
    "WorkSession",
    "ProjectEntry",
    "init_db",
    "get_categories",
    "add_category",
    "set_category_active",
    "rename_category",
    "get_active_session",
    "start_session",
    "end_session",
    "get_active_project_entry",
    "start_project_entry",
    "end_project_entry",
    "list_sessions_between",
    "list_project_entries_between",
    "update_session",
    "delete_session",
    "update_project_entry",
    "delete_project_entry",
    "ensure_session_for_date",
    "add_manual_project_entry",
    "list_all_sessions",
    "list_all_project_entries",
    "sessions_as_dicts",
    "entries_as_dicts",
]
