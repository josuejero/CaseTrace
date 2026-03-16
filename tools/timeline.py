"""Timeline exploration helpers for CaseTrace cases."""
from __future__ import annotations

import argparse
import csv
import html
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

TIMELINE_COLUMNS = [
    "record_id",
    "artifact_type",
    "event_type",
    "event_type_rank",
    "event_time_start",
    "event_time_end",
    "event_time_local",
    "timezone",
    "actor",
    "target",
    "source_file",
    "raw_ref",
    "content_preview",
    "deleted_flag",
    "confidence",
    "has_location",
    "location_label",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect CaseTrace timeline events")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=Path("cases/CT-2026-001"),
        help="Case directory containing the parsed output",
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=None,
        help="Directory where parsed artifacts live (default: <case_dir>/parsed)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Direct path to case.db (overrides case-dir/parsed-dir)",
    )
    parser.add_argument("--deleted-only", action="store_true", help="Show only deleted events")
    parser.add_argument("--location-only", action="store_true", help="Show only events with location data")
    parser.add_argument(
        "--contact",
        type=str,
        default=None,
        help="Filter events involving the provided contact (actor or target)",
    )
    parser.add_argument(
        "--anchor",
        type=str,
        default=None,
        help="Record ID to center the window on",
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=10,
        help="Minutes before and after the anchor to include",
    )
    parser.add_argument("--output-csv", type=Path, default=None, help="Export a CSV report")
    parser.add_argument("--output-html", type=Path, default=None, help="Export an HTML report")
    args = parser.parse_args()

    db_path = args.db_path or (args.parsed_dir or args.case_dir / "parsed") / "case.db"
    rows = _fetch_timeline_rows(db_path)
    filtered = _apply_filters(rows, args)

    if args.output_csv:
        _write_csv(args.output_csv, filtered)
    if args.output_html:
        _write_html(args.output_html, filtered)
    if not args.output_csv and not args.output_html:
        _print_summary(filtered)


def _fetch_timeline_rows(db_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "SELECT * FROM timeline_events ORDER BY event_time_start, event_type_rank"
        )
        return [dict(row) for row in cursor]


def _apply_filters(rows: Iterable[dict[str, object]], args: argparse.Namespace) -> list[dict[str, object]]:
    all_rows = list(rows)
    filtered = all_rows
    if args.deleted_only:
        filtered = [row for row in filtered if row.get("deleted_flag")]
    if args.location_only:
        filtered = [row for row in filtered if row.get("has_location")]
    if args.contact:
        needle = args.contact.lower()
        filtered = [
            row
            for row in filtered
            if (row.get("actor") and needle in row["actor"].lower())
            or (row.get("target") and needle in row["target"].lower())
        ]
    if args.anchor:
        anchor_row = next((row for row in all_rows if row.get("record_id") == args.anchor), None)
        if not anchor_row:
            raise SystemExit(f"Anchor record {args.anchor} not found in timeline")
        anchor_dt = _parse_iso8601(anchor_row["event_time_start"])
        window = timedelta(minutes=max(args.window_minutes, 0))
        start_dt = anchor_dt - window
        end_dt = anchor_dt + window
        filtered = [
            row
            for row in filtered
            if start_dt <= _parse_iso8601(row["event_time_start"]) <= end_dt
        ]
    return filtered


def _parse_iso8601(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMELINE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_html(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>CaseTrace Timeline</title>
  <style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ccc;padding:4px;text-align:left;}th{background:#f0f0f0;}</style>
</head>
<body>
  <h1>Timeline events</h1>
  <table>
    <thead>
      <tr>\n"""
        + "".join(f"        <th>{html.escape(col)}</th>\n" for col in TIMELINE_COLUMNS)
        + "      </tr>\n    </thead>\n    <tbody>\n"
        )
        for row in rows:
            handle.write("      <tr>" + "".join(
                f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in TIMELINE_COLUMNS
            ) + "</tr>\n")
        handle.write("    </tbody>\n  </table>\n</body>\n</html>\n")


def _print_summary(rows: list[dict[str, object]]) -> None:
    if not rows:
        print("No timeline events match the requested filters.")
        return
    print(f"Timeline events ({len(rows)} rows):")
    for row in rows[:20]:
        actor = row.get("actor") or "-"
        target = row.get("target") or "-"
        deleted = bool(row.get("deleted_flag"))
        print(
            f"- {row['record_id']}: {row['event_time_start']} {row['event_type']} actor={actor} target={target} deleted={deleted}"
        )
    if len(rows) > 20:
        print(f"...and {len(rows) - 20} more rows")


if __name__ == "__main__":
    main()
