"""
Pydantic models for the AI dataset quality insight layer.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PriorityIssue(BaseModel):
    """Specific high-priority dataset quality problem identified by AI interpretation."""

    issue: str = Field(..., description="Short name or category of the priority issue")
    importance: str = Field(..., description="Severity or business importance, e.g. 'High', 'Critical', 'Medium'")
    explanation: str = Field(..., description="Contextual explanation of why this problem matters for downstream analytics/ML")
    recommendation: str = Field(..., description="Concrete, actionable remediation advice")


class AiInsightResponse(BaseModel):
    """Structured AI-generated insights and recommendations."""

    dataset_id: str = Field(..., description="Dataset session identifier")
    summary: str = Field(..., description="Executive summary of the dataset quality and fitness for purpose")
    priority_issues: List[PriorityIssue] = Field(..., description="Ranked list of the most critical quality problems")
    cleaning_plan: List[str] = Field(..., description="Actionable, step-by-step cleaning sequence and remediation plan")
    text_observations: Optional[List[str]] = Field(default_factory=list, description="Observations regarding text column health, formatting, or NLP readiness")
    source: str = Field(default="llm", description="Origin of insights: 'llm' or 'deterministic_fallback'")

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "summary": "The customer dataset displays fair structural consistency (Score: 78/100) but suffers from high missingness in contact information and duplicate customer entries that could skew downstream analytics.",
                "priority_issues": [
                    {
                        "issue": "Duplicate Customer Records",
                        "importance": "High",
                        "explanation": "Multiple identical user rows inflate customer counts and will bias conversion rate models.",
                        "recommendation": "Deduplicate based on primary key user_id keeping the latest timestamp."
                    }
                ],
                "cleaning_plan": [
                    "Step 1: Remove exact duplicate rows across all fields.",
                    "Step 2: Impute or flag missing values in email and address columns.",
                    "Step 3: Strip extraneous whitespace from categorical text fields."
                ],
                "text_observations": [
                    "Column 'notes' has high trailing whitespace and several single-character placeholders."
                ],
                "source": "llm"
            }
        }
    }
