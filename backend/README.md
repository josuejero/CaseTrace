# CaseTrace Search Service

Phase 7 introduces the FastAPI search service that exposes the SQLite FTS5 index to investigator workflows.

## Running the API

```bash
pip install -r requirements.txt  # installs fastapi, uvicorn, requests
uvicorn backend.main:app --reload
```

The server defaults to `cases/CT-2026-001/parsed/case.db`. Override the database path with `CASE_DB_PATH=/path/to/case.db`.

## API surface

- `GET /search`: Query parameters `q` (keywords), repeated `type` filters (artifact types), `limit`, and `offset`. Returns hit counts per type, snippet previews, and timeline context.
- `GET /records/{record_id}`: Details for a single artifact along with its surrounding timeline events.
- `GET /integrity`: Returns the hash manifest, processing log, and file summary that power the Integrity panel discussed in `docs/phase8-integrity.md`.
 - `GET /overview`: Returns case metadata, file summary, artifact counts, and notable recovered artifacts for the Overview tab.
 - `GET /timeline`: Streams grouped timeline events with artifact filters, deleted/location flags, and optional anchor windows.
 - `GET /artifacts`: Answers the artifacts browser with sortable rows from `timeline_events`.
 - `GET /entity-graph`: Serves the `reports/analysis/graph-data.json` payload produced by `tools/build_graph.py`.
 - `GET /reports/latest`, `/reports/latest/html`, `/reports/latest/pdf`: Surface the latest investigator report metadata and files.
 - `POST /reports/render`: Builds the Phase 9 HTML/PDF export, refreshes the manifest, and writes a `report_export` log entry (pass `pdf=true` to produce a PDF if `weasyprint` is installed).

Refer to `docs/phase7-search.md` for detailed expectations and UI flows.
