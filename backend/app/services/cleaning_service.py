"""
Dataset cleaning service.

Executes safe, non-destructive transformations on an uploaded dataset:
- Deduplicates exact duplicate rows
- Trims extraneous whitespace from text cells
- Normalizes obvious formatting inconsistencies (internal multi-space collapsing, email lowercasing)
- Standardizes confidently identifiable missing-value placeholders to standard null
- Preserves ambiguous anomalies (outliers, invalid emails, negative ages) with clear recommendations
- NEVER overwrites the original dataset file — persists to a separate cleaned file
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
from fastapi import HTTPException, status

from app.analyzers.profiler import load_dataset_readonly, locate_dataset_file
from app.config import UPLOAD_DIR
from app.models.cleaning import CleanDatasetResponse, TransformationRecord

# Confidently identifiable missing placeholder tokens (compared case-insensitively when stripped)
CONFIDENT_NULL_STRINGS: Set[str] = {
    "",
    "n/a",
    "na",
    "null",
    "none",
    "nan",
    "-",
    "--",
    "nil",
    "undefined",
    "#n/a",
    "?",
}


def clean_dataset(dataset_id: str) -> CleanDatasetResponse:
    """
    Execute deterministic, non-destructive cleaning pipeline on the dataset.
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    raw_df = load_dataset_readonly(file_path, fmt)

    # Work on a copy so the original dataset is never mutated in memory or on disk
    df = raw_df.copy()
    original_rows = len(df)

    transformations: List[TransformationRecord] = []
    warnings: List[str] = []
    total_cells_modified = 0

    # -------------------------------------------------------------
    # 1. REMOVE EXACT DUPLICATE ROWS
    # -------------------------------------------------------------
    duplicate_mask = df.duplicated(keep="first")
    num_duplicates = int(duplicate_mask.sum())

    if num_duplicates > 0:
        df = df[~duplicate_mask].reset_index(drop=True)
        transformations.append(
            TransformationRecord(
                type="remove_duplicates",
                description=f"Removed {num_duplicates} exact duplicate row(s) (preserved first occurrence).",
                affected_rows=num_duplicates,
                cells_modified=0,
                affected_columns=None,
            )
        )

    # -------------------------------------------------------------
    # 2. TRIM UNNECESSARY WHITESPACE
    # -------------------------------------------------------------
    trimmed_cols: List[str] = []
    total_trimmed_cells = 0
    trimmed_rows_set = set()

    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            # Identify string cells with leading or trailing whitespace
            def check_and_trim(val):
                nonlocal total_trimmed_cells
                if isinstance(val, str):
                    trimmed = val.strip()
                    if trimmed != val:
                        total_trimmed_cells += 1
                        return trimmed
                return val

            # Check which rows are affected
            mask = df[col].apply(lambda x: isinstance(x, str) and (x != x.strip()))
            affected_count = int(mask.sum())
            if affected_count > 0:
                trimmed_rows_set.update(df.index[mask].tolist())
                df[col] = df[col].apply(check_and_trim)
                trimmed_cols.append(str(col))

    if total_trimmed_cells > 0:
        total_cells_modified += total_trimmed_cells
        transformations.append(
            TransformationRecord(
                type="trim_whitespace",
                description=f"Trimmed leading and trailing whitespace across {len(trimmed_cols)} column(s) ({total_trimmed_cells} cells modified).",
                affected_rows=len(trimmed_rows_set),
                cells_modified=total_trimmed_cells,
                affected_columns=trimmed_cols,
            )
        )

    # -------------------------------------------------------------
    # 3. NORMALIZE OBVIOUS FORMATTING INCONSISTENCIES
    # -------------------------------------------------------------
    # A) Multi-space collapsing inside strings
    multispace_cols: List[str] = []
    multispace_cells = 0
    multispace_rows_set = set()

    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            def collapse_spaces(val):
                nonlocal multispace_cells
                if isinstance(val, str):
                    collapsed = re.sub(r"[ \t]{2,}", " ", val)
                    if collapsed != val:
                        multispace_cells += 1
                        return collapsed
                return val

            mask = df[col].apply(lambda x: isinstance(x, str) and bool(re.search(r"[ \t]{2,}", x)))
            if int(mask.sum()) > 0:
                multispace_rows_set.update(df.index[mask].tolist())
                df[col] = df[col].apply(collapse_spaces)
                multispace_cols.append(str(col))

    if multispace_cells > 0:
        total_cells_modified += multispace_cells
        transformations.append(
            TransformationRecord(
                type="normalize_whitespace",
                description=f"Collapsed consecutive internal whitespace in text values across {len(multispace_cols)} column(s) ({multispace_cells} cells modified).",
                affected_rows=len(multispace_rows_set),
                cells_modified=multispace_cells,
                affected_columns=multispace_cols,
            )
        )

    # B) Standardize email casing (lowercase valid email strings)
    email_cols: List[str] = []
    email_cells_modified = 0
    email_rows_set = set()
    email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    for col in df.columns:
        if "email" in str(col).lower() or df[col].astype(str).str.contains("@").sum() > (0.3 * len(df)):
            def lowercase_email(val):
                nonlocal email_cells_modified
                if isinstance(val, str) and email_pattern.match(val.strip()):
                    lowered = val.strip().lower()
                    if lowered != val:
                        email_cells_modified += 1
                        return lowered
                return val

            mask = df[col].apply(lambda x: isinstance(x, str) and bool(email_pattern.match(x.strip())) and x.strip().lower() != x)
            if int(mask.sum()) > 0:
                email_rows_set.update(df.index[mask].tolist())
                df[col] = df[col].apply(lowercase_email)
                email_cols.append(str(col))

    if email_cells_modified > 0:
        total_cells_modified += email_cells_modified
        transformations.append(
            TransformationRecord(
                type="normalize_email_casing",
                description=f"Standardized email addresses to lowercase in column(s): {', '.join(email_cols)} ({email_cells_modified} cells modified).",
                affected_rows=len(email_rows_set),
                cells_modified=email_cells_modified,
                affected_columns=email_cols,
            )
        )

    # -------------------------------------------------------------
    # 4. STANDARDIZE MISSING-VALUE REPRESENTATIONS
    # -------------------------------------------------------------
    standardized_null_cols: List[str] = []
    total_null_cells_standardized = 0
    null_rows_set = set()

    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            def standardize_placeholder(val):
                nonlocal total_null_cells_standardized
                if pd.isna(val):
                    return val
                if isinstance(val, str):
                    cleaned_token = val.strip().lower()
                    if cleaned_token in CONFIDENT_NULL_STRINGS:
                        total_null_cells_standardized += 1
                        return np.nan
                return val

            mask = df[col].apply(
                lambda x: not pd.isna(x) and isinstance(x, str) and x.strip().lower() in CONFIDENT_NULL_STRINGS
            )
            affected_count = int(mask.sum())
            if affected_count > 0:
                null_rows_set.update(df.index[mask].tolist())
                df[col] = df[col].apply(standardize_placeholder)
                standardized_null_cols.append(str(col))

    if total_null_cells_standardized > 0:
        total_cells_modified += total_null_cells_standardized
        transformations.append(
            TransformationRecord(
                type="standardize_missing",
                description=f"Standardized ambiguous placeholder strings ('N/A', 'null', 'none', empty strings) to standard missing values in {len(standardized_null_cols)} column(s) ({total_null_cells_standardized} cells).",
                affected_rows=len(null_rows_set),
                cells_modified=total_null_cells_standardized,
                affected_columns=standardized_null_cols,
            )
        )

    # -------------------------------------------------------------
    # 5. DETECT AMBIGUOUS ANOMALIES FOR RECOMMENDATIONS & WARNINGS
    # -------------------------------------------------------------
    # A) Outliers in numeric columns
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            valid_nums = df[col].dropna()
            if len(valid_nums) >= 5:
                q25 = valid_nums.quantile(0.25)
                q75 = valid_nums.quantile(0.75)
                iqr = q75 - q25
                if iqr > 0:
                    lower = q25 - 1.5 * iqr
                    upper = q75 + 1.5 * iqr
                    outliers = valid_nums[(valid_nums < lower) | (valid_nums > upper)]
                    if len(outliers) > 0:
                        warnings.append(
                            f"Detected {len(outliers)} statistical outlier(s) in numeric column '{col}' outside [{lower:.1f}, {upper:.1f}]. Preserved without automatic clipping; manual inspection or domain-specific Winsorization recommended."
                        )

    # B) Negative values in plausibly non-negative columns
    non_negative_keywords = ["age", "count", "quantity", "price", "revenue", "spending", "visits", "total", "num_"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in non_negative_keywords) and pd.api.types.is_numeric_dtype(df[col]):
            negatives = df[df[col] < 0]
            if len(negatives) > 0:
                warnings.append(
                    f"Found {len(negatives)} negative value(s) in column '{col}' (e.g. {negatives[col].iloc[0]}). Preserved without sign inversion to avoid data distortion; please verify data ingestion source."
                )

    # C) Malformed emails
    for col in df.columns:
        if "email" in str(col).lower():
            str_col = df[col].dropna().astype(str)
            malformed = str_col[~str_col.str.contains(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", regex=True)]
            if len(malformed) > 0:
                warnings.append(
                    f"Detected {len(malformed)} malformed email address(es) in column '{col}' (e.g. '{malformed.iloc[0]}'). Preserved without deletion to prevent accidental data loss; verify with user records."
                )

    # D) Columns with high null percentages
    for col in df.columns:
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        if null_pct > 60:
            warnings.append(
                f"Column '{col}' has {null_pct:.1f}% missing values ({null_count}/{len(df)} rows). Column retained; evaluate whether this column should be dropped based on business context."
            )

    # -------------------------------------------------------------
    # 6. PERSIST SEPARATE CLEANED DATASET FILE (NEVER OVERWRITE ORIGINAL)
    # -------------------------------------------------------------
    upload_dir = Path(UPLOAD_DIR).resolve()
    cleaned_filename = f"{dataset_id}_cleaned.{fmt}"
    cleaned_path = upload_dir / cleaned_filename

    try:
        if fmt == "csv":
            df.to_csv(cleaned_path, index=False, encoding="utf-8")
        elif fmt == "json":
            df.to_json(cleaned_path, orient="records", indent=2)
        else:
            df.to_csv(cleaned_path, index=False, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist cleaned dataset: {str(e)}",
        )

    download_url = f"/api/datasets/{dataset_id}/download-cleaned"

    resp = CleanDatasetResponse(
        dataset_id=dataset_id,
        cleaned_filename=cleaned_filename,
        download_url=download_url,
        original_rows=original_rows,
        cleaned_rows=len(df),
        rows_removed=original_rows - len(df),
        cells_modified=total_cells_modified,
        transformations_performed=transformations,
        warnings=warnings,
    )

    try:
        audit_path = upload_dir / f"{dataset_id}_cleaning_audit.json"
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(resp.model_dump_json(indent=2))
    except Exception:
        pass

    return resp

