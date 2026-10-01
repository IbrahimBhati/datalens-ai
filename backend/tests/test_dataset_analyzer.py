"""
Tests for deterministic data-quality detection engine.

Endpoint: POST /api/datasets/{dataset_id}/analyze

Covers:
1. Missing Values (missing cells, high missing percentages, completely empty columns)
2. Duplicates (duplicate rows, duplicate identifiers, normalized duplicates)
3. Invalid Values (emails, percentages, non-negative violations, phones, dates)
4. Constant Columns (cardinality == 1)
5. Low-Variance Columns (dominant category >= 99%)
6. Outliers (IQR detection with transparent method string)
7. Text Quality (near-empty, long strings, repetitions, whitespace formatting)
8. Response schema compliance (type, severity, column, affected_rows, percentage, description, method)
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

UPLOAD_URL = "/api/datasets/upload"


def upload_dataset(content: str, filename: str, content_type: str = "text/csv") -> str:
    """Helper to upload dataset and return dataset_id."""
    res = client.post(
        UPLOAD_URL,
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), content_type)},
    )
    assert res.status_code == 200
    return res.json()["dataset_id"]


class TestMissingValuesDetector:
    """Tests for missing values, high null rates, and empty columns."""

    def test_detect_empty_column_and_high_missing(self):
        csv_data = (
            "id,name,empty_col,mostly_null\n"
            "1,Alice,,val1\n"
            "2,Bob,,\n"
            "3,Charlie,,\n"
            "4,Diana,,\n"
            "5,Evan,,\n"
        )
        ds_id = upload_dataset(csv_data, "missing_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        empty_issues = [i for i in data["issues"] if i["type"] == "empty_column"]
        assert len(empty_issues) == 1
        assert empty_issues[0]["column"] == "empty_col"
        assert empty_issues[0]["percentage"] == 100.0
        assert empty_issues[0]["severity"] == "high"

        high_missing = [i for i in data["issues"] if i["type"] == "high_missing_percentage"]
        assert len(high_missing) >= 1
        mostly = next(i for i in high_missing if i["column"] == "mostly_null")
        assert mostly["percentage"] == 80.0
        assert mostly["severity"] == "high"


class TestDuplicatesDetector:
    """Tests for exact duplicate rows, duplicate IDs, and normalized duplicates."""

    def test_detect_duplicate_rows_and_identifiers(self):
        csv_data = (
            "user_id,email,country\n"
            "U101,a@test.com,USA\n"
            "U102,b@test.com,Canada\n"
            "U101,c@test.com,UK\n"         # Duplicate user_id
            "U103,d@test.com,Germany\n"
            "U103,d@test.com,Germany\n"    # Complete duplicate row
        )
        ds_id = upload_dataset(csv_data, "dup_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        # Check full-row duplicates
        row_dup_issues = [i for i in data["issues"] if i["type"] == "duplicate_rows"]
        assert len(row_dup_issues) == 1
        assert row_dup_issues[0]["affected_rows"] == 2
        assert "Exact full-row" in row_dup_issues[0]["method"]

        # Check identifier duplicates
        id_dup_issues = [i for i in data["issues"] if i["type"] == "duplicate_identifier"]
        assert len(id_dup_issues) >= 1
        user_id_issue = next(i for i in id_dup_issues if i["column"] == "user_id")
        assert user_id_issue["affected_rows"] >= 2

    def test_detect_normalized_duplicates(self):
        csv_data = (
            "city,code\n"
            "London,LDN\n"
            "paris,PRS\n"
            "PARIS ,PRS\n"  # Near duplicate with whitespace & casing
            "Berlin,BER\n"
        )
        ds_id = upload_dataset(csv_data, "norm_dup.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        norm_issues = [i for i in data["issues"] if i["type"] == "normalized_duplicate_rows"]
        assert len(norm_issues) == 1
        assert norm_issues[0]["affected_rows"] >= 2


class TestValidationDetector:
    """Tests for invalid values, domain boundaries, and constants."""

    def test_detect_malformed_emails_and_phones(self):
        csv_data = (
            "email,phone_number\n"
            "valid.user@example.com,+15551234567\n"
            "broken-email-no-at.com,1234\n"       # Bad email, bad short phone
            "missingdomain@,abc-phone-invalid\n"   # Bad email, bad characters phone
            "ok@domain.org,(555) 987-6543\n"
        )
        ds_id = upload_dataset(csv_data, "validation_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        email_issues = [i for i in data["issues"] if i["type"] == "invalid_email"]
        assert len(email_issues) == 1
        assert email_issues[0]["column"] == "email"
        assert email_issues[0]["affected_rows"] == 2

        phone_issues = [i for i in data["issues"] if i["type"] == "malformed_phone"]
        assert len(phone_issues) == 1
        assert phone_issues[0]["column"] == "phone_number"
        assert phone_issues[0]["affected_rows"] == 2

    def test_detect_impossible_percentages_and_negative_quantities(self):
        csv_data = (
            "discount_pct,age,item_count\n"
            "15.0,25,5\n"
            "120.0,-5,10\n"    # 120% impossible, age -5 negative violation
            "-10.0,30,-2\n"    # -10% impossible, item_count -2 negative violation
            "45.0,40,8\n"
        )
        ds_id = upload_dataset(csv_data, "bounds_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        pct_issues = [i for i in data["issues"] if i["type"] == "impossible_percentage"]
        assert len(pct_issues) == 1
        assert pct_issues[0]["column"] == "discount_pct"
        assert pct_issues[0]["affected_rows"] == 2

        neg_issues = [i for i in data["issues"] if i["type"] == "negative_value_violation"]
        assert len(neg_issues) == 2
        neg_cols = {i["column"] for i in neg_issues}
        assert "age" in neg_cols
        assert "item_count" in neg_cols

    def test_detect_constant_column(self):
        csv_data = (
            "status,country,score\n"
            "active,USA,90\n"
            "active,USA,80\n"
            "active,USA,70\n"
            "active,USA,60\n"
        )
        ds_id = upload_dataset(csv_data, "constant_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        constant_issues = [i for i in data["issues"] if i["type"] == "constant_column"]
        assert len(constant_issues) == 2
        const_cols = {i["column"] for i in constant_issues}
        assert "status" in const_cols
        assert "country" in const_cols


class TestOutliersDetector:
    """Tests for numerical outliers using transparent IQR."""

    def test_detect_iqr_outliers(self):
        # 10 values with 1 extreme outlier (999.0)
        csv_data = "salary\n50\n52\n48\n51\n49\n53\n50\n52\n47\n999\n"
        ds_id = upload_dataset(csv_data, "outlier_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        outlier_issues = [i for i in data["issues"] if i["type"] == "outliers"]
        assert len(outlier_issues) == 1
        issue = outlier_issues[0]
        assert issue["column"] == "salary"
        assert issue["affected_rows"] == 1
        assert "IQR" in issue["method"]


class TestTextQualityDetector:
    """Tests for text anomalies: near-empty, repetitions, whitespace formatting."""

    def test_detect_text_quality_anomalies(self):
        csv_data = (
            "description\n"
            "Standard product summary description here\n"
            "Another normal text description goes here\n"
            ".\n"                           # Near-empty (len <= 1)
            "aaaaa\n"                       # Repeated characters
            "test test test test\n"          # Repeated word pattern
            "   leading space text   \n"    # Suspicious whitespace
        )
        ds_id = upload_dataset(csv_data, "text_test.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        types = {i["type"] for i in data["issues"]}
        assert "near_empty_text" in types
        assert "repeated_text_anomaly" in types
        assert "whitespace_formatting_anomaly" in types


class TestQualityIssueSchemaCompliance:
    """Verify that every detected issue adheres to the required schema."""

    def test_issue_schema_fields(self):
        csv_data = "colA,colB\n1,\n1,\n"
        ds_id = upload_dataset(csv_data, "schema_check.csv")
        res = client.post(f"/api/datasets/{ds_id}/analyze")
        assert res.status_code == 200
        data = res.json()

        assert "total_issues" in data
        assert "issues_by_severity" in data
        assert "issues" in data
        assert len(data["issues"]) > 0

        for issue in data["issues"]:
            assert "type" in issue
            assert "severity" in issue
            assert issue["severity"] in ("high", "medium", "low")
            assert "column" in issue
            assert "affected_rows" in issue
            assert isinstance(issue["affected_rows"], int)
            assert "percentage" in issue
            assert isinstance(issue["percentage"], (int, float))
            assert "description" in issue
            assert len(issue["description"]) > 0
            assert "method" in issue
            assert len(issue["method"]) > 0
