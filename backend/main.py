"""FastAPI-based investigator data service for CaseTrace Phase 9."""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from integrity import (
    case_dir_from_db,
    gather_file_summary,
    load_manifest,
    load_processing_log,
)
from tools.phase9_report import ReportGenerationResult, generate_report

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACT_TYPES = [
    "message",
    "call",
    "browser_visit",
    "location_point",
    "photo",
    "app_event",
    "recovered_record",
    "evidence_file",
]


class CaseSearchSettings(BaseSettings):
    case_db_path: Path = Field(default=Path("cases/CT-2026-001/parsed/case.db"), env="CASE_DB_PATH")
    context_window_minutes: int = Field(default=3, ge=1, le=15, env="CONTEXT_WINDOW_MINUTES")


# Search models retained for compatibility
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


# New models for Phase 9 UI
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


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _format_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_case_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class CaseDataEngine:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        if not self.db_path.exists():
            raise RuntimeError(f"Case database not found at {self.db_path}")
        self.case_dir = case_dir_from_db(self.db_path)
        self.case_metadata = _load_case_metadata(self.case_dir)
        self._graph_cache: dict[str, Any] | None = None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path.as_posix())
        connection.row_factory = sqlite3.Row
        return connection

    def _load_manifest(self) -> dict[str, Any]:
        try:
            return load_manifest(self.case_dir)
        except FileNotFoundError:
            return {}

    def _load_processing_log(self) -> dict[str, Any]:
        return load_processing_log(self.case_dir)

    def record_detail(self, record_id: str, context_window_minutes: int) -> RecordDetail | None:
        where = "WHERE s.record_id = ?"
        params = [record_id]
        with self._connect() as connection:
            timeline_rows = self._load_timeline(connection)
            index_map = {row["record_id"]: idx for idx, row in enumerate(timeline_rows)}
            row = connection.execute(
                self._select_clause() + "LEFT JOIN timeline_events t ON t.record_id = s.record_id " + where,
                params,
            ).fetchone()
        if not row:
            return None
        return RecordDetail(
            record_id=row["record_id"],
            artifact_type=row["artifact_type"],
            content_summary=row["content_summary"],
            raw_ref=row["raw_ref"],
            event_time=row["event_time_start"],
            event_time_local=row["event_time_local"],
            source_file=row["source_file"],
            metadata_text=row["metadata_text"],
            timeline_context=self._timeline_context(
                row["record_id"], timeline_rows, index_map, context_window_minutes
            ),
        )

    def search(
        self,
        query: str | None,
        artifact_types: list[str],
        limit: int,
        offset: int,
        context_window_minutes: int,
    ) -> tuple[int, dict[str, int], dict[str, int], list[SearchHit]]:
        trimmed_query = query.strip() if query else None
        where_clause, params = self._build_filters(trimmed_query, artifact_types)
        with self._connect() as connection:
            timeline_rows = self._load_timeline(connection)
            index_map = {row["record_id"]: idx for idx, row in enumerate(timeline_rows)}
            hit_rows = self._fetch_hits(
                connection, where_clause, params, limit, offset, bool(trimmed_query)
            )
            artifact_counts = self._artifact_counts(connection, where_clause, params)
            source_counts = self._source_counts(connection, where_clause, params)
        total_hits = sum(artifact_counts.values())
        hits = [
            self._format_hit(row, timeline_rows, index_map, context_window_minutes)
            for row in hit_rows
        ]
        return total_hits, artifact_counts, source_counts, hits

    def overview(self) -> OverviewResponse:
        manifest = self._load_manifest()
        metadata = self.case_metadata
        case_id = manifest.get("case_id") or metadata.get("case_id")
        subject = metadata.get("subject", {}).get("display_name")
        parser_version = manifest.get("parser_version")
        file_summary = gather_file_summary(manifest.get("files", [])) if manifest else {"file_count": 0, "total_size_bytes": 0}
        with self._connect() as connection:
            artifact_counts = self._artifact_counts(connection, "", [])
            notable = self._notable_recovery_findings(connection)
        top_files = sorted(manifest.get("files", []), key=lambda entry: entry.get("size_bytes", 0), reverse=True)[:5]
        top_files_models = [FileEntry(**{"path": entry["path"], "size_bytes": entry.get("size_bytes", 0), "sha256": entry.get("sha256")}) for entry in top_files]
        return OverviewResponse(
            case_id=case_id,
            title=metadata.get("title"),
            subject=subject,
            acquisition=manifest.get("acquisition", {}),
            parser_version=parser_version,
            file_summary=file_summary,
            artifact_counts=artifact_counts,
            top_files=top_files_models,
            notable_artifacts=notable,
            latest_report=manifest.get("report"),
        )

    def timeline(
        self,
        artifact_types: list[str],
        deleted_only: bool,
        location_only: bool,
        anchor: str | None,
        window_minutes: int,
        limit: int,
        offset: int,
    ) -> TimelineResponse:
        filters, params = self._build_timeline_filters(
            artifact_types, deleted_only, location_only, anchor, window_minutes
        )
        with self._connect() as connection:
            rows = self._fetch_timeline_rows(connection, filters, params, limit, offset)
            total = self._count_timeline_rows(connection, filters, params)
        grouped = self._group_timeline(rows)
        return TimelineResponse(total=total, groups=grouped)

    def artifacts(
        self,
        artifact_type: str | None,
        show_deleted: bool,
        show_recovered_only: bool,
        sort_by: str,
        sort_dir: str,
        limit: int,
        offset: int,
    ) -> ArtifactsResponse:
        filters: list[str] = []
        params: list[Any] = []
        if artifact_type:
            filters.append("artifact_type = ?")
            params.append(artifact_type)
        if not show_deleted:
            filters.append("deleted_flag = 0")
        if show_recovered_only:
            filters.append("artifact_type = 'recovered_record'")
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        order_field = sort_by if sort_by in {"event_time_start", "confidence", "record_id"} else "event_time_start"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        order_clause = f"ORDER BY {order_field} {direction}, event_time_start DESC"
        query = (
            "SELECT record_id, artifact_type, event_time_start, event_time_local, actor, target, confidence, deleted_flag, source_file, raw_ref, event_type "
            "FROM timeline_events "
            f"{where_clause} {order_clause} LIMIT ? OFFSET ?"
        )
        with self._connect() as connection:
            cursor = connection.execute(query, [*params, limit, offset])
            rows = cursor.fetchall()
            total = self._count_timeline_rows(connection, where_clause, params)
        return ArtifactsResponse(total=total, rows=[self._artifact_row_from_row(row) for row in rows])

    def entity_graph(self, refresh: bool = False) -> EntityGraphResponse:
        if refresh or self._graph_cache is None:
            graph_path = self.case_dir / "reports" / "analysis" / "graph-data.json"
            if not graph_path.exists():
                raise FileNotFoundError(
                    "Entity graph data not found. Run tools/build_graph.py --case-dir <case> to generate it."
                )
            with graph_path.open("r", encoding="utf-8") as handle:
                self._graph_cache = json.load(handle)
            self._graph_cache.setdefault("case_id", self.case_metadata.get("case_id"))
        data = self._graph_cache
        return EntityGraphResponse(
            case_id=data.get("case_id"),
            generated_at=data.get("generated_at"),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
        )

    def report_summary(self) -> ReportSummary:
        manifest = self._load_manifest()
        report = manifest.get("report")
        if not report or not report.get("path"):
            raise HTTPException(status_code=404, detail="No report found in manifest")
        pdf_path = report.get("pdf_path")
        return ReportSummary(
            generated_at=report.get("generated_at"),
            path=report["path"],
            sha256=report.get("sha256", ""),
            pdf_path=pdf_path,
            validation=report.get("validation"),
        )

    # helpers
    def _artifact_row_from_row(self, row: sqlite3.Row) -> ArtifactRow:
        return ArtifactRow(
            record_id=row["record_id"],
            artifact_type=row["artifact_type"],
            event_time_start=row["event_time_start"],
            event_time_local=row["event_time_local"],
            actor=row["actor"],
            target=row["target"],
            confidence=row["confidence"],
            deleted_flag=bool(row["deleted_flag"]),
            raw_ref=row["raw_ref"],
            source_file=row["source_file"],
            event_type=row["event_type"],
        )

    def _count_timeline_rows(self, connection: sqlite3.Connection, where: str, params: list[Any]) -> int:
        sql = "SELECT COUNT(*) AS cnt FROM timeline_events " + where
        cursor = connection.execute(sql, params)
        result = cursor.fetchone()
        return result["cnt"] if result else 0

    def _build_timeline_filters(
        self,
        artifact_types: list[str],
        deleted_only: bool,
        location_only: bool,
        anchor: str | None,
        window_minutes: int,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if artifact_types:
            placeholders = ",".join("?" for _ in artifact_types)
            clauses.append(f"artifact_type IN ({placeholders})")
            params.extend(artifact_types)
        if deleted_only:
            clauses.append("deleted_flag = 1")
        if location_only:
            clauses.append("has_location = 1")
        if anchor:
            anchor_times = self._anchor_window(anchor, window_minutes)
            if anchor_times:
                clauses.append("event_time_start BETWEEN ? AND ?")
                params.extend(anchor_times)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_clause, params

    def _anchor_window(self, record_id: str, window_minutes: int) -> tuple[str, str] | None:
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT event_time_start FROM timeline_events WHERE record_id = ?", (record_id,)
            )
            row = cursor.fetchone()
        if not row:
            return None
        anchor_dt = _parse_iso(row["event_time_start"])
        if not anchor_dt:
            return None
        window = timedelta(minutes=window_minutes)
        start = _format_iso(anchor_dt - window)
        end = _format_iso(anchor_dt + window)
        return start, end

    def _fetch_timeline_rows(
        self, connection: sqlite3.Connection, where_clause: str, params: list[Any], limit: int, offset: int
    ) -> list[sqlite3.Row]:
        cursor = connection.execute(
            "SELECT * FROM timeline_events " + where_clause + " ORDER BY event_time_start, event_type_rank LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        return cursor.fetchall()

    def _group_timeline(self, rows: list[sqlite3.Row]) -> list[TimelineGroup]:
        grouped: OrderedDict[str, list[sqlite3.Row]] = OrderedDict()
        for row in rows:
            key = (row["event_time_local"] or row["event_time_start"] or "UNKNOWN")[:10]
            grouped.setdefault(key, []).append(row)
        output: list[TimelineGroup] = []
        for period, items in grouped.items():
            counts: dict[str, int] = {}
            for row in items:
                counts[row["artifact_type"]] = counts.get(row["artifact_type"], 0) + 1
            output.append(
                TimelineGroup(
                    period=period,
                    artifact_counts=counts,
                    events=[
                        TimelineEvent(
                            record_id=item["record_id"],
                            artifact_type=item["artifact_type"],
                            event_time_start=item["event_time_start"],
                            event_time_local=item["event_time_local"],
                            content_preview=item["content_preview"],
                            event_type=item["event_type"],
                            actor=item["actor"],
                            target=item["target"],
                            source_file=item["source_file"],
                            raw_ref=item["raw_ref"],
                            deleted_flag=bool(item["deleted_flag"]),
                            has_location=bool(item["has_location"]),
                        )
                        for item in items
                    ],
                )
            )
        return output

    def _notable_recovery_findings(self, connection: sqlite3.Connection) -> list[NotableArtifact]:
        cursor = connection.execute(
            "SELECT record_id, artifact_type, summary, raw_ref, database_file, confidence FROM recovery_findings "
            "ORDER BY confidence DESC LIMIT 6"
        )
        return [
            NotableArtifact(
                record_id=row["record_id"],
                artifact_type=row["artifact_type"],
                confidence=row["confidence"],
                summary=row["summary"],
                raw_ref=row["raw_ref"],
                database_file=row["database_file"],
            )
            for row in cursor.fetchall()
        ]

    def _load_timeline(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        cursor = connection.execute(
            "SELECT record_id, artifact_type, event_time_start, event_time_local, content_preview, event_type FROM timeline_events ORDER BY event_time_start, event_type_rank"
        )
        return [dict(row) for row in cursor]

    def _source_counts(self, connection: sqlite3.Connection, where_clause: str, base_params: list[str]) -> dict[str, int]:
        sql = (
            "SELECT COALESCE(t.source_file, 'unknown') AS resolved_source, COUNT(*) AS cnt "
            "FROM search_index s "
            "LEFT JOIN timeline_events t ON t.record_id = s.record_id "
            + where_clause
            + " GROUP BY COALESCE(t.source_file, 'unknown')"
        )
        cursor = connection.execute(sql, base_params)
        return {row["resolved_source"]: row["cnt"] for row in cursor.fetchall()}

    def _artifact_counts(self, connection: sqlite3.Connection, where_clause: str, base_params: list[str]) -> dict[str, int]:
        sql = (
            "SELECT s.artifact_type, COUNT(*) AS cnt FROM search_index s " + where_clause + " GROUP BY s.artifact_type"
        )
        cursor = connection.execute(sql, base_params)
        counts = {atype: 0 for atype in DEFAULT_ARTIFACT_TYPES}
        for row in cursor.fetchall():
            counts[row["artifact_type"]] = row["cnt"]
        return counts

    def _build_filters(self, query: str | None, artifact_types: list[str]) -> tuple[str, list[str]]:
        clauses: list[str] = []
        params: list[str] = []
        if query:
            clauses.append("search_index MATCH ?")
            params.append(self._prepare_match_query(query))
        if artifact_types:
            placeholders = ",".join("?" for _ in artifact_types)
            clauses.append(f"s.artifact_type IN ({placeholders})")
            params.extend(artifact_types)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_clause, params

    @staticmethod
    def _prepare_match_query(raw_query: str) -> str:
        normalized_tokens: list[str] = []
        for token in raw_query.split():
            stripped = token.strip()
            if not stripped:
                continue
            if ":" in stripped and not (stripped.startswith('"') and stripped.endswith('"')):
                escaped = stripped.replace('"', '""')
                stripped = f'"{escaped}"'
            normalized_tokens.append(stripped)
        return " ".join(normalized_tokens)

    def _select_clause(self) -> str:
        return (
            "SELECT "
            "s.record_id, s.artifact_type, s.content_summary, s.content_summary AS metadata_text, "
            "s.actor, s.counterparty, "
            "s.source_file, "
            "t.event_time_start, t.event_time_local, t.raw_ref, t.content_preview, t.event_type, "
            "snippet(search_index, 2, '<mark>', '</mark>', '...', 64) AS snippet "
            "FROM search_index s "
        )

    def _fetch_hits(
        self,
        connection: sqlite3.Connection,
        where_clause: str,
        base_params: list[str],
        limit: int,
        offset: int,
        ranked: bool,
    ) -> list[sqlite3.Row]:
        order_clause = (
            "ORDER BY bm25(search_index) ASC, t.event_time_start, t.event_type_rank"
            if ranked
            else "ORDER BY t.event_time_start, t.event_type_rank"
        )
        params = list(base_params) + [limit, offset]
        sql = (
            self._select_clause()
            + "LEFT JOIN timeline_events t ON t.record_id = s.record_id "
            + where_clause
            + " "
            + order_clause
            + " LIMIT ? OFFSET ?"
        )
        cursor = connection.execute(sql, params)
        return cursor.fetchall()

    def _format_hit(
        self,
        row: sqlite3.Row,
        timeline_rows: list[dict[str, str | None]],
        record_index: dict[str, int],
        context_window_minutes: int,
    ) -> SearchHit:
        snippet = row["snippet"] or row["content_summary"] or ""
        return SearchHit(
            record_id=row["record_id"],
            artifact_type=row["artifact_type"],
            snippet=snippet,
            event_time=row["event_time_start"],
            event_time_local=row["event_time_local"],
            raw_ref=row["raw_ref"],
            actor=row["actor"],
            counterparty=row["counterparty"],
            source_file=row["source_file"],
            url=None,
            title=None,
            metadata_text=row["metadata_text"],
            timeline_context=self._timeline_context(
                row["record_id"], timeline_rows, record_index, context_window_minutes
            ),
        )

    def _timeline_context(
        self,
        record_id: str,
        timeline_rows: list[dict[str, str | None]],
        record_index: dict[str, int],
        window: int,
    ) -> list[TimelineEntry]:
        idx = record_index.get(record_id)
        if idx is None:
            return []
        start = max(0, idx - window)
        end = min(len(timeline_rows), idx + window + 1)
        return [
            TimelineEntry(
                record_id=row["record_id"],
                artifact_type=row["artifact_type"],
                event_time_start=row.get("event_time_start"),
                event_time_local=row.get("event_time_local"),
                content_preview=row.get("content_preview"),
                event_type=row.get("event_type"),
            )
            for row in timeline_rows[start:end]
        ]


@lru_cache(maxsize=1)
def get_settings() -> CaseSearchSettings:
    return CaseSearchSettings()


@lru_cache(maxsize=1)
def get_engine() -> CaseDataEngine:
    settings = get_settings()
    return CaseDataEngine(settings.case_db_path)


app = FastAPI(title="CaseTrace Investigator API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/overview", response_model=OverviewResponse)
def overview() -> OverviewResponse:
    engine = get_engine()
    return engine.overview()


@app.get("/timeline", response_model=TimelineResponse)
def timeline(
    artifact_types: list[str] | None = Query(None, alias="type"),
    deleted_only: bool = Query(False),
    location_only: bool = Query(False),
    anchor: str | None = Query(None),
    window_minutes: int = Query(30, ge=5, le=240),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TimelineResponse:
    engine = get_engine()
    return engine.timeline(
        artifact_types or [], deleted_only, location_only, anchor, window_minutes, limit, offset
    )


@app.get("/artifacts", response_model=ArtifactsResponse)
def artifacts(
    artifact_type: str | None = Query(None, description="Optional artifact type filter"),
    show_deleted: bool = Query(False),
    show_recovered_only: bool = Query(False),
    sort_by: str = Query("event_time_start"),
    sort_dir: str = Query("desc"),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ArtifactsResponse:
    engine = get_engine()
    return engine.artifacts(artifact_type, show_deleted, show_recovered_only, sort_by, sort_dir, limit, offset)


@app.get("/entity-graph", response_model=EntityGraphResponse)
def entity_graph(refresh: bool = Query(False)) -> EntityGraphResponse:
    engine = get_engine()
    try:
        return engine.entity_graph(refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/reports/latest", response_model=ReportSummary)
def latest_report() -> ReportSummary:
    engine = get_engine()
    return engine.report_summary()


@app.get("/reports/latest/html")
def latest_report_html() -> FileResponse:
    engine = get_engine()
    summary = engine.report_summary()
    path = engine.case_dir / summary.path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report HTML not found")
    return FileResponse(path, media_type="text/html", filename=path.name)


@app.get("/reports/latest/pdf")
def latest_report_pdf() -> FileResponse:
    engine = get_engine()
    summary = engine.report_summary()
    if not summary.pdf_path:
        raise HTTPException(status_code=404, detail="PDF version not yet generated")
    path = engine.case_dir / summary.pdf_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.post("/reports/render", response_model=ReportRenderResponse)
def render_report(pdf: bool = Query(False)) -> ReportRenderResponse:
    case_dir = get_engine().case_dir
    _run_report_job(case_dir, pdf)
    return ReportRenderResponse(status="completed", message="Report generation finished")


def _run_report_job(case_dir: Path, generate_pdf: bool) -> None:
    try:
        result: ReportGenerationResult = generate_report(case_dir, generate_pdf=generate_pdf)
        logger.info("Report generated at %s", result.html_path)
    except Exception as exc:  # pragma: no cover - guard best effort
        logger.exception("Report generation failed: %s", exc)


@app.get("/search", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Keyword expression to search"),
    artifact_types: list[str] | None = Query(None, alias="type", description="Artifact types to restrict"),
    limit: int = Query(20, ge=1, le=100, description="Maximum hits to return"),
    offset: int = Query(0, ge=0, description="Paging offset"),
) -> SearchResponse:
    engine = get_engine()
    settings = get_settings()
    total, counts, sources, hits = engine.search(q, artifact_types or [], limit, offset, settings.context_window_minutes)
    return SearchResponse(total_hits=total, artifact_counts=counts, source_counts=sources, hits=hits)


@app.get("/records/{record_id}", response_model=RecordDetail)
def record_detail(record_id: str) -> RecordDetail:
    engine = get_engine()
    settings = get_settings()
    detail = engine.record_detail(record_id, settings.context_window_minutes)
    if not detail:
        raise HTTPException(status_code=404, detail="Record not found")
    return detail


@app.get("/integrity", response_model=IntegrityResponse)
def integrity_data() -> IntegrityResponse:
    settings = get_settings()
    case_dir = case_dir_from_db(settings.case_db_path)
    try:
        manifest = load_manifest(case_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    processing_log = load_processing_log(case_dir)
    summary = gather_file_summary(manifest.get("files", []))
    return IntegrityResponse(
        manifest=manifest,
        processing_log=processing_log,
        file_summary=summary,
    )
