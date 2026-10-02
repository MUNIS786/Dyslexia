"""
backend/routers/v2_multilingual.py — V2 Multilingual Support & Localization Router.

Endpoints:
- GET  /api/v2/multilingual/languages   (Catalogue of supported languages and speech codes)
- GET  /api/v2/multilingual/preference  (Authenticated user's current preferred language)
- PUT  /api/v2/multilingual/preference  (Update authenticated user's preferred language)
- PATCH/api/v2/multilingual/preference  (Alias update endpoint)

Security & Governance:
- Guarded by feature flag V2_MULTILINGUAL (returns 503 Service Unavailable when disabled).
- Strict allowlist validation: ['en', 'mr', 'hi'] (with BCP-47 alias handling).
- Users can update only their own preference (isolated by JWT caller ID).
- Backward-compatible with existing db.users and db.learner_profiles.
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from deps.deps import get_current_user
from core.config import settings
from database.database import db
from models.v2_multilingual import (
    LanguageInfo,
    LanguagePreferenceUpdate,
    LanguagePreferenceResponse,
    SUPPORTED_LANGUAGES,
    LOCALE_ALIASES,
    normalize_locale,
)

logger = logging.getLogger("dyslexaid.routers.v2_multilingual")
router = APIRouter(prefix="/v2/multilingual", tags=["V2 Multilingual Support"])


def _check_feature_flag():
    """Ensures V2_MULTILINGUAL feature flag is enabled."""
    is_enabled = getattr(settings, "V2_MULTILINGUAL", False) or getattr(settings, "V2_MULTILINGUAL_SUPPORT", False)
    if not is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Multilingual Support is currently disabled via feature flags."
        )


@router.get("/languages", response_model=List[LanguageInfo])
async def list_supported_languages():
    """Returns the list of supported system languages, speech codes, and learning content availability."""
    _check_feature_flag()
    return list(SUPPORTED_LANGUAGES.values())


@router.get("/preference", response_model=LanguagePreferenceResponse)
async def get_my_language_preference(
    current_user: dict = Depends(get_current_user)
):
    """Retrieves authenticated user's current preferred language with system fallback."""
    _check_feature_flag()
    user_id = current_user.get("id")

    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "preferredLanguage": 1, "languages": 1})
    raw_code = "en"
    if user_doc:
        raw_code = user_doc.get("preferredLanguage") or (user_doc.get("languages") or ["en"])[0]

    code = normalize_locale(raw_code)
    if code not in SUPPORTED_LANGUAGES:
        code = "en"

    active_info = SUPPORTED_LANGUAGES[code]
    return LanguagePreferenceResponse(
        status="ok",
        preferredLanguage=code,
        activeLanguage=active_info,
        supportedLanguages=list(SUPPORTED_LANGUAGES.values()),
    )


@router.put("/preference", response_model=LanguagePreferenceResponse)
@router.patch("/preference", response_model=LanguagePreferenceResponse)
async def update_my_language_preference(
    payload: LanguagePreferenceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Updates the authenticated user's preferred language.
    Validates locale against allowlist and synchronizes both db.users and db.learner_profiles.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    raw_code = payload.get_target_code()
    norm_code = normalize_locale(raw_code)

    if not norm_code or norm_code not in SUPPORTED_LANGUAGES:
        valid_options = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code '{raw_code}'. Supported languages are: {valid_options}."
        )

    # 1. Update user document in db.users
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "preferredLanguage": norm_code,
            "languages": [norm_code],
        }}
    )

    # 2. Synchronize preferred_language in db.learner_profiles (if profile exists)
    try:
        await db.learner_profiles.update_one(
            {"learnerId": user_id},
            {"$set": {
                "preferred_language": norm_code,
                "preferredLanguage": norm_code,
            }}
        )
    except Exception as e:
        logger.warning(f"Could not sync language preference to learner_profile for {user_id}: {e}")

    active_info = SUPPORTED_LANGUAGES[norm_code]
    logger.info(f"User {user_id} updated language preference to '{norm_code}'.")

    return LanguagePreferenceResponse(
        status="ok",
        preferredLanguage=norm_code,
        activeLanguage=active_info,
        supportedLanguages=list(SUPPORTED_LANGUAGES.values()),
    )
