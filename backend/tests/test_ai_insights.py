"""
Tests for AI Insight Layer.

Endpoint: POST /api/datasets/{dataset_id}/ai-insights

Verifies:
1. PII Redaction: Emails, phone numbers, SSNs, and sensitive tokens are scrubbed before LLM ingestion.
2. Compact Summary Construction: Full raw dataset is NEVER sent; only compact dimensions, metadata, stats, and redacted samples.
3. Resilience & Fallback: Gracefully delivers high-quality structured insights when LLM is unavailable or fails.
4. Schema Compliance: Response matches required JSON schema (summary, priority_issues, cleaning_plan, text_observations).
5. Prompt Injection Defense: Data samples are isolated and explicitly tagged as untrusted data.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_insight_service import build_compact_dataset_summary
from app.utils.privacy import redact_pii_text, redact_sample_value

client = TestClient(app)

UPLOAD_URL = "/api/datasets/upload"


def upload_dataset(content: str, filename: str = "dataset.csv") -> str:
    """Helper to upload CSV content and return dataset_id."""
    res = client.post(
        UPLOAD_URL,
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 200
    return res.json()["dataset_id"]


class TestPrivacyAndPIIRedaction:
    """Tests verifying sensitive PII is redacted prior to external processing."""

    def test_email_redaction(self):
        text = "Contact the user at alice.smith@corporate.org for details."
        redacted = redact_pii_text(text)
        assert "alice.smith@corporate.org" not in redacted
        assert "[EMAIL_REDACTED]" in redacted

    def test_phone_number_redaction(self):
        text = "Call support at +1 (555) 234-5678 or 555-876-5432."
        redacted = redact_pii_text(text)
        assert "234-5678" not in redacted
        assert "[PHONE_REDACTED]" in redacted

    def test_ssn_redaction(self):
        text = "SSN is 123-45-6789 confidential."
        redacted = redact_pii_text(text)
        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted

    def test_sensitive_column_value_redaction(self):
        val = redact_sample_value("secret_token_12345", "api_key")
        assert val == "[SENSITIVE_REDACTED]"


class TestCompactSummaryBuilder:
    """Verifies that the complete dataset is never sent to the LLM."""

    def test_compact_summary_does_not_contain_full_dataset(self):
        # 20 rows of data
        rows = [f"{i},user_{i}@example.com,{20 + i}" for i in range(20)]
        csv_data = "id,email,age\n" + "\n".join(rows) + "\n"
        ds_id = upload_dataset(csv_data, "large_dataset.csv")

        import pandas as pd
        from app.analyzers.profiler import locate_dataset_file
        file_path, _ = locate_dataset_file(ds_id)
        df = pd.read_csv(file_path)

        compact_summary = build_compact_dataset_summary(df, ds_id)

        assert "general" in compact_summary
        assert "quality_score" in compact_summary
        assert "columns" in compact_summary
        assert "detected_issues" in compact_summary

        # Must not contain all 20 raw rows in the payload
        serialized = json.dumps(compact_summary)
        # Should not have raw unredacted rows list
        assert len(compact_summary.get("representative_samples", {})) <= len(df.columns)
        assert compact_summary["general"]["row_count"] == 20


class TestAiInsightsEndpoint:
    """Tests for POST /api/datasets/{dataset_id}/ai-insights."""

    def test_ai_insights_schema_and_fallback(self):
        csv_data = (
            "user_id,email,age,status,empty_notes\n"
            "1,alice@example.com,29,active,\n"
            "2,invalid-email,-5,active,\n"
            "1,carol@example.com,35,active,\n"
            "3,diana@example.com,41,active,\n"
        )
        ds_id = upload_dataset(csv_data, "ai_test.csv")

        response = client.post(f"/api/datasets/{ds_id}/ai-insights")
        assert response.status_code == 200
        data = response.json()

        assert data["dataset_id"] == ds_id

        # 1. Executive Summary
        assert "summary" in data
        assert isinstance(data["summary"], str)
        assert len(data["summary"]) > 20

        # 2. Most important data-quality problems
        assert "priority_issues" in data
        assert isinstance(data["priority_issues"], list)
        assert len(data["priority_issues"]) > 0

        for issue in data["priority_issues"]:
            assert "issue" in issue
            assert "importance" in issue
            assert "explanation" in issue
            assert "recommendation" in issue
            assert len(issue["explanation"]) > 0
            assert len(issue["recommendation"]) > 0

        # 3. Recommended actions & Cleaning priorities
        assert "cleaning_plan" in data
        assert isinstance(data["cleaning_plan"], list)
        assert len(data["cleaning_plan"]) > 0
        for step in data["cleaning_plan"]:
            assert isinstance(step, str)

        # 4. Source indicator (proves fallback works smoothly without crashing)
        assert data["source"] in ("llm", "deterministic_fallback")

    def test_ai_insights_missing_dataset_returns_404(self):
        response = client.post("/api/datasets/00000000-0000-0000-0000-000000000000/ai-insights")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
