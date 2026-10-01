"""
Data validation analyzer.

Detects:
- Malformed email addresses
- Impossible percentages (< 0 or > 100)
- Negative values where column represents a non-negative quantity
- Malformed phone numbers
- Invalid dates
- Constant columns (cardinality == 1)
- Low-variance / low-information columns (>= 99% single value or near-zero variance)
"""

import re
from typing import List
import numpy as np
import pandas as pd
from app.models.analysis import QualityIssue

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_ALLOWED_CHARS = re.compile(r"^[0-9\s\+\-\(\)\.]+$")

NON_NEGATIVE_KEYWORDS = (
    "age",
    "count",
    "quantity",
    "qty",
    "inventory",
    "price",
    "revenue",
    "salary",
    "duration",
    "size",
    "height",
    "weight",
    "distance",
    "items",
    "num_of",
)

LEGITIMATE_NEGATIVE_KEYWORDS = (
    "profit",
    "loss",
    "temperature",
    "delta",
    "change",
    "diff",
    "balance",
    "growth",
    "return",
    "net",
    "variance",
    "offset",
)


def _is_strictly_non_negative_column(col_name: str) -> bool:
    """Check if column name indicates a quantity that cannot realistically be negative."""
    col_lower = col_name.strip().lower()

    # Exclude metrics that can legitimately be negative
    for excluded in LEGITIMATE_NEGATIVE_KEYWORDS:
        if excluded in col_lower:
            return False

    # Check for non-negative semantics
    for keyword in NON_NEGATIVE_KEYWORDS:
        # Match whole word or prefix/suffix
        if re.search(rf"\b{keyword}\b", col_lower) or col_lower.endswith(f"_{keyword}") or col_lower.startswith(f"{keyword}_"):
            return True

    return False


def detect_invalid_values_and_constants(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Scans dataframe for domain validation failures, constant columns, and low-variance columns.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        col_str = str(col)
        col_lower = col_str.lower()
        non_null = series.dropna()
        non_null_count = len(non_null)

        if non_null_count == 0:
            continue

        # -----------------------------------------------------------------------
        # 1. Constant Columns (cardinality == 1)
        # -----------------------------------------------------------------------
        unique_count = non_null.nunique()
        if unique_count == 1 and non_null_count > 1:
            first_val = str(non_null.iloc[0])
            if len(first_val) > 40:
                first_val = first_val[:37] + "..."
            pct = round((non_null_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="constant_column",
                    severity="medium",
                    column=col_str,
                    affected_rows=non_null_count,
                    percentage=pct,
                    description=f"Column '{col_str}' is constant; every non-null row contains the identical value '{first_val}'.",
                    method="Cardinality check (unique_count == 1)",
                )
            )
            # Skip low-variance check if already marked constant
            continue

        # -----------------------------------------------------------------------
        # 2. Low-Variance / Low-Information Columns (>= 99% single value)
        # -----------------------------------------------------------------------
        if total_rows >= 20 and unique_count > 1:
            top_freq = non_null.value_counts().iloc[0]
            top_pct = round((top_freq / total_rows) * 100, 2)
            if top_pct >= 99.0:
                issues.append(
                    QualityIssue(
                        type="low_variance_column",
                        severity="low",
                        column=col_str,
                        affected_rows=int(top_freq),
                        percentage=top_pct,
                        description=f"Column '{col_str}' provides very little information ({top_pct}% of rows share the same dominant value).",
                        method="Dominant value frequency threshold (>= 99%)",
                    )
                )

        # -----------------------------------------------------------------------
        # 3. Malformed Email Addresses
        # -----------------------------------------------------------------------
        is_email_candidate = "email" in col_lower or (
            (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series))
            and non_null.astype(str).str.contains("@").mean() > 0.4
        )
        if is_email_candidate:
            str_vals = non_null.astype(str).str.strip()
            invalid_email_mask = ~str_vals.apply(lambda v: bool(EMAIL_REGEX.match(v)))
            invalid_email_count = int(invalid_email_mask.sum())
            if invalid_email_count > 0:
                pct = round((invalid_email_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        type="invalid_email",
                        severity="high",
                        column=col_str,
                        affected_rows=invalid_email_count,
                        percentage=pct,
                        description=f"Column '{col_str}' contains {invalid_email_count} malformed email address(es).",
                        method="Standard RFC email regex verification",
                    )
                )

        # -----------------------------------------------------------------------
        # 4. Impossible Percentages ([0, 100] violation)
        # -----------------------------------------------------------------------
        is_pct_col = any(k in col_lower for k in ("percent", "pct", "rate", "ratio", "%"))
        if is_pct_col and pd.api.types.is_numeric_dtype(series):
            num_series = pd.to_numeric(non_null, errors="coerce").dropna()
            # If values appear to be on a 0-100 scale, check for < 0 or > 100
            impossible_mask = (num_series < 0) | (num_series > 100)
            impossible_count = int(impossible_mask.sum())
            if impossible_count > 0:
                pct = round((impossible_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        type="impossible_percentage",
                        severity="high",
                        column=col_str,
                        affected_rows=impossible_count,
                        percentage=pct,
                        description=f"Column '{col_str}' contains {impossible_count} impossible percentage value(s) outside [0, 100].",
                        method="Percentage boundary check [0, 100]",
                    )
                )

        # -----------------------------------------------------------------------
        # 5. Negative Values in Strictly Non-Negative Quantities
        # -----------------------------------------------------------------------
        if _is_strictly_non_negative_column(col_str) and pd.api.types.is_numeric_dtype(series):
            num_series = pd.to_numeric(non_null, errors="coerce").dropna()
            neg_mask = num_series < 0
            neg_count = int(neg_mask.sum())
            if neg_count > 0:
                pct = round((neg_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        type="negative_value_violation",
                        severity="high",
                        column=col_str,
                        affected_rows=neg_count,
                        percentage=pct,
                        description=f"Column '{col_str}' represents a strictly non-negative quantity but contains {neg_count} negative value(s).",
                        method="Domain-specific non-negativity constraint",
                    )
                )

        # -----------------------------------------------------------------------
        # 6. Malformed Phone Numbers
        # -----------------------------------------------------------------------
        is_phone_candidate = any(k in col_lower for k in ("phone", "telephone", "mobile", "cell_number"))
        if is_phone_candidate and (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)):
            str_vals = non_null.astype(str).str.strip()

            def is_valid_phone(v: str) -> bool:
                if not PHONE_ALLOWED_CHARS.match(v):
                    return False
                digits = re.sub(r"\D", "", v)
                return 7 <= len(digits) <= 15

            invalid_phone_mask = ~str_vals.apply(is_valid_phone)
            invalid_phone_count = int(invalid_phone_mask.sum())
            if invalid_phone_count > 0:
                pct = round((invalid_phone_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        type="malformed_phone",
                        severity="medium",
                        column=col_str,
                        affected_rows=invalid_phone_count,
                        percentage=pct,
                        description=f"Column '{col_str}' contains {invalid_phone_count} malformed phone number(s) (invalid digits or illegal characters).",
                        method="Phone format and digit length check (7 to 15 digits)",
                    )
                )

        # -----------------------------------------------------------------------
        # 7. Invalid Dates (in date-like columns)
        # -----------------------------------------------------------------------
        is_date_col = any(k in col_lower for k in ("date", "time", "created_at", "updated_at", "timestamp", "dob"))
        if is_date_col and (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)):
            str_vals = non_null.astype(str).str.strip()
            parsed_dates = pd.to_datetime(str_vals, errors="coerce")
            unparseable_mask = parsed_dates.isna()

            # Also check for out-of-range calendar years (< 1800 or > 2150)
            valid_dates = parsed_dates.dropna()
            out_of_range_mask = pd.Series(False, index=str_vals.index)
            if not valid_dates.empty:
                out_of_range_idx = valid_dates[(valid_dates.dt.year < 1800) | (valid_dates.dt.year > 2150)].index
                out_of_range_mask.loc[out_of_range_idx] = True

            total_invalid_mask = unparseable_mask | out_of_range_mask
            invalid_date_count = int(total_invalid_mask.sum())

            # Only report if column predominantly appears to be dates (e.g. at least 50% parsed or explicit name)
            if invalid_date_count > 0 and (parsed_dates.notna().mean() >= 0.5 or "date" in col_lower):
                pct = round((invalid_date_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        type="invalid_date",
                        severity="high",
                        column=col_str,
                        affected_rows=invalid_date_count,
                        percentage=pct,
                        description=f"Column '{col_str}' contains {invalid_date_count} unparseable or out-of-range date value(s).",
                        method="Calendar date parsing and realistic year range check [1800, 2150]",
                    )
                )

    return issues
