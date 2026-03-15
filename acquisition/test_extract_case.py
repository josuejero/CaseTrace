from __future__ import annotations

import json
import unittest
from pathlib import Path

from acquisition.extract_case import DEFAULT_CASE_DIR, collect_file_entries


class ManifestHelpersTest(unittest.TestCase):
    def test_collect_file_entries_matches_manifest(self):
        case_dir = DEFAULT_CASE_DIR
        files_dir = case_dir / "files"
        manifest_path = case_dir / "hash_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = collect_file_entries(files_dir, case_dir)
        self.assertEqual(entries, manifest.get("files", []))


if __name__ == "__main__":
    unittest.main()
