# Report Placeholder

Later phases will still render the formal HTML report for `CT-2026-001`. In the meantime, the Phase 5 tools expose a simple analyst view of the entity graph.

## Phase 5 graph artifacts

Run `python tools/build_graph.py --case-dir cases/CT-2026-001` to:

1. write `reports/analysis/graph-data.json`, the normalized node/edge payload that powers the visualizations.
2. render `reports/graph.html`, the WebGL/PyVis interactive map of actors, locations, devices, URLs, and files.
    3. emit `reports/analysis/entity-detail.html`, which loads `graph-data.json` and lists every person with the edges and raw references that support that relationship.

Open the files under `reports/analysis` with a simple HTTP server (e.g., `python -m http.server` from the reports folder) if the browser prevents `fetch()` from loading the JSON bundle via `file://`.

## WAL recovery explanation

Generate the WAL recovery narrative with:

```bash
python tools/recovery_report.py --case-dir cases/CT-2026-001 --output-html cases/CT-2026-001/reports/recovery.html
```

Then open `reports/recovery.html` from `cases/CT-2026-001/reports` (for example via `python -m http.server` run from that directory) to review the observed/recovered/inferred findings along with their provenance.

## Phase 10 validation report

The Phase 10 validation script recomputes the ground-truth checks and writes a human-readable summary.

```bash
python tools/validate_phase10.py --case-dir cases/CT-2026-001
```

View the generated report at `reports/validation.md` or consult `docs/phase10-validation.md` for the QA checklist, test coverage, and the scripted limitations statement that references NIST CFTT / SWGDE.
