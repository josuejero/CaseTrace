"""Unit tests covering the parser modules."""
from __future__ import annotations

import unittest
from pathlib import Path

from parser.parse_app_events import parse_app_events
from parser.parse_browser import parse_browser
from parser.parse_calls import parse_calls
from parser.parse_deleted_sqlite import parse_deleted_sqlite
from parser.parse_locations import parse_locations
from parser.parse_messages import parse_messages
from parser.parse_photos import parse_photos


CASE_DIR = Path("cases/CT-2026-001")


class ParserModuleTest(unittest.TestCase):
    def test_parse_messages_returns_records(self) -> None:
        records = parse_messages(CASE_DIR)
        self.assertTrue(records)
        self.assertEqual(records[0].record.artifact_type, "message")

    def test_parse_calls_count(self) -> None:
        records = parse_calls(CASE_DIR)
        self.assertEqual(records[0].record.artifact_type, "call")

    def test_parse_browser_visits(self) -> None:
        records = parse_browser(CASE_DIR)
        self.assertTrue(records)
        self.assertEqual(records[0].record.artifact_type, "browser_visit")

    def test_parse_locations_produces_points(self) -> None:
        records = parse_locations(CASE_DIR)
        self.assertEqual(len(records), 10)
        self.assertEqual(records[0].record.artifact_type, "location_point")

    def test_parse_photos_produces_media(self) -> None:
        records = parse_photos(CASE_DIR)
        self.assertEqual(records[0].record.artifact_type, "photo")

    def test_parse_app_events_produces_events(self) -> None:
        records = parse_app_events(CASE_DIR)
        self.assertEqual(records[0].record.artifact_type, "app_event")

    def test_parse_deleted_records_filters(self) -> None:
        records = parse_deleted_sqlite(CASE_DIR)
        self.assertGreaterEqual(len(records), 2)
        self.assertTrue(all(record.record.artifact_type == "recovered_record" for record in records))


if __name__ == "__main__":
    unittest.main()
