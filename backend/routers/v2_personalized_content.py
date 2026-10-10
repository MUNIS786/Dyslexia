"""
backend/routers/v2_personalized_content.py — Phase 15 Personalized Learning Content & Activity Engine API.

Endpoints:
- GET  /api/v2/personalized-content/next
- GET  /api/v2/personalized-content/activities
- GET  /api/v2/personalized-content/recommendation/{recommendation_id}
- POST /api/v2/personalized-content/launch
- GET  /api/v2/personalized-content/teacher/{learner_id}
- GET  /api/v2/personalized-content/parent/{learner_id}

Security & Governance:
- Authenticated via JWT tokens. Student identity derived strictly from session.
- Governed by feature flag: V2_PERSONALIZED_CONTENT (HTTP 503 if disabled).
- Preserves tenant isolation across students, teachers, and parents.
- Zero clinical or diagnostic claims.
- Never exposes raw speech audio, AI tutor chat transcripts, or teacher-private notes.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher, require_parent
from core.config import settings
from models.v2_personalized_content import (
    PersonalizedContentItem,
    PersonalizedActivityNextResponse,
    PersonalizedActivitiesListResponse,
    PersonalizedContentLaunchRequest,
    PersonalizedContentLaunchResponse,
    TeacherPersonalizedContentResponse,
    ParentPersonalizedContentResponse,
)
from services.learning.personalized_content import (
    get_next_personalized_activity,
    list_personalized_activities,
    get_content_for_recommendation,
    record_activity_launch,
    get_teacher_personalized_content,
    get_parent_personalized_content,
)

logger = logging.getLogger("dyslexaid.routers.v2_personalized_content")
router = APIRouter(prefix="/v2/personalized-content", tags=["V2 Personalized Learning Content"])


def _check_feature_flag():
    """Ensures V2_PERSONALIZED_CONTENT feature flag is enabled."""
    if not getattr(settings, "V2_PERSONALIZED_CONTENT", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Personalized Learning Content Engine is currently disabled via feature flags."
        )


@router.get("/next", response_model=PersonalizedActivityNextResponse)
async def get_next_activity(
    language: Optional[str] = Query(None, description="Optional target language ('en', 'mr', 'hi')"),
    activity_type: Optional[str] = Query(None, description="Optional target activity type filter"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the immediate next best personalized learning activity for the authenticated student.
    Strictly tenant-isolated to the token user.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        next_act = await get_next_personalized_activity(
            learner_id=student_id,
            language=language,
            activity_type=activity_type,
        )
        return next_act
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching next personalized activity for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve personalized activity."
        )


@router.get("/activities", response_model=PersonalizedActivitiesListResponse)
async def get_personalized_activities(
    language: Optional[str] = Query(None, description="Filter by language code ('en', 'mr', 'hi')"),
    tier: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty tier (1-5)"),
    category: Optional[str] = Query(None, description="Filter by recommendation category"),
    limit: int = Query(6, ge=1, le=20, description="Max activities to return"),
    current_user: dict = Depends(get_current_user),
):
    """
    Lists available personalized learning activities for the authenticated student,
    filtered by language, tier, and category.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        activities = await list_personalized_activities(
            learner_id=student_id,
            language=language,
            tier=tier,
            category=category,
            limit=limit,
        )
        return activities
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing personalized activities for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve personalized activities."
        )


@router.get("/recommendation/{recommendation_id}", response_model=PersonalizedContentItem)
async def get_activity_for_recommendation(
    recommendation_id: str,
    language: Optional[str] = Query(None, description="Optional target language"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the personalized activity content directly linked to a Phase 14 recommendation.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        content_item = await get_content_for_recommendation(
            learner_id=student_id,
            recommendation_id=recommendation_id,
            preferred_language=language or "en",
        )
        return content_item
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activity for recommendation {recommendation_id} for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation content."
        )


@router.post("/launch", response_model=PersonalizedContentLaunchResponse)
async def launch_activity(
    req: PersonalizedContentLaunchRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Records an activity launch telemetry event.
    Distinguishes launch from completion: does NOT mark the activity completed.
    """
    _check_feature_flag()
    student_id = current_user.get("id") or str(current_user.get("_id", ""))
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student session."
        )

    try:
        launch_res = await record_activity_launch(
            learner_id=student_id,
            req=req,
        )
        return launch_res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging activity launch for {student_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log activity launch."
        )


@router.get("/teacher/{learner_id}", response_model=TeacherPersonalizedContentResponse)
async def get_teacher_content(
    learner_id: str,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Returns educator-facing personalized activity overview and pedagogical rationale for a student.
    Enforces teacher-student classroom/tenant authorization.
    """
    _check_feature_flag()
    teacher_id = current_teacher.get("id") or str(current_teacher.get("_id", ""))

    try:
        teacher_res = await get_teacher_personalized_content(
            teacher_id=teacher_id,
            learner_id=learner_id,
        )
        return teacher_res
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting teacher personalized content for {learner_id} by {teacher_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teacher personalized content."
        )


@router.get("/parent/{learner_id}", response_model=ParentPersonalizedContentResponse)
async def get_parent_content(
    learner_id: str,
    current_parent: dict = Depends(require_parent),
):
    """
    Returns parent-facing at-home practice activity and guidance.
    Enforces verified parent-student link authorization.
    """
    _check_feature_flag()
    parent_id = current_parent.get("id") or str(current_parent.get("_id", ""))

    try:
        parent_res = await get_parent_personalized_content(
            parent_id=parent_id,
            learner_id=learner_id,
        )
        return parent_res
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parent personalized content for {learner_id} by {parent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve parent personalized content."
        )
