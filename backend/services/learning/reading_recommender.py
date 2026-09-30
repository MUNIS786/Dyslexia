"""
backend/services/learning/reading_recommender.py — Adaptive Reading Passage Recommender.

Determines the optimal reading passage for a learner based on:
- Active adaptive difficulty tier (Zone of Proximal Development 1-5)
- Rolling comprehension scores and consecutive passes/failures
- Learner strengths and prioritized practice areas from V2 Profile
- Recent reading session history (avoiding immediate repetition)
- Explainable, child-friendly pedagogical rationale

IMPORTANT:
Recommendations are deterministic and educational. No external LLM is required.
"""
import logging
from typing import Optional, Dict, Any, List

from database.database import db
from models.v2_reading import (
    ReadingPassage,
    ReadingRecommendationResponse,
)
from services.learning.difficulty_engine import clamp_tier
from services.learning.reading_service import get_passages, DEFAULT_PASSAGES
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    get_learning_state,
)

logger = logging.getLogger("dyslexaid.reading_recommender")


def _build_explainable_reading_reason(
    passage: Dict[str, Any],
    tier: int,
    consecutive_passes: int,
    recent_accuracy: Optional[float],
    is_practice_area: bool,
    is_strength: bool
) -> str:
    """
    Constructs an encouraging, child-friendly explanation for why this passage was selected.
    Non-clinical and supportive.
    """
    title = passage.get("title", "this story")

    if consecutive_passes >= 2 and tier < 5:
        return (
            f"You've been reading with great comprehension! '{title}' is calibrated at Level {tier} "
            f"to help you build mastery and prepare for higher levels."
        )
    elif recent_accuracy is not None and recent_accuracy < 60.0:
        return (
            f"Here is a comfortable, well-paced passage: '{title}'. It has clear sentences "
            f"and helpful word hints to build your reading confidence."
        )
    elif is_practice_area:
        return (
            f"'{title}' gives you fun practice with story understanding and key ideas at Level {tier}, "
            f"focusing on your current learning goals."
        )
    elif is_strength:
        return (
            f"Celebrate your reading superpowers with '{title}' at Level {tier}! "
            f"It's a wonderful match for your visual and story skills."
        )
    else:
        return (
            f"'{title}' is tailored at Level {tier} for your reading sweet spot. "
            f"Enjoy exploring this interesting topic!"
        )


async def recommend_reading_passage(
    learner_id: str,
    preferred_language: str = "en"
) -> ReadingRecommendationResponse:
    """
    Recommends a single best-fit reading passage for the learner.
    Integrates with Phase 2 Learner Profile and Phase 3 Adaptive Learning State.
    """
    # 1. Fetch learner profile & learning state
    profile_doc = await get_or_create_learner_profile(learner_id)
    state_doc = await get_learning_state(learner_id)

    # 2. Extract active tier (source of truth is Phase 3 learning state)
    current_tier = clamp_tier(
        state_doc.get("active_difficulty_tier") or
        state_doc.get("activeDifficultyTier") or
        profile_doc.get("adaptive_difficulty", {}).get("active_tier") or
        1
    )

    consecutive_passes = int(state_doc.get("consecutive_passes", 0))
    consecutive_failures = int(state_doc.get("consecutive_failures", 0))
    rolling_scores = list(state_doc.get("rolling_comprehension_scores", []))
    recent_accuracy = rolling_scores[-1] if rolling_scores else None

    # 3. Retrieve recent reading sessions to avoid immediate repetition
    recent_sessions = []
    try:
        cursor = db.reading_sessions.find(
            {"learnerId": learner_id},
            {"passageId": 1, "completedAt": 1}
        ).sort("createdAt", -1).limit(5)
        recent_sessions = await cursor.to_list(length=5)
    except Exception as e:
        logger.warning(f"Error fetching recent sessions for user {learner_id}: {e}")

    recently_read_passage_ids = {s["passageId"] for s in recent_sessions if "passageId" in s}

    # 4. Fetch available passages at current tier
    candidates = await get_passages(tier=current_tier, language=preferred_language)
    if not candidates:
        # Fallback to any tier if none available at current_tier
        candidates = await get_passages(language=preferred_language)
    if not candidates:
        candidates = DEFAULT_PASSAGES

    # 5. Prioritize passages not read recently
    unread_candidates = [p for p in candidates if p["passageId"] not in recently_read_passage_ids]
    selection_pool = unread_candidates if unread_candidates else candidates

    # 6. Check learner practice areas and strengths
    practice_areas = profile_doc.get("areas_for_practice", [])
    has_comp_practice = any(p.get("domain") == "reading_comprehension" for p in practice_areas)
    strengths = profile_doc.get("strengths", [])
    has_comp_strength = any(s.get("domain") == "reading_comprehension" for s in strengths)

    # Pick the best candidate from selection pool
    selected_passage = selection_pool[0]

    # If learner has high recent comprehension, pick a slightly longer passage in tier
    if consecutive_passes >= 1 and len(selection_pool) > 1:
        # Sort by word count descending for gentle challenge
        sorted_by_length = sorted(selection_pool, key=lambda p: p.get("wordCount", 0), reverse=True)
        selected_passage = sorted_by_length[0]
    elif consecutive_failures >= 1 and len(selection_pool) > 1:
        # Sort by word count ascending for gentle support
        sorted_by_length = sorted(selection_pool, key=lambda p: p.get("wordCount", 0))
        selected_passage = sorted_by_length[0]

    # 7. Generate explainable rationale
    reason = _build_explainable_reading_reason(
        passage=selected_passage,
        tier=selected_passage.get("difficulty", current_tier),
        consecutive_passes=consecutive_passes,
        recent_accuracy=recent_accuracy,
        is_practice_area=has_comp_practice,
        is_strength=has_comp_strength,
    )

    confidence = 0.90 if unread_candidates else 0.82

    return ReadingRecommendationResponse(
        recommendedPassage=ReadingPassage(**selected_passage),
        difficulty=selected_passage.get("difficulty", current_tier),
        domain=selected_passage.get("domain", "reading_comprehension"),
        reason=reason,
        confidence=confidence,
    )
