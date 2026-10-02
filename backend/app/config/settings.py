"""
DataLens AI — Application settings.

Loads settings from environment variables with sensible defaults.
All other modules should import from here, not from os.environ directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Upload constraints
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))  # 50 MB
ALLOWED_EXTENSIONS: set[str] = {".csv", ".json"}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://datalens-ai-ibrahim.netlify.app,https://frontend-nu-hazel-44.vercel.app",
    ).split(",")
    if origin.strip()
]
# Allows Vercel and Netlify preview and production URLs (*.vercel.app, *.netlify.app)
CORS_ORIGIN_REGEX: str | None = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$|^https:\/\/.*\.vercel\.app$|^https:\/\/.*\.netlify\.app$",
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
# Stateless temporary file storage for dataset processing.
# In containerized/cloud environments (Render, Linux), fallback safely to system tempdir.
import tempfile

_default_upload_dir = (
    os.path.join(tempfile.gettempdir(), "datalens_uploads")
    if os.getenv("RENDER") or os.getenv("VERCEL") or os.getenv("PORT")
    else os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
)
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", _default_upload_dir)

# ---------------------------------------------------------------------------
# Server Network Binding
# ---------------------------------------------------------------------------
PORT: int = int(os.getenv("PORT", "8000"))
HOST: str = os.getenv("HOST", "0.0.0.0")

# ---------------------------------------------------------------------------
# AI / LLM Configuration
# ---------------------------------------------------------------------------
LLM_API_KEY: str = (
    os.getenv("LLM_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "25.0"))

# ---------------------------------------------------------------------------
# Privacy & Security Governance
# ---------------------------------------------------------------------------
DATASET_RETENTION_HOURS: int = int(os.getenv("DATASET_RETENTION_HOURS", "24"))
RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))

