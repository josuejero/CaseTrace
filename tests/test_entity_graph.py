"""Tests for the Phase 5 entity graph builder."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from parser import run_pipeline
from tools.entity_graph_builder import EntityGraphBuilder

CASE_DIR = Path("cases/CT-2026-001")


class EntityGraphTest(unittest.TestCase):
    def test_graph_exports_expected_nodes_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            parsed_dir = Path(tmpdir)
            run_pipeline(CASE_DIR, parsed_dir)
            graph_data = EntityGraphBuilder(parsed_dir / "case.db", CASE_DIR).build()
            payload = graph_data.to_dict()
            nodes = payload["nodes"]
            edges = payload["edges"]

            self.assertTrue(
                any(node["type"] == "person" and node["label"] == "Jordan Vega" for node in nodes),
                "Jordan Vega must appear as a person node",
            )
            self.assertTrue(
                any(edge["type"] == "messaged" and edge["metadata"]["record_id"] == "msg-001" for edge in edges),
                "msg-001 must be captured by a messaged edge",
            )
            self.assertTrue(
                any(node["type"] == "keyword" for node in nodes),
                "There should be at least one keyword node for an app event",
            )
            self.assertTrue(
                any(node["type"] == "keyword" and "session" in node["label"].lower() for node in nodes),
                "At least one keyword node should mention the session",
            )
            self.assertTrue(
                any(node["type"] == "URL" for node in nodes),
                "Browser visits should create URL nodes",
            )
            self.assertTrue(
                any(edge["type"] == "stored_in" for edge in edges), "At least one stored_in edge is required"
            )
            self.assertTrue(
                any(edge["type"] == "linked_to_case" for edge in edges),
                "Each file should link back to case metadata",
            )
            self.assertTrue(
                any(edge["type"] == "called" and edge["metadata"]["record_id"] == "call-001" for edge in edges),
                "call-001 should generate a called edge",
            )
            for edge in edges:
                self.assertIn("record_id", edge["metadata"])
                self.assertIn("raw_ref", edge["metadata"])
            self.assertEqual(payload["case_id"], "CT-2026-001")


if __name__ == "__main__":
    unittest.main()
