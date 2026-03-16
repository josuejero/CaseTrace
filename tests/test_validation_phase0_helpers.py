"""Regression tests for Phase 0 validation utilities."""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from tools.validate_phase0 import (
    assert_reserved_hosts,
    bundle_path_from_source_file,
    raw_ref_target,
    sha256_digest,
    validate_example_fixtures,
    verify_case_bundle,
    verify_docs_consistency,
    verify_hash_manifest,
)


class ValidationPhase0HelpersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = Path("cases/CT-2026-001")

    def test_bundle_and_raw_ref_paths(self) -> None:
        source_file = "/data/user/0/com.casetrace.waypoint/databases/waypoint_core.db"
        expected = (self.case_dir / "files" / "databases" / "waypoint_core.db").resolve()
        self.assertEqual(bundle_path_from_source_file(source_file), expected)
        with self.assertRaises(AssertionError):
            bundle_path_from_source_file("/tmp/other.db")
        raw_ref = "db://files/databases/waypoint_core.db#table=messages&rowid=1"
        self.assertEqual(raw_ref_target(raw_ref), expected)

    def test_sha256_digest_matches_manual_value(self) -> None:
        readme = Path("README.md")
        expected = hashlib.sha256(readme.read_bytes()).hexdigest()
        self.assertEqual(sha256_digest(readme), expected)

    def test_assert_reserved_hosts_accepts_examples(self) -> None:
        assert_reserved_hosts("Visited https://example.com/details today.")
        assert_reserved_hosts("Refer to https://example.test/logs.")
        with self.assertRaises(AssertionError):
            assert_reserved_hosts("https://google.com/secret")

    def test_validation_scripts_run_against_case(self) -> None:
        # Run the helper scripts to ensure the frozen datasets stay consistent.
        validate_example_fixtures()
        verify_case_bundle()
        verify_hash_manifest()
        verify_docs_consistency()
