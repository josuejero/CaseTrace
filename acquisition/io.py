\"\"\"File-system helpers for the acquisition workflow.\"\"\"
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def load_case_metadata(case_dir: Path) -> dict[str, Any]:
    case_json = case_dir / "case.json"
    if not case_json.exists():
        raise FileNotFoundError(f"case.json missing in {case_dir}")
    with case_json.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\\n")


def relative_to_or_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)
