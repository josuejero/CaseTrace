\"\"\"Evidence acquisition helpers for copying files from the emulator.\"\"\"
from __future__ import annotations

import logging
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import List

from integrity import utc_timestamp

logger = logging.getLogger(__name__)


def stream_tarball(serial: str, package: str, dest_tar: Path, actions: List[dict[str, str]]) -> None:
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
