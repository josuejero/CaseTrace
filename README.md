# CaseTrace

**CaseTrace - Synthetic Android Evidence Analysis Lab**

CaseTrace is a synthetic-only Android evidence analysis lab built to demonstrate a repeatable mobile forensics workflow: preservation, acquisition, examination, analysis, and reporting. Phase 0 defines the fixed case model, the normalized artifact schema, the bundle contract, and the validation dataset that later parser and UI work must honor.

## Phase 0 Scope Lock

- Seed app package: `com.casetrace.waypoint`
- Device: `pixel7-api34-emulator`
- ADB serial: `emulator-5554`
- Subject: `Jordan Vega`
- Case folder: `cases/CT-2026-001/`
- Acquisition source path: `/data/user/0/com.casetrace.waypoint/`
- Acquisition method: `adb exec-out run-as com.casetrace.waypoint tar -cf - .`
- Narrative window: single synthetic day in `America/New_York`
- Artifact classes: `message`, `call`, `browser_visit`, `location_point`, `photo`, `app_event`, `recovered_record`
- Formal report format: `HTML`
- Canonical validation dataset: `case_ct_2026_001_ground_truth.json`

## Workflow

`Seed App -> Android Emulator -> acquisition script -> evidence bundle -> parser/normalizer -> case SQLite DB -> React UI -> HTML report`

The Phase 0 evidence bundle contract is:

- `case.json` for case metadata and acquisition context
- `files/` for raw acquired files
- `hash_manifest.json` for SHA-256 integrity tracking
- `parsed/` for future normalized outputs
- `reports/` for future HTML exports
- `validation/` for ground truth and expected metrics

## Chosen Stack

- Seed app: Kotlin, Jetpack architecture, Room over SQLite
- Analysis pipeline: Python 3.12+, FastAPI, Pydantic, SQLite/FTS5, NetworkX, ExifTool
- Investigator UI: React + Vite
- Reproducibility: Docker Compose and GitHub Actions in later phases

Phase 0 stops before building the Android app, FastAPI service, or React UI. This repo currently defines the contracts those later phases must implement.

## Repository Layout

- `docs/` contains the architecture diagram, parser schema spec, and synthetic evidence rules.
- `schemas/` contains the JSON Schema contracts for normalized artifacts and bundle metadata.
- `cases/CT-2026-001/` contains the locked case metadata, raw-source placeholders, and validation fixtures.
- `android/`, `backend/`, `frontend/`, and `acquisition/` are placeholders for later implementation phases.
- `tools/validate_phase0.py` verifies schema validity, fixture counts, traceability, and hash coverage.

## Integrity and Traceability Limits

- CaseTrace is synthetic-only and is not intended to process real personal data.
- Every normalized artifact must trace back to source evidence through `raw_ref`.
- Deleted evidence is limited to seeded SQLite WAL-derived records and carries reduced confidence.
- Phase 0 artifacts include placeholder raw source files where later phases will generate true emulator acquisitions.
- The repository is a portfolio lab, not a claim of courtroom readiness or forensic certification.

## Validation Dataset

The canonical dataset is frozen at 42 normalized records:

- 8 `message`
- 4 `call`
- 6 `browser_visit`
- 10 `location_point`
- 4 `photo`
- 8 `app_event`
- 2 `recovered_record`

The dataset also includes 12 cross-artifact correlations that later parsers and reports must preserve.

## Non-Goals

- Supporting multiple devices, users, or app packages in v1
- Ingesting real phones, cloud backups, or third-party apps
- Performing invasive recovery beyond seeded app files and seeded WAL content
- Claiming evidentiary authenticity beyond documented synthetic fixtures
- Defining alternative report formats beyond `HTML` for the formal export

## Phase 0 Verification

Run the verifier from the project root:

```bash
python3 tools/validate_phase0.py
```

The verifier checks the JSON Schemas, valid and invalid example fixtures, case metadata, hash coverage, ground-truth counts, deleted-record rules, and document consistency.

## Phase 7 Search

- The FastAPI search service now lives in `backend/main.py` and exposes the enhanced FTS5 index plus timeline context.
- The React + Vite UI in `frontend/` provides the global search box, artifact filters with hit counts, snippet previews, and detail panel for raw references.
- Detailed expectations and workflow notes are documented in `docs/phase7-search.md`, and the backend README explains how to run `uvicorn backend.main:app --reload`.
