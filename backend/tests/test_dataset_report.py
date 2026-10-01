"""
Unit tests for the Dataset Quality Report system:
- HTML Report generation with 12 sections
- PDF Report generation using ReportLab
- Content integrity and no leakage of prompts or keys
- Cleaning audit inclusion in reports
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_dataset_bytes() -> bytes:
    content = (
        "id,name,email,age,country,notes\n"
        "1,Alice Smith,alice@example.com,30,USA,Good customer\n"
        "2,Bob Jones,bob@example.com,45,USA,N/A\n"
        "3,Charlie Brown,invalid-email,-5,USA,none\n"
        "4,Diana Prince,diana@themyscira.com,32,USA,Regular\n"
        "1,Alice Smith,alice@example.com,30,USA,Good customer\n"  # Duplicate row
    )
    return content.encode("utf-8")


def test_html_report_contains_all_12_sections(sample_dataset_bytes):
    # Upload
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("customers.csv", io.BytesIO(sample_dataset_bytes), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    # Request HTML report
    res = client.get(f"/api/datasets/{dataset_id}/report/html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

    html_text = res.text
    # Verify all 12 sections are present
    assert "1" in html_text and "Dataset Overview" in html_text
    assert "2" in html_text and "Overall Quality Score" in html_text
    assert "3" in html_text and "Dimension Scores" in html_text
    assert "4" in html_text and "Column Profile" in html_text
    assert "5" in html_text and "Missing-Value Analysis" in html_text
    assert "6" in html_text and "Duplicate Analysis" in html_text
    assert "7" in html_text and "Validation" in html_text
    assert "8" in html_text and "Outlier" in html_text
    assert "9" in html_text and "Text-Quality" in html_text
    assert "10" in html_text and "AI Executive Summary" in html_text
    assert "11" in html_text and "Priority Remediation" in html_text or "Priority Recommendations" in html_text
    assert "12" in html_text and "Cleaning Summary" in html_text

    # Verify no internal prompt leakage
    assert "CRITICAL SECURITY INSTRUCTION" not in html_text
    assert "UNTRUSTED DATA" not in html_text
    assert "API_KEY" not in html_text


def test_pdf_report_generation(sample_dataset_bytes):
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("customers.csv", io.BytesIO(sample_dataset_bytes), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    res = client.get(f"/api/datasets/{dataset_id}/report/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 3000  # Multi-page complete PDF


def test_report_reflects_cleaning_when_performed(sample_dataset_bytes):
    upload_res = client.post(
        "/api/datasets/upload",
        files={"file": ("customers.csv", io.BytesIO(sample_dataset_bytes), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    # Clean the dataset
    clean_res = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200

    # HTML report should now contain the executed cleaning audit stats
    html_res = client.get(f"/api/datasets/{dataset_id}/report/html")
    assert html_res.status_code == 200
    assert "Cleaned Rows" in html_res.text
    assert "Rows Removed" in html_res.text


def test_report_nonexistent_dataset():
    res = client.get("/api/datasets/nonexistent-dataset-id/report/html")
    assert res.status_code == 404

    res_pdf = client.get("/api/datasets/nonexistent-dataset-id/report/pdf")
    assert res_pdf.status_code == 404
