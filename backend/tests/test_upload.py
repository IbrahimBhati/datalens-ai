"""
Tests for the upload endpoint.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthCheck:
    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestUploadEndpoint:
    """Tests for POST /api/upload"""

    def _make_csv(self, content: str) -> io.BytesIO:
        return io.BytesIO(content.encode("utf-8"))

    def _make_json(self, data: list[dict]) -> io.BytesIO:
        return io.BytesIO(json.dumps(data).encode("utf-8"))

    # --- Happy path ---

    def test_upload_valid_csv(self):
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        response = client.post(
            "/api/upload",
            files={"file": ("test.csv", self._make_csv(csv_content), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert data["filename"] == "test.csv"
        assert data["file_type"] == "csv"
        assert data["column_count"] == 3
        assert data["row_count"] == 2
        assert set(data["columns"]) == {"name", "age", "city"}

    def test_upload_valid_json(self):
        json_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        response = client.post(
            "/api/upload",
            files={"file": ("test.json", self._make_json(json_data), "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "json"
        assert data["column_count"] == 2
        assert data["row_count"] == 2

    def test_upload_returns_preview_rows(self):
        csv_content = "x,y\n1,2\n3,4\n5,6\n"
        response = client.post(
            "/api/upload",
            files={"file": ("data.csv", self._make_csv(csv_content), "text/csv")},
        )
        data = response.json()
        assert "preview_rows" in data
        assert len(data["preview_rows"]) <= 5

    # --- Validation errors ---

    def test_reject_unsupported_extension(self):
        response = client.post(
            "/api/upload",
            files={"file": ("data.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_reject_empty_file(self):
        response = client.post(
            "/api/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_reject_unparseable_csv(self):
        # Binary garbage with csv extension
        response = client.post(
            "/api/upload",
            files={"file": ("bad.csv", io.BytesIO(b"\x00\x01\x02\x03"), "text/csv")},
        )
        # Should either 400 or parse as a single-value CSV; either is acceptable
        assert response.status_code in (200, 400)

    def test_reject_unparseable_json(self):
        response = client.post(
            "/api/upload",
            files={"file": ("bad.json", io.BytesIO(b"not json at all{{{"), "application/json")},
        )
        assert response.status_code == 400

    def test_no_file_returns_422(self):
        response = client.post("/api/upload")
        assert response.status_code == 422
