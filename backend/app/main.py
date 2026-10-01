"""
DataLens AI — FastAPI application entry point.
"""

import collections
import logging
import time
from contextlib import asynccontextmanager
from typing import Deque, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import datasets, health
from app.config import (
    CORS_ORIGINS,
    CORS_ORIGIN_REGEX,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
)
from app.routers import upload
from app.services.dataset_service import cleanup_expired_datasets

logger = logging.getLogger("datalens.security")

# Sliding window rate limiter state: {client_ip: deque([timestamps])}
_rate_limit_records: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)
_WINDOW_SECONDS = 60.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: runs startup cleanup of expired dataset files."""
    pruned = cleanup_expired_datasets()
    if pruned > 0:
        logger.info(f"Startup maintenance: Purged {pruned} expired temporary dataset file(s).")
    yield


app = FastAPI(
    title="DataLens AI",
    description="AI-powered dataset quality analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Rate Limiting & Safe Error Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_and_rate_limiting_middleware(request: Request, call_next):
    # Exempt health checks, OPTIONS preflight, and interactive API documentation
    if request.method == "OPTIONS" or request.url.path in ("/health", "/api/health", "/docs", "/openapi.json"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old requests outside window
    timestamps = _rate_limit_records[client_ip]
    while timestamps and (now - timestamps[0] > _WINDOW_SECONDS):
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for IP {client_ip} on path {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please slow down and try again."},
            headers={"Retry-After": "60"},
        )

    timestamps.append(now)

    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # Prevent stack trace leakage to client on unhandled exceptions
        logger.exception("Unhandled server exception intercepted:")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please try again later."},
        )


# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health & Root Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"], summary="Service health check")
async def root_health_check():
    """
    Lightweight health endpoint for cloud platform health checks (Render, Railway, Fly.io).
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)       # GET /api/health
app.include_router(datasets.router)     # /api/datasets
app.include_router(upload.router)       # /api/upload (legacy compatibility)
