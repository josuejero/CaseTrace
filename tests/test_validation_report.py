"""Regression tests for the Phase 10 validation surface."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.validate_phase10 import build_validation_summary, ValidationSummary


CASE_DIR = Path("cases/CT-2026-001")


class ValidationReportTest(unittest.TestCase):
    def test_validation_summary_passes(self) -> None:
        summary = build_validation_summary(CASE_DIR)
        self.assertIsInstance(summary, ValidationSummary)
        self.assertTrue(summary.passed)

        checks = {check.name: check for check in summary.checks}
        self.assertIn("message count", checks)
        self.assertEqual(checks["message count"].expected, checks["message count"].actual)
        self.assertEqual(checks["message count"].passed, True)

        self.assertIn("recovered/deleted rows", checks)
        self.assertEqual(checks["recovered/deleted rows"].expected, checks["recovered/deleted rows"].actual)

        self.assertIn("timeline locations with GPS", checks)
        self.assertEqual(checks["timeline locations with GPS"].expected, checks["timeline locations with GPS"].actual)

        self.assertGreaterEqual(len(summary.photo_checks), 4)
        self.assertTrue(all(photo.passed for photo in summary.photo_checks))


if __name__ == "__main__":
    unittest.main()
