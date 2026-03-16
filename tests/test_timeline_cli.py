"""Integration tests for the timeline CLI."""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from parser import run_pipeline

CASE_DIR = Path("cases/CT-2026-001")


class TimelineCLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp_dir = tempfile.TemporaryDirectory()
        cls.parsed_dir = Path(cls.tmp_dir.name) / "parsed"
        cls.parsed_dir.mkdir(parents=True, exist_ok=True)
        run_pipeline(CASE_DIR, cls.parsed_dir)
        cls.db_path = cls.parsed_dir / "case.db"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp_dir.cleanup()

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        command = [sys.executable, "tools/timeline.py", "--db-path", str(self.db_path), *args]
        return subprocess.run(command, check=True, capture_output=True, text=True)

    def test_deleted_only_exports_csv(self) -> None:
        csv_path = Path(self.tmp_dir.name) / "deleted.csv"
        self._run_cli("--deleted-only", "--output-csv", str(csv_path))
        with csv_path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        self.assertEqual({row["record_id"] for row in rows}, {"rec-001", "rec-002"})

    def test_location_only_exports_html(self) -> None:
        html_path = Path(self.tmp_dir.name) / "locations.html"
        self._run_cli("--location-only", "--output-html", str(html_path))
        text = html_path.read_text(encoding="utf-8")
        self.assertIn("<table", text)
        self.assertIn("has_location", text)
        self.assertIn("location_label", text)

    def test_contact_filter_is_case_insensitive(self) -> None:
        csv_path = Path(self.tmp_dir.name) / "contact.csv"
        self._run_cli("--contact", "jordan vega", "--output-csv", str(csv_path))
        with csv_path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        ids = {row["record_id"] for row in rows}
        self.assertGreaterEqual(len(rows), 40)
        self.assertIn("msg-001", ids)
        self.assertIn("call-004", ids)

    def test_anchor_window_limits_rows(self) -> None:
        csv_path = Path(self.tmp_dir.name) / "anchor.csv"
        self._run_cli("--anchor", "msg-001", "--window-minutes", "10", "--output-csv", str(csv_path))
        with csv_path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        ids = {row["record_id"] for row in rows}
        self.assertIn("msg-001", ids)
        self.assertIn("msg-002", ids)
        anchor = datetime.fromisoformat("2026-03-12T12:10:00+00:00")
        window = timedelta(minutes=10)
        for row in rows:
            timestamp = datetime.fromisoformat(row["event_time_start"].replace("Z", "+00:00"))
            self.assertTrue(anchor - window <= timestamp <= anchor + window, msg=row["record_id"])
