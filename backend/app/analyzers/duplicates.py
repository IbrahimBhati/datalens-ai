"""
Duplicate detection analyzer.

Detects:
- Completely duplicate rows
- Duplicate values in likely identifier / key columns
- Duplicate records detected via normalized (case & whitespace trimmed) comparison
"""

import re
from typing import List
import pandas as pd
from app.models.analysis import QualityIssue

# Keywords commonly identifying primary keys or unique identifiers
IDENTIFIER_KEYWORDS = (
    "id",
    "uuid",
    "guid",
    "key",
    "code",
    "ssn",
    "email",
    "username",
    "account_number",
    "account_no",
    "token",
)


def _is_likely_identifier(col_name: str) -> bool:
    """Determine if a column name strongly implies unique identification."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "", col_name.strip().lower())
    if clean in IDENTIFIER_KEYWORDS:
        return True
    if clean.endswith(("_id", "_key", "_code", "_uuid", "_guid", "_pk")):
        return True
    if clean.startswith(("id_", "key_", "pk_")):
        return True
    return False


def detect_duplicates(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Scans for exact row duplicates, identifier collisions, and normalized row duplicates.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows <= 1:
        return issues

    # 1. Exact full-row duplicates
    exact_mask = df.duplicated(keep=False)
    exact_count = int(df.duplicated(keep="first").sum())
    exact_affected = int(exact_mask.sum())

    if exact_count > 0:
        pct = round((exact_affected / total_rows) * 100, 2)
        issues.append(
            QualityIssue(
                type="duplicate_rows",
                severity="high",
                column=None,
                affected_rows=exact_affected,
                percentage=pct,
                description=f"Found {exact_count} duplicate row(s) ({exact_affected} total rows involved in duplication).",
                method="Exact full-row comparison",
            )
        )

    # 2. Duplicate values in likely identifier columns
    for col in df.columns:
        if _is_likely_identifier(str(col)):
            series = df[col].dropna()
            if len(series) > 0:
                id_dup_mask = series.duplicated(keep=False)
                id_dup_count = int(id_dup_mask.sum())
                if id_dup_count > 0:
                    pct = round((id_dup_count / total_rows) * 100, 2)
                    issues.append(
                        QualityIssue(
                            type="duplicate_identifier",
                            severity="high",
                            column=str(col),
                            affected_rows=id_dup_count,
                            percentage=pct,
                            description=f"Likely identifier column '{col}' contains {id_dup_count} duplicate entry/entries ({pct}% of rows).",
                            method="Identifier uniqueness check",
                        )
                    )

    # 3. Normalized row duplicates (case-insensitive & whitespace-stripped comparison)
    # Only report if it discovers additional duplicates beyond the exact duplicates
    string_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_object_dtype(df[c])]
    if string_cols:
        norm_df = df.copy()
        for c in string_cols:
            norm_df[c] = norm_df[c].astype(str).str.strip().str.lower()

        norm_mask = norm_df.duplicated(keep=False)
        norm_count = int(norm_df.duplicated(keep="first").sum())
        norm_affected = int(norm_mask.sum())

        additional_dups = norm_count - exact_count
        additional_affected = norm_affected - exact_affected

        if additional_dups > 0 and additional_affected > 0:
            pct = round((additional_affected / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    type="normalized_duplicate_rows",
                    severity="medium",
                    column=None,
                    affected_rows=additional_affected,
                    percentage=pct,
                    description=f"Found {additional_dups} near-duplicate row(s) caused by subtle letter casing or whitespace inconsistencies.",
                    method="Normalized row comparison (lowercased & whitespace trimmed)",
                )
            )

    return issues
