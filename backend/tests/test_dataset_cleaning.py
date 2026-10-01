"""
Unit tests for the dataset-cleaning system:
- Safe, non-destructive cleaning operations
- Verification that original dataset file is NEVER overwritten
- Audit trail of transformations performed
- Ambiguous transformations preserved with advisories/warnings
- Download endpoint functionality
"""

import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import UPLOAD_DIR
from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_dirty_csv() -> bytes:
    csv_content = (
        "id,name,email,age,country,notes\n"
        "1,Alice Smith,alice@example.com,30,USA,Good\n"
        "2,Bob Jones  ,BOB@EXAMPLE.COM,45,USA,  N/A  \n"
        "3,Charlie   Brown,charlie@sample.org,-5,USA,none\n"
        "4,Diana Prince,invalid-email,28,USA,Valid\n"
        "1,Alice Smith,alice@example.com,30,USA,Good\n"  # Exact duplicate of row 1
    )
    return csv_content.encode("utf-8")


def test_clean_dataset_removes_duplicates_and_preserves_original(sample_dirty_csv):
    # 1. Upload
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("dirty.csv", io.BytesIO(sample_dirty_csv), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    orig_path = Path(UPLOAD_DIR) / f"{dataset_id}.csv"
    assert orig_path.exists()
    orig_mtime_before = orig_path.stat().st_mtime
    orig_size_before = orig_path.stat().st_size

    # 2. Clean
    clean_res = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200
    data = clean_res.json()

    assert data["dataset_id"] == dataset_id
    assert data["original_rows"] == 5
    assert data["cleaned_rows"] == 4
    assert data["rows_removed"] == 1
    assert data["cells_modified"] > 0

    # 3. Check original file was NOT overwritten
    assert orig_path.exists()
    assert orig_path.stat().st_size == orig_size_before

    # 4. Check separate cleaned file exists
    cleaned_path = Path(UPLOAD_DIR) / f"{dataset_id}_cleaned.csv"
    assert cleaned_path.exists()
    assert cleaned_path.stat().st_size > 0


def test_clean_dataset_transformations_audit(sample_dirty_csv):
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("dirty.csv", io.BytesIO(sample_dirty_csv), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    clean_res = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200
    data = clean_res.json()

    types = [t["type"] for t in data["transformations_performed"]]
    assert "remove_duplicates" in types
    assert "trim_whitespace" in types
    assert "standardize_missing" in types

    # Check warnings for ambiguous issues
    warnings = data["warnings"]
    assert any("negative" in w.lower() for w in warnings)
    assert any("email" in w.lower() for w in warnings)


def test_clean_dataset_download_endpoint(sample_dirty_csv):
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("dirty.csv", io.BytesIO(sample_dirty_csv), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    # Download before cleaning should return 404
    dl_before = client.get(f"/api/datasets/{dataset_id}/download-cleaned")
    assert dl_before.status_code == 404

    # Run clean
    clean_res = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200

    # Download after cleaning
    dl_after = client.get(f"/api/datasets/{dataset_id}/download-cleaned")
    assert dl_after.status_code == 200
    assert "text/csv" in dl_after.headers["content-type"]
    assert "attachment" in dl_after.headers.get("content-disposition", "")
    assert len(dl_after.content) > 0

    # Cleaned file content should have 4 data rows + 1 header row = 5 lines
    lines = dl_after.content.decode("utf-8").strip().splitlines()
    assert len(lines) == 5
    # Row with bob should have lowercase email and trimmed name
    assert "Bob Jones" in dl_after.content.decode("utf-8")
    assert "bob@example.com" in dl_after.content.decode("utf-8")


def test_clean_nonexistent_dataset():
    res = client.post("/api/datasets/nonexistent-id-0000/clean")
    assert res.status_code == 404
