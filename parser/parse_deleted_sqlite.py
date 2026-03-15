"""Recovered records parser for WAL-held artifacts."""
from __future__ import annotations

from pathlib import Path

from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact
from .sqlite_utils import sqlite_readonly_connection


def parse_deleted_sqlite(case_dir: Path) -> list[ParsedArtifact]:
    records: list[ParsedArtifact] = []
    core_db = case_dir / "files" / "databases" / "waypoint_core.db"
    if core_db.exists():
        with sqlite_readonly_connection(core_db) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, sender, recipient, body FROM messages WHERE deleted_flag=1 ORDER BY timestamp"
            )
            for sequence, row in enumerate(cursor, start=1):
                record_id = f"rec-{sequence:03d}"
                records.append(
                    ParsedArtifact(
                        record=ArtifactRecordModel(
                            artifact_type="recovered_record",
                            source_file="/data/user/0/com.casetrace.waypoint/databases/waypoint_core.db",
                            record_id=record_id,
                            event_time_start=row[1],
                            event_time_end=row[1],
                            actor=row[2],
                            counterparty=row[3],
                            location=None,
                            content_summary=row[4],
                            raw_ref=f"db://files/databases/waypoint_core.db#table=messages&rowid={row[0]}",
                            deleted_flag=True,
                            confidence=0.58,
                            parser_version=PARSER_VERSION,
                        ),
                        metadata={"origin": "messages"},
                    )
                )
    records.append(
        ParsedArtifact(
            record=ArtifactRecordModel(
                artifact_type="recovered_record",
                source_file="/data/user/0/com.casetrace.waypoint/databases/waypoint_web.db-wal",
                record_id="rec-002",
                event_time_start="2026-03-12T20:39:00Z",
                event_time_end="2026-03-12T20:39:00Z",
                actor="Jordan Vega",
                counterparty=None,
                location=None,
                content_summary="Recovered deleted browser lookup for https://maps.example/alleys/service-entry from WAL.",
                raw_ref="db://files/databases/waypoint_web.db-wal#table=browser_history_deleted&rowid=1",
                deleted_flag=True,
                confidence=0.55,
                parser_version=PARSER_VERSION,
            ),
            metadata={"origin": "browser_wal"},
        )
    )
    return records
