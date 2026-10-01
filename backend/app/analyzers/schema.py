"""
Schema and type inference analyzer.

Determines:
- Inferred high-level data types: numeric, text, boolean, datetime, categorical
- Safe date detection with confidence score (does not aggressively convert ambiguous numbers)
"""

import re
from typing import Tuple
import pandas as pd
from app.models.profile import DateStats

# Regular expressions for common date patterns
ISO_DATE_REGEX = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$")
SLASH_DATE_REGEX = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$")
MONTH_NAME_DATE_REGEX = re.compile(r"^(?:\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})")


def detect_date_column(series: pd.Series) -> DateStats:
    """
    Safely detect whether a series represents dates or timestamps.
    Reports confidence and earliest/latest dates without mutating the series.
    Guards against converting ambiguous numeric values (e.g. 2024, 42).
    """
    # 1. Native pandas datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        non_null = series.dropna()
        if non_null.empty:
            return DateStats(is_date=True, confidence=1.0, detected_format="datetime64")
        return DateStats(
            is_date=True,
            confidence=1.0,
            detected_format="datetime64",
            earliest=str(non_null.min()),
            latest=str(non_null.max()),
        )

    # 2. Reject numeric types to prevent aggressive conversion of ints/floats to epoch
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return DateStats(is_date=False, confidence=0.0)

    # 3. String / Object series inspection
    non_null_strings = series.dropna().astype(str).str.strip()
    if non_null_strings.empty:
        return DateStats(is_date=False, confidence=0.0)

    # Sample up to 100 values for performance and safety
    sample = non_null_strings.head(100)
    sample_size = len(sample)

    # Check if all values are just plain numbers without delimiters (e.g. "2024", "123")
    pure_numbers = sum(bool(re.match(r"^\d{1,6}$", val)) for val in sample)
    if pure_numbers / sample_size > 0.3:
        # Ambiguous numbers or IDs - do NOT treat as dates
        return DateStats(is_date=False, confidence=0.0)

    # Count pattern matches
    iso_matches = sum(bool(ISO_DATE_REGEX.match(val)) for val in sample)
    slash_matches = sum(bool(SLASH_DATE_REGEX.match(val)) for val in sample)
    month_matches = sum(bool(MONTH_NAME_DATE_REGEX.match(val)) for val in sample)

    detected_format = None
    if iso_matches / sample_size >= 0.8:
        detected_format = "ISO 8601 (YYYY-MM-DD)"
    elif slash_matches / sample_size >= 0.8:
        detected_format = "Delimited Date (MM/DD/YYYY or DD/MM/YYYY)"
    elif month_matches / sample_size >= 0.8:
        detected_format = "Named Month Date"

    if detected_format is None and (iso_matches + slash_matches + month_matches) / sample_size < 0.7:
        return DateStats(is_date=False, confidence=0.0)

    # Attempt parsing with pandas to verify valid calendar dates (e.g. not 99/99/9999)
    try:
        parsed = pd.to_datetime(sample, errors="coerce")
        valid_count = parsed.notna().sum()
        ratio = valid_count / sample_size

        if ratio >= 0.9:
            # Check reasonable year boundaries (1800 - 2100)
            valid_years = parsed.dropna().dt.year
            if ((valid_years >= 1800) & (valid_years <= 2100)).all():
                earliest_str = str(parsed.dropna().min())
                latest_str = str(parsed.dropna().max())
                confidence = round(float(ratio), 2)
                return DateStats(
                    is_date=True,
                    confidence=confidence,
                    detected_format=detected_format or "Standard Date",
                    earliest=earliest_str,
                    latest=latest_str,
                )
    except Exception:
        pass

    return DateStats(is_date=False, confidence=0.0)


def infer_column_type(series: pd.Series, date_stats: DateStats) -> str:
    """
    Infer the business/analytical data type of a column.
    Possible return values: 'numeric', 'datetime', 'boolean', 'categorical', 'text'.
    """
    # 1. Datetime
    if date_stats.is_date and date_stats.confidence >= 0.85:
        return "datetime"

    # 2. Boolean
    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    # Check for boolean-like text (e.g., True/False, Yes/No, 0/1 strings)
    non_null = series.dropna()
    if not non_null.empty:
        unique_vals = set(non_null.astype(str).str.lower().unique())
        if unique_vals in ({"true", "false"}, {"yes", "no"}, {"y", "n"}, {"t", "f"}):
            return "boolean"

    # 3. Numeric
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # 4. Categorical vs Text
    unique_count = len(non_null.unique())
    total_count = len(non_null)

    if total_count > 0:
        # If low cardinality (20 or fewer unique values, or <= 5% unique for larger sets)
        if unique_count <= 20 or (total_count > 50 and (unique_count / total_count) <= 0.05):
            return "categorical"

    return "text"
