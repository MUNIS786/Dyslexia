"""
backend/routers/v2_tutor.py — V2 Personal AI Tutor API Router.

Endpoints:
- POST   /api/v2/tutor/chat      (Send a message / inquiry to the personal AI tutor)
- GET    /api/v2/tutor/context   (Inspect compact pedagogical context for the learner)
- GET    /api/v2/tutor/history   (Retrieve bounded conversational history)
- DELETE /api/v2/tutor/history   (Clear conversation history)

Safety & Governance:
- Governed by feature flag: V2_AI_TUTOR
- Strict authentication on all endpoints
- Enforces strict student tenancy: learner identity is derived from current_user["id"]
- Student cannot query another learner's context (returns 403 Forbidden)
- Thin HTTP layer: delegates context building and tutor inference to services
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user
from core.config import settings
from models.v2_tutor import (
    TutorRequest,
    TutorResponse,
    TutorContext,
)
from services.learning.tutor_context import build_tutor_context
from services.learning.tutor_service import (
    handle_tutor_chat,
    get_tutor_history,
    clear_tutor_history,
)

logger = logging.getLogger("dyslexaid.routers.v2_tutor")
router = APIRouter(prefix="/v2/tutor", tags=["V2 Personal AI Tutor"])


def _check_feature_flag():
    """Ensures V2_AI_TUTOR is enabled."""
    if not getattr(settings, "V2_AI_TUTOR", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Personal AI Tutor is currently disabled via feature flags."
        )


@router.post("/chat", response_model=TutorResponse)
async def tutor_chat(
    req: TutorRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submits a student inquiry or request to the Personal AI Tutor.
    Derives learner identity securely from the authenticated token.
    """
    _check_feature_flag()

    learner_id = current_user["id"]
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    try:
        response = await handle_tutor_chat(learner_id=learner_id, request=req)
        return response
    except Exception as e:
        logger.error(f"Error executing tutor chat turn for learner {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating educational tutor guidance."
        )


@router.get("/context", response_model=TutorContext)
async def get_tutor_context(
    activePassageId: Optional[str] = Query(None, description="Optional active passage ID"),
    activeWord: Optional[str] = Query(None, description="Optional active word queried"),
    learnerId: Optional[str] = Query(None, description="Optional learner ID; students can only view self"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the deterministic, compact pedagogical context built for the AI tutor.
    Prevents cross-student data leakage.
    """
    _check_feature_flag()

    target_learner_id = current_user["id"]
    if learnerId and learnerId != current_user["id"]:
        # Only teachers can view context of other learners
        role = current_user.get("role", "student")
        if role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only access their own tutor context."
            )
        target_learner_id = learnerId

    try:
        ctx = await build_tutor_context(
            learner_id=target_learner_id,
            active_passage_id=activePassageId,
            active_word=activeWord,
        )
        return ctx
    except Exception as e:
        logger.error(f"Error fetching tutor context for learner {target_learner_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assemble tutor context."
        )


@router.get("/history")
async def get_conversation_history(
    limit: int = Query(20, ge=1, le=50, description="Max messages to retrieve"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves bounded conversational history for the authenticated student.
    """
    _check_feature_flag()

    learner_id = current_user["id"]
    try:
        messages = await get_tutor_history(learner_id=learner_id, limit=limit)
        return {"status": "ok", "learnerId": learner_id, "messages": messages}
    except Exception as e:
        logger.error(f"Error retrieving tutor history for learner {learner_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tutor conversation history."
        )


@router.delete("/history")
async def clear_conversation_history(
    current_user: dict = Depends(get_current_user),
):
    """
    Clears conversation history for the authenticated student.
    """
    _check_feature_flag()

    learner_id = current_user["id"]
    try:
        cleared = await clear_tutor_history(learner_id=learner_id)
        return {"status": "ok", "learnerId": learner_id, "cleared": cleared}
    except Exception as e:
        logger.error(f"Error clearing tutor history for learner {learner_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear tutor conversation history."
        )
