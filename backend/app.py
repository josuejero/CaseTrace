"""FastAPI application definition for the CaseTrace investigator API."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.engine import CaseDataEngine
from backend.models import (
    ArtifactsResponse,
    EntityGraphResponse,
    IntegrityResponse,
    OverviewResponse,
    RecordDetail,
    ReportRenderResponse,
    ReportSummary,
    SearchResponse,
    TimelineResponse,
)
from backend.settings import get_engine, get_settings
from integrity import case_dir_from_db, gather_file_summary, load_manifest, load_processing_log
from tools.phase9_report import ReportGenerationResult, generate_report

logger = logging.getLogger(__name__)

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
    try:
        return engine.report_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/reports/latest/html")
def latest_report_html() -> FileResponse:
    engine = get_engine()
    try:
        summary = engine.report_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    path = engine.case_dir / summary.path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report HTML not found")
    return FileResponse(path, media_type="text/html", filename=path.name)


@app.get("/reports/latest/pdf")
def latest_report_pdf() -> FileResponse:
    engine = get_engine()
    try:
        summary = engine.report_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
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
