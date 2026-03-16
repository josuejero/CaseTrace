"""Helpers for building the case search index rows."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import guess_mime_type
from .models import ParsedArtifact

SEARCH_COLUMNS = (
    "record_id",
    "artifact_type",
    "content_summary",
    "actor",
    "counterparty",
    "source_file",
    "url",
    "title",
    "metadata_text",
)


def artifact_search_row(artifact: ParsedArtifact) -> dict[str, str | None]:
    metadata_text = _serialize_metadata(artifact.metadata)
    metadata_text = metadata_text or artifact.record.content_summary
    metadata = artifact.metadata or {}
    url = metadata.get("url") or metadata.get("raw_url")
    title = metadata.get("title")
    return {
        "record_id": artifact.record.record_id,
        "artifact_type": artifact.record.artifact_type,
        "content_summary": artifact.record.content_summary,
        "actor": artifact.record.actor,
        "counterparty": artifact.record.counterparty,
        "source_file": artifact.record.source_file,
        "url": url,
        "title": title,
        "metadata_text": metadata_text,
    }


def file_search_rows(files: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for entry in files:
        path = entry.get("path")
        if not path:
            continue
        name = Path(path).name
        mime = guess_mime_type(path)
        metadata_parts = [f"sha256:{entry.get('sha256')}" if entry.get("sha256") else None]
        if entry.get("size_bytes"):
            metadata_parts.append(f"size:{entry['size_bytes']}")
        if mime:
            metadata_parts.append(f"mime:{mime}")
        metadata_text = " ".join(part for part in metadata_parts if part)
        metadata_text = metadata_text or name
        rows.append(
            {
                "record_id": path,
                "artifact_type": "evidence_file",
                "content_summary": f"Evidence file {name}",
                "actor": None,
                "counterparty": None,
                "source_file": path,
                "url": None,
                "title": None,
                "metadata_text": metadata_text,
            }
        )
    return rows


def _serialize_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""
    parts: list[str] = []
    for key in sorted(metadata):
        value = metadata[key]
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            value = ",".join(str(item) for item in value)
        parts.append(f"{key}:{value}")
    return " ".join(parts)
