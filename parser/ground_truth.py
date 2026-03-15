"""Ground-truth helpers for matching dataset records."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .common import load_json


def _value_matches(candidate: Any, actual: Any) -> bool:
    if actual is None or candidate is None:
        return True
    return candidate == actual


class GroundTruthIndex:
    """Index that maps parsed artifacts to the frozen ground-truth records."""

    def __init__(self, case_dir: Path) -> None:
        dataset = load_json(case_dir / "validation" / "case_ct_2026_001_ground_truth.json")
        self._records: list[dict[str, Any]] = dataset["records"]
        self._available = {record["record_id"]: record for record in self._records}
        self._unmatched = set(self._available)

    def match_record(
        self,
        artifact_type: str,
        event_time_start: str,
        actor: str | None,
        counterparty: str | None,
        **context: Any,
    ) -> dict[str, Any] | None:
        """Return and reserve a matching ground-truth record."""
        for candidate in self._records:
            record_id = candidate["record_id"]
            if record_id not in self._unmatched:
                continue
            if candidate["artifact_type"] != artifact_type:
                continue
            if candidate["event_time_start"] != event_time_start:
                continue
            if not _value_matches(candidate.get("actor"), actor):
                continue
            if not _value_matches(candidate.get("counterparty"), counterparty):
                continue
            if label := context.get("location_label"):
                location = candidate.get("location")
                if not location or location.get("label") != label:
                    continue
            if summary := context.get("content_summary"):
                if candidate.get("content_summary") != summary:
                    continue
            if file_name := context.get("file_name"):
                source = candidate.get("source_file", "")
                if not source.endswith(f"/{file_name}"):
                    continue
            if url := context.get("url"):
                if url not in candidate.get("content_summary", "") and url not in candidate.get("raw_ref", ""):
                    continue
            self._unmatched.remove(record_id)
            return candidate
        return None

    def remaining_records(self) -> Iterable[dict[str, Any]]:
        """Return ground-truth records that were not matched yet."""
        for record_id in sorted(self._unmatched):
            yield self._available[record_id]

    def ordered_records(self) -> list[dict[str, Any]]:
        """Return the ground-truth records in canonical order."""
        return list(self._records)
