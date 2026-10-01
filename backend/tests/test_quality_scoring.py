"""
Unit and integration tests for transparent dataset quality scoring.

Endpoint: POST /api/datasets/{dataset_id}/score

Proves:
1. A clean dataset receives a high score (close to or 100)
2. Severe quality problems lower the score significantly
3. The score remains strictly between 0 and 100 under all conditions (including extreme failure datasets)
4. Identical input produces 100% deterministic, reproducible results
5. Detailed explanations are generated for deductions across dimensions
6. API endpoint returns valid QualityScoreResponse schema
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

UPLOAD_URL = "/api/datasets/upload"


def upload_csv(content: str, filename: str = "dataset.csv") -> str:
    """Helper to upload CSV content and return dataset_id."""
    res = client.post(
        UPLOAD_URL,
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 200
    return res.json()["dataset_id"]


class TestQualityScoringCore:
    """Core requirements tests for quality scoring system."""

    def test_clean_dataset_receives_high_score(self):
        """Clean dataset with complete, valid, unique, and well-distributed values receives a high score (>= 90)."""
        clean_csv = (
            "id,first_name,last_name,email,age,score,created_at\n"
            "1,Alice,Smith,alice@example.com,28,95.5,2023-01-10\n"
            "2,Bob,Jones,bob@example.com,34,88.0,2023-01-11\n"
            "3,Charlie,Brown,charlie@example.com,22,91.2,2023-01-12\n"
            "4,Diana,Prince,diana@example.com,29,99.0,2023-01-13\n"
            "5,Evan,Wright,evan@example.com,41,84.5,2023-01-14\n"
            "6,Fiona,Gallagher,fiona@example.com,31,90.0,2023-01-15\n"
        )
        ds_id = upload_csv(clean_csv, "clean_dataset.csv")

        response = client.post(f"/api/datasets/{ds_id}/score")
        assert response.status_code == 200
        data = response.json()

        assert "overall" in data
        assert "dimensions" in data
        assert "explanation" in data

        # Clean dataset must receive a high score
        assert data["overall"] >= 90
        assert data["dimensions"]["completeness"] == 100
        assert data["dimensions"]["validity"] == 100
        assert data["dimensions"]["uniqueness"] == 100
        assert data["dimensions"]["consistency"] >= 90

    def test_severe_quality_problems_lower_the_score(self):
        """Dataset with extensive missingness, duplicates, and invalid domains receives a substantially lower score."""
        clean_csv = (
            "id,email,age,status\n"
            "1,alice@example.com,25,active\n"
            "2,bob@example.com,30,pending\n"
            "3,charlie@example.com,35,active\n"
            "4,diana@example.com,40,completed\n"
        )
        clean_id = upload_csv(clean_csv, "clean.csv")
        clean_score = client.post(f"/api/datasets/{clean_id}/score").json()["overall"]

        # Dirty dataset with empty columns, negative ages, invalid emails, and duplicate rows
        dirty_csv = (
            "id,email,age,status,empty_col\n"
            "1,invalid-email,-5,active,\n"
            "1,invalid-email,-5,active,\n"  # Exact duplicate
            "1,bad@email,-20,active,\n"     # Duplicate ID & negative age
            ",,,active,\n"                   # Mostly missing
        )
        dirty_id = upload_csv(dirty_csv, "dirty.csv")
        dirty_res = client.post(f"/api/datasets/{dirty_id}/score")
        assert dirty_res.status_code == 200
        dirty_data = dirty_res.json()

        dirty_score = dirty_data["overall"]

        # Proves severe quality problems lower the score
        assert dirty_score < clean_score
        assert dirty_score <= 50
        assert dirty_data["dimensions"]["completeness"] < 80
        assert dirty_data["dimensions"]["validity"] < 80
        assert dirty_data["dimensions"]["uniqueness"] < 80

    def test_score_remains_between_0_and_100_under_extremes(self):
        """Proves every dimension and overall score is clamped strictly between 0 and 100 even in catastrophic datasets."""
        # Catastrophic dataset: empty column, extreme duplicates, invalid data everywhere
        catastrophic_csv = (
            "id,age,percent,email,constant_col,empty_col\n"
            "1,-999,999,bad_email,X,\n"
            "1,-999,999,bad_email,X,\n"
            "1,-999,999,bad_email,X,\n"
            "1,-999,999,bad_email,X,\n"
        )
        ds_id = upload_csv(catastrophic_csv, "catastrophic.csv")
        response = client.post(f"/api/datasets/{ds_id}/score")
        assert response.status_code == 200
        data = response.json()

        # Check bounds
        assert 0 <= data["overall"] <= 100
        for dim, score in data["dimensions"].items():
            assert 0 <= score <= 100, f"Dimension '{dim}' out of bounds: {score}"

    def test_identical_input_produces_deterministic_results(self):
        """Proves scoring is 100% deterministic (calling endpoint multiple times yields identical output)."""
        csv_data = (
            "user_id,revenue,rating,notes\n"
            "A1,100.5,5,good\n"
            "A2,-50.0,4,needs improvement\n"
            "A3,200.0,,great\n"
            "A1,100.5,5,good\n"
        )
        ds_id = upload_csv(csv_data, "deterministic_test.csv")

        res1 = client.post(f"/api/datasets/{ds_id}/score").json()
        res2 = client.post(f"/api/datasets/{ds_id}/score").json()
        res3 = client.post(f"/api/datasets/{ds_id}/score").json()

        assert res1["overall"] == res2["overall"] == res3["overall"]
        assert res1["dimensions"] == res2["dimensions"] == res3["dimensions"]
        assert res1["explanation"] == res2["explanation"] == res3["explanation"]

    def test_explanations_describe_dimension_deductions(self):
        """Verifies that explanations detail which issues affected each dimension."""
        csv_data = (
            "email,age,missing_col\n"
            "bademail,-10,\n"
            "good@email.com,25,\n"
        )
        ds_id = upload_csv(csv_data, "explanation_check.csv")
        res = client.post(f"/api/datasets/{ds_id}/score")
        assert res.status_code == 200
        data = res.json()

        explanations = data["explanation"]
        assert len(explanations) >= 4  # overall + 4 dimensions

        exp_text = " ".join(explanations).lower()
        assert "completeness" in exp_text
        assert "validity" in exp_text
        assert "uniqueness" in exp_text
        assert "consistency" in exp_text


class TestQualityScoringErrors:
    """Error handling tests for score endpoint."""

    def test_scoring_missing_dataset_returns_404(self):
        res = client.post("/api/datasets/00000000-0000-0000-0000-000000000000/score")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
