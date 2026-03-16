"""Pydantic schemas used by the CaseTrace FastAPI backend."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TimelineEntry(BaseModel):
    record_id: str
    artifact_type: str
    event_time_start: str | None
    event_time_local: str | None
    content_preview: str | None
    event_type: str | None


class SearchHit(BaseModel):
    record_id: str
    artifact_type: str
    snippet: str
    event_time: str | None
    event_time_local: str | None
    raw_ref: str | None
    actor: str | None
    counterparty: str | None
    source_file: str | None
    url: str | None
    title: str | None
    metadata_text: str | None
    timeline_context: list[TimelineEntry]


class SearchResponse(BaseModel):
    total_hits: int
    artifact_counts: dict[str, int]
    source_counts: dict[str, int]
    hits: list[SearchHit]


class RecordDetail(BaseModel):
    record_id: str
    artifact_type: str
    content_summary: str | None
    raw_ref: str | None
    event_time: str | None
    event_time_local: str | None
    source_file: str | None
    metadata_text: str | None
    timeline_context: list[TimelineEntry]


class IntegrityManifest(BaseModel):
    case_id: str
    algorithm: str
    generated_at: str
    acquisition: dict[str, Any]
    app: dict[str, Any]
    environment: dict[str, Any]
    parser_version: str
    report: dict[str, Any] | None
    files: list[dict[str, Any]]


class ProcessingLogStep(BaseModel):
    stage: str
    timestamp: str
    description: str
    actor: str | None
    details: dict[str, Any] | None


class ProcessingLog(BaseModel):
    case_id: str
    generated_at: str
    steps: list[ProcessingLogStep]


class IntegrityResponse(BaseModel):
    manifest: IntegrityManifest
    processing_log: ProcessingLog
    file_summary: dict[str, int]


class FileEntry(BaseModel):
    path: str
    size_bytes: int
    sha256: str | None = None


class NotableArtifact(BaseModel):
    record_id: str
    artifact_type: str
    confidence: float | None
    summary: str | None
    raw_ref: str | None
    database_file: str | None


class OverviewResponse(BaseModel):
    case_id: str | None
    title: str | None
    subject: str | None
    acquisition: dict[str, Any]
    parser_version: str | None
    file_summary: dict[str, int]
    artifact_counts: dict[str, int]
    top_files: list[FileEntry]
    notable_artifacts: list[NotableArtifact]
    latest_report: dict[str, Any] | None


class TimelineEvent(BaseModel):
    record_id: str
    artifact_type: str
    event_time_start: str | None
    event_time_local: str | None
    content_preview: str | None
    event_type: str | None
    actor: str | None
    target: str | None
    source_file: str | None
    raw_ref: str | None
    deleted_flag: bool
    has_location: bool


class TimelineGroup(BaseModel):
    period: str
    artifact_counts: dict[str, int]
    events: list[TimelineEvent]


class TimelineResponse(BaseModel):
    total: int
    groups: list[TimelineGroup]


class ArtifactRow(BaseModel):
    record_id: str
    artifact_type: str
    event_time_start: str | None
    event_time_local: str | None
    actor: str | None
    target: str | None
    confidence: float | None
    deleted_flag: bool
    raw_ref: str | None
    source_file: str | None
    event_type: str | None


class ArtifactsResponse(BaseModel):
    total: int
    rows: list[ArtifactRow]


class EntityGraphResponse(BaseModel):
    case_id: str | None
    generated_at: str | None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class ReportSummary(BaseModel):
    generated_at: str
    path: str
    sha256: str
    pdf_path: str | None
    validation: dict[str, Any] | None


class ReportRenderResponse(BaseModel):
    status: str
    message: str | None = None
