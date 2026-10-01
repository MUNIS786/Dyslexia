"""
backend/routers/v2_intervention.py — V2 Intervention Effectiveness API Router.

Endpoints:
- POST   /api/v2/teacher/interventions                          (Create support activity & establish baseline)
- GET    /api/v2/teacher/interventions                          (List classroom support activities)
- GET    /api/v2/teacher/interventions/{intervention_id}        (Retrieve intervention details)
- PATCH  /api/v2/teacher/interventions/{intervention_id}        (Update intervention goal, activity, review date)
- POST   /api/v2/teacher/interventions/{intervention_id}/start  (Transition: planned -> active)
- POST   /api/v2/teacher/interventions/{intervention_id}/review (Transition: active -> review)
- POST   /api/v2/teacher/interventions/{intervention_id}/complete (Transition: review/active -> completed)
- POST   /api/v2/teacher/interventions/{intervention_id}/cancel (Transition: planned/active/review -> cancelled)
- GET    /api/v2/teacher/interventions/{intervention_id}/effectiveness (Comparative report & observed changes)
- POST   /api/v2/teacher/interventions/{intervention_id}/measurements  (Add manual teacher observation/measurement)

Security & Governance:
- Protected by require_teacher dependency (students rejected with 403 Forbidden).
- Governed by feature flag: V2_INTERVENTION_EFFECTIVENESS (returns 503 if disabled).
- Enforces strict classroom tenant boundary: Teacher can only inspect and manage students in their classroom.
- Descriptive educational measurement only: Zero clinical or medical claims.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import require_teacher
from core.config import settings
from models.v2_intervention import (
    V2Intervention,
    InterventionCreateRequest,
    InterventionUpdateRequest,
    InterventionTransitionRequest,
    ManualFollowUpRequest,
    InterventionEffectivenessReport,
)
from services.analytics.intervention_effectiveness import (
    create_intervention,
    get_teacher_interventions,
    verify_teacher_intervention_access,
    update_intervention,
    transition_intervention_status,
    record_manual_followup,
    generate_effectiveness_report,
)

logger = logging.getLogger("dyslexaid.routers.v2_intervention")
router = APIRouter(prefix="/v2/teacher/interventions", tags=["V2 Intervention Effectiveness"])


def _check_feature_flag():
    """Ensures V2_INTERVENTION_EFFECTIVENESS feature flag is enabled."""
    if not getattr(settings, "V2_INTERVENTION_EFFECTIVENESS", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Intervention Effectiveness is currently disabled via feature flags."
        )


@router.post("", response_model=V2Intervention, status_code=status.HTTP_201_CREATED)
async def create_new_intervention(
    req: InterventionCreateRequest,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Creates a new learning support activity, gathers an initial baseline from existing student data,
    and initializes it in 'planned' status.
    """
    _check_feature_flag()
    try:
        intervention = await create_intervention(teacher=current_teacher, req=req)
        return intervention
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating intervention: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create intervention."
        )


@router.get("", response_model=List[Dict[str, Any]])
async def list_interventions(
    learner_id: Optional[str] = Query(None, description="Optional filter by student user ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional filter by status"),
    current_teacher: dict = Depends(require_teacher),
):
    """
    Lists all learning support activities / interventions for the teacher's classroom.
    """
    _check_feature_flag()
    try:
        interventions = await get_teacher_interventions(
            teacher=current_teacher,
            learner_id=learner_id,
            status_filter=status_filter,
        )
        return interventions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing interventions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classroom interventions."
        )


@router.get("/{intervention_id}", response_model=Dict[str, Any])
async def get_intervention_detail(
    intervention_id: str,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Retrieves full details of a specific intervention, including baseline and follow-up measurements.
    """
    _check_feature_flag()
    doc = await verify_teacher_intervention_access(current_teacher, intervention_id)
    return doc


@router.patch("/{intervention_id}", response_model=Dict[str, Any])
async def update_intervention_detail(
    intervention_id: str,
    req: InterventionUpdateRequest,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Applies partial updates to goal, support activity, review date, or appends a note.
    """
    _check_feature_flag()
    try:
        updated = await update_intervention(
            teacher=current_teacher,
            intervention_id=intervention_id,
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating intervention {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update intervention."
        )


@router.post("/{intervention_id}/start", response_model=Dict[str, Any])
async def start_intervention_flow(
    intervention_id: str,
    req: Optional[InterventionTransitionRequest] = None,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Transitions intervention from 'planned' to 'active'.
    """
    _check_feature_flag()
    try:
        updated = await transition_intervention_status(
            teacher=current_teacher,
            intervention_id=intervention_id,
            target_status="active",
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting intervention {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start intervention."
        )


@router.post("/{intervention_id}/review", response_model=Dict[str, Any])
async def review_intervention_flow(
    intervention_id: str,
    req: Optional[InterventionTransitionRequest] = None,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Transitions intervention from 'active' to 'review' stage and collects follow-up measurements.
    """
    _check_feature_flag()
    try:
        updated = await transition_intervention_status(
            teacher=current_teacher,
            intervention_id=intervention_id,
            target_status="review",
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transitioning intervention {intervention_id} to review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move intervention to review stage."
        )


@router.post("/{intervention_id}/complete", response_model=Dict[str, Any])
async def complete_intervention_flow(
    intervention_id: str,
    req: Optional[InterventionTransitionRequest] = None,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Transitions intervention to 'completed' stage, locking in final measurements.
    """
    _check_feature_flag()
    try:
        updated = await transition_intervention_status(
            teacher=current_teacher,
            intervention_id=intervention_id,
            target_status="completed",
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing intervention {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete intervention."
        )


@router.post("/{intervention_id}/cancel", response_model=Dict[str, Any])
async def cancel_intervention_flow(
    intervention_id: str,
    req: Optional[InterventionTransitionRequest] = None,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Transitions intervention to 'cancelled' stage.
    """
    _check_feature_flag()
    try:
        updated = await transition_intervention_status(
            teacher=current_teacher,
            intervention_id=intervention_id,
            target_status="cancelled",
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling intervention {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel intervention."
        )


@router.get("/{intervention_id}/effectiveness", response_model=InterventionEffectivenessReport)
async def get_effectiveness_report(
    intervention_id: str,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Calculates and returns the comparative effectiveness report between baseline
    and follow-up observations.
    """
    _check_feature_flag()
    doc = await verify_teacher_intervention_access(current_teacher, intervention_id)
    try:
        report = await generate_effectiveness_report(intervention=doc, teacher=current_teacher)
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating effectiveness report for {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate intervention effectiveness report."
        )


@router.post("/{intervention_id}/measurements", response_model=Dict[str, Any])
async def add_manual_measurement(
    intervention_id: str,
    req: ManualFollowUpRequest,
    current_teacher: dict = Depends(require_teacher),
):
    """
    Allows a teacher to record an interim observation measurement during active support.
    """
    _check_feature_flag()
    try:
        updated = await record_manual_followup(
            teacher=current_teacher,
            intervention_id=intervention_id,
            req=req,
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording manual measurement for {intervention_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record measurement."
        )
