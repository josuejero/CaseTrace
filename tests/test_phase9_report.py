"""Tests for the Phase 9 investigator report generator."""
from __future__ import annotations

import shutil
import tempfile
import unittest

from pathlib import Path

from integrity import load_manifest
from tools.phase9_report import generate_report


class Phase9ReportTest(unittest.TestCase):
    def test_generate_report_populates_manifest(self) -> None:
        source = Path("cases/CT-2026-001")
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "case"
            shutil.copytree(source, case_dir)
            result = generate_report(case_dir, output_dir=case_dir / "reports", generate_pdf=False)
            self.assertTrue(result.html_path.exists())
            manifest = load_manifest(case_dir)
            self.assertEqual(manifest["report"]["path"], result.html_path.relative_to(case_dir).as_posix())
            self.assertIn("validation", manifest["report"])
            self.assertEqual(manifest["report"]["sha256"], result.sha256)
