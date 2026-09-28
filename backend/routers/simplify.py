"""Simplify route — AI with offline fallback + notes converter + personalization.

Connects to:
  - services/ai_service.py          (simplify_with_ai, convert_notes_offline)
  - services/offline_simplifier.py  (simplify_offline — no-internet fallback)
  - services/personalization.py     (personalize_output — profile-based accommodations)
  - deps/deps.py                    (get_current_user_optional — reads stored readingProfile)
  - database/database.py            (db.users.readingProfile.type / active_profiles)
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

from services.ai_service import simplify_with_ai, convert_notes_offline
from services.offline_simplifier import simplify_offline
from services.personalization import personalize_output
from deps.deps import get_current_user_optional
from database.database import db

router = APIRouter(tags=["simplify"])


class SimplifyReq(BaseModel):
    text: str
    language: Optional[str] = "english"
    # Explicit profile(s) from the client, e.g. ["Phonological Dyslexia"]
    # or canonical keys, e.g. ["phonological", "working_memory"].
    # If omitted, falls back to the logged-in user's stored readingProfile.
    profile_types: Optional[List[str]] = None


class NotesConvertReq(BaseModel):
    text: str
    language: Optional[str] = "english"
    title: Optional[str] = ""
    profile_types: Optional[List[str]] = None


async def _resolve_profile_types(explicit: Optional[List[str]], authorization: Optional[str]) -> List[str]:
    """Use client-supplied profile types if given, otherwise look up the
    logged-in user's stored reading profile (single type + any recorded
    multi-label active profiles)."""
    if explicit:
        return explicit

    user = await get_current_user_optional(authorization)
    if not user:
        return []

    reading_profile = user.get("readingProfile") or {}
    types: List[str] = []

    primary_type = reading_profile.get("type")
    if primary_type:
        types.append(primary_type)

    active_profiles = reading_profile.get("active_profiles")
    if active_profiles:
        for p in active_profiles:
            if p not in types:
                types.append(p)

    return types


@router.post("/simplify")
async def simplify(req: SimplifyReq, authorization: Optional[str] = Header(None)):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "No text provided")

    structured, method = await simplify_with_ai(text, req.language or "english")
    if not structured or not structured.get("text"):
        structured = simplify_offline(text)
        method = "offline"

    profile_types = await _resolve_profile_types(req.profile_types, authorization)
    personalization = personalize_output(structured, profile_types)

    return {
        "original": text,
        "simplified": structured.get("text", ""),
        "bullet_points": structured.get("bullet_points", []),
        "highlights": structured.get("highlights", []),
        "language": req.language or "english",
        "method": method,
        "personalization": personalization,
    }


@router.post("/convert-notes")
async def convert_notes(req: NotesConvertReq, authorization: Optional[str] = Header(None)):
    """
    Convert student-uploaded notes to dyslexia-friendly format.
    Works fully offline with rule-based fallback.
    Used when student uploads their class notes for offline reading.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "No notes provided")

    data, method = await convert_notes_offline(text, req.language or "english")

    profile_types = await _resolve_profile_types(req.profile_types, authorization)
    personalization = personalize_output(data, profile_types)

    return {
        "title": req.title or "My Notes",
        "original": text,
        "simplified": data.get("text", ""),
        "bullet_points": data.get("bullet_points", []),
        "highlights": data.get("highlights", []),
        "language": req.language or "english",
        "method": method,
        "offline_safe": True,   # This conversion works offline
        "personalization": personalization,
    }