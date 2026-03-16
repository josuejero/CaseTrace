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
        self.assertEqual(payload["total_hits"], 55)
        self.assertEqual(payload["artifact_counts"]["message"], 8)
        self.assertEqual(payload["artifact_counts"]["evidence_file"], 13)
        self.assertEqual(len(payload["hits"]), 20)
        first_hit = payload["hits"][0]
        self.assertGreater(len(first_hit["timeline_context"]), 0)
        self.assertIn("snippet", first_hit)

    def test_search_filters_and_snippet(self) -> None:
        response = self.client.get(
            "/search",
            params={"q": "sha256:cc681b59", "type": "evidence_file"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_hits"], 1)
        hit = payload["hits"][0]
        self.assertEqual(hit["artifact_type"], "evidence_file")
        self.assertIn("sha256:cc681b59", hit["metadata_text"])
        self.assertEqual(hit["timeline_context"], [])

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
