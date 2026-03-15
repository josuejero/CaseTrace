"""Call artifact parser."""
from __future__ import annotations

from pathlib import Path

from .common import ensure_file
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact
from .sqlite_utils import sqlite_readonly_connection


def parse_calls(case_dir: Path) -> list[ParsedArtifact]:
    db_path = case_dir / "files" / "databases" / "waypoint_core.db"
    ensure_file(db_path)
    query = """
        SELECT id, call_type, contact_name, timestamp_start, timestamp_end, duration_seconds, summary
        FROM calls
        ORDER BY timestamp_start
    """
    records: list[ArtifactRecordModel] = []
    with sqlite_readonly_connection(db_path) as conn:
        cursor = conn.execute(query)
        for sequence, row in enumerate(cursor, start=1):
            record_id = f"call-{sequence:03d}"
            record = ArtifactRecordModel(
                artifact_type="call",
                source_file="/data/user/0/com.casetrace.waypoint/databases/waypoint_core.db",
                record_id=record_id,
                event_time_start=row[3],
                event_time_end=row[4],
                actor="Jordan Vega",
                counterparty=row[2],
                location=None,
                content_summary=row[6],
                raw_ref=f"db://files/databases/waypoint_core.db#table=calls&rowid={row[0]}",
                deleted_flag=False,
                confidence=0.97,
                parser_version=PARSER_VERSION,
            )
            metadata = {
                "call_type": row[1],
                "duration_seconds": row[5],
            }
            records.append(ParsedArtifact(record=record, metadata=metadata))
    return records
