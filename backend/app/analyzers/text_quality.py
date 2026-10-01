"""
Text quality and formatting anomaly analyzer.

Detects:
- Empty or near-empty text values (len <= 1)
- Extremely long text anomalies (> 500 chars or > 3 std devs above mean)
- Obvious repetitive placeholder text (e.g. 'aaaaa', 'test test test')
- Suspicious whitespace formatting problems (leading/trailing whitespace, multiple spaces, tab/newline pollution)
"""

import re
from typing import List
import numpy as np
import pandas as pd
from app.models.analysis import QualityIssue

# Single repeated character (e.g. "aaaaa", "?????", "-------")
REPEATED_CHAR_REGEX = re.compile(r"^(.)\1{4,}$")
# Repeated word sequence (e.g. "test test test")
REPEATED_WORD_REGEX = re.compile(r"\b(\w+)\b(?:\s+\1\b){2,}", re.IGNORECASE)


def detect_text_quality_issues(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Scans text columns for text formatting, length anomalies, and placeholder repetitions.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        # Only analyze text/object series
        if not (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)):
            continue

        non_null_strings = series.dropna().astype(str)
        non_null_count = len(non_null_strings)
        if non_null_count == 0:
            continue

        lengths = non_null_strings.str.len()
        mean_len = float(lengths.mean())
        std_len = float(lengths.std()) if non_null_count > 1 else 0.0

        # -----------------------------------------------------------------------
        # 1. Empty or Near-Empty Text (len <= 1, e.g. ".", "-", " ")
        # -----------------------------------------------------------------------
        stripped = non_null_strings.str.strip()
        near_empty_mask = stripped.str.len() <= 1
        near_empty_count = int(near_empty_mask.sum())
        # Only report if column isn't meant to be single char codes (mean_len > 3)
        if near_empty_count > 0 and mean_len > 3.0:
            pct = round((near_empty_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="near_empty_text",
                    severity="medium" if pct >= 5.0 else "low",
                    column=str(col),
                    affected_rows=near_empty_count,
                    percentage=pct,
                    description=f"Column '{col}' contains {near_empty_count} near-empty or single-character entry/entries ({pct}% of rows).",
                    method="Trimmed text length audit (length <= 1)",
                )
            )

        # -----------------------------------------------------------------------
        # 2. Extremely Long Values
        # -----------------------------------------------------------------------
        length_threshold = max(500, int(mean_len + 3 * std_len)) if std_len > 0 else 500
        extreme_long_mask = lengths >= length_threshold
        extreme_long_count = int(extreme_long_mask.sum())
        if extreme_long_count > 0:
            pct = round((extreme_long_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="extremely_long_text",
                    severity="medium",
                    column=str(col),
                    affected_rows=extreme_long_count,
                    percentage=pct,
                    description=f"Column '{col}' has {extreme_long_count} abnormally long string(s) exceeding {length_threshold} characters.",
                    method=f"Text length anomaly threshold (>= {length_threshold} chars)",
                )
            )

        # -----------------------------------------------------------------------
        # 3. Obvious Repetitive Placeholder Text
        # -----------------------------------------------------------------------
        def has_repetitive_text(val: str) -> bool:
            clean = val.strip()
            if len(clean) >= 5 and REPEATED_CHAR_REGEX.match(clean):
                return True
            if REPEATED_WORD_REGEX.search(clean):
                return True
            return False

        repeat_mask = non_null_strings.apply(has_repetitive_text)
        repeat_count = int(repeat_mask.sum())
        if repeat_count > 0:
            pct = round((repeat_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="repeated_text_anomaly",
                    severity="medium",
                    column=str(col),
                    affected_rows=repeat_count,
                    percentage=pct,
                    description=f"Column '{col}' contains {repeat_count} entry/entries with repeating placeholder characters or words.",
                    method="Repetitive character & repeated word regex inspection",
                )
            )

        # -----------------------------------------------------------------------
        # 4. Suspicious Whitespace and Formatting Problems
        # -----------------------------------------------------------------------
        def has_whitespace_problems(val: str) -> bool:
            # Leading or trailing whitespace
            if val != val.strip():
                return True
            # Multiple consecutive spaces
            if "  " in val:
                return True
            # Embedded newlines, carriage returns, or tab characters
            if "\n" in val or "\r" in val or "\t" in val:
                return True
            return False

        whitespace_mask = non_null_strings.apply(has_whitespace_problems)
        whitespace_count = int(whitespace_mask.sum())
        if whitespace_count > 0:
            pct = round((whitespace_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="whitespace_formatting_anomaly",
                    severity="low",
                    column=str(col),
                    affected_rows=whitespace_count,
                    percentage=pct,
                    description=f"Column '{col}' contains {whitespace_count} value(s) with unstripped whitespace, consecutive spaces, or control characters.",
                    method="Whitespace and control character audit",
                )
            )

    return issues
