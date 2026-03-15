"""Message artifact parser."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .common import ensure_file
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact
from .sqlite_utils import sqlite_readonly_connection


def parse_messages(case_dir: Path) -> list[ParsedArtifact]:
    db_path = case_dir / "files" / "databases" / "waypoint_core.db"
    ensure_file(db_path)
    query = """
        SELECT id, direction, timestamp, sender, recipient, body, deleted_flag
        FROM messages
        ORDER BY id
    """
    records: list[ArtifactRecordModel] = []
    with sqlite_readonly_connection(db_path) as conn:
        cursor = conn.execute(query)
        for row in cursor:
            record_id = f"msg-{row[0]:03d}"
            deleted = bool(row[6])
            record = ArtifactRecordModel(
                artifact_type="message",
                source_file="/data/user/0/com.casetrace.waypoint/databases/waypoint_core.db",
                record_id=record_id,
                event_time_start=row[2],
                event_time_end=row[2],
                actor=row[3],
                counterparty=row[4],
                location=None,
                content_summary=row[5],
                raw_ref=f"db://files/databases/waypoint_core.db#table=messages&rowid={row[0]}",
                deleted_flag=deleted,
                confidence=0.95,
                parser_version=PARSER_VERSION,
            )
            metadata = {"direction": row[1], "thread_id": row[0]}
            records.append(ParsedArtifact(record=record, metadata=metadata))
    return records
