"""Photo artifact parser."""
from __future__ import annotations

from pathlib import Path

from .common import ensure_file
from .models import ArtifactRecordModel, LocationModel, PARSER_VERSION, ParsedArtifact
from .sqlite_utils import sqlite_readonly_connection


def parse_photos(case_dir: Path) -> list[ParsedArtifact]:
    db_path = case_dir / "files" / "databases" / "waypoint_core.db"
    ensure_file(db_path)
    query = """
        SELECT id, file_name, timestamp, summary, latitude, longitude
        FROM photos
        ORDER BY timestamp
    """
    records: list[ParsedArtifact] = []
    with sqlite_readonly_connection(db_path) as conn:
        cursor = conn.execute(query)
        for sequence, row in enumerate(cursor, start=1):
            record_id = f"photo-{sequence:03d}"
            loc = LocationModel(
                latitude=row[4],
                longitude=row[5],
                accuracy_m=6.0,
                label=row[1],
            )
            metadata = {"file_name": row[1], "latitude": row[4], "longitude": row[5]}
            records.append(
                ParsedArtifact(
                    record=ArtifactRecordModel(
                        artifact_type="photo",
                        source_file="/data/user/0/com.casetrace.waypoint/media/" + row[1],
                        record_id=record_id,
                        event_time_start=row[2],
                        event_time_end=row[2],
                        actor="Jordan Vega",
                        counterparty=None,
                        location=loc,
                        content_summary=row[3],
                        raw_ref=f"db://files/databases/waypoint_core.db#table=photos&rowid={row[0]}",
                        deleted_flag=False,
                        confidence=0.95,
                        parser_version=PARSER_VERSION,
                    ),
                    metadata=metadata,
                )
            )
    return records
