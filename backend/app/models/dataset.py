"""
Pydantic models for dataset upload and metadata.
"""

from pydantic import BaseModel, Field


class DatasetUploadResponse(BaseModel):
    """Metadata response returned upon successful dataset upload."""

    dataset_id: str = Field(..., description="Unique UUID assigned to the uploaded dataset")
    filename: str = Field(..., description="Original filename without path traversal characters")
    format: str = Field(..., description="Detected and validated format ('csv' or 'json')")
    size_bytes: int = Field(..., description="File size in bytes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "filename": "customers.csv",
                "format": "csv",
                "size_bytes": 123456,
            }
        }
    }
