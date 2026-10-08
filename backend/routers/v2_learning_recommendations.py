"""
backend/routers/v2_learning_recommendations.py — V2 Learning Recommendations & Study Plan Router.

Endpoints:
- GET  /api/v2/learning-recommendations/student
- POST /api/v2/learning-recommendations/student/refresh
- GET  /api/v2/learning-recommendations/teacher/{learner_id}
- GET  /api/v2/learning-recommendations/parent/{learner_id}

Security & Governance:
- Protected by strict authentication & role authorization dependencies.
- Governed by feature flag: V2_LEARNING_RECOMMENDATIONS (HTTP 503 if disabled).
- Students cannot access other learners' recommendations (tenant isolation).
- Teachers can only access students enrolled in their assigned classroom.
- Parents can only access students with active, verified parent links.
- Non-clinical, descriptive educational recommendations only. Zero medical/diagnostic claims.
- Never exposes raw speech audio, AI tutor chat transcripts, or teacher-private notes.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher, require_parent
from core.config import settings
from models.v2_learning_recommendations import (
    StudentRecommendationsResponse,
    TeacherLearnerRecommendationsResponse,
    ParentLearnerRecommendationsResponse,
)
from services.learning.learning_recommendations import (
    generate_learner_recommendations,
    get_teacher_learner_recommendations,
    get_parent_learner_recommendations,
)

logger = logging.getLogger("dyslexaid.routers.v2_learning_recommendations")
router = APIRouter(prefix="/v2/learning-recommendations", tags=["V2 Learning Recommendations"])


def _check_feature_flag():
    """Ensures V2_LEARNING_RECOMMENDATIONS feature flag is enabled."""
    if not getattr(settings, "V2_LEARNING_RECOMMENDATIONS", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Learning Recommendations is currently disabled via feature flags."
        )


@router.get("/student", response_model=StudentRecommendationsResponse)
async def get_my_recommendations(
    period: str = Query("today", pattern="^(today|7d)$", description="Planning horizon"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns personalized next-step learning recommendations and daily study plan
    for the currently authenticated student.
    Strictly tenant-isolated to current_user.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        recommendations = await generate_learner_recommendations(
            learner_id=student_id,
            horizon=period,
        )
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating learning recommendations for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate learning recommendations."
        )


@router.post("/student/refresh", response_model=StudentRecommendationsResponse)
async def refresh_my_recommendations(
    period: str = Query("today", pattern="^(today|7d)$", description="Planning horizon"),
    current_user: dict = Depends(get_current_user),
):
    """
    Refreshes recommendations and study plan with the latest progress telemetry.
    Safe and idempotent.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        recommendations = await generate_learner_recommendations(
            learner_id=student_id,
            horizon=period,
        )
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing recommendations for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh learning recommendations."
        )


@router.get("/teacher/{learner_id}", response_model=TeacherLearnerRecommendationsResponse)
async def get_teacher_recommendations(
    learner_id: str,
    period: str = Query("today", pattern="^(today|7d)$", description="Planning horizon"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves teacher-facing recommended focus, pedagogical rationale, and supporting evidence
    for an individual student enrolled in the teacher's classroom.
    """
    _check_feature_flag()
    try:
        res = await get_teacher_learner_recommendations(
            teacher=current_teacher,
            learner_id=learner_id,
            horizon=period,
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recommendations for teacher {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch teacher learner recommendations."
        )


@router.get("/parent/{learner_id}", response_model=ParentLearnerRecommendationsResponse)
async def get_parent_recommendations(
    learner_id: str,
    period: str = Query("today", pattern="^(today|7d)$", description="Planning horizon"),
    current_parent: dict = Depends(require_parent),
):
    """
    Retrieves parent-facing suggested practice at home and supportive encouragement tips
    for a linked child.
    """
    _check_feature_flag()
    try:
        res = await get_parent_learner_recommendations(
            parent=current_parent,
            learner_id=learner_id,
            horizon=period,
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching parent recommendations for child {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch parent recommendations."
        )
