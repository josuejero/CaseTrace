\"\"\"Utility creators for exports and log fixtures.\"\"\"
from __future__ import annotations

import json
from pathlib import Path

from tools.seed_artifacts.data import APP_EVENTS, JSON_INDENT, LOCATIONS


def write_exports(case_dir: Path) -> None:
    exports_dir = case_dir / "files" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_id": case_dir.name,
        "points": [
            {
                "timestamp_utc": timestamp,
                "label": label,
                "latitude": lat,
                "longitude": lon,
                "accuracy_m": acc,
            }
            for timestamp, lat, lon, acc, label in LOCATIONS
        ],
    }
    (exports_dir / "location_trace.json").write_text(json.dumps(payload, indent=JSON_INDENT))


def write_logs(case_dir: Path) -> None:
    logs_dir = case_dir / "files" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    target = logs_dir / "app-events-20260312.jsonl"
    with target.open("w", encoding="utf-8") as handle:
        for timestamp, event, summary in APP_EVENTS:
            handle.write(json.dumps({"timestamp_utc": timestamp, "event": event, "summary": summary}) + "\n")
