# Phase 8 Chain-of-Custody Integrity

Phase 8 is where CaseTrace shifts from a dashboard feel into a disciplined lab workflow. Every acquisition, re‑hash, and export is captured so another trained examiner can reproduce what happened and verify fixity along the way. The manifest/log pair follows the integrity calls made by NIST SP 800-86, the OSAC Digital and Multimedia Evidence Guidelines, and SWGDE’s Observational Integrity guidance: hash everything as early as possible, re-check before any processing or reporting, and write down every transform as a discrete step.

## Structured manifest

- `case_id`, `algorithm`, and `generated_at` provide the basic fixity identity and timestamp.
- `acquisition` records the operator name, acquisition timestamp/method, script version, and device/emulator fields (logical ID, adb serial, platform). This mirrors the scenario-focused metadata suggested by OSAC’s Acquisition and Preservation subgroup.
- `app` captures the package, label, and version of the seed artifact so any folder-level rehash can be tied directly back to the seeded application.
- `environment` stores the git commit plus an optional container image digest so the exact toolset is traceable, satisfying the reproducibility expectations from SWGDE’s validation checklists.
- `parser_version` and `report` record the last parser step and exported report, and the `files` array lists every file path alongside its SHA-256 and size. The hooded script re-hashes before analysis and once more before exporting a report so analysts always see the freshest digest.

## Processing log and UI

`processing_log.json` is the narrative ledger. Every transform — acquisition, analysis, and report export — becomes a log entry with a timestamp, description, actor, and detail table (hash summary, parser version, report digest, etc.). The FastAPI `/integrity` endpoint now returns the manifest, log, and file summary; the React UI renders that payload in the Integrity panel so detectives see operator/device/problem statements alongside the raw hashes.

## Tools and verification

- `acquisition/extract_case.py` and `tools/generate_seed_artifacts.py` both reuse the shared `integrity.py` helpers, so they always emit identical manifest/log shapes and reuse the same hash/log append routines.
- `tools/recovery_report.py` re-hashes the bundle before rendering the HTML report, updates the `report` object in the manifest, and appends a `report_export` step for traceability.
- `tools/validate_phase0.py` now loads both JSON files, validates them against `schemas/hash-manifest.schema.json` and `schemas/processing-log.schema.json`, and ensures the log contains the canonical acquisition/analysis/report stages.

Read this document in tandem with `README.md`’s Phase 7/8 descriptions to see how the UI endpoint fits into the broader CaseTrace workflow.
