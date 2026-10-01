"""
Pydantic models for deterministic data-quality issue detection and analysis.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    """Represents a single detected data quality issue."""

    type: str = Field(..., description="Category/type of issue, e.g. 'missing_values', 'duplicate_rows', 'invalid_email'")
    severity: str = Field(..., description="Issue severity: 'high', 'medium', or 'low'")
    column: Optional[str] = Field(None, description="Affected column name, or None if dataset-wide")
    affected_rows: int = Field(..., description="Count of affected rows")
    percentage: float = Field(..., description="Percentage of affected rows (0.0 to 100.0)")
    description: str = Field(..., description="Human-readable explanation of the detected problem")
    method: str = Field(..., description="Deterministic detection method or algorithm used")


class DatasetAnalysisResponse(BaseModel):
    """Response returned by POST /api/datasets/{dataset_id}/analyze."""

    dataset_id: str
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues: List[QualityIssue]
    analyzed_rows: int
    analyzed_columns: int
