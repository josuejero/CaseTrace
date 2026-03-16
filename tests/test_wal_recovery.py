"""Unit tests for the WAL recovery helpers."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from parser.models import PARSER_VERSION
from parser.wal_recovery import parse_wal_recovery


class WalRecoveryTest(unittest.TestCase):
    def test_wal_recovery_emits_observed_recovered_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "case"
            db_dir = case_dir / "files" / "databases"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "forensic.db"
            connection = self._build_synthetic_wal(db_path)
            try:
                result = parse_wal_recovery(case_dir)
            finally:
                connection.close()
            self.assertEqual(len(result.artifacts), 2)

            labels = {finding.label for finding in result.findings}
            self.assertTrue({"observed", "recovered", "inferred"}.issubset(labels))

            for finding in result.findings:
                self.assertTrue(finding.database_file.endswith("forensic.db"))
                self.assertEqual(finding.parser_method, "wal_recovery")
                self.assertEqual(finding.parser_version, PARSER_VERSION)
                if finding.label == "recovered":
                    self.assertIn("-wal", finding.raw_ref)
                    self.assertTrue(finding.confidence >= 0.5)
                if finding.label == "inferred":
                    self.assertIn("Inferred", finding.summary)

    def _build_synthetic_wal(self, db_path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(db_path)
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.execute("PRAGMA wal_autocheckpoint=0;")
        connection.execute(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                recipient TEXT,
                body TEXT,
                timestamp TEXT,
                deleted_flag INTEGER
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE browser_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                timestamp TEXT,
                typed_url INTEGER,
                referrer TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO messages (sender, recipient, body, timestamp, deleted_flag) VALUES (?, ?, ?, ?, ?)",
            ("Alice", "Jordan", "Drafted the rendezvous note.", "2026-03-12T08:00:00Z", 1),
        )
        connection.execute(
            "INSERT INTO browser_history (url, title, timestamp, typed_url, referrer) VALUES (?, ?, ?, ?, ?)",
            ("https://maps.example/device-entry", "Device entry", "2026-03-12T08:05:00Z", 1, None),
        )
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        connection.commit()
        connection.execute(
            "INSERT INTO browser_history (url, title, timestamp, typed_url, referrer) VALUES (?, ?, ?, ?, ?)",
            ("https://maps.example/service-entry", "Service entry", "2026-03-12T08:20:00Z", 1, "https://maps.example/device-entry"),
        )
        connection.commit()
        return connection
