"""
DataLens AI — Quality Scoring Configuration.

Contains configurable dimension weights and penalty multipliers for the heuristic
dataset quality score calculation. Adjust these parameters to calibrate scoring behavior.
"""

from typing import Dict

# ---------------------------------------------------------------------------
# Dimension Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
DIMENSION_WEIGHTS: Dict[str, float] = {
    "completeness": 0.30,
    "validity": 0.30,
    "uniqueness": 0.20,
    "consistency": 0.20,
}

# ---------------------------------------------------------------------------
# Penalty Weights & Multipliers
# ---------------------------------------------------------------------------
PENALTY_CONFIG: Dict[str, float] = {
    # Completeness penalties
    "empty_column_deduction": 15.0,
    "high_missing_rate_deduction": 8.0,
    "elevated_missing_rate_deduction": 4.0,

    # Consistency penalties
    "constant_column_deduction": 10.0,
    "low_variance_deduction": 5.0,

    # Severity scaling factors for affected row percentages
    "severity_high_multiplier": 1.0,
    "severity_medium_multiplier": 0.6,
    "severity_low_multiplier": 0.3,
}
