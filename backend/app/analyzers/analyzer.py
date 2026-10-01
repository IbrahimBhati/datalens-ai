"""
Deterministic Data-Quality Analysis Engine.

Orchestrates all modular quality detectors:
- Missing values & empty columns
- Exact duplicates, identifier duplicates, normalized duplicates
- Invalid values (emails, percentages, non-negative quantities, phones, dates)
- Constant & low-variance columns
- Statistical outliers (IQR)
- Text quality (near-empty, long strings, repetitions, whitespace anomalies)
"""

from typing import Dict, List
import pandas as pd

from app.analyzers.duplicates import detect_duplicates
from app.analyzers.missing_values import detect_missing_values
from app.analyzers.outliers import detect_outliers
from app.analyzers.profiler import load_dataset_readonly, locate_dataset_file
from app.analyzers.text_quality import detect_text_quality_issues
from app.analyzers.validation import detect_invalid_values_and_constants
from app.models.analysis import DatasetAnalysisResponse, QualityIssue


def analyze_dataset_quality(dataset_id: str) -> DatasetAnalysisResponse:
    """
    Executes all deterministic data-quality checks on the dataset.
    Does not use an LLM or modify the underlying dataset file.
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    df = load_dataset_readonly(file_path, fmt)

    issues: List[QualityIssue] = []

    # 1. Missing Values & Empty Columns
    issues.extend(detect_missing_values(df))

    # 2. Duplicates (rows, identifiers, normalized rows)
    issues.extend(detect_duplicates(df))

    # 3. Invalid Values, Constants, and Low-Variance
    issues.extend(detect_invalid_values_and_constants(df))

    # 4. Statistical Outliers
    issues.extend(detect_outliers(df))

    # 5. Text Quality & Formatting Anomalies
    issues.extend(detect_text_quality_issues(df))

    # Aggregate counts by severity
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        sev = issue.severity.lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
        else:
            severity_counts[sev] = 1

    return DatasetAnalysisResponse(
        dataset_id=dataset_id,
        total_issues=len(issues),
        issues_by_severity=severity_counts,
        issues=issues,
        analyzed_rows=len(df),
        analyzed_columns=len(df.columns),
    )
