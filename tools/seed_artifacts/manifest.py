"""Manifest and logging helpers for the seed artifact generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from integrity import (
    HASH_ALGORITHM,
    append_processing_step,
    capture_git_commit,
    collect_file_entries,
    container_image_digest,
    examiner_name,
    gather_file_summary,
    sha256_digest,
    utc_timestamp,
    write_manifest,
    write_processing_log,
)
from parser.common import load_json
from parser.models import PARSER_VERSION

ACQUISITION_SCRIPT_VERSION = "phase2-acquisition/1.0.0"


def _relative_to_or_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def update_manifest_and_log(case_dir: Path, report_file: Path | None = None) -> None:
    case_metadata = load_json(case_dir / "case.json")
    case_id = case_metadata["case_id"]
    files_dir = case_dir / "files"
    entries = collect_file_entries(files_dir, case_dir)
    summary = gather_file_summary(entries)
    environment: dict[str, Any] = {"git_commit": capture_git_commit()}
    digest = container_image_digest()
    if digest:
        environment["container_image_digest"] = digest
    manifest = {
        "case_id": case_id,
        "algorithm": HASH_ALGORITHM,
        "generated_at": utc_timestamp(),
        "acquisition": {
            "acquired_at": case_metadata["acquisition"]["acquired_at"],
            "operator": examiner_name(),
            "script_version": ACQUISITION_SCRIPT_VERSION,
            "device": case_metadata["device"],
            "method": case_metadata["acquisition"]["method"],
        },
        "app": {
            "package": case_metadata["seed_app"]["package_name"],
            "label": case_metadata["seed_app"]["label"],
            "version": case_metadata["seed_app"]["version"],
        },
        "environment": environment,
        "parser_version": PARSER_VERSION,
        "files": entries,
    }
    report_file = report_file or case_dir / "reports" / "recovery.html"
    report_rel = _relative_to_or_str(report_file, case_dir)
    report_timestamp = utc_timestamp()
    report_digest = sha256_digest(report_file) if report_file.exists() else None
    manifest["report"] = {
        "generated_at": report_timestamp,
        "path": report_rel,
        "sha256": report_digest,
    }
    manifest["generated_at"] = report_timestamp
    write_manifest(case_dir, manifest)
    write_processing_log(case_dir, {"case_id": case_id, "generated_at": utc_timestamp(), "steps": []})
    append_processing_step(
        case_dir,
        case_id,
        stage="acquisition",
        description="Seed files crafted in tools/generate_seed_artifacts",
        actor=examiner_name(),
        details={
            "script_version": ACQUISITION_SCRIPT_VERSION,
            "hash_summary": summary,
        },
    )
    append_processing_step(
        case_dir,
        case_id,
        stage="analysis",
        description="Normalized artifact fixtures produced",
        actor=examiner_name(),
        details={
            "parser_version": PARSER_VERSION,
            "hash_summary": summary,
        },
    )
    append_processing_step(
        case_dir,
        case_id,
        stage="report_export",
        description="Logged WAL recovery report sample",
        actor=examiner_name(),
        details={
            "report_path": report_rel,
            "report_sha256": report_digest,
            "hash_summary": summary,
        },
    )
