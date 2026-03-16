"""Integration tests for the parser pipeline."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from parser import run_pipeline

CASE_DIR = Path("cases/CT-2026-001")
GROUND_TRUTH_PATH = CASE_DIR / "validation" / "case_ct_2026_001_ground_truth.json"


class PipelineTest(unittest.TestCase):
    def test_pipeline_outputs_match_ground_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            parsed_dir = Path(tmpdir)
            records = run_pipeline(CASE_DIR, parsed_dir)
            self.assertEqual(len(records), 42)
            output_path = parsed_dir / "artifact_records.json"
            self.assertTrue(output_path.exists())
            recorded = json.loads(output_path.read_text(encoding="utf-8"))
            expected = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))["records"]
            self.assertEqual(recorded, expected)
            db_path = parsed_dir / "case.db"
            self.assertTrue(db_path.exists())
            with sqlite3.connect(db_path) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM artifacts_messages").fetchone()[0], 8)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM recovery_findings").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0], 42)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0], 42)
                case_timezone = json.loads((CASE_DIR / "case.json").read_text(encoding="utf-8"))["timezone"]
                timezones = {row[0] for row in conn.execute("SELECT DISTINCT timezone FROM timeline_events")}
                self.assertEqual(timezones, {case_timezone})
                location_rows = conn.execute("SELECT COUNT(*) FROM timeline_events WHERE has_location=1").fetchone()[0]
                self.assertEqual(location_rows, 14)
