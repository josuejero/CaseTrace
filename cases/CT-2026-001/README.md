# CT-2026-001

This folder is the locked Phase 0 evidence bundle scaffold for the synthetic CaseTrace case.

## Fixed Case Facts

- subject: `Jordan Vega`
- package: `com.casetrace.waypoint`
- device: `pixel7-api34-emulator`
- ADB serial: `emulator-5554`
- timezone: `America/New_York`
- acquisition path: `/data/user/0/com.casetrace.waypoint/`
- report format: `HTML`

## Bundle Layout

- `case.json` records the case identity and acquisition context.
- `files/` contains placeholder raw sources that mirror the app directory structure.
- `hash_manifest.json` covers every file in `files/` with SHA-256.
- `parsed/` is reserved for future normalized exports.
- `reports/` is reserved for future HTML output.
- `validation/` contains the canonical ground truth and expected metrics.

The files in `files/` are Phase 0 placeholders. The JSON and JSONL sources already match the locked dataset, while the `.db`, `.db-wal`, and `.jpg` files stand in for later emulator-generated artifacts.

