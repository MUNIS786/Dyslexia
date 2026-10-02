"""
backend/routers/v2_gamification.py — V2 Gamification & Positive Engagement Router.

Endpoints:
- GET  /api/v2/gamification/summary                   (Learner points, streaks, badges summary)
- GET  /api/v2/gamification/achievements              (Complete badge catalogue with learner progress)
- GET  /api/v2/gamification/milestones                (Upcoming milestone targets)
- GET  /api/v2/gamification/history                   (Paginated, auditable reward event ledger)
- GET  /api/v2/gamification/teacher/learner/{student_id} (Teacher view of student rewards without leaderboards)

Governance:
- Governed by feature flag V2_GAMIFICATION (returns 503 if disabled).
- Server-determined points only; no client-supplied arbitrary point totals.
- Transparent, non-shaming, non-competitive educational engagement.
"""
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher
from core.config import settings
from database.database import db
from models.v2_gamification import (
    GamificationSummary,
    BadgeProgressItem,
    MilestoneProgressItem,
    GamificationHistoryResponse,
)
from services.learning.gamification_service import (
    get_gamification_summary,
    get_achievements_with_progress,
    get_milestones_progress,
    get_reward_history,
    get_teacher_learner_reward_summary,
    process_learning_reward,
)

logger = logging.getLogger("dyslexaid.routers.v2_gamification")
router = APIRouter(prefix="/v2/gamification", tags=["V2 Gamification & Engagement"])


def _check_feature_flag():
    """Ensures V2_GAMIFICATION feature flag is enabled."""
    if not getattr(settings, "V2_GAMIFICATION", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Gamification & Engagement is currently disabled via feature flags."
        )


@router.get("/summary", response_model=GamificationSummary)
async def get_my_summary(current_user: dict = Depends(get_current_user)):
    """
    Retrieve current student's points, streaks, earned badges, and recent reward feed.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        return await get_gamification_summary(user_id)
    except Exception as e:
        logger.error(f"Error fetching gamification summary for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gamification summary."
        )


@router.get("/achievements", response_model=List[BadgeProgressItem])
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    """
    Retrieve all achievement badges with current progress and unlock timestamps.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        return await get_achievements_with_progress(user_id)
    except Exception as e:
        logger.error(f"Error fetching achievements for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve achievements."
        )


@router.get("/milestones", response_model=List[MilestoneProgressItem])
async def get_my_milestones(current_user: dict = Depends(get_current_user)):
    """
    Retrieve upcoming practice milestone targets to motivate next steps.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        return await get_milestones_progress(user_id)
    except Exception as e:
        logger.error(f"Error fetching milestones for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve milestones."
        )


@router.get("/history", response_model=GamificationHistoryResponse)
async def get_my_reward_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve paginated, auditable ledger of points awarded for completed activities.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        return await get_reward_history(user_id, page=page, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching reward history for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reward history."
        )


@router.get("/teacher/learner/{student_id}")
async def get_student_gamification_for_teacher(
    student_id: str,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Allows a teacher to view a student's gamification points and consistency summary
    within their authorized classroom (no competitive leaderboards).
    """
    _check_feature_flag()
    try:
        return await get_teacher_learner_reward_summary(current_teacher, student_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching gamification for student {student_id} by teacher {current_teacher.get('id')}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve student gamification summary."
        )


class ClaimEventRequest(BaseModel):
    """Request payload to claim rewards for a persisted learning event."""
    sourceEventId: str = Field(..., min_length=1, description="Identifier of the completed event (attemptId or sessionId)")
    eventType: str = Field(..., min_length=1, description="'activity_attempt' | 'reading_session'")


@router.post("/claim-event")
async def claim_event_reward(
    req: ClaimEventRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Idempotently claims rewards for a verified learning event.
    The server validates that the source event exists in the database and belongs
    to the calling learner. Client cannot supply arbitrary point values.
    """
    _check_feature_flag()
    user_id = current_user.get("id")

    if req.eventType == "activity_attempt":
        attempt = await db.activity_attempts.find_one({"attemptId": req.sourceEventId})
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity attempt '{req.sourceEventId}' not found."
            )
        if attempt.get("learnerId") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this activity attempt."
            )
        metadata = {
            "scorePercent": attempt.get("scorePercent", 0),
            "domain": attempt.get("domain", "practice"),
            "attemptId": req.sourceEventId,
        }
    elif req.eventType == "reading_session":
        session = await db.reading_sessions.find_one({"sessionId": req.sourceEventId})
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reading session '{req.sourceEventId}' not found."
            )
        if session.get("learnerId") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this reading session."
            )
        if not session.get("completed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reading session is not completed yet."
            )
        metadata = {
            "comprehensionScore": session.get("comprehensionAccuracy", session.get("comprehensionScore", 0)),
            "wordsRead": session.get("wordsRead", 0),
            "wordsPresented": session.get("wordsPresented", 0),
            "sessionId": req.sourceEventId,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported eventType '{req.eventType}' for claiming rewards."
        )

    res = await process_learning_reward(
        user_id=user_id,
        source_event_id=req.sourceEventId,
        event_type=req.eventType,
        metadata=metadata,
    )
    return res.model_dump()

