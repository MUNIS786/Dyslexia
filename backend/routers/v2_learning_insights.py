"""
backend/routers/v2_learning_insights.py — V2 Learning Insights & Progress Reports API Router.

Endpoints:
- GET /api/v2/learning-insights/student
  (Authenticated student's own progress insights, trends, strengths, and timeline)
- GET /api/v2/learning-insights/teacher/overview
  (Class-wide aggregated progress trends and individual student cards for enrolled classroom)
- GET /api/v2/learning-insights/teacher/{learner_id}
  (Authorized teacher drill-down into specific enrolled student's learning insights)
- GET /api/v2/learning-insights/parent/{learner_id}
  (Authorized parent progress summary with simplified non-jargon metrics)

Security & Governance:
- Protected by strict authentication & authorization dependencies.
- Governed by feature flag: V2_LEARNING_INSIGHTS (HTTP 503 if disabled).
- Students cannot access other learners' insights (tenant isolation).
- Teachers can only access students enrolled in their assigned classroom.
- Parents can only access students with active, verified parent links.
- Non-clinical, descriptive educational indicators only. Zero medical/diagnostic claims.
- Never exposes raw speech audio, AI tutor chat transcripts, or teacher-private notes.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher, require_parent
from core.config import settings
from models.v2_learning_insights import (
    StudentInsightsResponse,
    ClassInsightsOverviewResponse,
    ParentInsightsResponse,
)
from services.analytics.teacher_analytics import verify_teacher_student_access
from services.learning.learning_insights import (
    get_student_learning_insights,
    get_class_insights_overview,
    get_parent_student_insights,
)

logger = logging.getLogger("dyslexaid.routers.v2_learning_insights")
router = APIRouter(prefix="/v2/learning-insights", tags=["V2 Learning Insights"])


def _check_feature_flag():
    """Ensures V2_LEARNING_INSIGHTS feature flag is enabled."""
    if not getattr(settings, "V2_LEARNING_INSIGHTS", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Learning Insights is currently disabled via feature flags."
        )


@router.get("/student", response_model=StudentInsightsResponse)
async def get_my_learning_insights(
    period: str = Query("30d", pattern="^(7d|30d|90d)$", description="Reporting period"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns learning insights and progress reports for the currently authenticated student.
    Strictly isolated to the authenticated user's ID.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        insights = await get_student_learning_insights(student_id=student_id, period=period)
        return insights
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student learning insights for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate student learning insights."
        )


@router.get("/teacher/overview", response_model=ClassInsightsOverviewResponse)
async def get_teacher_class_overview(
    period: str = Query("30d", pattern="^(7d|30d|90d)$", description="Reporting period"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves class-wide learning trends, distribution, and student cards for the teacher's classroom.
    """
    _check_feature_flag()
    try:
        overview = await get_class_insights_overview(teacher=current_teacher, period=period)
        return overview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating teacher class insights overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate class insights overview."
        )


@router.get("/teacher/{learner_id}", response_model=StudentInsightsResponse)
async def get_teacher_learner_insights(
    learner_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$", description="Reporting period"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves detailed multi-domain learning insights for an individual student.
    Enforces that student is enrolled in the teacher's classroom.
    """
    _check_feature_flag()
    # Verify teacher has access to this student
    await verify_teacher_student_access(current_teacher, learner_id)

    try:
        insights = await get_student_learning_insights(student_id=learner_id, period=period)
        return insights
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching learner insights for teacher {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch learner learning insights."
        )


@router.get("/parent/{learner_id}", response_model=ParentInsightsResponse)
async def get_parent_learner_insights(
    learner_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$", description="Reporting period"),
    current_parent: dict = Depends(require_parent),
):
    """
    Retrieves simplified, non-clinical progress report for a linked child.
    Enforces active, verified parent-child relationship.
    """
    _check_feature_flag()
    try:
        insights = await get_parent_student_insights(
            parent=current_parent,
            student_id=learner_id,
            period=period,
        )
        return insights
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching parent insights for child {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch parent progress insights."
        )
