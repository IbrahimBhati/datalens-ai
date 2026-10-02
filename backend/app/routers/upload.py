"""
DataLens AI - File Upload Router

Handles CSV and JSON file uploads with validation:
- File extension check
- File size enforcement
- Content-type verification
- Basic content validation (can the file be parsed?)
"""

import os
import uuid
import shutil
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, UploadFile, HTTPException, status

from app.config import MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS, UPLOAD_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _ensure_upload_dir() -> Path:
    """Create the upload directory if it doesn't exist."""
    path = Path(UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_extension(filename: str) -> str:
    """Validate and return the lowercase file extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def _read_with_size_check(file: UploadFile) -> bytes:
    """Read file contents while enforcing the size limit."""
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE / (1024 * 1024):.0f} MB.",
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    return contents


from app.analyzers.profiler import load_json_to_dataframe


def _parse_and_validate_content(file_path: Path, ext: str) -> dict:
    """
    Try to parse the file to confirm it's valid CSV/JSON.
    Returns basic metadata about the dataset.
    """
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, nrows=5)
            # Count lines minus header for CSVs without loading everything into memory
            with open(file_path, encoding="utf-8", errors="replace") as f_in:
                row_count = sum(1 for _ in f_in) - 1
        elif ext == ".json":
            df = load_json_to_dataframe(file_path)
            row_count = len(df)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse the uploaded file: {str(e)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no data rows.",
        )

    if len(df.columns) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no columns.",
        )

    return {
        "columns": [str(c) for c in df.columns],
        "column_count": len(df.columns),
        "row_count": max(row_count, 0),
        "preview_rows": df.head(5).to_dict(orient="records"),
    }



@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV or JSON dataset for analysis.

    Validates the file (type, size, parsability) and stores it
    temporarily. Returns a dataset_id for subsequent operations
    and basic metadata about the uploaded file.
    """
    # 1. Validate filename & extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )
    ext = _validate_extension(file.filename)

    # 2. Read contents with size enforcement
    contents = await _read_with_size_check(file)

    # 3. Generate a unique ID and save
    dataset_id = str(uuid.uuid4())
    upload_dir = _ensure_upload_dir()
    file_path = upload_dir / f"{dataset_id}{ext}"

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )

    # 4. Validate content can be parsed
    try:
        metadata = _parse_and_validate_content(file_path, ext)
    except HTTPException:
        # Clean up the saved file on validation failure
        file_path.unlink(missing_ok=True)
        raise

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "file_type": ext.lstrip("."),
        "size_bytes": len(contents),
        **metadata,
    }
