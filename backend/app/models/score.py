"""
Pydantic models for dataset quality scoring and dimension breakdowns.
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class QualityDimensions(BaseModel):
    """Quality scores across core dimensions (0 to 100)."""

    completeness: int = Field(..., ge=0, le=100, description="Completeness score (0-100)")
    validity: int = Field(..., ge=0, le=100, description="Validity score (0-100)")
    uniqueness: int = Field(..., ge=0, le=100, description="Uniqueness score (0-100)")
    consistency: int = Field(..., ge=0, le=100, description="Consistency score (0-100)")


class QualityScoreResponse(BaseModel):
    """Overall quality score, dimension breakdown, and deterministic explanations."""

    overall: int = Field(..., ge=0, le=100, description="Overall weighted quality score (0-100)")
    dimensions: QualityDimensions
    explanation: List[str] = Field(default_factory=list, description="List of explanations detailing how issues affected each dimension")

    model_config = {
        "json_schema_extra": {
            "example": {
                "overall": 78,
                "dimensions": {
                    "completeness": 82,
                    "validity": 76,
                    "uniqueness": 91,
                    "consistency": 73,
                },
                "explanation": [
                    "Completeness (82/100): Deducted 18 pts for missing values across 2 columns.",
                    "Validity (76/100): Deducted 24 pts due to 1 malformed email and 1 negative age value.",
                    "Uniqueness (91/100): Deducted 9 pts due to 1 duplicate identifier in column 'user_id'.",
                    "Consistency (73/100): Deducted 27 pts due to constant column 'country' and 2 statistical outliers.",
                ],
            }
        }
    }
