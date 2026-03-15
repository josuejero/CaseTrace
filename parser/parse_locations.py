"""Location artifact parser."""
from __future__ import annotations

from pathlib import Path

from .common import ensure_file, load_json
from .models import ArtifactRecordModel, LocationModel, PARSER_VERSION, ParsedArtifact


def parse_locations(case_dir: Path) -> list[ParsedArtifact]:
    path = case_dir / "files" / "exports" / "location_trace.json"
    ensure_file(path)
    payload = load_json(path)
    points = payload.get("points", [])
    records: list[ParsedArtifact] = []
    for index, point in enumerate(points, start=1):
        record_id = f"loc-{index:03d}"
        location = LocationModel(
            latitude=point["latitude"],
            longitude=point["longitude"],
            accuracy_m=point["accuracy_m"],
            label=point["label"],
        )
        metadata = {"label": point["label"]}
        records.append(
            ParsedArtifact(
                record=ArtifactRecordModel(
                    artifact_type="location_point",
                    source_file="/data/user/0/com.casetrace.waypoint/exports/location_trace.json",
                    record_id=record_id,
                    event_time_start=point["timestamp_utc"],
                    event_time_end=point["timestamp_utc"],
                    actor="Jordan Vega",
                    counterparty=None,
                    location=location,
                    content_summary=f"Location fix near {point['label']}.",
                    raw_ref=f"file://files/exports/location_trace.json#jsonpath=$.points[{index-1}]",
                    deleted_flag=False,
                    confidence=0.98,
                    parser_version=PARSER_VERSION,
                ),
                metadata=metadata,
            )
        )
    return records
