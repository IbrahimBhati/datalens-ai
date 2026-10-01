"""
Statistical calculation module for dataset profiling.

Computes:
- Numeric metrics (min, max, mean, median, standard deviation, quartiles)
- Text metrics (min_length, max_length, avg_length)
- Categorical distributions (top values, counts, frequencies)
"""

import math
from typing import Optional
import numpy as np
import pandas as pd

from app.models.profile import (
    CategoricalStats,
    CategoricalValueFrequency,
    NumericStats,
    TextStats,
)


def _clean_number(val: Optional[float]) -> Optional[float]:
    """Helper to convert NaN, Inf, or numpy floats to clean Python floats or None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def calculate_numeric_stats(series: pd.Series) -> Optional[NumericStats]:
    """
    Calculate summary statistics for numeric series:
    minimum, maximum, mean, median, standard deviation, and quartiles (25%, 50%, 75%).
    """
    if pd.api.types.is_bool_dtype(series):
        return None

    try:
        numeric_series = pd.to_numeric(series, errors="coerce").astype(float).dropna()
    except Exception:
        return None

    if numeric_series.empty:
        return None

    std_val = numeric_series.std() if len(numeric_series) > 1 else None

    return NumericStats(
        min=_clean_number(numeric_series.min()),
        max=_clean_number(numeric_series.max()),
        mean=_clean_number(numeric_series.mean()),
        median=_clean_number(numeric_series.median()),
        std=_clean_number(std_val),
        q25=_clean_number(numeric_series.quantile(0.25)),
        q50=_clean_number(numeric_series.quantile(0.50)),
        q75=_clean_number(numeric_series.quantile(0.75)),
    )


def calculate_text_stats(series: pd.Series) -> Optional[TextStats]:
    """
    Calculate text metrics for string/text series:
    minimum text length, maximum text length, and average text length.
    """
    non_null_strings = series.dropna().astype(str)
    if non_null_strings.empty:
        return None

    lengths = non_null_strings.str.len()
    return TextStats(
        min_length=int(lengths.min()),
        max_length=int(lengths.max()),
        avg_length=round(float(lengths.mean()), 2),
    )


def calculate_categorical_stats(series: pd.Series, top_n: int = 10) -> Optional[CategoricalStats]:
    """
    Calculate value frequencies for categorical/discrete series:
    top values, counts, and percentage of non-null rows.
    """
    non_null = series.dropna().astype(str)
    total = len(non_null)
    if total == 0:
        return None

    counts = non_null.value_counts().head(top_n)
    top_values = [
        CategoricalValueFrequency(
            value=str(val),
            count=int(cnt),
            percentage=round(float(cnt / total * 100), 2),
        )
        for val, cnt in counts.items()
    ]

    return CategoricalStats(top_values=top_values)
