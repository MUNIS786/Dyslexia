"""
backend/services/accessibility/accessibility_service.py — Service layer for Accessibility & Personalization.
Handles user-scoped preferences retrieval, validation, persistence, reset, and cross-phase synchronization.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database.database import db
from models.v2_accessibility import (
    V2AccessibilityPreferences,
    AccessibilityPreferencesPatch,
    AccessibilityPreferencesResponse,
)

logger = logging.getLogger("dyslexaid.accessibility_service")


async def get_user_accessibility_preferences(user_id: str) -> AccessibilityPreferencesResponse:
    """
    Retrieve the accessibility preferences for a given user.
    Falls back gracefully to user.settings or canonical defaults if not yet customized.
    """
    if not user_id:
        return AccessibilityPreferencesResponse(preferences=V2AccessibilityPreferences())

    # 1. Check dedicated collection
    doc = await db.user_accessibility_preferences.find_one({"userId": user_id})
    if doc and "preferences" in doc:
        try:
            prefs = V2AccessibilityPreferences(**doc["preferences"])
            return AccessibilityPreferencesResponse(
                preferences=prefs,
                updatedAt=doc.get("updatedAt"),
            )
        except Exception as e:
            logger.warning("Error deserializing accessibility doc for user %s: %s", user_id, e)

    # 2. Check embedded user.settings in users collection
    user = await db.users.find_one({"id": user_id})
    if user and user.get("settings"):
        try:
            raw_settings = user["settings"]
            # Convert any existing keys into V2AccessibilityPreferences
            prefs = V2AccessibilityPreferences(**raw_settings)
            return AccessibilityPreferencesResponse(preferences=prefs)
        except Exception as e:
            logger.warning("Error migrating legacy user.settings for user %s: %s", user_id, e)

    # 3. Canonical defaults
    return AccessibilityPreferencesResponse(preferences=V2AccessibilityPreferences())


async def update_user_accessibility_preferences(
    user_id: str,
    patch: AccessibilityPreferencesPatch,
) -> AccessibilityPreferencesResponse:
    """
    Update accessibility preferences for a user, validating inputs and maintaining
    backward-compatibility with legacy users.settings.
    """
    current_resp = await get_user_accessibility_preferences(user_id)
    current_prefs = current_resp.preferences

    # Extract non-None patch values
    patch_data = patch.model_dump(exclude_unset=True, by_alias=False)

    # Merge into a new preference object
    merged_data = current_prefs.model_dump(by_alias=False)
    merged_data.update(patch_data)

    # Validate full merged model
    updated_prefs = V2AccessibilityPreferences(**merged_data)
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Save in user_accessibility_preferences collection
    await db.user_accessibility_preferences.update_one(
        {"userId": user_id},
        {
            "$set": {
                "userId": user_id,
                "preferences": updated_prefs.model_dump(by_alias=False),
                "updatedAt": now_iso,
            }
        },
        upsert=True,
    )

    # 2. Synchronize legacy keys to users.settings for V1 compatibility
    legacy_sync_keys = [
        "font", "fontSize", "lineSpacing", "letterSpacing",
        "bgColor", "textColor", "ttsSpeed", "ttsLanguage",
        "highlightWords", "showBulletPoints", "autoSimplify",
    ]
    legacy_patch = {
        f"settings.{k}": getattr(updated_prefs, k)
        for k in legacy_sync_keys
        if hasattr(updated_prefs, k)
    }
    if legacy_patch:
        await db.users.update_one({"id": user_id}, {"$set": legacy_patch})

    return AccessibilityPreferencesResponse(
        preferences=updated_prefs,
        updatedAt=now_iso,
    )


async def reset_user_accessibility_preferences(user_id: str) -> AccessibilityPreferencesResponse:
    """
    Reset accessibility preferences for a user back to factory defaults.
    """
    default_prefs = V2AccessibilityPreferences()
    now_iso = datetime.now(timezone.utc).isoformat()

    await db.user_accessibility_preferences.update_one(
        {"userId": user_id},
        {
            "$set": {
                "userId": user_id,
                "preferences": default_prefs.model_dump(by_alias=False),
                "updatedAt": now_iso,
            }
        },
        upsert=True,
    )

    legacy_sync_keys = [
        "font", "fontSize", "lineSpacing", "letterSpacing",
        "bgColor", "textColor", "ttsSpeed", "ttsLanguage",
        "highlightWords", "showBulletPoints", "autoSimplify",
    ]
    legacy_patch = {
        f"settings.{k}": getattr(default_prefs, k)
        for k in legacy_sync_keys
        if hasattr(default_prefs, k)
    }
    if legacy_patch:
        await db.users.update_one({"id": user_id}, {"$set": legacy_patch})

    return AccessibilityPreferencesResponse(
        preferences=default_prefs,
        updatedAt=now_iso,
    )
