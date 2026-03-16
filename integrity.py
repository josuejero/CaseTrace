"""Shared chain-of-custody helpers for manifest/log handling."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HASH_ALGORITHM = "sha256"
MANIFEST_FILENAME = "hash_manifest.json"
PROCESSING_LOG_FILENAME = "processing_log.json"
DEFAULT_EXAMINER_NAME = os.getenv("CASE_EXAMINER_NAME", "CaseTrace Lab Analyst")
CONTAINER_DIGEST_ENV = "CASE_CONTAINER_DIGEST"


def utc_timestamp(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path(case_dir: Path) -> Path:
    return case_dir / MANIFEST_FILENAME


def processing_log_path(case_dir: Path) -> Path:
    return case_dir / PROCESSING_LOG_FILENAME


def collect_file_entries(files_dir: Path, case_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(files_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(case_dir).as_posix()
        entries.append(
            {
                "path": rel,
                "sha256": sha256_digest(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return entries


def gather_file_summary(entries: Iterable[dict[str, Any]]) -> dict[str, int]:
    total_files = sum(1 for _ in entries)
    total_bytes = sum(entry.get("size_bytes", 0) for entry in entries)
    return {"file_count": total_files, "total_size_bytes": total_bytes}


def case_dir_from_db(db_path: Path) -> Path:
    candidate = db_path
    if db_path.name == "case.db" and db_path.parent.name == "parsed":
        candidate = db_path.parent.parent
    return candidate


def capture_git_commit() -> str:
    repo_root = Path(__file__).resolve().parent
    if not (repo_root / ".git").exists():
        return "(no git repo)"
    result = os.popen("git -C " + str(repo_root) + " rev-parse HEAD")
    commit = result.read().strip()
    result.close()
    return commit or "(git rev-parse failed)"


def _ensure_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_manifest(case_dir: Path) -> dict[str, Any]:
    path = manifest_path(case_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing")
    return _ensure_json(path)


def write_manifest(case_dir: Path, manifest: dict[str, Any]) -> None:
    path = manifest_path(case_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_processing_log(case_dir: Path) -> dict[str, Any]:
    path = processing_log_path(case_dir)
    if path.exists():
        return _ensure_json(path)
    return {"case_id": None, "generated_at": utc_timestamp(), "steps": []}


def write_processing_log(case_dir: Path, log: dict[str, Any]) -> None:
    path = processing_log_path(case_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(log, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def append_processing_step(
    case_dir: Path,
    case_id: str,
    stage: str,
    description: str,
    *,
    actor: str | None = None,
    details: Any | None = None,
    timestamp: str | None = None,
) -> None:
    log = load_processing_log(case_dir)
    log["case_id"] = case_id
    log.setdefault("steps", [])
    step: dict[str, Any] = {
        "stage": stage,
        "timestamp": timestamp or utc_timestamp(),
        "description": description,
    }
    if actor:
        step["actor"] = actor
    if details is not None:
        step["details"] = details
    log["steps"].append(step)
    log["generated_at"] = utc_timestamp()
    write_processing_log(case_dir, log)


def examiner_name() -> str:
    return DEFAULT_EXAMINER_NAME


def container_image_digest() -> str | None:
    return os.getenv(CONTAINER_DIGEST_ENV)
