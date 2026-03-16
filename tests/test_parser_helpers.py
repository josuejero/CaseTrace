"""Unit tests for parser helpers and ground-truth utilities."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from parser.common import ensure_file, guess_mime_type, iter_jsonl
from parser.ground_truth import GroundTruthIndex
from parser.models import ArtifactRecordModel, ParsedArtifact
from parser.search_index import artifact_search_row, file_search_rows
from parser.sqlite_utils import rows_from_cursor, sqlite_readonly_connection

CASE_DIR = Path("cases/CT-2026-001")


class ParserCommonTest(unittest.TestCase):
    def test_ensure_file_rejects_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "not_found.txt"
            with self.assertRaises(FileNotFoundError):
                ensure_file(missing)

    def test_iter_jsonl_ignores_blank_lines(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as handle:
            handle.write("{\"event\": \"first\"}\n")
            handle.write("\n")
            handle.write("  \n")
            handle.write("{\"event\": \"second\"}\n")
            temp_path = Path(handle.name)
        try:
            entries = list(iter_jsonl(temp_path))
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["event"], "first")
            self.assertEqual(entries[1]["event"], "second")
        finally:
            temp_path.unlink()

    def test_guess_mime_type_detects_known_extensions(self) -> None:
        mime = guess_mime_type("trace-report.html")
        self.assertEqual(mime, "text/html")


def _build_record(artifact_type: str, metadata: dict[str, object] | None = None) -> ParsedArtifact:
    record = ArtifactRecordModel(
        artifact_type=artifact_type,
        source_file="/tmp/source",
        record_id="test-001",
        event_time_start="2026-03-12T00:00:00Z",
        event_time_end="2026-03-12T00:00:00Z",
        actor="Tester",
        counterparty="Receiver",
        location=None,
        content_summary="summary",
        raw_ref="raw://reference",
        deleted_flag=False,
        confidence=0.5,
        parser_version="phase0-spec/1.0.0",
    )
    return ParsedArtifact(record=record, metadata=metadata or {})


class SearchIndexTest(unittest.TestCase):
    def test_artifact_row_serializes_metadata_sorted(self) -> None:
        metadata = {
            "b": "beta",
            "url": "https://example.test/detail",
            "a": "alpha",
            "ratings": [1, 2],
        }
        artifact = _build_record("message", metadata=metadata)
        row = artifact_search_row(artifact)
        self.assertEqual(row["record_id"], "test-001")
        self.assertIn("a:alpha", row["metadata_text"])
        self.assertIn("b:beta", row["metadata_text"])
        self.assertIn("ratings:1,2", row["metadata_text"])
        # url should appear in metadata_text as well as separate field
        self.assertIn("url:https://example.test/detail", row["metadata_text"])
        self.assertEqual(row["url"], metadata["url"])

    def test_artifact_row_falls_back_to_content_summary(self) -> None:
        artifact = _build_record("call", metadata={})
        row = artifact_search_row(artifact)
        self.assertEqual(row["metadata_text"], "summary")

    def test_file_rows_include_sha_size_and_mime(self) -> None:
        entry = {
            "path": "cases/CT-2026-001/reports/phase9-investigator-report.html",
            "sha256": "deadbeef",
            "size_bytes": 123,
        }
        rows = file_search_rows([entry, {"path": "", "sha256": "ignored"}])
        self.assertEqual(len(rows), 1)
        metadata = rows[0]["metadata_text"]
        self.assertIn("sha256:deadbeef", metadata)
        self.assertIn("size:123", metadata)
        self.assertIn("mime:text/html", metadata)
        self.assertEqual(rows[0]["artifact_type"], "evidence_file")


class GroundTruthIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = GroundTruthIndex(CASE_DIR)

    def _find_record(self, artifact_type: str) -> dict[str, object]:
        dataset = (CASE_DIR / "validation" / "case_ct_2026_001_ground_truth.json").read_text()
        entries = json.loads(dataset)["records"]
        for item in entries:
            if item["artifact_type"] == artifact_type:
                return item
        raise AssertionError(f"no {artifact_type} record found")

    def test_match_reserves_records(self) -> None:
        message = self._find_record("message")
        matched = self.index.match_record(
            message["artifact_type"],
            message["event_time_start"],
            message.get("actor"),
            message.get("counterparty"),
            content_summary=message.get("content_summary"),
            file_name=Path(message.get("source_file", "")).name,
            url=message.get("raw_ref"),
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched["record_id"], message["record_id"])
        remaining = list(self.index.remaining_records())
        self.assertNotIn(message["record_id"], [record["record_id"] for record in remaining])

    def test_match_respects_location_label_and_none_counterparty(self) -> None:
        location = self._find_record("location_point")
        matched = self.index.match_record(
            location["artifact_type"],
            location["event_time_start"],
            location.get("actor"),
            location.get("counterparty"),
            location_label=location.get("location", {}).get("label"),
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched["record_id"], location["record_id"])
        # attempt to match again should return None
        self.assertIsNone(
            self.index.match_record(
                location["artifact_type"],
                location["event_time_start"],
                location.get("actor"),
                location.get("counterparty"),
                location_label=location.get("location", {}).get("label"),
            )
        )

    def test_remaining_records_decrements(self) -> None:
        total = 42
        _ = self.index.match_record("message", "2026-03-12T12:10:00Z", "Mira Chen", "Jordan Vega")
        remaining = list(self.index.remaining_records())
        self.assertEqual(len(remaining), total - 1)


class SqliteUtilsTest(unittest.TestCase):
    def test_readonly_connection_and_rows_from_cursor(self) -> None:
        db_path = CASE_DIR / "files" / "databases" / "waypoint_core.db"
        with sqlite_readonly_connection(db_path) as connection:
            cursor = connection.execute("SELECT COUNT(*) AS cnt FROM messages")
            rows = rows_from_cursor(cursor)
            self.assertEqual(rows[0]["cnt"], 8)
            cursor = connection.execute("SELECT id, sender FROM messages ORDER BY id LIMIT 1")
            row_entries = rows_from_cursor(cursor)
            self.assertGreaterEqual(row_entries[0]["id"], 1)
            self.assertIsInstance(row_entries[0]["sender"], str)
