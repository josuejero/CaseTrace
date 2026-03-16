# Phase 9 Investigator UI & Reporting

This phase stitches together the CaseTrace lab into a demo-ready investigator workflow that can be shown in under two minutes. The stack is a FastAPI backend powering a React UI plus a server-generated HTML/PDF report so the narrative, integrity, and findings stay anchored to the normalized case data.

## Investigator screens

1. **Case overview** – Surface the case metadata, acquisition context, parser version, hash summary, artifact counts, and the highest-confidence recovered artifacts. The overview endpoint also returns the most recent report reference so the UI can surface the formal export alongside the integrity story.
2. **Timeline** – Grouped, filterable events derived from `timeline_events`. Artifact-type chips, deleted/location toggles, and a “jump to source” button allow investigators to pivot directly into the search workspace.
3. **Artifacts browser** – Browse each artifact type with sortable columns, deleted/recovered toggles, and links into the record detail view (powered by `/records/{record_id}`).
4. **Entity graph** – Render the PyVis-generated `graph-data.json` via `react-force-graph-2d`, show a metadata sidebar for the selected node, and offer click-through onto related evidence records.
5. **Search** – Keeps the Phase 7 search experience but now shares the selected record state with timeline/graph so every pivot stays in sync.
6. **Report** – Embeds the HTML report (served by `/reports/latest/html`), shows validation/integrity summaries, and lets users trigger a new export via `POST /reports/render`.

## Backend endpoints

- `GET /overview` – Returns artifact counts, file summary, notable recovered artifacts, and the latest report metadata.
- `GET /timeline` – Supports artifact filters, deleted/location flags, and anchor windows to group events by day/type.
- `GET /artifacts` – Returns rows from `timeline_events` with sorting and deleted/recovered filters.
- `GET /entity-graph` – Serves `reports/analysis/graph-data.json` (refreshable) for the interactive graph panel.
- `GET /reports/latest` – Exposes the latest report metadata/validation payload.
- `GET /reports/latest/html|/pdf` – Streams the generated report files.
- `POST /reports/render` – Kicks off the `tools.phase9_report.generate_report` job (HTML + optional PDF) and rewrites the manifest/log.

The existing search, record detail, and integrity endpoints remain available for the React UI.

## Report generator

`tools/phase9_report.py` builds a Jinja2-powered HTML report that highlights the executive summary, methods, findings table, integrity ledger, limitations, and validation results (grounded by `validation/expected_metrics.json`). The script writes `reports/phase9-investigator-report.html` (and optionally a PDF if `weasyprint` is installed), updates `hash_manifest.json`, and appends a `report_export` log step.

## Running the stack

```bash
# FastAPI backend
pip install -e .
uvicorn backend.main:app --reload

# React UI
cd frontend
npm install
npm run dev
```

Open the UI, switch through the tabs, and capture the timeline, artifacts, graph, search, and report panels for your portfolio.
