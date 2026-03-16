"""Integration tests for the Phase 7 search API."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.main import app


class SearchApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_search_defaults(self) -> None:
        response = self.client.get("/search")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_hits"], 42)
        self.assertEqual(payload["artifact_counts"]["message"], 8)
        self.assertEqual(payload["artifact_counts"]["photo"], 4)
        self.assertEqual(payload["artifact_counts"]["evidence_file"], 0)
        self.assertEqual(len(payload["hits"]), 20)
        first_hit = payload["hits"][0]
        self.assertGreater(len(first_hit["timeline_context"]), 0)
        self.assertIn("snippet", first_hit)

    def test_search_filters_and_snippet(self) -> None:
        response = self.client.get(
            "/search",
            params={"q": "Harbor", "type": "message"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_hits"], 1)
        hit = payload["hits"][0]
        self.assertEqual(hit["artifact_type"], "message")
        self.assertIn("Harbor", hit["snippet"])
        self.assertIn("Harbor", hit["metadata_text"])
        self.assertGreaterEqual(len(hit["timeline_context"]), 1)

    def test_record_detail_matches_search_hit(self) -> None:
        response = self.client.get("/search", params={"q": "Jordan", "type": "message"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["total_hits"], 0)
        hit = payload["hits"][0]
        record_id = hit["record_id"]
        detail_resp = self.client.get(f"/records/{record_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["record_id"], record_id)
        self.assertTrue(any(entry["record_id"] == record_id for entry in detail["timeline_context"]))

    def test_overview_endpoint(self) -> None:
        response = self.client.get("/overview")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("artifact_counts", payload)
        self.assertIn("file_summary", payload)
        self.assertIsInstance(payload.get("notable_artifacts"), list)

    def test_timeline_and_artifact_endpoints(self) -> None:
        timeline_resp = self.client.get("/timeline", params={"limit": 10})
        self.assertEqual(timeline_resp.status_code, 200)
        timeline_payload = timeline_resp.json()
        self.assertIn("groups", timeline_payload)
        artifacts_resp = self.client.get("/artifacts", params={"artifact_type": "message", "limit": 5})
        self.assertEqual(artifacts_resp.status_code, 200)
        artifacts_payload = artifacts_resp.json()
        self.assertLessEqual(len(artifacts_payload.get("rows", [])), 5)

    def test_entity_graph_and_report_endpoints(self) -> None:
        graph_resp = self.client.get("/entity-graph")
        self.assertEqual(graph_resp.status_code, 200)
        graph_payload = graph_resp.json()
        self.assertIn("nodes", graph_payload)
        report_resp = self.client.get("/reports/latest")
        self.assertEqual(report_resp.status_code, 200)
        report_payload = report_resp.json()
        self.assertIn("path", report_payload)
