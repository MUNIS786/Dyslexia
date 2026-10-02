"""
backend/routers/v2_accessibility.py — API Router for Phase 12 Accessibility & Personalization.
Exposes endpoints for user-scoped reading ergonomics, focus tools, and display preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from core.config import settings
from deps.deps import get_current_user
from models.v2_accessibility import (
    V2AccessibilityPreferences,
    AccessibilityPreferencesPatch,
    AccessibilityPreferencesResponse,
)
from services.accessibility.accessibility_service import (
    get_user_accessibility_preferences,
    update_user_accessibility_preferences,
    reset_user_accessibility_preferences,
)

router = APIRouter(prefix="/v2/accessibility", tags=["v2-accessibility"])


def _check_feature_flag():
    if not settings.V2_ACCESSIBILITY_PREFERENCES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Accessibility preferences feature is currently disabled",
        )


@router.get("/preferences", response_model=AccessibilityPreferencesResponse)
async def get_accessibility_preferences(user: dict = Depends(get_current_user)):
    """Retrieve accessibility preferences for the authenticated user."""
    _check_feature_flag()
    return await get_user_accessibility_preferences(user["id"])


@router.put("/preferences", response_model=AccessibilityPreferencesResponse)
async def set_accessibility_preferences(
    preferences: V2AccessibilityPreferences,
    user: dict = Depends(get_current_user),
):
    """Replace all accessibility preferences for the authenticated user."""
    _check_feature_flag()
    patch = AccessibilityPreferencesPatch(**preferences.model_dump(by_alias=False))
    return await update_user_accessibility_preferences(user["id"], patch)


@router.patch("/preferences", response_model=AccessibilityPreferencesResponse)
async def patch_accessibility_preferences(
    patch: AccessibilityPreferencesPatch,
    user: dict = Depends(get_current_user),
):
    """Partially update accessibility preferences for the authenticated user."""
    _check_feature_flag()
    return await update_user_accessibility_preferences(user["id"], patch)


@router.post("/preferences/reset", response_model=AccessibilityPreferencesResponse)
async def reset_accessibility_preferences(user: dict = Depends(get_current_user)):
    """Reset accessibility preferences back to factory defaults."""
    _check_feature_flag()
    return await reset_user_accessibility_preferences(user["id"])
