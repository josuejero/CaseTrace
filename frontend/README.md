# CaseTrace Investigator UI

The Phase 9 React + Vite frontend now renders a full investigator workspace: case overview, timeline, artifacts browser, entity graph, global search, and the embedded investigator report. Each tab talks to the FastAPI backend endpoints described in `docs/phase9-investigator-ui.md`.

## Getting started

```bash
cd frontend
npm install
npm run dev
```

The UI expects the backend at `http://localhost:8000` by default. Override it with `VITE_API_URL` when you launch the dev server.

## Features

- **Multi-tab layout** – Pick overview, timeline, artifacts, graph, search, or report to tell a complete investigator story in under two minutes.
- **Graph rendering** – `react-force-graph-2d` draws the entity graph produced by `tools/build_graph.py`.
- **Artifacts timeline** – Filters for artifact type, deleted data, and location awareness stay in sync with the search workspace.
- **Report integration** – The report tab embeds the server-generated HTML export, surfaces validation/integrity insights, and lets users click “Regenerate report”.
- **Search continuity** – Timeline and graph jumps pin a record in the search panel, so evidence exploration stays linked.

## Docs & screenshots

Detailed UI expectations live in `docs/phase9-investigator-ui.md`. Capture polished screenshots (one per tab) via `docs/phase9-screenshots.md` and store them under `docs/screenshots/phase9/` for your portfolio.
