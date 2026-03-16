"""Logging helpers for acquisition actions and artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from integrity import utc_timestamp

from .io import relative_to_or_str, write_json


def log_action(actions: list[dict[str, str]], description: str) -> None:
    actions.append({"timestamp": utc_timestamp(), "description": description})


def build_acquisition_log(
    case_id: str,
    serial: str,
    package: str,
    emulator_name: str,
    android_version: str,
    app_version: str,
    host_os: str,
    git_commit: str,
    case_dir: Path,
    files_dir: Path,
    summary: dict[str, Any],
    manifest_path: Path,
    bundle_path: Path,
    actions: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "acquired_at": utc_timestamp(),
        "target_package": package,
        "emulator": {
            "serial": serial,
            "name": emulator_name,
            "android_version": android_version,
        },
        "app": {"version": app_version},
        "environment": {"host_os": host_os, "git_commit": git_commit},
        "files": {
            "path": relative_to_or_str(files_dir, case_dir),
            "summary": summary,
        },
        "manifest_path": relative_to_or_str(manifest_path, case_dir),
        "bundle_path": relative_to_or_str(bundle_path, case_dir),
        "actions": actions,
    }


def write_acquisition_log(log_path: Path, log_data: dict[str, Any]) -> None:
    write_json(log_path, log_data)
