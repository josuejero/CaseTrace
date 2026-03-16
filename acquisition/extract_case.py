#!/usr/bin/env python3
\"\"\"Repeatable emulator acquisition for CaseTrace Phase 2.\"\"\"
from __future__ import annotations

import argparse
import logging
import platform
import shutil
import sys
import tempfile
from pathlib import Path

from acquisition.adb import (
    ensure_adb_available,
    get_app_version,
    get_emulator_property,
    verify_device,
    verify_package,
)
from acquisition.evidence import create_evidence_bundle, extract_tarball, stream_tarball
from acquisition.io import clean_files_directory, load_case_metadata
from acquisition.logging import (
    build_acquisition_log,
    log_action,
    write_acquisition_log,
)
from integrity import (
    HASH_ALGORITHM,
    append_processing_step,
    capture_git_commit,
    collect_file_entries,
    container_image_digest,
    examiner_name,
    gather_file_summary,
    utc_timestamp,
    write_manifest,
)

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
DEFAULT_CASE_DIR = PROJECT_ROOT / "cases" / "CT-2026-001"
DEFAULT_CASE_ID = "CT-2026-001"
ACQUISITION_SCRIPT_VERSION = "phase2-acquisition/1.0.0"

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Acquire CaseTrace app data from an emulator via adb")
    parser.add_argument("--serial", help="ADB device serial", default=None)
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE_DIR)
    parser.add_argument("--bundle-path", type=Path, default=None)
    args = parser.parse_args()

    case_dir = args.case_dir.resolve()
    case_metadata = load_case_metadata(case_dir)
    case_id = case_metadata.get("case_id", DEFAULT_CASE_ID)
    package = case_metadata["seed_app"]["package_name"]
    serial = args.serial or case_metadata["device"]["adb_serial"]
    bundle_path = args.bundle_path or case_dir / f"{case_id}-evidence-bundle.zip"

    ensure_adb_available()
    actions: list[dict[str, str]] = []
    log_action(actions, "Starting acquisition")

    verify_device(serial)
    log_action(actions, f"Verified device {serial} is online")

    verify_package(serial, package)
    log_action(actions, f"Confirmed package {package} is installed")

    emulator_name = get_emulator_property(serial, "ro.product.model") or "unknown"
    android_release = get_emulator_property(serial, "ro.build.version.release") or "unknown"
    android_sdk = get_emulator_property(serial, "ro.build.version.sdk") or ""
    android_version = f"{android_release} (API {android_sdk})" if android_sdk else android_release
    app_version = get_app_version(serial, package)
    host_os = platform.platform()
    git_commit = capture_git_commit()
    log_action(actions, "Captured emulator and app metadata")

    files_dir = case_dir / "files"
    readme_path = files_dir / "README.md"
    readme_bytes: bytes | None = readme_path.read_bytes() if readme_path.exists() else None
    clean_files_directory(files_dir)
    log_action(actions, "Recreated files directory")

    staging_dir = Path(tempfile.mkdtemp(prefix=f"casetrace-acq-{case_id}-"))
    try:
        tar_path = staging_dir / "app.tar"
        stream_tarball(serial, package, tar_path, actions)
        extract_tarball(tar_path, files_dir)
        if readme_bytes is not None:
            readme_path.write_bytes(readme_bytes)
        log_action(actions, "Copied files into case bundle")
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    entries = collect_file_entries(files_dir, case_dir)
    summary = gather_file_summary(entries)
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
        "environment": {
            "git_commit": git_commit,
            "container_image_digest": container_image_digest(),
        },
        "parser_version": "",
        "report": {},
        "files": entries,
    }
    write_manifest(case_dir, manifest)
    append_processing_step(
        case_dir,
        case_id,
        stage="acquisition",
        description="Captured emulator files and recorded hashes",
        actor=examiner_name(),
        details={
            "script_version": ACQUISITION_SCRIPT_VERSION,
            "host_os": host_os,
            "hash_summary": summary,
            "actions": [action["description"] for action in actions],
        },
    )
    log_action(actions, "Wrote hash_manifest.json")

    bundle_path = bundle_path.resolve()
    create_evidence_bundle(bundle_path, case_dir)
    log_action(actions, "Created zipped evidence bundle")

    manifest_path = case_dir / "hash_manifest.json"
    log_data = build_acquisition_log(
        case_id=case_id,
        serial=serial,
        package=package,
        emulator_name=emulator_name,
        android_version=android_version,
        app_version=app_version,
        host_os=host_os,
        git_commit=git_commit,
        case_dir=case_dir,
        files_dir=files_dir,
        summary=summary,
        manifest_path=manifest_path,
        bundle_path=bundle_path,
        actions=actions,
    )
    log_path = case_dir / "acquisition_log.json"
    write_acquisition_log(log_path, log_data)
    logger.info("Acquisition log written to %s", log_path)
    logger.info("Acquisition complete for %s", case_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - main runner
        logger.error("Acquisition failed: %s", exc)
        sys.exit(1)
