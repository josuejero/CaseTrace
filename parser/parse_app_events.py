"""In-app event artifact parser."""
from __future__ import annotations

from pathlib import Path

from .common import ensure_file, iter_jsonl
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact


def parse_app_events(case_dir: Path) -> list[ParsedArtifact]:
    path = case_dir / "files" / "logs" / "app-events-20260312.jsonl"
    ensure_file(path)
    records: list[ParsedArtifact] = []
    for line_no, entry in enumerate(iter_jsonl(path), start=1):
        record_id = f"app-{line_no:03d}"
        timestamp = entry["timestamp_utc"]
        metadata = {"event_type": entry["event"]}
        records.append(
            ParsedArtifact(
                record=ArtifactRecordModel(
                    artifact_type="app_event",
                    source_file="/data/user/0/com.casetrace.waypoint/logs/app-events-20260312.jsonl",
                    record_id=record_id,
                    event_time_start=timestamp,
                    event_time_end=timestamp,
                    actor="Jordan Vega",
                    counterparty=None,
                    location=None,
                    content_summary=entry["summary"],
                    raw_ref=f"file://files/logs/app-events-20260312.jsonl#line={line_no}",
                    deleted_flag=False,
                    confidence=0.94,
                    parser_version=PARSER_VERSION,
                ),
                metadata=metadata,
            )
        )
    return records
