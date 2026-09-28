"""
backend/routers/v2_learner.py — V2 Learner Intelligence Profile & State API.

Endpoints:
- GET   /api/v2/learner/profile
- PATCH /api/v2/learner/profile
- GET   /api/v2/learner/state
- GET   /api/v2/learner/student/{id}/profile  (Teacher only)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from deps.deps import get_current_user, require_teacher
from core.config import settings
from models.v2_learner_profile import V2LearnerProfileUpdate
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    update_learner_profile,
    get_learning_state,
)
from database.database import db

logger = logging.getLogger("dyslexaid.routers.v2_learner")
router = APIRouter(prefix="/v2/learner", tags=["V2 Learner Intelligence"])


@router.get("/profile")
async def get_my_learner_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve the V2 Learner Intelligence profile for the authenticated student."""
    if not settings.V2_LEARNER_PROFILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Learner Profile feature is currently disabled via feature flags."
        )

    user_id = current_user.get("id")
    try:
        profile = await get_or_create_learner_profile(user_id)
        return {"status": "ok", "profile": profile}
    except Exception as e:
        logger.error(f"Error fetching learner profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learner profile."
        )


@router.patch("/profile")
async def update_my_learner_profile(
    patch_data: V2LearnerProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update goals, preferred language, or accessibility preferences in the V2 Learner Profile."""
    if not settings.V2_LEARNER_PROFILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Learner Profile feature is currently disabled via feature flags."
        )

    user_id = current_user.get("id")
    try:
        updated = await update_learner_profile(user_id, patch_data)
        return {"status": "ok", "profile": updated}
    except Exception as e:
        logger.error(f"Error updating learner profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update learner profile."
        )


@router.get("/state")
async def get_my_learning_state(current_user: dict = Depends(get_current_user)):
    """Retrieve the real-time active learning state, streak, and difficulty tier."""
    user_id = current_user.get("id")
    try:
        state = await get_learning_state(user_id)
        return {"status": "ok", "learning_state": state}
    except Exception as e:
        logger.error(f"Error fetching learning state for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning state."
        )


@router.get("/student/{student_id}/profile")
async def get_student_profile_for_teacher(
    student_id: str,
    teacher: dict = Depends(require_teacher)
):
    """Teacher view: retrieve an enrolled student's V2 Learner Profile."""
    teacher_code = teacher.get("classroomCode")
    if not teacher_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher does not have an active classroom code."
        )

    # Verify student is in this teacher's classroom
    student = await db.users.find_one(
        {"id": student_id, "classroomJoined": teacher_code},
        {"_id": 0}
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in your assigned classroom."
        )

    profile = await get_or_create_learner_profile(student_id)
    return {"status": "ok", "student_name": student.get("name"), "profile": profile}
