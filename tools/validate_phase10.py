"""Phase 10 validation surface for CaseTrace."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from integrity import utc_timestamp

CASE_VALIDATION_DIR = "validation"
EXPECTED_METRICS_FILE = "expected_metrics.json"
DEFAULT_DATASET_FILE = "case_ct_2026_001_ground_truth.json"
ACQUISITION_ROOT = "/data/user/0/com.casetrace.waypoint/"


@dataclass
class ValidationCheck:
    name: str
    expected: int | None
    actual: int | None
    passed: bool
    note: str | None = None


@dataclass
class PhotoExifValidation:
    record_id: str
    source_file: str | None
    record_timestamp: str | None
    exif_timestamp: str | None
    passed: bool
    note: str | None = None


@dataclass
class ValidationSummary:
    case_id: str | None
    dataset_path: str | None
    generated_at: str
    checks: list[ValidationCheck]
    photo_checks: list[PhotoExifValidation]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks) and all(photo.passed for photo in self.photo_checks)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _bundle_path_from_source_file(case_dir: Path, source_file: str) -> Path | None:
    if not source_file.startswith(ACQUISITION_ROOT):
        return None
    relative = source_file.removeprefix(ACQUISITION_ROOT).lstrip("/")
    return case_dir / "files" / relative


def _normalize_exif_timestamp(value: str | bytes | None) -> str | None:
    if value is None:
        return None
    raw = value.decode("utf-8") if isinstance(value, bytes) else str(value)
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def _photo_rows(connection: sqlite3.Connection) -> list[tuple[str, str, str]]:
    cursor = connection.execute(
        "SELECT record_id, event_time_start, source_file FROM artifacts_media"
    )
    return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def _count_messages(connection: sqlite3.Connection) -> int:
    return connection.execute(
        "SELECT COUNT(*) FROM timeline_events WHERE artifact_type='message'"
    ).fetchone()[0]


def _count_locations(connection: sqlite3.Connection) -> int:
    return connection.execute(
        "SELECT COUNT(*) FROM timeline_events WHERE has_location=1"
    ).fetchone()[0]


def _count_recovered_rows(connection: sqlite3.Connection) -> int:
    return connection.execute(
        """SELECT COUNT(*) FROM recovery_findings
        WHERE finding_label IN ('recovered', 'inferred')"""
    ).fetchone()[0]


def _read_photo_exif(path: Path) -> str | None:
    if not path.exists():
        return None
    with Image.open(path) as image:
        exif = image.getexif()
        candidate = exif.get(36867) or exif.get(306)
        return _normalize_exif_timestamp(candidate)


def build_validation_summary(case_dir: Path, parsed_dir: Path | None = None) -> ValidationSummary:
    parsed_dir = parsed_dir or case_dir / "parsed"
    db_path = parsed_dir / "case.db"
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} does not exist")

    case_metadata = _load_json(case_dir / "case.json")
    metrics_path = case_dir / CASE_VALIDATION_DIR / EXPECTED_METRICS_FILE
    metrics = _load_json(metrics_path)
    dataset_file = metrics.get("dataset_file", f"{CASE_VALIDATION_DIR}/{DEFAULT_DATASET_FILE}")
    dataset_path = case_dir / dataset_file
    dataset = _load_json(dataset_path)
    expected_states = metrics.get("expected_artifact_counts", {})
    expected_message_count = expected_states.get("message")
    expected_deleted_count = metrics.get("expected_deleted_record_count", 0)
    expected_location_count = sum(1 for record in dataset.get("records", []) if record.get("location"))

    checks: list[ValidationCheck] = []
    photo_validations: list[PhotoExifValidation] = []

    with sqlite3.connect(db_path) as connection:
        actual_messages = _count_messages(connection)
        actual_locations = _count_locations(connection)
        actual_recovered = _count_recovered_rows(connection)
        photo_rows = _photo_rows(connection)

    checks.append(
        ValidationCheck(
            name="message count",
            expected=expected_message_count,
            actual=actual_messages,
            passed=expected_message_count == actual_messages,
        )
    )
    checks.append(
        ValidationCheck(
            name="recovered/deleted rows",
            expected=expected_deleted_count,
            actual=actual_recovered,
            passed=expected_deleted_count == actual_recovered,
        )
    )
    checks.append(
        ValidationCheck(
            name="timeline locations with GPS",
            expected=expected_location_count,
            actual=actual_locations,
            passed=expected_location_count == actual_locations,
        )
    )

    for record_id, record_timestamp, source_file in photo_rows:
        note = None
        source_path = _bundle_path_from_source_file(case_dir, source_file) if source_file else None
        exif_timestamp = None
        if source_path:
            exif_timestamp = _read_photo_exif(source_path)
            if exif_timestamp is None:
                note = "EXIF timestamp missing or malformed"
        else:
            note = "Unable to map source file to bundle path"

        passed = record_timestamp == exif_timestamp and exif_timestamp is not None
        photo_validations.append(
            PhotoExifValidation(
                record_id=record_id,
                source_file=source_file,
                record_timestamp=record_timestamp,
                exif_timestamp=exif_timestamp,
                passed=passed,
                note=note,
            )
        )

    summary = ValidationSummary(
        case_id=case_metadata.get("case_id"),
        dataset_path=dataset_path.relative_to(case_dir).as_posix() if dataset_path.exists() else None,
        generated_at=utc_timestamp(),
        checks=checks,
        photo_checks=photo_validations,
    )
    return summary


def render_markdown_report(summary: ValidationSummary, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 10 Validation Report",
        "",
        f"- Case: {summary.case_id or 'unknown'}",
        f"- Generated: {summary.generated_at}",
        f"- Validation dataset: {summary.dataset_path or 'unknown'}",
        "",
        "## Summary",
        "",
        "| Check | Expected | Actual | Status | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in summary.checks:
        status = "pass" if check.passed else "fail"
        note = check.note or ""
        expected = check.expected if check.expected is not None else "n/a"
        actual = check.actual if check.actual is not None else "n/a"
        lines.append(f"| {check.name} | {expected} | {actual} | {status} | {note} |")

    lines.append("")
    lines.append("## EXIF Validation")
    lines.append("")
    lines.append("| Photo | Record Time | EXIF Time | Source File | Status | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for photo in summary.photo_checks:
        status = "pass" if photo.passed else "fail"
        lines.append(
            "| "
            f"{photo.record_id} | {photo.record_timestamp or 'n/a'} | {photo.exif_timestamp or 'n/a'} | "
            f"{photo.source_file or 'n/a'} | {status} | {photo.note or ''} |"
        )

    lines.append("")
    lines.append("## Conclusion")
    overall = "pass" if summary.passed else "fail"
    lines.append(f"- Overall validation: **{overall}**")
    if not summary.passed:
        lines.append("- Inspect the details above and rerun `python tools/validate_phase10.py` after debugging.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 10 validation checks for CaseTrace.")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=Path("cases/CT-2026-001"),
        help="Case directory containing the parsed outputs and validation fixtures.",
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        help="Optional override for the parsed output directory.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Destination for the Markdown validation report (default: <case-dir>/reports/validation.md).",
    )
    args = parser.parse_args()

    report_path = args.report_path or (args.case_dir / "reports" / "validation.md")
    summary = build_validation_summary(args.case_dir, args.parsed_dir)
    render_markdown_report(summary, report_path)

    print("Phase 10 validation results:")
    for check in summary.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"- {check.name}: expected={check.expected} actual={check.actual} -> {status}")

    failed_photos = [photo for photo in summary.photo_checks if not photo.passed]
    if failed_photos:
        print(f"- Photo EXIF mismatches: {len(failed_photos)} record(s) failed")
        for photo in failed_photos:
            print(f"  - {photo.record_id}: file={photo.source_file} note={photo.note or 'mismatch'}")
    else:
        print(f"- Photo EXIF comparisons: {len(summary.photo_checks)} records OK")

    conclusion = "PASSED" if summary.passed else "FAILED"
    print(f"Overall Phase 10 validation: {conclusion}")

    if not summary.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
