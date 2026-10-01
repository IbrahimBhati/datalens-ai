"""
Dataset API routes.

Provides:
- POST /api/datasets/upload
- POST /api/datasets/{dataset_id}/profile
- POST /api/datasets/{dataset_id}/analyze
- POST /api/datasets/{dataset_id}/score
- POST /api/datasets/{dataset_id}/ai-insights
"""

from pathlib import Path as FilePath

from fastapi import APIRouter, File, HTTPException, Path, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse

from app.analyzers.analyzer import analyze_dataset_quality
from app.analyzers.profiler import locate_dataset_file, profile_dataset
from app.config import UPLOAD_DIR
from app.models.ai_insights import AiInsightResponse
from app.models.analysis import DatasetAnalysisResponse
from app.models.cleaning import CleanDatasetResponse
from app.models.dataset import DatasetUploadResponse
from app.models.profile import DatasetProfileResponse
from app.models.score import QualityScoreResponse
from app.services.ai_insight_service import generate_ai_insights
from app.services.cleaning_service import clean_dataset
from app.services.dataset_service import delete_dataset, handle_dataset_upload
from app.services.report_service import generate_html_report, generate_pdf_report
from app.services.scoring_service import compute_dataset_quality_score

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload dataset file",
    description="Validates and safely stores a CSV or JSON dataset in temporary storage and returns metadata.",
)
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset file (CSV or JSON format, max 50MB)")
) -> DatasetUploadResponse:
    """
    1. Receive the uploaded file
    2. Validate it (extension, MIME, size, parsability)
    3. Save it to temporary storage with a safe server-side filename
    4. Assign a dataset/session ID
    5. Return metadata (dataset_id, filename, format, size_bytes)
    """
    return await handle_dataset_upload(file)


@router.post(
    "/{dataset_id}/profile",
    response_model=DatasetProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Profile dataset",
    description="Deterministically analyzes dataset structure, column nullability, unique counts, distributions, and statistics without using an LLM.",
)
async def profile_dataset_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> DatasetProfileResponse:
    """
    1. Retrieve the dataset file from temporary storage
    2. Read data without modifying the source file
    3. Calculate general metrics (row count, column count, format, memory)
    4. Profile each column (types, nulls, uniqueness, numeric stats, text stats, distributions, date detection)
    5. Return structured JSON profile
    """
    return profile_dataset(dataset_id)


@router.post(
    "/{dataset_id}/analyze",
    response_model=DatasetAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze dataset quality",
    description="Deterministically detects missing values, duplicates, invalid values, constants, low variance, outliers, and text quality issues without using an LLM.",
)
async def analyze_dataset_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> DatasetAnalysisResponse:
    """
    Execute all deterministic data-quality checks on the dataset.
    """
    return analyze_dataset_quality(dataset_id)


@router.post(
    "/{dataset_id}/score",
    response_model=QualityScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate dataset quality score",
    description="Calculates a transparent, deterministic quality score (0-100) across completeness, validity, uniqueness, and consistency.",
)
async def score_dataset_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> QualityScoreResponse:
    """
    Compute overall quality score, dimension breakdown, and deterministic explanations.
    """
    return compute_dataset_quality_score(dataset_id)


@router.post(
    "/{dataset_id}/ai-insights",
    response_model=AiInsightResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI dataset quality insights",
    description="Uses an LLM on compact, privacy-redacted summaries to generate an executive summary, prioritized quality problems, and a recommended cleaning plan.",
)
async def ai_insights_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> AiInsightResponse:
    """
    1. Prepare compact privacy-scrubbed summary (never sends full raw dataset)
    2. Request LLM interpretation with timeout & prompt injection defenses
    3. Return structured JSON insights or graceful deterministic fallback
    """
    return await generate_ai_insights(dataset_id)


@router.post(
    "/{dataset_id}/clean",
    response_model=CleanDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Clean dataset safely",
    description="Performs non-destructive, safe cleaning operations: removes exact duplicates, trims whitespace, normalizes formatting, and standardizes missing-value placeholders. Persists a separate cleaned file without modifying the original.",
)
async def clean_dataset_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> CleanDatasetResponse:
    """
    Execute non-destructive dataset cleaning pipeline.
    Never overwrites original file.
    """
    return clean_dataset(dataset_id)


@router.get(
    "/{dataset_id}/download-cleaned",
    status_code=status.HTTP_200_OK,
    summary="Download cleaned dataset",
    description="Streams the cleaned dataset file as an attachment download.",
)
async def download_cleaned_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> FileResponse:
    """
    Download the generated cleaned dataset file.
    """
    orig_path, fmt = locate_dataset_file(dataset_id)
    upload_dir = FilePath(UPLOAD_DIR).resolve()
    cleaned_path = upload_dir / f"{dataset_id}_cleaned.{fmt}"

    if not cleaned_path.exists() or not cleaned_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cleaned dataset not found. Please run the clean endpoint first.",
        )

    # Use friendly download name
    download_filename = f"cleaned_{orig_path.stem}.{fmt}"
    media_type = "text/csv" if fmt == "csv" else "application/json"

    return FileResponse(
        path=cleaned_path,
        filename=download_filename,
        media_type=media_type,
    )


@router.get(
    "/{dataset_id}/report/html",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="Get printable HTML dataset quality report",
    description="Renders a complete, print-friendly 12-section dataset quality report with embedded print CSS.",
)
async def get_html_report_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> HTMLResponse:
    """
    Renders standalone print-friendly HTML quality audit report.
    """
    html_content = await generate_html_report(dataset_id)
    return HTMLResponse(content=html_content, status_code=200)


@router.get(
    "/{dataset_id}/report/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download PDF dataset quality report",
    description="Generates and streams a professional multi-page PDF quality report via ReportLab.",
)
async def get_pdf_report_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> Response:
    """
    Generates and returns professional vector PDF report.
    """
    orig_path, _ = locate_dataset_file(dataset_id)
    pdf_bytes = await generate_pdf_report(dataset_id)

    download_filename = f"DataLens_Quality_Report_{orig_path.stem}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        },
    )


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete temporary dataset",
    description="Deletes the uploaded dataset and any generated cleaned variants from server temporary storage immediately.",
)
async def delete_dataset_endpoint(
    dataset_id: str = Path(..., description="Unique dataset UUID returned during upload")
) -> dict:
    """
    Explicit user-initiated dataset purge.
    Removes raw and cleaned files from disk immediately.
    """
    deleted = delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found or already deleted.",
        )
    return {
        "status": "success",
        "message": f"Dataset '{dataset_id}' deleted successfully.",
        "dataset_id": dataset_id,
    }


