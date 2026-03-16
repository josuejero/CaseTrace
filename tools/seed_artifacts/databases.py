\"\"\"SQLite builders for the seed artifact generator.\"\"\"
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from tools.seed_artifacts.data import (
    APP_EVENTS,
    BROWSERS,
    CALLS,
    DELETED_BROWSER,
    DELETED_MESSAGE,
    MESSAGES,
)


def create_core_database(case_dir: Path, build_root: Path | None = None) -> None:
    files_dir = case_dir / "files"
    db_dir = files_dir / "databases"
    db_dir.mkdir(parents=True, exist_ok=True)
    temp_root = _temp_root(build_root, "tmp_seed_core")
    db_path = temp_root / "waypoint_core.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA wal_autocheckpoint=0;")
    cursor.execute(
        \"\"\"
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            thread_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            read_flag INTEGER NOT NULL,
            deleted_flag INTEGER NOT NULL
        );
        \"\"\"
    )
    cursor.execute(
        \"\"\"
        CREATE TABLE calls (
            id INTEGER PRIMARY KEY,
            call_type TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            timestamp_start TEXT NOT NULL,
            timestamp_end TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            summary TEXT NOT NULL
        );
        \"\"\"
    )
    cursor.execute(
        \"\"\"
        CREATE TABLE photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            summary TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            device_model TEXT NOT NULL,
            orientation INTEGER NOT NULL
        );
        \"\"\"
    )
    cursor.execute(
        \"\"\"
        CREATE TABLE app_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp_start TEXT NOT NULL,
            timestamp_end TEXT NOT NULL,
            summary TEXT NOT NULL
        );
        \"\"\"
    )

    for idx, message in enumerate(MESSAGES):
        read_flag = 1 if idx < 6 else 0
        cursor.execute(
            \"\"\"INSERT INTO messages(id, thread_id, direction, timestamp, sender, recipient, body, read_flag, deleted_flag)\n            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)\"\"\",
            (
                message["id"],
                message["thread_id"],
                message["direction"],
                message["timestamp"],
                message["actor"],
                message["counterparty"],
                message["body"],
                read_flag,
            ),
        )

    for call in CALLS:
        cursor.execute(
            \"\"\"INSERT INTO calls(id, call_type, contact_name, timestamp_start, timestamp_end, duration_seconds, summary)\n            VALUES (?, ?, ?, ?, ?, ?, ?)\"\"\",
            (
                call["id"],
                call["call_type"],
                call["contact"],
                call["start"],
                call["end"],
                call["duration"],
                call["summary"],
            ),
        )

    for event in APP_EVENTS:
        cursor.execute(
            \"\"\"INSERT INTO app_events(event_type, timestamp_start, timestamp_end, summary)\n            VALUES (?, ?, ?, ?)\"\"\",
            (event[1], event[0], event[0], event[2]),
        )

    conn.commit()
    mutate_core_database(conn)
    conn.close()
    _copy_sqlite_artifacts(db_path, db_dir, "core")


def mutate_core_database(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    mutated = MESSAGES[0]
    cursor.execute(
        \"\"\"INSERT INTO messages(id, thread_id, direction, timestamp, sender, recipient, body, read_flag, deleted_flag)\n        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)\"\"\",
        (
            mutated["id"] + 100,
            "mutate-case_alpha",
            mutated["direction"],
            DELETED_MESSAGE["timestamp"],
            DELETED_MESSAGE["actor"],
            DELETED_MESSAGE["counterparty"],
            DELETED_MESSAGE["body"],
            0,
        ),
    )
    cursor.execute(
        \"\"\"UPDATE messages SET body = ? WHERE id = ?\"\"\",
        (f"[mutated] {mutated['body']}", mutated["id"]),
    )
    cursor.execute("DELETE FROM messages WHERE id = ?", (mutated["id"],))
    conn.commit()


def create_web_database(case_dir: Path, build_root: Path | None = None) -> None:
    files_dir = case_dir / "files"
    db_dir = files_dir / "databases"
    db_dir.mkdir(parents=True, exist_ok=True)
    temp_root = _temp_root(build_root, "tmp_seed_web")
    db_path = temp_root / "waypoint_web.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA wal_autocheckpoint=0;")
    cursor.execute(
        \"\"\"
        CREATE TABLE browser_history (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            typed_url INTEGER NOT NULL,
            referrer TEXT,
            timestamp TEXT NOT NULL
        );
        \"\"\"
    )

    for visit in BROWSERS:
        cursor.execute(
            \"\"\"INSERT INTO browser_history(id, title, url, typed_url, referrer, timestamp)\n            VALUES (?, ?, ?, ?, ?, ?)\"\"\",
            (
                visit["id"],
                visit["title"],
                visit["url"],
                1 if visit["typed"] else 0,
                visit["referrer"],
                visit["timestamp"],
            ),
        )

    conn.commit()
    mutate_browser_database(conn)
    conn.close()
    _copy_sqlite_artifacts(db_path, db_dir, "web")


def mutate_browser_database(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    visit = BROWSERS[0]
    new_id = visit["id"] + 100
    cursor.execute(
        \"\"\"INSERT INTO browser_history(id, title, url, typed_url, referrer, timestamp)\n        VALUES (?, ?, ?, ?, ?, ?)\"\"\",
        (
            new_id,
            DELETED_BROWSER["title"],
            DELETED_BROWSER["url"],
            1,
            None,
            DELETED_BROWSER["timestamp"],
        ),
    )
    cursor.execute("DELETE FROM browser_history WHERE id = ?", (new_id,))
    conn.commit()


def _temp_root(build_root: Path | None, folder_name: str) -> Path:
    root = (build_root or Path("build")) / folder_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _copy_sqlite_artifacts(temp_db: Path, target_dir: Path, label: str) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(temp_db, target_dir / temp_db.name)
    for suffix in ("-wal", "-shm"):
        src_path = Path(str(temp_db) + suffix)
        if not src_path.exists():
            raise RuntimeError(f"{label} {suffix.strip('-').upper()} missing after commit: {src_path}")
        shutil.copy(src_path, target_dir / (temp_db.name + suffix))
