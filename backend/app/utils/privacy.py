"""
PII Detection and Redaction Utilities.

Safeguards user privacy by scrubbing obvious sensitive data (emails, phone numbers,
SSNs, credit card numbers, sensitive credentials) before samples are sent to any LLM.
"""

import re
from typing import Any, Dict, List, Union

# Regex patterns for common PII formats
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# International and domestic phone formats (+1-555-123-4567, (555) 123-4567, 555-123-4567, etc.)
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b"
)

# US Social Security Number (XXX-XX-XXXX)
SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

# Standard Credit Card Numbers (13-19 digits, optionally separated by spaces or hyphens)
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b"
)


def redact_pii_text(text: str) -> str:
    """
    Scrub obvious PII (emails, phone numbers, SSNs, credit cards) from a string.
    """
    if not isinstance(text, str):
        return text

    # Redact in order of specificity
    sanitized = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    sanitized = SSN_PATTERN.sub("[SSN_REDACTED]", sanitized)
    sanitized = CREDIT_CARD_PATTERN.sub("[CARD_REDACTED]", sanitized)
    sanitized = PHONE_PATTERN.sub("[PHONE_REDACTED]", sanitized)

    return sanitized


def redact_sample_value(val: Any, col_name: str = "") -> Any:
    """
    Redact a single field value, considering both value pattern and column semantics.
    """
    if val is None:
        return None

    col_lower = col_name.lower()

    # If column is an identifier/credential column, redact immediately
    if any(k in col_lower for k in ("password", "secret", "token", "ssn", "api_key")):
        return "[SENSITIVE_REDACTED]"

    if isinstance(val, str):
        return redact_pii_text(val)

    if isinstance(val, (int, float, bool)):
        return val

    if isinstance(val, (list, tuple)):
        return [redact_sample_value(item, col_name) for item in val]

    if isinstance(val, dict):
        return {k: redact_sample_value(v, k) for k, v in val.items()}

    return str(val)


def redact_sample_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize a list of sample row records before sending them to the LLM.
    """
    sanitized_records: List[Dict[str, Any]] = []

    for row in records:
        sanitized_row: Dict[str, Any] = {}
        for col, val in row.items():
            sanitized_row[col] = redact_sample_value(val, col)
        sanitized_records.append(sanitized_row)

    return sanitized_records
