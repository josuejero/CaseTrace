"""FastAPI-based search endpoint for CaseTrace Phase 7."""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from integrity import (
    case_dir_from_db,
    gather_file_summary,
    load_manifest,
    load_processing_log,
)

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


@lru_cache(maxsize=1)
def get_settings() -> CaseSearchSettings:
    return CaseSearchSettings()


@lru_cache(maxsize=1)
def get_engine() -> "CaseSearchEngine":
    settings = get_settings()
    return CaseSearchEngine(settings.case_db_path)


app = FastAPI(title="CaseTrace Search API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"]
)


@app.get("/search", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Keyword expression to search"),
    artifact_types: list[str] | None = Query(None, alias="type", description="Artifact types to restrict"),
    limit: int = Query(20, ge=1, le=100, description="Maximum hits to return"),
    offset: int = Query(0, ge=0, description="Paging offset"),
) -> SearchResponse:
    engine = get_engine()
    settings = get_settings()
    total, counts, hits = engine.search(q, artifact_types or [], limit, offset, settings.context_window_minutes)
    return SearchResponse(total_hits=total, artifact_counts=counts, hits=hits)


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


class CaseSearchEngine:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        if not self.db_path.exists():
            raise RuntimeError(f"Case database not found at {self.db_path}")

    def search(
        self,
        query: str | None,
        artifact_types: list[str],
        limit: int,
        offset: int,
        context_window_minutes: int,
    ) -> tuple[int, dict[str, int], list[SearchHit]]:
        trimmed_query = query.strip() if query else None
        where_clause, params = self._build_filters(trimmed_query, artifact_types)
        with self._connect() as connection:
            timeline_rows = self._load_timeline(connection)
            index_map = {row["record_id"]: idx for idx, row in enumerate(timeline_rows)}
            hit_rows = self._fetch_hits(
                connection, where_clause, params, limit, offset, bool(trimmed_query)
            )
            artifact_counts = self._artifact_counts(connection, where_clause, params)
        total_hits = sum(artifact_counts.values())
        hits = [
            self._format_hit(row, timeline_rows, index_map, context_window_minutes)
            for row in hit_rows
        ]
        return total_hits, artifact_counts, hits

    def record_detail(self, record_id: str, context_window_minutes: int) -> RecordDetail | None:
        where = "WHERE s.record_id = ?"
        params = [record_id]
        with self._connect() as connection:
            timeline_rows = self._load_timeline(connection)
            index_map = {row["record_id"]: idx for idx, row in enumerate(timeline_rows)}
            row = connection.execute(self._select_clause() + " LEFT JOIN timeline_events t ON t.record_id = s.record_id " + where, params).fetchone()
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
            timeline_context=self._timeline_context(row["record_id"], timeline_rows, index_map, context_window_minutes),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path.as_posix())
        connection.row_factory = sqlite3.Row
        return connection

    def _build_filters(
        self, query: str | None, artifact_types: list[str]
    ) -> tuple[str, list[str]]:
        clauses: list[str] = []
        params: list[str] = []
        if query:
            clauses.append("search_index MATCH ?")
            params.append(query)
        if artifact_types:
            placeholders = ",".join("?" for _ in artifact_types)
            clauses.append(f"s.artifact_type IN ({placeholders})")
            params.extend(artifact_types)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_clause, params

    def _select_clause(self) -> str:
        return (
            "SELECT "
            "s.record_id, s.artifact_type, s.content_summary, s.actor, s.counterparty, "
            "s.source_file, s.url, s.title, s.metadata_text, "
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

    def _load_timeline(self, connection: sqlite3.Connection) -> list[dict[str, str | None]]:
        cursor = connection.execute(
            "SELECT record_id, artifact_type, event_time_start, event_time_local, content_preview, event_type FROM timeline_events ORDER BY event_time_start, event_type_rank"
        )
        return [dict(row) for row in cursor]

    def _artifact_counts(
        self, connection: sqlite3.Connection, where_clause: str, base_params: list[str]
    ) -> dict[str, int]:
        sql = (
            "SELECT s.artifact_type, COUNT(*) AS cnt FROM search_index s "
            + where_clause
            + " GROUP BY s.artifact_type"
        )
        params = list(base_params)
        cursor = connection.execute(sql, params)
        counts = {atype: 0 for atype in DEFAULT_ARTIFACT_TYPES}
        for row in cursor:
            counts[row["artifact_type"]] = row["cnt"]
        return counts

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
            url=row["url"],
            title=row["title"],
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
