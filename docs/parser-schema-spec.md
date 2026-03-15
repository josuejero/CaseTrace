# Parser Schema Spec

Phase 0 fixes a single normalized record model named `ArtifactRecord`. Every parser, database table, search index, graph node builder, UI component, and report section must consume this schema without adding alternate taxonomies.

## Fixed Case Profile

- Case ID: `CT-2026-001`
- Subject: `Jordan Vega`
- Package: `com.casetrace.waypoint`
- Device: `pixel7-api34-emulator`
- ADB serial: `emulator-5554`
- Acquisition path: `/data/user/0/com.casetrace.waypoint/`
- Timezone: `America/New_York`
- Formal report format: `HTML`
- Validation dataset: `case_ct_2026_001_ground_truth.json`
- Locked taxonomy: `message`, `call`, `browser_visit`, `location_point`, `photo`, `app_event`, `recovered_record`
- Locked normalized record total: `42`

## Canonical ArtifactRecord

The JSON Schema lives at [`schemas/artifact-record.schema.json`](/Users/wholesway/Documents/Internship-Projects/Wingcraft/CaseTrace/schemas/artifact-record.schema.json).

| Field | Type | Rules |
| --- | --- | --- |
| `artifact_type` | string | One of `message`, `call`, `browser_visit`, `location_point`, `photo`, `app_event`, `recovered_record` |
| `source_file` | string | Absolute acquired-app path under `/data/user/0/com.casetrace.waypoint/` |
| `record_id` | string | Stable per-record identifier in the ground-truth dataset |
| `event_time_start` | string | RFC3339 UTC timestamp, `Z` suffix required |
| `event_time_end` | string | RFC3339 UTC timestamp, `Z` suffix required |
| `actor` | string or null | Canonical event actor |
| `counterparty` | string or null | Canonical contact, participant, or counterpart |
| `location` | object or null | `latitude`, `longitude`, `accuracy_m`, and `label` when location is present |
| `content_summary` | string | Short human-readable summary of the normalized event |
| `raw_ref` | string | URI-like locator back to raw evidence, such as `db://...#rowid=...` or `file://...#jsonpath=...` |
| `deleted_flag` | boolean | `true` only for deleted or recovered evidence |
| `confidence` | number | Numeric confidence score in the range `[0.0, 1.0]` |
| `parser_version` | string | Parser or schema build identifier |

## Taxonomy Rules

- `ArtifactRecord` is the only approved normalized row type for Phase 0.
- `artifact_type` is a locked enum. Adding or renaming classes requires schema and validation updates.
- Instantaneous events still populate `event_time_end`; for point-in-time events it equals `event_time_start`.
- `actor` and `counterparty` are normalized display strings, not free-form raw data dumps.

## Traceability Rules

- `raw_ref` is mandatory for every record.
- `raw_ref` must point to evidence inside the case bundle using `db://` or `file://` locators.
- `source_file` identifies the acquired source path; `raw_ref` identifies the precise table row, file line, or JSON path inside the bundle.
- Reports and parser claims must resolve back to `raw_ref`.

## Deleted and Recovered Records

- `recovered_record` is the only artifact class used for recovered deleted content in Phase 0.
- Recovered records must set `deleted_flag` to `true`.
- Recovered records must trace back to seeded SQLite WAL content.
- Recovered records carry reduced confidence relative to intact artifacts.

## Companion Bundle Contracts

The bundle metadata contracts live in:

- [`schemas/case-metadata.schema.json`](/Users/wholesway/Documents/Internship-Projects/Wingcraft/CaseTrace/schemas/case-metadata.schema.json)
- [`schemas/hash-manifest.schema.json`](/Users/wholesway/Documents/Internship-Projects/Wingcraft/CaseTrace/schemas/hash-manifest.schema.json)
- [`schemas/expected-metrics.schema.json`](/Users/wholesway/Documents/Internship-Projects/Wingcraft/CaseTrace/schemas/expected-metrics.schema.json)
- [`schemas/ground-truth-dataset.schema.json`](/Users/wholesway/Documents/Internship-Projects/Wingcraft/CaseTrace/schemas/ground-truth-dataset.schema.json)

These contracts define:

- `case.json` for case identity, device, package, timezone, acquisition path, acquisition method, report target, and validation dataset
- `hash_manifest.json` for SHA-256 coverage of every raw file
- `validation/expected_metrics.json` for record totals, per-class counts, deleted-record totals, and correlation thresholds
- `validation/case_ct_2026_001_ground_truth.json` for the canonical normalized records and cross-artifact correlations

## Ground-Truth Dataset Requirements

- Total normalized records: 42
- Required class counts:
  - 8 `message`
  - 4 `call`
  - 6 `browser_visit`
  - 10 `location_point`
  - 4 `photo`
  - 8 `app_event`
  - 2 `recovered_record`
- Minimum cross-artifact correlations: 12
- Every record must map to an existing raw source file in the case bundle
