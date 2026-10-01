"""
Dataset Quality Scoring Service.

Computes a deterministic, transparent quality score (0 to 100)
across 4 dimensions:
1. Completeness
2. Validity
3. Uniqueness
4. Consistency

Uses configurable weights from app.config.scoring_config.
Provides transparent explanations of every deduction without using an LLM.
"""

from typing import List, Tuple
import pandas as pd

from app.analyzers.analyzer import analyze_dataset_quality
from app.analyzers.profiler import load_dataset_readonly, locate_dataset_file
from app.config.scoring_config import DIMENSION_WEIGHTS, PENALTY_CONFIG
from app.models.analysis import QualityIssue
from app.models.score import QualityDimensions, QualityScoreResponse


def calculate_quality_score(
    df: pd.DataFrame, issues: List[QualityIssue]
) -> QualityScoreResponse:
    """
    Computes dimension scores and overall score based on dataframe metrics and detected issues.
    Guarantees every score is strictly between 0 and 100.
    Produces deterministic explanations of deductions.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols

    explanations: List[str] = []

    # ---------------------------------------------------------------------------
    # 1. Completeness Dimension (Base 100)
    # ---------------------------------------------------------------------------
    completeness_deductions = 0.0
    comp_notes: List[str] = []

    if total_cells > 0:
        total_null_cells = int(df.isna().sum().sum())
        null_cell_pct = round((total_null_cells / total_cells) * 100, 2)
        if total_null_cells > 0:
            pts = min(40.0, null_cell_pct * 1.0)
            completeness_deductions += pts
            comp_notes.append(f"{total_null_cells} missing cell(s) across dataset ({null_cell_pct}% of total cells, -{pts:.1f} pts)")

    for issue in issues:
        if issue.type == "empty_column":
            pts = PENALTY_CONFIG.get("empty_column_deduction", 15.0)
            completeness_deductions += pts
            comp_notes.append(f"column '{issue.column}' is 100% empty (-{pts:.1f} pts)")
        elif issue.type == "high_missing_percentage":
            pts = (
                PENALTY_CONFIG.get("high_missing_rate_deduction", 8.0)
                if issue.severity == "high"
                else PENALTY_CONFIG.get("elevated_missing_rate_deduction", 4.0)
            )
            completeness_deductions += pts
            comp_notes.append(f"column '{issue.column}' has {issue.percentage}% missing rate (-{pts:.1f} pts)")

    completeness_score = max(0, min(100, int(round(100.0 - completeness_deductions))))

    if comp_notes:
        explanations.append(f"Completeness ({completeness_score}/100): Deductions due to " + "; ".join(comp_notes) + ".")
    else:
        explanations.append(f"Completeness ({completeness_score}/100): Perfect score — no missing values or empty columns detected.")

    # ---------------------------------------------------------------------------
    # 2. Validity Dimension (Base 100)
    # ---------------------------------------------------------------------------
    validity_deductions = 0.0
    val_notes: List[str] = []

    validity_issue_types = {
        "invalid_email",
        "impossible_percentage",
        "negative_value_violation",
        "malformed_phone",
        "invalid_date",
    }

    for issue in issues:
        if issue.type in validity_issue_types:
            mult = (
                PENALTY_CONFIG.get("severity_high_multiplier", 1.0)
                if issue.severity == "high"
                else PENALTY_CONFIG.get("severity_medium_multiplier", 0.6)
            )
            pts = min(35.0, max(5.0, issue.percentage * mult))
            validity_deductions += pts
            val_notes.append(f"column '{issue.column}' contains {issue.affected_rows} {issue.type.replace('_', ' ')} entry/entries (-{pts:.1f} pts)")

    validity_score = max(0, min(100, int(round(100.0 - validity_deductions))))

    if val_notes:
        explanations.append(f"Validity ({validity_score}/100): Deductions due to " + "; ".join(val_notes) + ".")
    else:
        explanations.append(f"Validity ({validity_score}/100): Perfect score — all inspected records adhere to domain constraints and formats.")

    # ---------------------------------------------------------------------------
    # 3. Uniqueness Dimension (Base 100)
    # ---------------------------------------------------------------------------
    uniqueness_deductions = 0.0
    uniq_notes: List[str] = []

    for issue in issues:
        if issue.type == "duplicate_rows":
            pts = min(60.0, issue.percentage * 1.5)
            uniqueness_deductions += pts
            uniq_notes.append(f"{issue.affected_rows} duplicate rows detected ({issue.percentage}% of dataset, -{pts:.1f} pts)")
        elif issue.type == "duplicate_identifier":
            pts = min(40.0, issue.percentage * 1.2)
            uniqueness_deductions += pts
            uniq_notes.append(f"identifier collision in '{issue.column}' ({issue.affected_rows} duplicate keys, -{pts:.1f} pts)")
        elif issue.type == "normalized_duplicate_rows":
            pts = min(25.0, issue.percentage * 0.8)
            uniqueness_deductions += pts
            uniq_notes.append(f"{issue.affected_rows} near-duplicate records with subtle casing/whitespace differences (-{pts:.1f} pts)")

    uniqueness_score = max(0, min(100, int(round(100.0 - uniqueness_deductions))))

    if uniq_notes:
        explanations.append(f"Uniqueness ({uniqueness_score}/100): Deductions due to " + "; ".join(uniq_notes) + ".")
    else:
        explanations.append(f"Uniqueness ({uniqueness_score}/100): Perfect score — no duplicate rows or identifier collisions detected.")

    # ---------------------------------------------------------------------------
    # 4. Consistency Dimension (Base 100)
    # ---------------------------------------------------------------------------
    consistency_deductions = 0.0
    cons_notes: List[str] = []

    for issue in issues:
        if issue.type == "constant_column":
            pts = PENALTY_CONFIG.get("constant_column_deduction", 10.0)
            consistency_deductions += pts
            cons_notes.append(f"column '{issue.column}' is constant with zero variation (-{pts:.1f} pts)")
        elif issue.type == "low_variance_column":
            pts = PENALTY_CONFIG.get("low_variance_deduction", 5.0)
            consistency_deductions += pts
            cons_notes.append(f"column '{issue.column}' provides near-zero informational variance (-{pts:.1f} pts)")
        elif issue.type == "outliers":
            pts = min(20.0, max(3.0, issue.percentage * 0.5))
            consistency_deductions += pts
            cons_notes.append(f"column '{issue.column}' has {issue.affected_rows} statistical outlier(s) (-{pts:.1f} pts)")
        elif issue.type in ("near_empty_text", "extremely_long_text", "repeated_text_anomaly", "whitespace_formatting_anomaly"):
            pts = min(15.0, max(2.0, issue.percentage * 0.3))
            consistency_deductions += pts
            cons_notes.append(f"column '{issue.column}' exhibits text formatting anomalies ({issue.type}, -{pts:.1f} pts)")

    consistency_score = max(0, min(100, int(round(100.0 - consistency_deductions))))

    if cons_notes:
        explanations.append(f"Consistency ({consistency_score}/100): Deductions due to " + "; ".join(cons_notes) + ".")
    else:
        explanations.append(f"Consistency ({consistency_score}/100): Perfect score — uniform distributions and formatting across all columns.")

    # ---------------------------------------------------------------------------
    # 5. Overall Quality Score (Weighted combination)
    # ---------------------------------------------------------------------------
    w_comp = DIMENSION_WEIGHTS.get("completeness", 0.30)
    w_valid = DIMENSION_WEIGHTS.get("validity", 0.30)
    w_uniq = DIMENSION_WEIGHTS.get("uniqueness", 0.20)
    w_cons = DIMENSION_WEIGHTS.get("consistency", 0.20)

    raw_overall = (
        w_comp * completeness_score
        + w_valid * validity_score
        + w_uniq * uniqueness_score
        + w_cons * consistency_score
    )

    overall_score = max(0, min(100, int(round(raw_overall))))

    explanations.insert(
        0,
        f"Overall Quality Score ({overall_score}/100): Weighted synthesis of Completeness ({int(w_comp*100)}%), "
        f"Validity ({int(w_valid*100)}%), Uniqueness ({int(w_uniq*100)}%), and Consistency ({int(w_cons*100)}%)."
    )

    return QualityScoreResponse(
        overall=overall_score,
        dimensions=QualityDimensions(
            completeness=completeness_score,
            validity=validity_score,
            uniqueness=uniqueness_score,
            consistency=consistency_score,
        ),
        explanation=explanations,
    )


def compute_dataset_quality_score(dataset_id: str) -> QualityScoreResponse:
    """
    Load dataset, run deterministic analyzer checks, and compute transparent quality score.
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    df = load_dataset_readonly(file_path, fmt)
    analysis = analyze_dataset_quality(dataset_id)
    return calculate_quality_score(df, analysis.issues)
