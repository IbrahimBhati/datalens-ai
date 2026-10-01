"""
DataLens AI — Health check route.

GET /api/health → {"status": "ok"}
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    """Returns service liveness status."""
    return {"status": "ok"}
