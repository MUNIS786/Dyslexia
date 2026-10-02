"""
backend/services/learning/adaptive_engine.py — Core Adaptive Learning Progression Engine.

Implements the continuous adaptive learning loop:
- Zone of Proximal Development (ZPD) difficulty tier calibration (Tiers 1-5)
- Telemetry evaluation across rolling comprehension scores, hesitations, and hints
- Deterministic adaptation rules (±15% comprehension change, 3 consecutive passes / 2 failures)
- Profile recalibration and recommendation recording
"""
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from database.database import db
from models.v2_learning_state import (
    ActivityAttemptCreate,
    ActivityAttempt,
    AdaptiveStateInfo,
    AdaptiveAttemptResponse,
)
from core.config import settings
from services.learning.difficulty_engine import clamp_tier, TIER_CONFIGURATIONS
from services.learning.learner_profile_service import recalibrate_from_activity, get_learning_state

logger = logging.getLogger("dyslexaid.adaptive_engine")


async def evaluate_attempt_and_adapt(
    user_id: str,
    attempt_in: ActivityAttemptCreate
) -> AdaptiveAttemptResponse:
    """
    Evaluates an interactive micro-task attempt, checks ZPD progression rules,
    adjusts difficulty tiers if triggered, recalibrates learner profile, and records telemetry.
    """
    now = int(time.time())
    attempt_id = str(uuid.uuid4())

    # 1. Fetch current learning state
    state_doc = await get_learning_state(user_id)
    previous_tier = clamp_tier(state_doc.get("active_difficulty_tier", state_doc.get("activeDifficultyTier", 1)))
    consecutive_passes = int(state_doc.get("consecutive_passes", state_doc.get("consecutivePasses", 0)))
    consecutive_failures = int(state_doc.get("consecutive_failures", state_doc.get("consecutiveFailures", 0)))
    rolling_scores: List[float] = list(state_doc.get("rolling_comprehension_scores", state_doc.get("rollingComprehensionScores", [])))
    current_streak = int(state_doc.get("current_streak", state_doc.get("currentStreak", 0)))
    tasks_completed = int(state_doc.get("today_tasks_completed", state_doc.get("todayTasksCompleted", 0)))

    # 2. Score analysis
    score = round(float(attempt_in.scorePercent), 1)
    rolling_scores.append(score)
    if len(rolling_scores) > 10:
        rolling_scores = rolling_scores[-10:]

    is_pass = score >= 80.0
    is_failure = score < 50.0

    if is_pass:
        consecutive_passes += 1
        consecutive_failures = 0
    elif is_failure:
        consecutive_failures += 1
        consecutive_passes = 0
    else:
        # Balanced performance in ZPD
        consecutive_passes = max(0, consecutive_passes)
        consecutive_failures = max(0, consecutive_failures)

    # 3. Adaptation Evaluation
    new_tier = previous_tier
    adaptation_triggered = False
    adaptation_reason = None

    # Check for UPWARD adaptation
    if consecutive_passes >= 3 and previous_tier < 5:
        new_tier = previous_tier + 1
        adaptation_triggered = True
        adaptation_reason = (
            f"Mastery demonstrated! 3 consecutive high-scoring activities completed. "
            f"Advancing from Level {previous_tier} to Level {new_tier}."
        )
        consecutive_passes = 0
        consecutive_failures = 0
    elif len(rolling_scores) >= 5 and previous_tier < 5:
        # Check rolling comprehension increase of +15%
        early_avg = sum(rolling_scores[:2]) / 2.0
        recent_avg = sum(rolling_scores[-3:]) / 3.0
        if recent_avg - early_avg >= 15.0 and recent_avg >= 80.0:
            new_tier = previous_tier + 1
            adaptation_triggered = True
            adaptation_reason = (
                f"Comprehension jump: Average score increased by +{round(recent_avg - early_avg, 1)}%! "
                f"Moving up to Level {new_tier}."
            )
            consecutive_passes = 0
            consecutive_failures = 0

    # Check for DOWNWARD adaptation (scaffolding / comfort reinforcement)
    if not adaptation_triggered:
        if consecutive_failures >= 2 and previous_tier > 1:
            new_tier = previous_tier - 1
            adaptation_triggered = True
            adaptation_reason = (
                f"Support mode activated: Providing additional scaffolding and moving to "
                f"Level {new_tier} to reinforce core reading confidence."
            )
            consecutive_passes = 0
            consecutive_failures = 0
        elif len(rolling_scores) >= 4 and previous_tier > 1:
            early_avg = sum(rolling_scores[:2]) / 2.0
            recent_avg = sum(rolling_scores[-2:]) / 2.0
            if early_avg - recent_avg >= 15.0 and recent_avg < 50.0:
                new_tier = previous_tier - 1
                adaptation_triggered = True
                adaptation_reason = (
                    f"Pacing adjustment: Recalibrating to Level {new_tier} for gentle practice."
                )
                consecutive_passes = 0
                consecutive_failures = 0

    tier_changed = new_tier != previous_tier

    # 4. Fetch activity metadata to get domain
    activity = await db.learning_activities.find_one({"id": attempt_in.activityId}, {"_id": 0})
    domain = activity.get("domain", "phonological_awareness") if activity else "phonological_awareness"

    # 5. Persist Attempt
    attempt_doc = {
        "id": attempt_id,
        "learnerId": user_id,
        "activityId": attempt_in.activityId,
        "domain": domain,
        "difficultyTier": previous_tier,
        "scorePercent": score,
        "durationSeconds": attempt_in.durationSeconds,
        "hesitationCount": attempt_in.hesitationCount,
        "hintsRequested": attempt_in.hintsRequested,
        "completedAt": now,
        "adaptationTriggered": adaptation_triggered,
        "previousTier": previous_tier,
        "newTier": new_tier,
    }
    await db.activity_attempts.insert_one(attempt_doc)

    # 6. Update streak and daily task count
    tasks_completed += 1
    if tasks_completed == 1:
        current_streak = max(1, current_streak + 1)

    # 7. Update Learning State in DB
    tier_info = TIER_CONFIGURATIONS.get(new_tier, TIER_CONFIGURATIONS[1])
    updated_state = {
        "learnerId": user_id,
        "activeDifficultyTier": new_tier,
        "active_difficulty_tier": new_tier,
        "tierName": tier_info["name"],
        "consecutivePasses": consecutive_passes,
        "consecutive_passes": consecutive_passes,
        "consecutiveFailures": consecutive_failures,
        "consecutive_failures": consecutive_failures,
        "rollingComprehensionScores": rolling_scores,
        "rolling_comprehension_scores": rolling_scores,
        "todayTasksCompleted": tasks_completed,
        "today_tasks_completed": tasks_completed,
        "currentStreak": current_streak,
        "current_streak": current_streak,
        "lastSessionTimestamp": now,
        "last_session_timestamp": now,
        "adaptationTriggerDue": False,
        "adaptation_due": False,
        "lastAdaptationReason": adaptation_reason,
        "updatedAt": now,
        "updated_at": now,
    }
    await db.learning_states.update_one(
        {"learnerId": user_id},
        {"$set": updated_state},
        upsert=True
    )

    # 8. Record adaptive recommendation history if tier changed
    if adaptation_triggered:
        rec_doc = {
            "id": str(uuid.uuid4()),
            "learnerId": user_id,
            "triggerEvent": "zpd_adaptation_threshold",
            "previousTier": previous_tier,
            "recommendedTier": new_tier,
            "reasoning": adaptation_reason,
            "generatedAt": now,
            "applied": True,
        }
        await db.adaptive_recommendations.insert_one(rec_doc)
        logger.info(f"Adaptation triggered for user {user_id}: {adaptation_reason}")

    # 9. Recalibrate Learner Profile dynamically
    try:
        await recalibrate_from_activity(
            user_id=user_id,
            activity_data={
                "domain": domain,
                "score": score,
                "tier": new_tier,
                "hesitationCount": attempt_in.hesitationCount,
                "hintsRequested": attempt_in.hintsRequested,
            }
        )
    except Exception as e:
        logger.error(f"Error during profile recalibration for user {user_id}: {e}", exc_info=True)

    # 10. Generate feedback message
    celebration = score >= 80.0 or tier_changed and new_tier > previous_tier
    if tier_changed and new_tier > previous_tier:
        msg = f"Fantastic work! You leveled up to {tier_info['name']} (Level {new_tier})!"
    elif tier_changed and new_tier < previous_tier:
        msg = f"Great effort! We've added gentle scaffolding and adjusted your practice to {tier_info['name']} for comfortable reading."
    elif score >= 90.0:
        msg = "Superstar performance! You nailed this challenge!"
    elif score >= 75.0:
        msg = "Great job! You're making solid progress!"
    else:
        msg = "Good try! Every practice makes your reading brain stronger!"

    # 11. Gamification & Effort Rewards (if enabled)
    gamification_res = None
    if getattr(settings, "V2_GAMIFICATION", False):
        try:
            from services.learning.gamification_service import process_learning_reward
            reward_eval = await process_learning_reward(
                user_id=user_id,
                source_event_id=attempt_id,
                event_type="activity_attempt",
                metadata={
                    "scorePercent": score,
                    "domain": domain,
                    "tier": new_tier,
                    "attemptId": attempt_id,
                }
            )
            gamification_res = reward_eval.model_dump()
        except Exception as ge:
            logger.error(f"Gamification reward error for user {user_id}: {ge}", exc_info=True)

    return AdaptiveAttemptResponse(
        status="ok",
        attemptId=attempt_id,
        scorePercent=score,
        adaptationTriggered=adaptation_triggered,
        previousTier=previous_tier,
        currentTier=new_tier,
        tierChanged=tier_changed,
        celebration=celebration,
        message=msg,
        streak=current_streak,
        learningState=updated_state,
        gamification=gamification_res,
    )
