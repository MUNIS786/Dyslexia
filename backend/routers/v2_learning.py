"""
backend/routers/v2_learning.py — V2 Adaptive Learning Engine API.

Endpoints:
- GET  /api/v2/learning/activities        (Browse/filter catalog of micro-tasks)
- GET  /api/v2/learning/recommendations   (ZPD-tailored daily recommendations with rationale)
- POST /api/v2/learning/attempt           (Submit task attempt, adapt difficulty, recalibrate profile)
- GET  /api/v2/learning/state             (Active adaptive progression state & tier info)
- GET  /api/v2/learning/tier-info         (Educational tier calibrations 1-5)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from deps.deps import get_current_user
from core.config import settings
from models.v2_learning_state import (
    ActivityAttemptCreate,
    AdaptiveAttemptResponse,
)
from services.learning.difficulty_engine import (
    TIER_CONFIGURATIONS,
    get_tier_calibration,
    clamp_tier,
)
from services.learning.activity_recommender import (
    get_catalog_activities,
    recommend_adaptive_activities,
)
from services.learning.adaptive_engine import evaluate_attempt_and_adapt
from services.learning.learner_profile_service import get_learning_state

logger = logging.getLogger("dyslexaid.routers.v2_learning")
router = APIRouter(prefix="/v2/learning", tags=["V2 Adaptive Learning Engine"])


def _check_feature_flag():
    if not settings.V2_ADAPTIVE_ENGINE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Adaptive Learning Engine is currently disabled via feature flags."
        )


@router.get("/activities")
async def get_activities(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tier: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty tier (1-5)"),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve available interactive learning micro-tasks filtered by domain and/or difficulty tier."""
    _check_feature_flag()
    try:
        activities = await get_catalog_activities(domain=domain, tier=tier)
        return {"status": "ok", "count": len(activities), "activities": activities}
    except Exception as e:
        logger.error(f"Error fetching activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning activities."
        )


@router.get("/recommendations")
async def get_recommendations(
    count: int = Query(4, ge=1, le=10, description="Number of recommendations"),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve personalized micro-learning recommendations based on student's ZPD, strengths, and practice areas."""
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        recs = await recommend_adaptive_activities(user_id=user_id, count=count)
        return {
            "status": "ok",
            "learnerId": user_id,
            "count": len(recs),
            "recommendations": [r.model_dump() for r in recs],
        }
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate adaptive recommendations."
        )


@router.post("/attempt", response_model=AdaptiveAttemptResponse)
async def submit_attempt(
    attempt_in: ActivityAttemptCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit interactive task attempt telemetry (score, duration, hesitation, hints).
    Evaluates ZPD adaptation triggers, updates difficulty tier, and recalibrates profile.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        result = await evaluate_attempt_and_adapt(user_id=user_id, attempt_in=attempt_in)
        return result
    except Exception as e:
        logger.error(f"Error processing attempt for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process activity attempt."
        )


@router.get("/state")
async def get_state(current_user: dict = Depends(get_current_user)):
    """Retrieve current adaptive progression state, tier, streak, and tier parameters."""
    _check_feature_flag()
    user_id = current_user.get("id")
    try:
        state = await get_learning_state(user_id)
        current_tier = clamp_tier(state.get("active_difficulty_tier", state.get("activeDifficultyTier", 1)))
        calibration = get_tier_calibration(current_tier)
        return {
            "status": "ok",
            "state": state,
            "tierCalibration": calibration.model_dump(),
        }
    except Exception as e:
        logger.error(f"Error fetching state for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning state."
        )


@router.get("/tier-info")
async def get_tier_info(current_user: dict = Depends(get_current_user)):
    """Retrieve informational calibrations for all 5 difficulty tiers."""
    _check_feature_flag()
    return {
        "status": "ok",
        "tiers": TIER_CONFIGURATIONS,
    }
