"""
Dataset upload and storage service.

Handles:
- Validation (extensions, MIME types, empty files, size constraints)
- Path traversal prevention & safe filename generation
- Temporary file persistence
- Metadata extraction without running dataset analysis
"""

import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile, status

from app.config import (
    ALLOWED_EXTENSIONS,
    DATASET_RETENTION_HOURS,
    MAX_UPLOAD_SIZE,
    UPLOAD_DIR,
)
from app.models.dataset import DatasetUploadResponse

logger = logging.getLogger(__name__)

# Strict regex pattern for dataset identifiers
DATASET_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")

# MIME types commonly associated with CSV and JSON
ALLOWED_CSV_MIMES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "text/x-csv",
    "application/octet-stream",
}

ALLOWED_JSON_MIMES = {
    "application/json",
    "text/plain",
    "application/x-json",
    "application/octet-stream",
}

DISALLOWED_MIME_PREFIXES = (
    "application/x-msdownload",
    "application/x-sh",
    "application/x-executable",
    "application/x-dosexec",
    "application/javascript",
    "text/html",
    "image/",
    "video/",
    "audio/",
)


def ensure_upload_dir() -> Path:
    """Ensure upload storage directory exists with proper permissions."""
    path = Path(UPLOAD_DIR).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the user-provided filename to prevent path traversal and script injection.
    Strips directory separators, null bytes, and non-whitelisted characters.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )
    # Extract only the base name (prevents ../ or C:\ path traversal)
    clean_name = Path(filename.replace("\x00", "")).name
    stem = Path(clean_name).stem
    suffix = Path(clean_name).suffix.lower()

    # Retain only safe characters (alphanumeric, underscores, hyphens)
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem).strip("._")
    safe_suffix = re.sub(r"[^a-zA-Z0-9.]", "", suffix)

    if not safe_stem:
        safe_stem = "dataset"

    clean_name = f"{safe_stem}{safe_suffix}"
    if not clean_name or clean_name in (".", ".."):
        clean_name = "dataset"
    return clean_name


def delete_dataset(dataset_id: str) -> bool:
    """
    Safely delete a dataset file and its cleaned variant from temporary storage.
    Enforces strict identifier validation to prevent path traversal.
    """
    if not dataset_id or not DATASET_ID_REGEX.match(dataset_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dataset ID format.",
        )
    upload_dir = ensure_upload_dir()
    deleted_any = False

    # Match exact dataset files (e.g. {dataset_id}.csv, {dataset_id}.json, {dataset_id}_cleaned.csv)
    for p in upload_dir.iterdir():
        if p.is_file() and (p.name.startswith(f"{dataset_id}.") or p.name.startswith(f"{dataset_id}_cleaned.")):
            try:
                p.unlink()
                deleted_any = True
            except OSError as e:
                logger.error(f"Failed to delete dataset file {p.name}: {e}")

    return deleted_any


def cleanup_expired_datasets(max_age_hours: float | None = None) -> int:
    """
    Scans temporary upload directory and removes files older than max_age_hours.
    Returns the count of purged files.
    """
    if max_age_hours is None:
        max_age_hours = float(DATASET_RETENTION_HOURS)

    max_age_seconds = max_age_hours * 3600.0
    upload_dir = ensure_upload_dir()
    now = time.time()
    pruned_count = 0

    try:
        for p in upload_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                try:
                    mtime = p.stat().st_mtime
                    if now - mtime > max_age_seconds:
                        p.unlink()
                        pruned_count += 1
                except OSError:
                    pass
    except Exception as e:
        logger.error(f"Error during expired dataset cleanup: {e}")

    return pruned_count


def validate_file_metadata(filename: str, content_type: str | None) -> Tuple[str, str]:
    """
    Validate file extension and MIME type.
    Returns (normalized_ext, format_name).
    """
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Supported formats: {allowed}.",
        )

    fmt = ext.lstrip(".")

    # MIME type validation if provided
    if content_type:
        clean_mime = content_type.lower().split(";")[0].strip()

        # Reject dangerous/executable MIME types
        for blocked in DISALLOWED_MIME_PREFIXES:
            if clean_mime.startswith(blocked):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Disallowed MIME type '{clean_mime}'.",
                )

        if fmt == "csv" and clean_mime not in ALLOWED_CSV_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{clean_mime}' is not valid for CSV datasets.",
            )
        elif fmt == "json" and clean_mime not in ALLOWED_JSON_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{clean_mime}' is not valid for JSON datasets.",
            )

    return ext, fmt


def validate_content_integrity(contents: bytes, fmt: str) -> None:
    """
    Verify basic structural integrity of the file content without full analysis.
    """
    if fmt == "json":
        # Check if valid JSON or JSON Lines
        try:
            json.loads(contents.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            # Check JSON Lines
            try:
                lines = contents.decode("utf-8").strip().splitlines()
                if not lines:
                    raise ValueError("Empty lines")
                for line in lines[:10]:  # check first few lines
                    json.loads(line)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format. File could not be parsed as JSON or JSON Lines.",
                )
    elif fmt == "csv":
        try:
            # Must be decodable text
            sample = contents[:4096].decode("utf-8", errors="strict")
            if not sample.strip():
                raise ValueError("Empty CSV content")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file must be UTF-8 encoded text.",
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV format.",
            )


async def handle_dataset_upload(file: UploadFile) -> DatasetUploadResponse:
    """
    Full pipeline to receive, validate, safely store, and return metadata.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    safe_name = sanitize_filename(file.filename)
    ext, fmt = validate_file_metadata(safe_name, file.content_type)

    # Read content while checking size limit
    contents = await file.read()
    size_bytes = len(contents)

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if size_bytes > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {max_mb:.0f} MB (got {size_bytes / (1024 * 1024):.2f} MB).",
        )

    # Basic structural check
    validate_content_integrity(contents, fmt)

    # Generate server-side session/dataset ID
    dataset_id = str(uuid.uuid4())
    upload_dir = ensure_upload_dir()

    # Store with randomized UUID-based name (prevents traversal & collisions)
    server_filename = f"{dataset_id}{ext}"
    server_path = upload_dir / server_filename

    try:
        with open(server_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist dataset to temporary storage: {str(e)}",
        )

    return DatasetUploadResponse(
        dataset_id=dataset_id,
        filename=safe_name,
        format=fmt,
        size_bytes=size_bytes,
    )
