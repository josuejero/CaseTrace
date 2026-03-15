"""Helper utilities for CaseTrace parser modules."""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Iterable


def load_json(path: Path) -> object:
    """Load JSON from a file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_file(path: Path) -> Path:
    """Raise if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing")
    return path


def iter_jsonl(path: Path) -> Iterable[object]:
    """Yield JSON objects from a newline-delimited file."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)


def guess_mime_type(path: Path | str) -> str | None:
    """Return a MIME hint for a given filename."""
    mime, _ = mimetypes.guess_type(str(path))
    return mime
