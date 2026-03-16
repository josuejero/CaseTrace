# CaseTrace Search UI

This directory now hosts the Phase 7 search experience: a small React + Vite single-page app that talks to `backend/main.py`.

## Getting started

```bash
cd frontend
npm install
npm run dev
```

By default the app calls `http://localhost:8000/search`. If you run the FastAPI backend on another host or port, set `VITE_API_URL` before starting the dev server:

```bash
VITE_API_URL=http://127.0.0.1:9000 npm run dev
```

## Features

- Global keyword input that hits the SQLite FTS5 search index.
- Artifact-type chips with hit counts reported by the backend.
- Result cards with snippet previews, metadata, and clickable detail panels.
- Timeline context for each record plus raw reference/source information.
