"""
Tests for deterministic dataset profiling engine.

Endpoint: POST /api/datasets/{dataset_id}/profile

Covers:
- General metrics (row count, column count, file format, memory usage)
- Column nullability & uniqueness metrics
- Numeric column stats (min, max, mean, median, std, quartiles)
- Text column stats (min length, max length, avg length)
- Categorical distribution (top values and frequencies)
- Safe date detection and confidence scoring
- Guard against aggressive date conversion on ambiguous numbers
- Non-modification of original file on disk
- 404 on missing dataset ID
- Path traversal protection on dataset ID
"""

import hashlib
import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

UPLOAD_URL = "/api/datasets/upload"


def upload_content(content: str, filename: str, content_type: str) -> str:
    """Helper to upload a dataset and return its dataset_id."""
    res = client.post(
        UPLOAD_URL,
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), content_type)},
    )
    assert res.status_code == 200
    return res.json()["dataset_id"]


class TestDatasetProfilerGeneral:
    """Tests for general dataset dimensions and non-modification."""

    def test_profile_csv_general_and_integrity(self):
        csv_content = (
            "id,name,age,salary,signup_date,city\n"
            "1,Alice,25,50000.0,2023-01-10,New York\n"
            "2,Bob,30,60000.0,2023-02-15,San Francisco\n"
            "3,Charlie,,75000.0,2023-03-20,New York\n"
            "4,Diana,40,90000.0,2023-04-25,Chicago\n"
            "5,Evan,35,,2023-05-30,New York\n"
        )
        dataset_id = upload_content(csv_content, "employees.csv", "text/csv")

        # Record file hash before profiling to verify original dataset is untouched
        from app.analyzers.profiler import locate_dataset_file
        file_path, _ = locate_dataset_file(dataset_id)
        hash_before = hashlib.sha256(file_path.read_bytes()).hexdigest()

        response = client.post(f"/api/datasets/{dataset_id}/profile")
        assert response.status_code == 200
        profile = response.json()

        # 1. General Profile
        general = profile["general"]
        assert general["dataset_id"] == dataset_id
        assert general["row_count"] == 5
        assert general["column_count"] == 6
        assert general["file_format"] == "csv"
        assert general["memory_usage_bytes"] > 0
        assert "B" in general["memory_usage_human"] or "KB" in general["memory_usage_human"]

        # 2. Check original file was not modified
        hash_after = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert hash_before == hash_after, "Original dataset file must remain strictly unmodified"

    def test_profile_json_dataset(self):
        records = [
            {"product": "Laptop", "category": "Electronics", "price": 1200.0, "in_stock": True},
            {"product": "Mouse", "category": "Electronics", "price": 25.5, "in_stock": True},
            {"product": "Desk", "category": "Furniture", "price": 350.0, "in_stock": False},
        ]
        dataset_id = upload_content(json.dumps(records), "catalog.json", "application/json")

        response = client.post(f"/api/datasets/{dataset_id}/profile")
        assert response.status_code == 200
        profile = response.json()

        assert profile["general"]["row_count"] == 3
        assert profile["general"]["column_count"] == 4
        assert profile["general"]["file_format"] == "json"


class TestColumnProfilingMetrics:
    """Tests for detailed column metrics: numeric, text, categorical, and date."""

    @pytest.fixture(autouse=True)
    def setup_dataset(self):
        # 6 rows dataset with various data types and missing values
        csv_data = (
            "score,comments,department,created_at,ambiguous_year\n"
            "10.0,Good,Engineering,2023-01-01,2021\n"
            "20.0,Superb work,Engineering,2023-02-01,2022\n"
            "30.0,Fair,Sales,2023-03-01,2021\n"
            "40.0,,Marketing,2023-04-01,2023\n"
            "50.0,Needs improvement,Engineering,2023-05-01,2024\n"
            ",N/A,Sales,2023-06-01,2021\n"
        )
        self.dataset_id = upload_content(csv_data, "evaluation.csv", "text/csv")
        res = client.post(f"/api/datasets/{self.dataset_id}/profile")
        assert res.status_code == 200
        self.profile = res.json()
        self.cols_by_name = {col["name"]: col for col in self.profile["columns"]}

    def test_numeric_column_statistics(self):
        score_col = self.cols_by_name["score"]
        assert score_col["inferred_type"] == "numeric"
        assert score_col["non_null_count"] == 5
        assert score_col["null_count"] == 1
        assert score_col["null_percentage"] == round(1 / 6 * 100, 2)
        assert score_col["unique_count"] == 5

        # Check numeric stats
        num_stats = score_col["numeric_stats"]
        assert num_stats is not None
        assert num_stats["min"] == 10.0
        assert num_stats["max"] == 50.0
        assert num_stats["mean"] == 30.0
        assert num_stats["median"] == 30.0
        assert num_stats["std"] is not None
        assert num_stats["q25"] == 20.0
        assert num_stats["q50"] == 30.0
        assert num_stats["q75"] == 40.0

    def test_text_column_statistics(self):
        comments_col = self.cols_by_name["comments"]
        assert comments_col["inferred_type"] in ("text", "categorical")
        text_stats = comments_col["text_stats"]
        assert text_stats is not None
        assert text_stats["min_length"] > 0
        assert text_stats["max_length"] >= text_stats["min_length"]
        assert text_stats["avg_length"] > 0

    def test_categorical_distribution(self):
        dept_col = self.cols_by_name["department"]
        assert dept_col["inferred_type"] == "categorical"
        cat_stats = dept_col["categorical_stats"]
        assert cat_stats is not None
        top_vals = cat_stats["top_values"]
        assert len(top_vals) > 0
        # Engineering should have highest count (3 out of 6 = 50%)
        eng = next((v for v in top_vals if v["value"] == "Engineering"), None)
        assert eng is not None
        assert eng["count"] == 3
        assert eng["percentage"] == 50.0

    def test_safe_date_detection(self):
        created_col = self.cols_by_name["created_at"]
        assert created_col["inferred_type"] == "datetime"
        date_stats = created_col["date_stats"]
        assert date_stats is not None
        assert date_stats["is_date"] is True
        assert date_stats["confidence"] >= 0.85
        assert "2023-01-01" in date_stats["earliest"]
        assert "2023-06-01" in date_stats["latest"]

    def test_do_not_convert_ambiguous_numbers_to_dates(self):
        year_col = self.cols_by_name["ambiguous_year"]
        # Plain 4-digit numbers like 2021, 2022 should be numeric, not converted to epoch dates
        assert year_col["inferred_type"] in ("numeric", "categorical")
        assert year_col["date_stats"] is None or year_col["date_stats"]["is_date"] is False


class TestDatasetProfilerErrors:
    """Tests for edge cases and errors."""

    def test_missing_dataset_returns_404(self):
        response = client.post("/api/datasets/00000000-0000-0000-0000-000000000000/profile")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_path_traversal_returns_400(self):
        response = client.post("/api/datasets/..%2F..%2Fetc/profile")
        assert response.status_code in (400, 404)
