"""
Deterministic Dataset Profiler Engine.

Analyzes dataset structure, column nullability, unique counts, distributions,
and statistics without using an LLM or modifying the original dataset file.
"""

import re
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
from fastapi import HTTPException, status

from app.analyzers.schema import detect_date_column, infer_column_type
from app.analyzers.statistics import (
    calculate_categorical_stats,
    calculate_numeric_stats,
    calculate_text_stats,
)
from app.config import ALLOWED_EXTENSIONS, UPLOAD_DIR
from app.models.profile import (
    ColumnProfile,
    DatasetProfileResponse,
    GeneralProfile,
)

DATASET_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def _format_bytes(num_bytes: int) -> str:
    """Format bytes into readable units."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.2f} MB"


def locate_dataset_file(dataset_id: str) -> Tuple[Path, str]:
    """
    Safely find the dataset file in temporary storage by ID.
    Enforces strict alphanumeric/UUID regex to prevent directory traversal or control injections.
    Returns (resolved_file_path, file_format).
    Raises 404 if not found or 400 if dataset_id contains invalid characters.
    """
    if not dataset_id or not DATASET_ID_REGEX.match(dataset_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dataset ID format. Must be an alphanumeric session identifier.",
        )

    upload_dir = Path(UPLOAD_DIR).resolve()

    for ext in ALLOWED_EXTENSIONS:
        candidate = upload_dir / f"{dataset_id}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate, ext.lstrip(".")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Dataset with ID '{dataset_id}' was not found in storage.",
    )


import json


def load_json_to_dataframe(file_path: Path) -> pd.DataFrame:
    """
    Universally parse a JSON file into a pandas DataFrame:
    1. Read with utf-8-sig (handles standard UTF-8 and Windows/Notepad BOM).
    2. Handle list of dicts (with json_normalize).
    3. Handle wrapped objects (e.g. {"data": [...]}, {"items": [...]}, {"results": [...]}, etc.).
    4. Handle dict-of-records (orient='index').
    5. Handle dict-of-lists (columnar).
    6. Handle single object (single row).
    7. Fallback to JSON Lines (NDJSON).
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        raw_text = f.read().strip()

    if not raw_text:
        return pd.DataFrame()

    try:
        data = json.loads(raw_text)
    except Exception:
        # Fallback to JSON Lines (NDJSON)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
        if records:
            return pd.json_normalize(records)
        raise ValueError("Could not parse file as valid JSON or JSON Lines format.")

    if isinstance(data, list):
        if not data:
            return pd.DataFrame()
        if isinstance(data[0], dict):
            return pd.json_normalize(data)
        return pd.DataFrame({"value": data})

    elif isinstance(data, dict):
        # Look for standard data collection wrapper keys
        for key in ["data", "items", "records", "results", "rows", "dataset", "features", "payload"]:
            if (
                key in data
                and isinstance(data[key], list)
                and len(data[key]) > 0
                and isinstance(data[key][0], dict)
            ):
                return pd.json_normalize(data[key])

        # Dict of records: {"r1": {"a": 1}, "r2": {"a": 2}}
        if data and all(isinstance(v, dict) for v in data.values()):
            return pd.DataFrame.from_dict(data, orient="index")

        # Column-oriented dict: {"col1": [1, 2], "col2": [3, 4]}
        if data and all(isinstance(v, list) for v in data.values()):
            try:
                return pd.DataFrame(data)
            except Exception:
                pass

        # Single record object: {"id": 1, "name": "..."}
        return pd.DataFrame([data])

    return pd.DataFrame()


def load_dataset_readonly(file_path: Path, fmt: str) -> pd.DataFrame:
    """
    Load a dataset strictly in read-only mode without mutating the source file.
    Supports CSV and universal JSON formats. Sanitizes nested dicts/lists to JSON strings
    so duplicate detection, grouping, and unique indexing operate without unhashable errors.
    """
    try:
        if fmt == "csv":
            df = pd.read_csv(file_path, low_memory=False)
        elif fmt == "json":
            df = load_json_to_dataframe(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{fmt}'.",
            )

        # Sanitize unhashable types (dict, list) in object columns
        for col in df.columns:
            if df[col].dtype == object or str(df[col].dtype) == "object":
                has_nested = df[col].apply(lambda x: isinstance(x, (dict, list))).any()
                if has_nested:
                    df[col] = df[col].apply(
                        lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)
                        if isinstance(x, (dict, list))
                        else x
                    )

        return df
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to read dataset file for profiling: {str(e)}",
        )



def profile_dataset(dataset_id: str) -> DatasetProfileResponse:
    """
    Main profiling pipeline:
    1. Locate dataset file
    2. Read dataset into memory
    3. Profile general dataset dimensions & memory
    4. Profile each column deterministically (schema, nulls, cardinality, stats)
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    df = load_dataset_readonly(file_path, fmt)

    row_count = len(df)
    col_count = len(df.columns)

    # Calculate memory footprint
    try:
        mem_bytes = int(df.memory_usage(deep=True).sum())
    except Exception:
        mem_bytes = int(df.memory_usage().sum())

    general = GeneralProfile(
        dataset_id=dataset_id,
        row_count=row_count,
        column_count=col_count,
        file_format=fmt,
        memory_usage_bytes=mem_bytes,
        memory_usage_human=_format_bytes(mem_bytes),
    )

    column_profiles = []

    for col in df.columns:
        series = df[col]
        non_null_count = int(series.notna().sum())
        null_count = int(series.isna().sum())
        null_pct = round((null_count / row_count * 100), 2) if row_count > 0 else 0.0

        unique_count = int(series.nunique(dropna=True))
        unique_pct = round((unique_count / row_count * 100), 2) if row_count > 0 else 0.0

        # Safe date detection
        date_stats = detect_date_column(series)

        # Inferred type
        inferred_type = infer_column_type(series, date_stats)
        orig_dtype = str(series.dtype)

        # Compute type-specific statistics
        numeric_stats = None
        text_stats = None
        categorical_stats = None

        if inferred_type == "numeric" and not pd.api.types.is_bool_dtype(series):
            numeric_stats = calculate_numeric_stats(series)

        if inferred_type in ("text", "categorical"):
            text_stats = calculate_text_stats(series)

        # Categorical distributions for categorical/boolean columns or low-cardinality columns
        if inferred_type in ("categorical", "boolean") or (unique_count > 0 and unique_count <= 25):
            categorical_stats = calculate_categorical_stats(series)

        column_profiles.append(
            ColumnProfile(
                name=str(col),
                inferred_type=inferred_type,
                original_dtype=orig_dtype,
                non_null_count=non_null_count,
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                unique_percentage=unique_pct,
                numeric_stats=numeric_stats,
                text_stats=text_stats,
                categorical_stats=categorical_stats,
                date_stats=date_stats if date_stats.is_date else None,
            )
        )

    return DatasetProfileResponse(
        general=general,
        columns=column_profiles,
    )
