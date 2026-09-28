"""
backend/routers/version.py — Application version and V2 feature flags endpoint.
"""
from fastapi import APIRouter
from core.config import settings

router = APIRouter(tags=["System"])


@router.get("/version")
async def get_version():
    """Returns platform version metadata and active V2 feature flags."""
    return settings.get_version_info()
