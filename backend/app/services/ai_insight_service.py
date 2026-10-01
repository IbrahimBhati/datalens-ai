"""
AI Insight Service.

Prepares compact, privacy-sanitized dataset summaries (never sends full raw datasets)
and orchestrates LLM interpretation for executive summaries, problem prioritization,
and cleaning sequences.
"""

from typing import Any, Dict, List
import pandas as pd

from app.analyzers.analyzer import analyze_dataset_quality
from app.analyzers.profiler import load_dataset_readonly, locate_dataset_file, profile_dataset
from app.models.ai_insights import AiInsightResponse
from app.services.llm_client import call_llm_for_insights
from app.services.scoring_service import compute_dataset_quality_score
from app.utils.privacy import redact_pii_text


def build_compact_dataset_summary(
    df: pd.DataFrame,
    dataset_id: str,
) -> Dict[str, Any]:
    """
    Build a compact, privacy-preserving structured summary for the LLM.
    Strictly avoids sending the complete raw dataset.
    """
    profile = profile_dataset(dataset_id)
    analysis = analyze_dataset_quality(dataset_id)
    score_resp = compute_dataset_quality_score(dataset_id)

    # 1. Dimensions
    general_summary = {
        "dataset_id": dataset_id,
        "row_count": profile.general.row_count,
        "column_count": profile.general.column_count,
        "file_format": profile.general.file_format,
        "memory_usage": profile.general.memory_usage_human,
    }

    # 2. Quality Scores
    score_summary = {
        "overall": score_resp.overall,
        "dimensions": score_resp.dimensions.model_dump(),
    }

    # 3. Compact Column Metadata & Stats
    columns_summary: List[Dict[str, Any]] = []
    for col in profile.columns:
        col_meta: Dict[str, Any] = {
            "name": col.name,
            "inferred_type": col.inferred_type,
            "null_percentage": col.null_percentage,
            "unique_count": col.unique_count,
        }
        if col.numeric_stats:
            col_meta["stats"] = {
                "min": col.numeric_stats.min,
                "max": col.numeric_stats.max,
                "mean": col.numeric_stats.mean,
                "median": col.numeric_stats.median,
            }
        elif col.text_stats:
            col_meta["stats"] = {
                "min_length": col.text_stats.min_length,
                "max_length": col.text_stats.max_length,
                "avg_length": col.text_stats.avg_length,
            }
        columns_summary.append(col_meta)

    # 4. Detected Quality Issues (ranked by severity)
    detected_issues = [
        {
            "type": issue.type,
            "severity": issue.severity,
            "column": issue.column,
            "affected_rows": issue.affected_rows,
            "percentage": issue.percentage,
            "description": issue.description,
        }
        for issue in analysis.issues
    ]

    # 5. Representative Sanitized Samples (Only for text anomaly columns, max 2 samples per column)
    text_issue_columns = {
        issue.column
        for issue in analysis.issues
        if issue.column and ("text" in issue.type or "whitespace" in issue.type)
    }

    representative_samples: Dict[str, List[str]] = {}
    for col_name in text_issue_columns:
        if col_name in df.columns:
            raw_samples = df[col_name].dropna().astype(str).head(2).tolist()
            # Redact all PII from samples
            representative_samples[col_name] = [redact_pii_text(s) for s in raw_samples]

    return {
        "general": general_summary,
        "quality_score": score_summary,
        "columns": columns_summary,
        "detected_issues": detected_issues,
        "representative_samples": representative_samples,
    }


async def generate_ai_insights(dataset_id: str) -> AiInsightResponse:
    """
    Main entry point for AI insights layer:
    1. Read dataset read-only
    2. Build compact, privacy-redacted summary (never sends full dataset)
    3. Invoke LLM client with timeout & injection protection
    4. Fall back seamlessly to deterministic engine if LLM fails or is unconfigured
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    df = load_dataset_readonly(file_path, fmt)

    compact_summary = build_compact_dataset_summary(df, dataset_id)
    return await call_llm_for_insights(dataset_id, compact_summary)
