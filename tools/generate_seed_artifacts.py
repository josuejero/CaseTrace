#!/usr/bin/env python3
"""Generate the CaseTrace seed artifacts from the Phase 0 fixtures."""
from __future__ import annotations

import argparse
from pathlib import Path

from tools.seed_artifacts.databases import create_core_database, create_web_database
from tools.seed_artifacts.exports import write_exports, write_logs
from tools.seed_artifacts.media import create_photos
from tools.seed_artifacts.manifest import update_manifest_and_log

DEFAULT_CASE_DIR = Path("cases/CT-2026-001")


def generate_seed_artifacts(case_dir: Path | str = DEFAULT_CASE_DIR) -> None:
    case_dir = Path(case_dir)
    create_photos(case_dir)
    create_core_database(case_dir)
    create_web_database(case_dir)
    write_exports(case_dir)
    write_logs(case_dir)
    update_manifest_and_log(case_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CaseTrace seed artifacts")
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE_DIR)
    args = parser.parse_args()
    generate_seed_artifacts(args.case_dir)


if __name__ == "__main__":
    main()
