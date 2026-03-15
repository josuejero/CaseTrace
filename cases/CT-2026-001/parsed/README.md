# Parsed Output Directory

This directory now hosts the Phase 3 parser outputs: the normalized `artifact_records.json` list and the `case.db` normalized analysis database.

Run the parser pipeline from the project root:

```bash
python tools/parse_case.py --case-dir cases/CT-2026-001 --output-dir cases/CT-2026-001/parsed
```

The CLI discovers the bundle, parses each artifact (messages, calls, browser visits, locations, photos, app events, and WAL recoveries), writes the canonical ground-truth records into `artifact_records.json`, and builds `case.db` with the artifact-, timeline-, entity-, search-, and evidence tables described in Phase 3. Parsed outputs are validated against `validation/case_ct_2026_001_ground_truth.json`.
