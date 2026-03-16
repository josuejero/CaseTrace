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
MANIFEST_PATH = CASE_DIR / "hash_manifest.json"


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
                recovery_total = conn.execute("SELECT COUNT(*) FROM recovery_findings").fetchone()[0]
                self.assertEqual(recovery_total, 4)
                label_counts = {
                    row[0]: row[1] for row in conn.execute("SELECT finding_label, COUNT(*) FROM recovery_findings GROUP BY finding_label")
                }
                self.assertEqual(label_counts.get("observed", 0), 2)
                inferred_or_recovered = label_counts.get("inferred", 0) + label_counts.get("recovered", 0)
                self.assertGreaterEqual(inferred_or_recovered, 2)
                self.assertGreaterEqual(label_counts.get("inferred", 0), 1)
                manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                expected_rows = 42 + len(manifest.get("files", []))
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0], expected_rows)
                file_row = conn.execute(
                    "SELECT metadata_text FROM search_index WHERE artifact_type='evidence_file' LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(file_row)
                self.assertIn("sha256:", file_row[0])
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0],
                    42,
                )
                parser_methods = {row[0] for row in conn.execute("SELECT DISTINCT parser_method FROM recovery_findings")}
                self.assertEqual(parser_methods, {"wal_recovery"})
                database_files = {row[0] for row in conn.execute("SELECT DISTINCT database_file FROM recovery_findings")}
                self.assertTrue(any("waypoint_core.db" in entry or "waypoint_web.db" in entry for entry in database_files))
                case_timezone = json.loads((CASE_DIR / "case.json").read_text(encoding="utf-8"))["timezone"]
                timezones = {row[0] for row in conn.execute("SELECT DISTINCT timezone FROM timeline_events")}
                self.assertEqual(timezones, {case_timezone})
                location_rows = conn.execute("SELECT COUNT(*) FROM timeline_events WHERE has_location=1").fetchone()[0]
                self.assertEqual(location_rows, 14)
