"""
Missing values detector.

Detects:
- Completely empty columns (100% null)
- Columns with unusually high missing percentages (>= 20% or >= 50%)
- Columns with missing cells
"""

from typing import List
import pandas as pd
from app.models.analysis import QualityIssue


def detect_missing_values(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Scans dataframe columns for missing values, elevated null rates, and completely empty columns.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        # Count standard nulls (NaN, None)
        null_count = int(series.isna().sum())

        # If object/string, also check for whitespace-only strings
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            whitespace_only = series.dropna().astype(str).str.strip() == ""
            null_count += int(whitespace_only.sum())

        if null_count == 0:
            continue

        pct = round((null_count / total_rows) * 100, 2)

        if null_count == total_rows:
            issues.append(
                QualityIssue(
                    type="empty_column",
                    severity="high",
                    column=str(col),
                    affected_rows=null_count,
                    percentage=100.0,
                    description=f"Column '{col}' is completely empty (100% missing values).",
                    method="Total null count verification",
                )
            )
        elif pct >= 50.0:
            issues.append(
                QualityIssue(
                    type="high_missing_percentage",
                    severity="high",
                    column=str(col),
                    affected_rows=null_count,
                    percentage=pct,
                    description=f"Column '{col}' has a critically high missing rate ({pct}% of rows are null).",
                    method="Null rate threshold (>= 50%)",
                )
            )
        elif pct >= 20.0:
            issues.append(
                QualityIssue(
                    type="high_missing_percentage",
                    severity="medium",
                    column=str(col),
                    affected_rows=null_count,
                    percentage=pct,
                    description=f"Column '{col}' has an elevated missing rate ({pct}% of rows are null).",
                    method="Null rate threshold (>= 20%)",
                )
            )
        else:
            issues.append(
                QualityIssue(
                    type="missing_values",
                    severity="low",
                    column=str(col),
                    affected_rows=null_count,
                    percentage=pct,
                    description=f"Column '{col}' contains {null_count} missing value(s) ({pct}%).",
                    method="Null cell check",
                )
            )

    return issues
