# Phase 7 Keyword Search

Phase 7 brings a full feature search layer so the CaseTrace lab feels like a product. The requirements are satisfied by three cooperating pieces:

1. **Enriched SQLite search index** in `parser/pipeline.py` (`search_index` FTS5 table) that now stores text for message bodies, browser URLs/titles, metadata, and evidence files. Every manifest entry also populates a row marked `artifact_type = "evidence_file"` so files can surface in the UI. The table uses `tokenize = 'porter unicode61'` for light stemming.
2. **FastAPI backend (`backend/main.py`)** that exposes:
   * `GET /search` accepts `q` (keywords), repeated `type` filters, `limit`, and `offset`. The service matches against the FTS table, orders by `bm25()`, returns snippet previews (with `<mark>` highlights), and bundles the surrounding timeline context for each hit via joins into `timeline_events`.
   * `GET /records/{record_id}` for raw metadata plus chronology so the investigator can click through to the underlying traceability details.
   * Artifact-level counts for every request so the UI chips show hit counts.
3. **React + Vite UI (`frontend/`)** that renders a global search box, filter chips, result cards with snippet previews, and an adjacent detail panel that surfaces `raw_ref`, `source_file`, and the scraped timeline window.

### Running the stack

- Build the backend dependencies and run the API:
  ```bash
  pip install fastapi uvicorn requests
  uvicorn backend.main:app --reload
  ```
  Override the database used in development with `CASE_DB_PATH=/path/to/case.db` if needed.
- Start the UI inside `/frontend`:
  ```bash
  cd frontend
  npm install
  VITE_API_URL=http://localhost:8000 npm run dev
  ```

### Expectations covered

| Feature | Implementation |
| --- | --- |
| Global keyword search | React input -> FastAPI `/search` -> FTS5 `search_index` with `content_summary`, `url`, `title`, `metadata_text` columns. |
| Per-artifact filtering | `/search` accepts repeated `type` params; `artifact_counts` returns counts for chips. |
| Snippet preview & ranking | Query uses `snippet(..., '<mark>', '</mark>')` and `bm25()` for ordering. |
| File/metadata search | Manifest entries feed `artifact_type = "evidence_file"`, metadata_text contains SHA and MIME. |
| Click-through raw/timeline context | `SearchHit` returns `raw_ref` and timeline context derived from `timeline_events`; `RecordDetail` endpoint provides deeper drilldowns. |

Additions to the repository layout:
- `backend/main.py`, `backend/__init__.py` for the FastAPI service.
- `frontend/` hosts the new React/Vite bundle.
- `docs/phase7-search.md` documents the feature, and `backend/README.md` shows how to run the API.
