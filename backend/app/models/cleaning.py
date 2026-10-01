"""
Pydantic models for dataset cleaning operations and transformation audits.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TransformationRecord(BaseModel):
    """Details of a single non-destructive transformation executed on the dataset."""

    type: str = Field(..., description="Machine-readable transformation type key, e.g. 'remove_duplicates', 'trim_whitespace'")
    description: str = Field(..., description="Human-readable explanation of what was changed")
    affected_rows: int = Field(default=0, ge=0, description="Count of rows affected by this transformation")
    cells_modified: int = Field(default=0, ge=0, description="Total individual cell values modified")
    affected_columns: Optional[List[str]] = Field(default=None, description="List of columns impacted, or None if dataset-wide")


class CleanDatasetResponse(BaseModel):
    """Response returned by POST /api/datasets/{dataset_id}/clean."""

    dataset_id: str = Field(..., description="Dataset session identifier")
    cleaned_filename: str = Field(..., description="Filename of the saved cleaned dataset")
    download_url: str = Field(..., description="Direct API URL path to download the cleaned file")
    original_rows: int = Field(..., ge=0, description="Row count of the original dataset")
    cleaned_rows: int = Field(..., ge=0, description="Row count of the cleaned dataset after deduplication")
    rows_removed: int = Field(..., ge=0, description="Total rows removed (e.g. exact duplicates)")
    cells_modified: int = Field(..., ge=0, description="Total individual cells normalized or updated")
    transformations_performed: List[TransformationRecord] = Field(default_factory=list, description="Audit trail of all executed cleaning steps")
    warnings: List[str] = Field(default_factory=list, description="Advisories for ambiguous or risky issues preserved without automatic modification")

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "cleaned_filename": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d_cleaned.csv",
                "download_url": "/api/datasets/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/download-cleaned",
                "original_rows": 100,
                "cleaned_rows": 98,
                "rows_removed": 2,
                "cells_modified": 18,
                "transformations_performed": [
                    {
                        "type": "remove_duplicates",
                        "description": "Removed 2 exact duplicate row(s)",
                        "affected_rows": 2,
                        "cells_modified": 0,
                        "affected_columns": None,
                    },
                    {
                        "type": "trim_whitespace",
                        "description": "Trimmed leading/trailing whitespace across 2 column(s) (12 cells)",
                        "affected_rows": 10,
                        "cells_modified": 12,
                        "affected_columns": ["name", "country"],
                    },
                    {
                        "type": "standardize_missing",
                        "description": "Standardized 'N/A' and empty placeholders to null in column 'notes' (6 cells)",
                        "affected_rows": 6,
                        "cells_modified": 6,
                        "affected_columns": ["notes"],
                    },
                ],
                "warnings": [
                    "Preserved 1 negative value in column 'age'. Manual domain validation recommended.",
                    "Preserved 1 malformed email in column 'email' to prevent destructive data loss.",
                ],
            }
        }
    }
