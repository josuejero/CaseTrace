"""Integration test for the backend integrity endpoint."""
from fastapi.testclient import TestClient

from backend.main import app


def test_integrity_endpoint_returns_manifest() -> None:
    client = TestClient(app)
    response = client.get("/integrity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest"]["case_id"] == "CT-2026-001"
    assert payload["processing_log"]["steps"]
    assert "file_summary" in payload
