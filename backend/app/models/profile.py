"""
Pydantic models for deterministic dataset profiling.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class NumericStats(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    q25: Optional[float] = None
    q50: Optional[float] = None
    q75: Optional[float] = None


class TextStats(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None


class CategoricalValueFrequency(BaseModel):
    value: str
    count: int
    percentage: float


class CategoricalStats(BaseModel):
    top_values: List[CategoricalValueFrequency] = Field(default_factory=list)


class DateStats(BaseModel):
    is_date: bool = False
    confidence: float = 0.0
    detected_format: Optional[str] = None
    earliest: Optional[str] = None
    latest: Optional[str] = None


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    original_dtype: str
    non_null_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    numeric_stats: Optional[NumericStats] = None
    text_stats: Optional[TextStats] = None
    categorical_stats: Optional[CategoricalStats] = None
    date_stats: Optional[DateStats] = None


class GeneralProfile(BaseModel):
    dataset_id: str
    row_count: int
    column_count: int
    file_format: str
    memory_usage_bytes: int
    memory_usage_human: str


class DatasetProfileResponse(BaseModel):
    general: GeneralProfile
    columns: List[ColumnProfile]
