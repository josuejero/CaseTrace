"""Browser visit artifact parser."""
from __future__ import annotations

from pathlib import Path

from .common import ensure_file
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact
from .sqlite_utils import sqlite_readonly_connection


def parse_browser(case_dir: Path) -> list[ParsedArtifact]:
    db_path = case_dir / "files" / "databases" / "waypoint_web.db"
    ensure_file(db_path)
    query = """
        SELECT id, title, url, referrer, timestamp
        FROM browser_history
        ORDER BY timestamp
    """
    records: list[ArtifactRecordModel] = []
    with sqlite_readonly_connection(db_path) as conn:
        cursor = conn.execute(query)
        for sequence, row in enumerate(cursor, start=1):
            record_id = f"web-{sequence:03d}"
            summary = f"Visited {row[2]}"
            record = ArtifactRecordModel(
                artifact_type="browser_visit",
                source_file="/data/user/0/com.casetrace.waypoint/databases/waypoint_web.db",
                record_id=record_id,
                event_time_start=row[4],
                event_time_end=row[4],
                actor="Jordan Vega",
                counterparty=None,
                location=None,
                content_summary=summary,
                raw_ref=f"db://files/databases/waypoint_web.db#table=browser_history&rowid={row[0]}",
                deleted_flag=False,
                confidence=0.96,
                parser_version=PARSER_VERSION,
            )
            metadata = {"title": row[1], "url": row[2], "referrer": row[3]}
            records.append(ParsedArtifact(record=record, metadata=metadata))
    return records
