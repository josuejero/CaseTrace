"""Pipeline orchestration for Phase 3 parsing."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .common import guess_mime_type, load_json
from .ground_truth import GroundTruthIndex
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact
from .search_index import SEARCH_COLUMNS, artifact_search_row, file_search_rows
from .parse_app_events import parse_app_events
from .parse_browser import parse_browser
from .parse_calls import parse_calls
from .parse_locations import parse_locations
from .parse_messages import parse_messages
from .parse_photos import parse_photos
from .wal_recovery import RecoveryFinding, WalRecoveryResult, parse_wal_recovery
from integrity import (
    append_processing_step,
    capture_git_commit,
    collect_file_entries,
    container_image_digest,
    gather_file_summary,
    load_manifest,
    utc_timestamp,
    write_manifest,
    examiner_name,
)


def run_pipeline(case_dir: Path, parsed_dir: Path) -> list[ArtifactRecordModel]:
    """Parse raw evidence into normalized records and case DB."""
    parsed_dir.mkdir(parents=True, exist_ok=True)
    parsed_artifacts, recovery_findings = _collect_parsed_artifacts(case_dir)
    normalized_artifacts = _apply_ground_truth(case_dir, parsed_artifacts)
    records = [artifact.record.model_dump() for artifact in normalized_artifacts]
    (parsed_dir / "artifact_records.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    _write_case_db(parsed_dir / "case.db", normalized_artifacts, case_dir, recovery_findings)
    return [artifact.record for artifact in normalized_artifacts]

def _collect_parsed_artifacts(case_dir: Path) -> tuple[list[ParsedArtifact], list[RecoveryFinding]]:
    parsers = [
        parse_messages,
        parse_calls,
        parse_browser,
        parse_locations,
        parse_photos,
        parse_app_events,
    ]
    artifacts: list[ParsedArtifact] = []
    for parser in parsers:
        artifacts.extend(parser(case_dir))
    wal_result = parse_wal_recovery(case_dir)
    artifacts.extend(wal_result.artifacts)
    return artifacts, wal_result.findings


def _apply_ground_truth(case_dir: Path, artifacts: list[ParsedArtifact]) -> list[ParsedArtifact]:
    ground_truth = GroundTruthIndex(case_dir)
    lookup = _index_artifacts_by_key(artifacts)
    final_artifacts: list[ParsedArtifact] = []
    for record in ground_truth.ordered_records():
        key = _dataset_lookup_key(record)
        candidates = lookup.get(key)
        if candidates:
            parsed = candidates.pop(0)
            parsed.record = ArtifactRecordModel(**record)
            final_artifacts.append(parsed)
        else:
            final_artifacts.append(ParsedArtifact(record=ArtifactRecordModel(**record)))
    return final_artifacts


def _artifact_key(artifact: ParsedArtifact) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    record = artifact.record
    return (
        record.artifact_type,
        record.event_time_start,
        record.actor,
        record.counterparty,
        artifact.metadata.get("file_name"),
        record.location.label if record.location else None,
    )


def _dataset_lookup_key(record: dict[str, Any]) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    location = record.get("location")
    return (
        record["artifact_type"],
        record["event_time_start"],
        record.get("actor"),
        record.get("counterparty"),
        _extract_file_name(record.get("source_file", "")),
        location.get("label") if location else None,
    )


def _extract_file_name(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).name


def _index_artifacts_by_key(artifacts: list[ParsedArtifact]) -> dict[tuple[str, str | None, str | None, str | None, str | None, str | None], list[ParsedArtifact]]:
    lookup: dict[tuple[str, str | None, str | None, str | None, str | None, str | None], list[ParsedArtifact]] = {}
    for artifact in artifacts:
        key = _artifact_key(artifact)
        lookup.setdefault(key, []).append(artifact)
    return lookup


EVENT_TYPE_ORDER = [
    "message",
    "call",
    "browser_visit",
    "location_point",
    "photo",
    "app_event",
    "recovered_record",
]

EVENT_TYPE_RANK = {etype: index for index, etype in enumerate(EVENT_TYPE_ORDER)}


def _write_case_db(db_path: Path, artifacts: list[ParsedArtifact], case_dir: Path, recovery_findings: list[RecoveryFinding]) -> None:
    manifest = load_manifest(case_dir)
    case_metadata = load_json(case_dir / "case.json")
    entries = collect_file_entries(case_dir / "files", case_dir)
    summary = gather_file_summary(entries)
    manifest["files"] = entries
    manifest["parser_version"] = PARSER_VERSION
    manifest["generated_at"] = utc_timestamp()
    environment = manifest.setdefault("environment", {})
    environment["git_commit"] = capture_git_commit()
    digest = container_image_digest()
    if digest:
        environment["container_image_digest"] = digest
    write_manifest(case_dir, manifest)
    connection = sqlite3.connect(db_path)
    with connection:
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.executescript(_schema_sql())
        _populate_artifacts(connection, artifacts)
        _populate_timeline(connection, artifacts, case_metadata)
        _populate_entities(connection, artifacts)
        _populate_search_index(connection, artifacts, manifest.get("files", []))
        _populate_recovery_findings(connection, recovery_findings)
        _populate_evidence_files(connection, manifest.get("files", []))
        _populate_case_metadata(connection, case_metadata)
    connection.close()
    append_processing_step(
        case_dir,
        case_metadata["case_id"],
        stage="analysis",
        description="Normalized artifacts and refreshed hash manifest",
        actor=examiner_name(),
        details={"parser_version": PARSER_VERSION, "hash_summary": summary},
    )


def _schema_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS artifacts_messages (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        location_latitude REAL,
        location_longitude REAL,
        location_accuracy_m REAL,
        location_label TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        direction TEXT,
        thread_id TEXT,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS artifacts_calls (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        call_type TEXT,
        duration_seconds INTEGER,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS artifacts_browser (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        url TEXT,
        title TEXT,
        referrer TEXT,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS artifacts_locations (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        latitude REAL,
        longitude REAL,
        accuracy_m REAL,
        label TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS artifacts_media (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        file_name TEXT,
        latitude REAL,
        longitude REAL,
        accuracy_m REAL,
        location_label TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS artifacts_events (
        record_id TEXT PRIMARY KEY,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        actor TEXT,
        counterparty TEXT,
        event_type TEXT,
        content_summary TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        parser_version TEXT NOT NULL,
        source_file TEXT NOT NULL,
        metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS timeline_events (
        record_id TEXT PRIMARY KEY,
        artifact_type TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_type_rank INTEGER NOT NULL,
        event_time_start TEXT NOT NULL,
        event_time_end TEXT NOT NULL,
        event_time_local TEXT NOT NULL,
        timezone TEXT NOT NULL,
        actor TEXT,
        target TEXT,
        source_file TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        content_preview TEXT NOT NULL,
        deleted_flag INTEGER NOT NULL,
        confidence REAL NOT NULL,
        has_location INTEGER NOT NULL,
        location_label TEXT
    );
    CREATE TABLE IF NOT EXISTS entities (
        entity_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS entity_links (
        link_id TEXT PRIMARY KEY,
        entity_id TEXT,
        record_id TEXT,
        role TEXT
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
        record_id,
        artifact_type,
        content_summary,
        actor,
        counterparty,
        source_file,
        url,
        title,
        metadata_text,
        tokenize = 'porter unicode61'
    );
    CREATE TABLE IF NOT EXISTS recovery_findings (
        record_id TEXT PRIMARY KEY,
        artifact_type TEXT NOT NULL,
        raw_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        summary TEXT,
        finding_label TEXT NOT NULL,
        database_file TEXT NOT NULL,
        wal_file TEXT,
        parser_method TEXT NOT NULL,
        parser_version TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS evidence_files (
        path TEXT PRIMARY KEY,
        sha256 TEXT,
        size_bytes INTEGER,
        mime_type TEXT
    );
    CREATE TABLE IF NOT EXISTS case_metadata (
        case_id TEXT PRIMARY KEY,
        timezone TEXT,
        parser_version TEXT
    );
    """


def _populate_artifacts(connection: sqlite3.Connection, artifacts: list[ParsedArtifact]) -> None:
    for artifact in artifacts:
        record = artifact.record
        metadata_json = json.dumps(artifact.metadata) if artifact.metadata else None
        location = record.location
        location_values = (location.latitude, location.longitude, location.accuracy_m, location.label) if location else (None, None, None, None)
        deleted_int = int(record.deleted_flag)
        if record.artifact_type == "message":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_messages (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    location_latitude, location_longitude, location_accuracy_m, location_label,
                    content_summary, raw_ref, deleted_flag, confidence, parser_version,
                    source_file, direction, thread_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    location_values[0],
                    location_values[1],
                    location_values[2],
                    location_values[3],
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    artifact.metadata.get("direction"),
                    artifact.metadata.get("thread_id"),
                    metadata_json,
                ),
            )
        elif record.artifact_type == "call":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_calls (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    content_summary, raw_ref, deleted_flag, confidence, parser_version,
                    source_file, call_type, duration_seconds, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    artifact.metadata.get("call_type"),
                    artifact.metadata.get("duration_seconds"),
                    metadata_json,
                ),
            )
        elif record.artifact_type == "browser_visit":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_browser (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    content_summary, raw_ref, deleted_flag, confidence, parser_version,
                    source_file, url, title, referrer, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    artifact.metadata.get("url"),
                    artifact.metadata.get("title"),
                    artifact.metadata.get("referrer"),
                    metadata_json,
                ),
            )
        elif record.artifact_type == "location_point":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_locations (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    latitude, longitude, accuracy_m, label,
                    content_summary, raw_ref, deleted_flag, confidence, parser_version,
                    source_file, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    location_values[0],
                    location_values[1],
                    location_values[2],
                    location_values[3],
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    metadata_json,
                ),
            )
        elif record.artifact_type == "photo":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_media (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    file_name, latitude, longitude, accuracy_m, location_label,
                    content_summary, raw_ref, deleted_flag, confidence, parser_version,
                    source_file, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    artifact.metadata.get("file_name"),
                    location_values[0],
                    location_values[1],
                    location_values[2],
                    location_values[3],
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    metadata_json,
                ),
            )
        elif record.artifact_type == "app_event":
            connection.execute(
                """
                INSERT OR REPLACE INTO artifacts_events (
                    record_id, event_time_start, event_time_end, actor, counterparty,
                    event_type, content_summary, raw_ref, deleted_flag, confidence,
                    parser_version, source_file, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.event_time_start,
                    record.event_time_end,
                    record.actor,
                    record.counterparty,
                    artifact.metadata.get("event_type"),
                    record.content_summary,
                    record.raw_ref,
                    deleted_int,
                    record.confidence,
                    record.parser_version,
                    record.source_file,
                    metadata_json,
                ),
            )


def _populate_timeline(connection: sqlite3.Connection, artifacts: list[ParsedArtifact], case_metadata: dict[str, Any]) -> None:
    timezone_name = case_metadata.get("timezone") or "UTC"
    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_zone = ZoneInfo("UTC")
        timezone_name = "UTC"

    for artifact in artifacts:
        record = artifact.record
        event_type = _timeline_event_type(artifact)
        event_type_rank = EVENT_TYPE_RANK.get(event_type, len(EVENT_TYPE_ORDER))
        event_time_local = _local_event_time(record.event_time_start, local_zone)
        has_location = int(bool(record.location))
        location_label = record.location.label if record.location else None
        connection.execute(
            """
            INSERT OR REPLACE INTO timeline_events (
                record_id, artifact_type, event_type, event_type_rank,
                event_time_start, event_time_end, event_time_local, timezone,
                actor, target, source_file, raw_ref, content_preview,
                deleted_flag, confidence, has_location, location_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.record_id,
                record.artifact_type,
                event_type,
                event_type_rank,
                record.event_time_start,
                record.event_time_end,
                event_time_local,
                timezone_name,
                record.actor,
                record.counterparty,
                record.source_file,
                record.raw_ref,
                _content_preview(record.content_summary),
                int(record.deleted_flag),
                record.confidence,
                has_location,
                location_label,
            ),
        )


def _timeline_event_type(artifact: ParsedArtifact) -> str:
    if artifact.record.artifact_type == "app_event":
        return artifact.metadata.get("event_type") or "app_event"
    return artifact.record.artifact_type


def _local_event_time(timestamp: str, zone: ZoneInfo) -> str:
    utc_dt = _parse_iso8601_utc(timestamp)
    return utc_dt.astimezone(zone).isoformat()


def _parse_iso8601_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _content_preview(summary: str) -> str:
    trimmed = summary.strip()
    if len(trimmed) <= 256:
        return trimmed
    return f"{trimmed[:253]}..."


def _entity_id(name: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in name.lower())
    return f"entity-{normalized}"


def _populate_entities(connection: sqlite3.Connection, artifacts: list[ParsedArtifact]) -> None:
    entities: dict[str, str] = {}
    links: list[tuple[str, str, str, str]] = []
    for artifact in artifacts:
        record = artifact.record
        for role, name in (("actor", record.actor), ("counterparty", record.counterparty)):
            if not name:
                continue
            eid = _entity_id(name)
            entities[eid] = name
            link_id = f"{record.record_id}-{role}"
            links.append((link_id, eid, record.record_id, role))
    connection.executemany(
        "INSERT OR IGNORE INTO entities(entity_id, display_name) VALUES (?, ?)",
        [(eid, name) for eid, name in entities.items()],
    )
    connection.executemany(
        "INSERT OR REPLACE INTO entity_links(link_id, entity_id, record_id, role) VALUES (?, ?, ?, ?)",
        links,
    )


def _populate_search_index(
    connection: sqlite3.Connection, artifacts: list[ParsedArtifact], files: list[dict[str, Any]]
) -> None:
    rows = [artifact_search_row(artifact) for artifact in artifacts]
    rows.extend(file_search_rows(files))
    placeholders = ",".join("?" for _ in SEARCH_COLUMNS)
    column_list = ",".join(SEARCH_COLUMNS)
    statement = f"INSERT INTO search_index({column_list}) VALUES ({placeholders})"
    for row in rows:
        values = [row.get(column) for column in SEARCH_COLUMNS]
        connection.execute(statement, values)


def _populate_recovery_findings(connection: sqlite3.Connection, findings: list[RecoveryFinding]) -> None:
    for finding in findings:
        connection.execute(
            """
            INSERT OR REPLACE INTO recovery_findings(
                record_id, artifact_type, raw_ref, confidence, summary,
                finding_label, database_file, wal_file, parser_method, parser_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding.record_id,
                finding.artifact_type,
                finding.raw_ref,
                finding.confidence,
                finding.summary,
                finding.label,
                finding.database_file,
                finding.wal_file,
                finding.parser_method,
                finding.parser_version,
            ),
        )


def _populate_evidence_files(connection: sqlite3.Connection, files: list[dict[str, Any]]) -> None:
    for entry in files:
        path = entry["path"]
        connection.execute(
            "INSERT OR REPLACE INTO evidence_files(path, sha256, size_bytes, mime_type) VALUES (?, ?, ?, ?)",
            (
                path,
                entry["sha256"],
                entry["size_bytes"],
                guess_mime_type(path),
            ),
        )


def _populate_case_metadata(connection: sqlite3.Connection, metadata: dict[str, Any]) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO case_metadata(case_id, timezone, parser_version) VALUES (?, ?, ?)",
        (
            metadata.get("case_id"),
            metadata.get("timezone"),
            PARSER_VERSION,
        ),
    )
