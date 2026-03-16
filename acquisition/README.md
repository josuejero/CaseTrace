# Emulator Acquisition Workflow

This folder now hosts the Phase 2 acquisition script and guidance for capturing the synthetic CaseTrace evidence bundle from the `pixel7-api34-emulator`.

## Prerequisites

- Android `adb` installed and on `PATH` (Android platform tools).
- The `pixel7-api34-emulator` running with `com.casetrace.waypoint` installed and debuggable.
- The repository checked out so `git rev-parse HEAD` resolves (used for metadata).

## Capturing the evidence bundle

Run the scripted flow from the project root:

```bash
python acquisition/extract_case.py \
  --serial emulator-5554 \
  --case-dir cases/CT-2026-001 \
  --bundle-path cases/CT-2026-001/CT-2026-001-evidence-bundle.zip
```

The script performs the following discipline:

1. Verifies `adb`, the target serial, and the installed package.
2. Records emulator properties (`ro.product.model`, Android release/API), app version, host OS, and the current `git` commit.
3. Re-creates `cases/CT-2026-001/files/` (databases, exports, logs, media) while preserving `files/README.md`.
4. Streams `run-as com.casetrace.waypoint tar -cf - .` into a temporary tarball, extracts it, and recomputes SHA-256 hashes.
5. Writes `hash_manifest.json`, `acquisition_log.json`, and `CT-2026-001-evidence-bundle.zip` (the zipped sample evidence bundle).

### Optional overrides

- `--serial` – override the default `emulator-5554` (useful if multiple emulators are running).
- `--case-dir` – point the script at a different case bundle directory.
- `--bundle-path` – choose a different destination for the zipped evidence bundle (the log still records the path).

## Outputs

- `cases/CT-2026-001/files/` – the live acquisition of `/data/user/0/com.casetrace.waypoint/`.
- `cases/CT-2026-001/hash_manifest.json` – SHA-256 coverage for every file in `files/`.
- `cases/CT-2026-001/processing_log.json` – acquisition → analysis → report entries that document every re-hash step.
- `cases/CT-2026-001/acquisition_log.json` – timestamped metadata, actions, and file statistics.
- `cases/CT-2026-001/CT-2026-001-evidence-bundle.zip` – a zipped bundle of `case.json`, `files/`, `hash_manifest.json`, `parsed/`, `reports/`, and `validation/`.

For lab validation, always analyze a copy of the zipped bundle or the copied `files/` tree; never mutate the live acquisition artifacts.

`docs/phase8-integrity.md` explains how the new manifest/log pair plus the `/integrity` endpoint align with NIST/OSAC/SWGDE guidance.
