"""Generate a simple HTML summary of WAL recovery findings."""
from __future__ import annotations

import argparse
import html
import sqlite3
from pathlib import Path
from typing import Iterable

from integrity import (
    append_processing_step,
    capture_git_commit,
    collect_file_entries,
    container_image_digest,
    examiner_name,
    gather_file_summary,
    load_manifest,
    sha256_digest,
    utc_timestamp,
    write_manifest,
)

FINDING_COLUMNS = [
    "record_id",
    "artifact_type",
    "finding_label",
    "confidence",
    "summary",
    "raw_ref",
    "database_file",
    "wal_file",
    "parser_method",
    "parser_version",
]


def _relative_to_or_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an HTML report of WAL recovery findings.")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=Path("cases/CT-2026-001"),
        help="Path to the case folder containing parsed artifacts.",
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=None,
        help="Directory where parsed outputs live (default: <case_dir>/parsed).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Direct path to case.db (overrides case-dir/parsed-dir).",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=None,
        help="Destination HTML file (default: <case_dir>/reports/recovery.html).",
    )
    args = parser.parse_args()

    db_path = args.db_path or (args.parsed_dir or args.case_dir / "parsed") / "case.db"
    case_dir = args.case_dir
    manifest = load_manifest(case_dir)
    entries = collect_file_entries(case_dir / "files", case_dir)
    summary = gather_file_summary(entries)
    manifest["files"] = entries
    environment = manifest.setdefault("environment", {})
    environment["git_commit"] = capture_git_commit()
    digest = container_image_digest()
    if digest:
        environment["container_image_digest"] = digest
    manifest["generated_at"] = utc_timestamp()
    write_manifest(case_dir, manifest)

    rows = _fetch_recovery_findings(db_path)
    output_path = args.output_html or case_dir / "reports" / "recovery.html"
    _write_html(output_path, rows)

    report_rel = _relative_to_or_str(output_path, case_dir)
    report_digest = sha256_digest(output_path)
    report_timestamp = utc_timestamp()
    manifest["report"] = {
        "generated_at": report_timestamp,
        "path": report_rel,
        "sha256": report_digest,
    }
    manifest["generated_at"] = report_timestamp
    write_manifest(case_dir, manifest)
    append_processing_step(
        case_dir,
        manifest["case_id"],
        stage="report_export",
        description="Exported WAL recovery findings and re-verified manifest hashes",
        actor=examiner_name(),
        details={
            "report_path": report_rel,
            "report_sha256": report_digest,
            "hash_summary": summary,
        },
    )


def _fetch_recovery_findings(db_path: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(db_path)
    try:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "SELECT * FROM recovery_findings ORDER BY finding_label, record_id"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


def _write_html(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Recovery Findings</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; }
    th { background: #f3f3f3; }
    tr:nth-child(odd) { background: #fafafa; }
    .summary { max-width: 320px; white-space: normal; }
  </style>
</head>
<body>
  <h1>WAL Recovery Findings</h1>
  <p>Use this report to understand what was observed, recovered, or inferred from WAL-backed state.</p>
  <table>\n"""
        )
        handle.write("    <thead>\n      <tr>\n")
        for col in FINDING_COLUMNS:
            handle.write(f"        <th>{html.escape(col)}</th>\n")
        handle.write("      </tr>\n    </thead>\n    <tbody>\n")
        for row in rows:
            handle.write("      <tr>\n")
            for col in FINDING_COLUMNS:
                value = row.get(col, "")
                escaped = html.escape(str(value)) if value is not None else ""
                handle.write(f"        <td class=\"{col}\">{escaped}</td>\n")
            handle.write("      </tr>\n")
        handle.write("    </tbody>\n  </table>\n</body>\n</html>\n")


if __name__ == "__main__":
    main()
