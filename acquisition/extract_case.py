#!/usr/bin/env python3
"""Repeatable emulator acquisition for CaseTrace Phase 2."""
from __future__ import annotations

import argparse
import json
import logging
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import List

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


def load_case_metadata(case_dir: Path) -> dict:
    case_json = case_dir / "case.json"
    if not case_json.exists():
        raise FileNotFoundError(f"case.json missing in {case_dir}")
    with case_json.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_adb_available() -> Path:
    adb = shutil.which("adb")
    if not adb:
        raise FileNotFoundError("'adb' executable not found on PATH; install Android platform tools")
    return Path(adb)


def run_adb_command(serial: str, *args: str, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["adb", "-s", serial]
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=capture_output, text=True)


def verify_device(serial: str) -> None:
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"adb devices failed: {result.stderr.strip()}")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        raise RuntimeError("no devices attached to adb")
    connected: list[str] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        serial_id, status = parts[0], parts[1]
        if status == "device":
            connected.append(serial_id)
    if serial not in connected:
        raise RuntimeError(f"target serial {serial} not connected; available: {connected}")


def verify_package(serial: str, package: str) -> None:
    result = run_adb_command(serial, "shell", "pm", "list", "packages", package)
    if result.returncode != 0:
        raise RuntimeError(f"pm list packages failed: {result.stderr.strip()}")
    if f"package:{package}" not in result.stdout:
        raise RuntimeError(f"package {package} not installed on device {serial}")


def get_emulator_property(serial: str, prop: str) -> str:
    result = run_adb_command(serial, "shell", "getprop", prop)
    if result.returncode != 0:
        raise RuntimeError(f"getprop {prop} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_app_version(serial: str, package: str) -> str:
    result = run_adb_command(serial, "shell", "dumpsys", "package", package)
    if result.returncode != 0:
        raise RuntimeError(f"dumpsys package failed: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if "versionName=" in line:
            return line.split("versionName=", 1)[1].strip()
    return "unknown"


def capture_git_commit() -> str:
    if not (PROJECT_ROOT / ".git").exists():
        return "(no git repo)"
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse failed: {result.stderr.strip()}")
    return result.stdout.strip()


def clean_files_directory(files_dir: Path) -> None:
    files_dir.mkdir(parents=True, exist_ok=True)
    for child in list(files_dir.iterdir()):
        if child.name == "README.md":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for name in ("databases", "exports", "logs", "media"):
        (files_dir / name).mkdir(parents=True, exist_ok=True)


def stream_tarball(serial: str, package: str, dest_tar: Path, actions: List[dict]) -> None:
    dest_tar.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["adb", "-s", serial, "exec-out", "run-as", package, "tar", "-cf", "-", "."]
    logger.info("Streaming tarball from emulator into %s", dest_tar)
    with dest_tar.open("wb") as handle:
        process = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        if process.returncode != 0:
            error = stderr.decode().strip() if stderr else ""
            raise RuntimeError(f"adb exec-out tar failed: {error}")
    actions.append({"timestamp": utc_timestamp(), "description": "Pulled app files via run-as tar"})


def extract_tarball(tar_path: Path, target_dir: Path) -> None:
    logger.info("Extracting tarball %s -> %s", tar_path, target_dir)
    with tarfile.open(tar_path, "r:") as tar:
        tar.extractall(path=target_dir)


def relative_to_or_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def create_evidence_bundle(bundle_path: Path, case_dir: Path) -> None:
    logger.info("Creating evidence bundle %s", bundle_path)
    entries = [
        case_dir / "case.json",
        case_dir / "files",
        case_dir / "hash_manifest.json",
        case_dir / "processing_log.json",
        case_dir / "parsed",
        case_dir / "reports",
        case_dir / "validation",
    ]
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for entry in entries:
            if not entry.exists():
                continue
            if entry.is_file():
                rel = entry.relative_to(case_dir).as_posix()
                zf.write(entry, rel)
                continue
            for sub in sorted(entry.rglob("*")):
                arcname = sub.relative_to(case_dir).as_posix()
                if sub.is_dir():
                    if any(True for _ in sub.iterdir()):
                        continue
                    zf.writestr(arcname + "/", "")
                else:
                    zf.write(sub, arcname)



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
    actions: List[dict] = []
    actions.append({"timestamp": utc_timestamp(), "description": "Starting acquisition"})

    verify_device(serial)
    actions.append({"timestamp": utc_timestamp(), "description": f"Verified device {serial} is online"})

    verify_package(serial, package)
    actions.append({"timestamp": utc_timestamp(), "description": f"Confirmed package {package} is installed"})

    emulator_name = get_emulator_property(serial, "ro.product.model") or "unknown"
    android_release = get_emulator_property(serial, "ro.build.version.release") or "unknown"
    android_sdk = get_emulator_property(serial, "ro.build.version.sdk") or ""
    android_version = f"{android_release} (API {android_sdk})" if android_sdk else android_release
    app_version = get_app_version(serial, package)
    host_os = platform.platform()
    git_commit = capture_git_commit()

    actions.append({"timestamp": utc_timestamp(), "description": "Captured emulator and app metadata"})

    files_dir = case_dir / "files"
    readme_path = files_dir / "README.md"
    readme_bytes: bytes | None = readme_path.read_bytes() if readme_path.exists() else None
    clean_files_directory(files_dir)
    actions.append({"timestamp": utc_timestamp(), "description": "Recreated files directory"})

    staging_dir = Path(tempfile.mkdtemp(prefix=f"casetrace-acq-{case_id}-"))
    try:
        tar_path = staging_dir / "app.tar"
        stream_tarball(serial, package, tar_path, actions)
        extract_tarball(tar_path, files_dir)
        if readme_bytes is not None:
            readme_path.write_bytes(readme_bytes)
        actions.append({"timestamp": utc_timestamp(), "description": "Copied files into case bundle"})
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
    actions.append({"timestamp": utc_timestamp(), "description": "Wrote hash_manifest.json"})

    bundle_path = bundle_path.resolve()
    create_evidence_bundle(bundle_path, case_dir)
    actions.append({"timestamp": utc_timestamp(), "description": "Created zipped evidence bundle"})
    manifest_path = case_dir / "hash_manifest.json"
    log_data = {
        "case_id": case_id,
        "acquired_at": utc_timestamp(),
        "target_package": package,
        "emulator": {
            "serial": serial,
            "name": emulator_name,
            "android_version": android_version,
        },
        "app": {
            "version": app_version,
        },
        "environment": {
            "host_os": host_os,
            "git_commit": git_commit,
        },
        "files": {
            "path": (files_dir.relative_to(case_dir)).as_posix(),
            "summary": summary,
        },
        "manifest_path": relative_to_or_str(manifest_path, case_dir),
        "bundle_path": relative_to_or_str(bundle_path, case_dir),
        "actions": actions,
    }
    log_path = case_dir / "acquisition_log.json"
    write_json(log_path, log_data)
    logger.info("Acquisition log written to %s", log_path)
    logger.info("Acquisition complete for %s", case_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - main runner
        logger.error("Acquisition failed: %s", exc)
        sys.exit(1)
