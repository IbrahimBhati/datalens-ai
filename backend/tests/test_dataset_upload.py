"""
Tests for POST /api/datasets/upload endpoint.

Covers:
- Valid CSV upload
- Valid JSON upload
- Unsupported file extension rejection
- Empty file rejection
- Oversized file rejection
- Path traversal protection
- Disallowed executable MIME type rejection
- Correct response schema without premature dataset analysis
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.config import MAX_UPLOAD_SIZE
from app.main import app

client = TestClient(app)

ENDPOINT = "/api/datasets/upload"


def make_file_payload(content: bytes | str, filename: str, content_type: str):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return {"file": (filename, io.BytesIO(content), content_type)}


class TestDatasetUploadSuccess:
    """Happy path upload tests."""

    def test_upload_valid_csv(self):
        csv_data = "id,name,score\n1,Alice,95.5\n2,Bob,88.0\n"
        response = client.post(
            ENDPOINT,
            files=make_file_payload(csv_data, "customers.csv", "text/csv"),
        )
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert len(data["dataset_id"]) >= 32
        assert data["filename"] == "customers.csv"
        assert data["format"] == "csv"
        assert data["size_bytes"] == len(csv_data.encode("utf-8"))
        # Ensure analysis was NOT performed yet
        assert "preview_rows" not in data
        assert "quality_score" not in data

    def test_upload_valid_json(self):
        records = [
            {"id": 1, "product": "Widget A", "price": 19.99},
            {"id": 2, "product": "Widget B", "price": 29.99},
        ]
        json_bytes = json.dumps(records).encode("utf-8")
        response = client.post(
            ENDPOINT,
            files=make_file_payload(json_bytes, "products.json", "application/json"),
        )
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert data["filename"] == "products.json"
        assert data["format"] == "json"
        assert data["size_bytes"] == len(json_bytes)

    def test_upload_valid_json_lines(self):
        jsonl = '{"id": 1, "status": "ok"}\n{"id": 2, "status": "pending"}\n'
        response = client.post(
            ENDPOINT,
            files=make_file_payload(jsonl, "events.json", "application/json"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"


class TestDatasetUploadValidation:
    """Validation and security tests."""

    def test_reject_unsupported_file_extension(self):
        response = client.post(
            ENDPOINT,
            files=make_file_payload(b"fake excel content", "sales.xlsx", "application/vnd.ms-excel"),
        )
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "unsupported file extension" in detail or "supported formats" in detail

    def test_reject_empty_file(self):
        response = client.post(
            ENDPOINT,
            files=make_file_payload(b"", "empty.csv", "text/csv"),
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_reject_oversized_file(self, monkeypatch):
        # Temporarily set max size to 100 bytes for deterministic testing
        import app.services.dataset_service as ds
        monkeypatch.setattr(ds, "MAX_UPLOAD_SIZE", 100)

        large_content = b"a" * 200
        response = client.post(
            ENDPOINT,
            files=make_file_payload(large_content, "large.csv", "text/csv"),
        )
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"].lower()

    def test_prevent_path_traversal(self):
        csv_data = "a,b\n1,2\n"
        # Attempt to upload using path traversal in filename
        response = client.post(
            ENDPOINT,
            files=make_file_payload(csv_data, "../../../etc/passwd.csv", "text/csv"),
        )
        assert response.status_code == 200
        data = response.json()
        # Must strip traversal components
        assert "/" not in data["filename"]
        assert "\\" not in data["filename"]
        assert data["filename"] == "passwd.csv"

    def test_reject_disallowed_mime_type(self):
        csv_data = "a,b\n1,2\n"
        # CSV extension with executable MIME type
        response = client.post(
            ENDPOINT,
            files=make_file_payload(csv_data, "exploit.csv", "application/x-msdownload"),
        )
        assert response.status_code == 400
        assert "disallowed mime type" in response.json()["detail"].lower()

    def test_reject_malformed_json(self):
        malformed = b"{not valid json at all:::"
        response = client.post(
            ENDPOINT,
            files=make_file_payload(malformed, "broken.json", "application/json"),
        )
        assert response.status_code == 400
        assert "invalid json" in response.json()["detail"].lower()

    def test_no_file_provided_returns_422(self):
        response = client.post(ENDPOINT)
        assert response.status_code == 422
