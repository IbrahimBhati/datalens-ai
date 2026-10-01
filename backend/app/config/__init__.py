# config package — re-export all settings for backwards-compatible imports.
from app.config.settings import (  # noqa: F401
    MAX_UPLOAD_SIZE,
    ALLOWED_EXTENSIONS,
    CORS_ORIGINS,
    CORS_ORIGIN_REGEX,
    UPLOAD_DIR,
    LLM_API_KEY,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
    DATASET_RETENTION_HOURS,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    PORT,
    HOST,
)
from app.config.scoring_config import (  # noqa: F401
    DIMENSION_WEIGHTS,
    PENALTY_CONFIG,
)

__all__ = [
    "MAX_UPLOAD_SIZE",
    "ALLOWED_EXTENSIONS",
    "CORS_ORIGINS",
    "UPLOAD_DIR",
    "LLM_API_KEY",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_TIMEOUT_SECONDS",
    "DATASET_RETENTION_HOURS",
    "RATE_LIMIT_REQUESTS_PER_MINUTE",
    "DIMENSION_WEIGHTS",
    "PENALTY_CONFIG",
]
