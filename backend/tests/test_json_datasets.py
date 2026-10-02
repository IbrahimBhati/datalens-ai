import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_nested_and_wrapped_json_upload_and_pipeline():
    """Verify JSON files with nested objects, wrapper keys, and lists work across the entire pipeline."""
    complex_data = {
        "status": "ok",
        "data": [
            {"id": 1, "user": {"name": "Alice", "city": "NY"}, "tags": ["admin", "dev"], "score": 95},
            {"id": 2, "user": {"name": "Bob", "city": "LA"}, "tags": ["user"], "score": 80},
            {"id": 3, "user": {"name": "Charlie", "city": "SF"}, "tags": ["dev"], "score": 75},
        ]
    }
    json_bytes = json.dumps(complex_data).encode("utf-8-sig")  # With BOM
    file_obj = io.BytesIO(json_bytes)

    # 1. Upload
    res_upload = client.post(
        "/api/datasets/upload",
        files={"file": ("complex_users.json", file_obj, "application/json")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    dataset_id = upload_data["dataset_id"]
    assert upload_data["format"] == "json"

    # 2. Profile
    res_profile = client.post(f"/api/datasets/{dataset_id}/profile")
    assert res_profile.status_code == 200
    profile_data = res_profile.json()
    assert profile_data["general"]["row_count"] == 3
    assert len(profile_data["columns"]) >= 3

    # 3. Analyze quality
    res_analysis = client.post(f"/api/datasets/{dataset_id}/analyze")
    assert res_analysis.status_code == 200
    assert "total_issues" in res_analysis.json()

    # 4. Score
    res_score = client.post(f"/api/datasets/{dataset_id}/score")
    assert res_score.status_code == 200
    assert "overall" in res_score.json()

    # 5. Clean
    res_clean = client.post(f"/api/datasets/{dataset_id}/clean")
    assert res_clean.status_code == 200
    clean_data = res_clean.json()
    assert clean_data["cleaned_rows"] == 3

    # 6. Download cleaned
    res_dl = client.get(f"/api/datasets/{dataset_id}/download-cleaned")
    assert res_dl.status_code == 200
