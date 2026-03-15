"""SQLite helpers tuned for readonly evidence exploration."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def sqlite_readonly_connection(path: Path) -> sqlite3.Connection:
    """Open a SQLite database in read-only immutable mode."""
    # Using URI form ensures mode and immutable settings are honoured.
    uri = f"file:{path}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def rows_from_cursor(cursor: sqlite3.Cursor) -> list[dict[str, object]]:
    """Convert a cursor description and rows into dictionaries."""
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
