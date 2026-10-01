"""
Outlier detection analyzer using transparent statistical algorithms (IQR).

Detects:
- Numerical outliers exceeding 1.5 * IQR above Q3 or below Q1
"""

from typing import List
import pandas as pd
from app.models.analysis import QualityIssue


def detect_outliers(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect statistical outliers across all numeric columns using the standard IQR rule.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows < 4:
        return issues

    for col in df.columns:
        series = df[col]
        # Ignore boolean and non-numeric columns
        if pd.api.types.is_bool_dtype(series) or not pd.api.types.is_numeric_dtype(series):
            continue

        num_series = pd.to_numeric(series, errors="coerce").astype(float).dropna()
        if len(num_series) < 4:
            continue

        q25 = float(num_series.quantile(0.25))
        q75 = float(num_series.quantile(0.75))
        iqr = q75 - q25

        if iqr <= 0:
            continue

        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        outlier_mask = (num_series < lower_bound) | (num_series > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            pct = round((outlier_count / total_rows) * 100, 2)
            severity = "high" if pct >= 10.0 else "medium" if pct >= 3.0 else "low"

            issues.append(
                QualityIssue(
                    type="outliers",
                    severity=severity,
                    column=str(col),
                    affected_rows=outlier_count,
                    percentage=pct,
                    description=(
                        f"Column '{col}' has {outlier_count} statistical outlier(s) ({pct}% of rows) "
                        f"outside the bounds [{lower_bound:.2f}, {upper_bound:.2f}]."
                    ),
                    method="IQR (Tukey's Fences: Q1 - 1.5*IQR to Q3 + 1.5*IQR)",
                )
            )

    return issues
