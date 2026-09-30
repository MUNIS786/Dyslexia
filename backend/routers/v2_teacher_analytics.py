"""
backend/routers/v2_teacher_analytics.py — V2 Teacher Analytics API Router.

Endpoints:
- GET /api/v2/teacher/analytics/overview               (Cohort metrics, distribution, and class insights)
- GET /api/v2/teacher/analytics/learners               (Roster of students with multi-modal progress)
- GET /api/v2/teacher/analytics/learners/{student_id}  (Individual student drill-down across all V2 domains)
- GET /api/v2/teacher/analytics/learners/{student_id}/trend (Longitudinal performance trend timeline)

Security & Governance:
- Protected by require_teacher dependency (students rejected with 403 Forbidden)
- Governed by feature flag: V2_TEACHER_ANALYTICS (returns 503 if disabled)
- Enforces strict classroom tenant boundary: Teacher can only inspect students enrolled in their classroom
- Non-clinical, descriptive analytics ONLY
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import require_teacher
from core.config import settings
from models.v2_teacher_analytics import (
    ClassAnalyticsResponse,
    LearnerAnalyticsSummary,
    LearnerAnalyticsDetail,
    ProgressTrendSummary,
)
from services.analytics.teacher_analytics import (
    get_class_overview,
    get_classroom_learners,
    get_learner_analytics_detail,
    calculate_progress_trends,
    verify_teacher_student_access,
)

logger = logging.getLogger("dyslexaid.routers.v2_teacher_analytics")
router = APIRouter(prefix="/v2/teacher/analytics", tags=["V2 Teacher Analytics"])


def _check_feature_flag():
    """Ensures V2_TEACHER_ANALYTICS feature flag is enabled."""
    if not getattr(settings, "V2_TEACHER_ANALYTICS", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Teacher Analytics is currently disabled via feature flags."
        )


@router.get("/overview", response_model=ClassAnalyticsResponse)
async def get_overview(
    time_range: str = Query("all", pattern="^(7d|30d|90d|all)$", description="Filter window"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves class-wide overview analytics for the authenticated teacher's classroom.
    """
    _check_feature_flag()
    try:
        response = await get_class_overview(teacher=current_teacher, time_range=time_range)
        return response
    except Exception as e:
        logger.error(f"Error generating class analytics overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate classroom analytics overview."
        )


@router.get("/learners", response_model=List[LearnerAnalyticsSummary])
async def get_learners_roster(
    time_range: str = Query("all", pattern="^(7d|30d|90d|all)$", description="Filter window"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves the learner roster with multi-modal learning levels, adaptive tiers,
    reading performance, and trend indicators for the teacher's classroom.
    """
    _check_feature_flag()
    try:
        learners = await get_classroom_learners(teacher=current_teacher, time_range=time_range)
        return learners
    except Exception as e:
        logger.error(f"Error fetching learners roster analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch classroom learners roster."
        )


@router.get("/learners/{student_id}", response_model=LearnerAnalyticsDetail)
async def get_learner_detail(
    student_id: str,
    time_range: str = Query("all", pattern="^(7d|30d|90d|all)$", description="Filter window"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Detailed multi-domain drill-down for a single authorized learner.
    Enforces that student is enrolled in the teacher's classroom.
    """
    _check_feature_flag()
    try:
        detail = await get_learner_analytics_detail(
            teacher=current_teacher,
            student_id=student_id,
            time_range=time_range,
        )
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating learner detail analytics for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate learner analytics detail."
        )


@router.get("/learners/{student_id}/trend", response_model=ProgressTrendSummary)
async def get_learner_trend(
    student_id: str,
    time_range: str = Query("all", pattern="^(7d|30d|90d|all)$", description="Filter window"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves chronological performance trend data points for the learner.
    Enforces student classroom enrollment authorization.
    """
    _check_feature_flag()
    # Verify access first
    await verify_teacher_student_access(current_teacher, student_id)
    try:
        trends = await calculate_progress_trends(student_id=student_id, time_range=time_range)
        return trends
    except Exception as e:
        logger.error(f"Error generating learner progress trends for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate learner progress trends."
        )
