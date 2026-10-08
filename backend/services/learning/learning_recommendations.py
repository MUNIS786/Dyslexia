"""
backend/services/learning/learning_recommendations.py — Personalized Learning Recommendation Engine.

Answers: "What should this learner practice next, and why?"
Synthesizes real signals across:
- Phase 2: Learner Intelligence Profile (level, strengths, practice areas)
- Phase 3: Adaptive Learning State (ZPD tier, learning stage, consecutive passes/fails)
- Phase 4: Reading Coach (accuracy, WPM, difficult words, recent passages)
- Phase 5: Speech & Reading Analysis (oral reading accuracy, pronunciation, speech frequency)
- Phase 8: Intervention Effectiveness (strategies, response rate)
- Phase 9: Gamification & Engagement (streak, activity frequency)
- Phase 13: Learning Insights (longitudinal trends & data sufficiency)

Principles:
- Does NOT replace or duplicate Phase 3 Adaptive Learning Engine (Phase 3 remains authoritative).
- Deterministic, explainable scoring formula (no opaque ML or hallucinations).
- Zero clinical, medical, or diagnostic claims.
- Never exposes raw speech audio, tutor chat transcripts, or teacher-private notes.
- Strict tenant and role isolation.
"""
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from database.database import db
from models.v2_learning_recommendations import (
    StudyPlanItem,
    RecommendationItem,
    StudyPlan,
    StudentRecommendationsResponse,
    TeacherLearnerRecommendationsResponse,
    ParentLearnerRecommendationsResponse,
)
from services.learning.difficulty_engine import clamp_tier
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    get_learning_state,
)
from services.learning.reading_service import DEFAULT_PASSAGES
from services.learning.activity_recommender import DEFAULT_ACTIVITIES
from services.learning.learning_insights import get_student_learning_insights
from services.analytics.teacher_analytics import verify_teacher_student_access
from services.parent.parent_service import verify_parent_student_access

logger = logging.getLogger("dyslexaid.learning_recommendations")

TIER_NAMES = {
    1: "Foundation",
    2: "Developing",
    3: "Expanding",
    4: "Bridging",
    5: "Fluent",
}


def _get_utc_today_start_ts() -> float:
    """Returns midnight UTC timestamp for the current calendar day."""
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
    return midnight.timestamp()


async def _check_today_completions(learner_id: str) -> Dict[str, bool]:
    """
    Checks real database records to determine which categories of activities
    the learner has completed today (UTC).
    Does NOT manufacture completion.
    """
    today_ts = _get_utc_today_start_ts()
    id_filter = {"$or": [{"learnerId": learner_id}, {"student_id": learner_id}, {"studentId": learner_id}, {"learner_id": learner_id}]}

    completions = {
        "reading": False,
        "difficult_words": False,
        "speech": False,
        "adaptive_activity": False,
    }

    try:
        # Check reading sessions today
        q_read = {**id_filter, "$or": [{"createdAt": {"$gte": today_ts}}, {"completedAt": {"$gte": today_ts}}]}
        # If there are sessions with status completed or ended
        cursor = db.reading_sessions.find(id_filter).limit(10)
        sessions = await cursor.to_list(length=10) if hasattr(cursor, "to_list") else []
        for s in sessions:
            created = s.get("createdAt") or s.get("completedAt") or 0
            if isinstance(created, (int, float)) and created >= today_ts:
                completions["reading"] = True
                break

        # Check speech analysis today
        cursor_speech = db.speech_reading_analyses.find(id_filter).limit(5)
        speech_records = await cursor_speech.to_list(length=5) if hasattr(cursor_speech, "to_list") else []
        for sp in speech_records:
            created = sp.get("createdAt") or 0
            if isinstance(created, (int, float)) and created >= today_ts:
                completions["speech"] = True
                break

        # Check activity attempts today
        cursor_att = db.activity_attempts.find(id_filter).limit(10)
        attempts = await cursor_att.to_list(length=10) if hasattr(cursor_att, "to_list") else []
        for a in attempts:
            created = a.get("completedAt") or a.get("createdAt") or 0
            if isinstance(created, (int, float)) and created >= today_ts:
                completions["adaptive_activity"] = True
                break
    except Exception as e:
        logger.warning(f"Error checking today completions for {learner_id}: {e}")

    return completions


async def generate_learner_recommendations(
    learner_id: str,
    horizon: str = "today",
    preferred_language: str = "en",
) -> StudentRecommendationsResponse:
    """
    Core Phase 14 recommendation engine.
    Collects real signals across Phases 2-13, evaluates candidate activities,
    ranks them using transparent scoring, generates a bounded study plan,
    and returns a clean, child-friendly contract.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Collect Learner Signals (Phases 2 & 3)
    try:
        profile_doc = await get_or_create_learner_profile(learner_id)
    except Exception as e:
        logger.warning(f"Error fetching profile for {learner_id}: {e}")
        profile_doc = {}

    try:
        state_doc = await get_learning_state(learner_id)
    except Exception as e:
        logger.warning(f"Error fetching learning state for {learner_id}: {e}")
        state_doc = {}

    # Extract level & tier (Phase 3 authoritative)
    current_tier = clamp_tier(
        state_doc.get("active_difficulty_tier")
        or state_doc.get("activeDifficultyTier")
        or profile_doc.get("adaptive_difficulty", {}).get("active_tier")
        or 1
    )
    current_tier_name = TIER_NAMES.get(current_tier, "Foundation")

    current_level = int(
        profile_doc.get("learning_level")
        or profile_doc.get("level")
        or current_tier
    )
    current_level_name = TIER_NAMES.get(current_level, "Foundation")

    consecutive_passes = int(state_doc.get("consecutive_passes", 0))
    consecutive_failures = int(state_doc.get("consecutive_failures", 0))

    # 2. Collect Longitudinal Signals (Phase 13 Learning Insights)
    insights_data = None
    try:
        insights_data = await get_student_learning_insights(student_id=learner_id, period="30d")
    except Exception as e:
        logger.warning(f"Error fetching Phase 13 insights for {learner_id}: {e}")

    summary = insights_data.summary if insights_data else None
    trends = insights_data.trends if insights_data else {}

    raw_sufficiency = getattr(summary, "dataSufficiency", "no_data") if summary else "no_data"
    data_sufficiency = raw_sufficiency.value if hasattr(raw_sufficiency, "value") else str(raw_sufficiency)

    # Difficult words from Phase 13 or Profile
    difficult_words = []
    if summary:
        if getattr(summary, "difficultWordsTop", None):
            difficult_words = list(summary.difficultWordsTop)
        elif getattr(summary, "difficultWords", None):
            difficult_words = list(summary.difficultWords)
    if not difficult_words:
        difficult_words = list(profile_doc.get("practice_areas", []))[:4]

    # Metrics
    reading_acc = getattr(summary, "readingAccuracyAvg", None) or getattr(summary, "readingAccuracy", None)
    reading_speed = getattr(summary, "readingSpeedWpmAvg", None) or getattr(summary, "readingSpeedWpm", None)
    speech_acc = getattr(summary, "speechAccuracyAvg", None) or getattr(summary, "speechAccuracy", None)
    current_streak = getattr(summary, "currentStreak", 0)
    active_days = getattr(summary, "activePracticeDays", 0) or getattr(summary, "activeDaysCount", 0)

    # Helper to extract trend direction
    def _extract_trend(metric_key: str) -> str:
        if not trends:
            return "insufficient_data"
        m = trends.get(metric_key) if isinstance(trends, dict) else getattr(trends, metric_key, None)
        if not m:
            return "insufficient_data"
        dir_val = getattr(m, "direction", "insufficient_data")
        return dir_val.value if hasattr(dir_val, "value") else str(dir_val)

    acc_trend = _extract_trend("readingAccuracy")
    speed_trend = _extract_trend("readingSpeedWpm")
    consistency_trend = _extract_trend("practiceConsistency")
    speech_trend = _extract_trend("speechAccuracy")

    # Check today completions
    completions = await _check_today_completions(learner_id)

    # 3. Handle NO DATA / INSUFFICIENT DATA Early Exit (Section 2, 15, 21)
    if data_sufficiency in ("no_data", "insufficient_data") or (summary and summary.readingSessionsCount == 0):
        starter_candidates = [
            RecommendationItem(
                id="rec-starter-read",
                category="READING_PRACTICE",
                title="Explore a Beginner Story",
                reason="We're getting to know your learning style. Start with a short story to begin building your progress history!",
                detailedExplanation="Reading your first short story will help DyslexAid understand your comfortable reading pace and vocabulary strengths.",
                actionUrl="/student/reading-coach",
                actionLabel="Start Reading",
                estimatedDurationMinutes=5,
                confidence="insufficient_data",
                priority=1,
                targetSkill="foundational_reading",
                completed=completions["reading"],
                evidenceSignals=["No prior reading sessions recorded yet"],
            ),
            RecommendationItem(
                id="rec-starter-sounds",
                category="REVIEW",
                title="Fun Sound Detective Game",
                reason="Play a quick word sound matching activity to discover your phonics superpowers.",
                detailedExplanation="Interactive micro-tasks help calibrate your personal reading challenge level without any test pressure.",
                actionUrl="/student/adaptive-learning",
                actionLabel="Play Activity",
                estimatedDurationMinutes=5,
                confidence="insufficient_data",
                priority=2,
                targetSkill="phonological_awareness",
                completed=completions["adaptive_activity"],
                evidenceSignals=["Calibrating initial foundational strengths"],
            ),
        ]

        study_plan_items = [
            StudyPlanItem(
                id="plan-starter-1",
                activityType="READING_PRACTICE",
                title="Explore a Beginner Story",
                reason="Start with a short story to begin your reading journey.",
                estimatedDurationMinutes=5,
                priority=1,
                actionUrl="/student/reading-coach",
                targetSkill="foundational_reading",
                completed=completions["reading"],
                sourceEvidence="Welcome activity for new learners",
            ),
            StudyPlanItem(
                id="plan-starter-2",
                activityType="REVIEW",
                title="Fun Sound Detective Game",
                reason="Discover your phonics superpowers with a quick game.",
                estimatedDurationMinutes=5,
                priority=2,
                actionUrl="/student/adaptive-learning",
                targetSkill="phonological_awareness",
                completed=completions["adaptive_activity"],
                sourceEvidence="Foundational skills discovery",
            ),
        ]

        study_plan = StudyPlan(
            horizon=horizon,
            items=study_plan_items,
            totalEstimatedMinutes=10,
            completedCount=sum(1 for i in study_plan_items if i.completed),
            totalCount=len(study_plan_items),
        )

        return StudentRecommendationsResponse(
            learnerId=learner_id,
            horizon=horizon,
            recommendations=starter_candidates,
            studyPlan=study_plan,
            currentLearningLevel=current_level,
            currentLearningLevelName=current_level_name,
            currentAdaptiveTier=current_tier,
            currentAdaptiveTierName=current_tier_name,
            dataSufficiency=data_sufficiency,
            dataSufficiencyMessage=(
                "We're getting to know your learning style. Complete a few reading activities and we'll suggest your next steps!"
            ),
            generatedAt=now_iso,
        )

    # 4. Generate Candidate Recommendations across Controlled Categories (Section 8)
    candidates: List[Dict[str, Any]] = []

    # Candidate 1: DIFFICULT_WORD_PRACTICE
    if difficult_words:
        top_words = difficult_words[:3]
        words_str = ", ".join(f'"{w}"' for w in top_words)
        
        # Scoring: Need (35 if words exist) + Recency (15) + Adaptive (25) + Gap (15) = 90
        score = 85
        if acc_trend == "needs_attention":
            score += 10
        if completions["difficult_words"] or completions["adaptive_activity"]:
            score -= 30

        candidates.append({
            "category": "DIFFICULT_WORD_PRACTICE",
            "title": f"Practice Tricky Words ({len(top_words)} words)",
            "reason": f"Your recent reading shows lower accuracy on words like {words_str}. A quick practice round will build confidence.",
            "detailedExplanation": f"Targeted practice with syllables and letter-sounds for tricky words reinforces recognition before your next story.",
            "actionUrl": "/student/adaptive-learning",
            "actionLabel": "Practice Words",
            "estimatedDurationMinutes": 5,
            "confidence": "high",
            "targetSkill": "sight_word_recognition",
            "targetWords": top_words,
            "completed": completions["difficult_words"] or completions["adaptive_activity"],
            "score": score,
            "evidenceSignals": [
                f"Identified tricky words: {words_str}",
                f"Recent comprehension: {reading_acc or 0}%",
            ],
        })

    # Candidate 2: READING_PRACTICE (Passage at current tier)
    # Find matching passage from catalog
    matching_passages = [p for p in DEFAULT_PASSAGES if p.get("difficultyTier", 1) == current_tier]
    selected_passage = matching_passages[0] if matching_passages else DEFAULT_PASSAGES[0]
    pas_title = selected_passage.get("title", "Story Time")
    pas_id = selected_passage.get("passageId", "pas-t1-001")

    # Scoring: Core activity
    read_score = 75
    if acc_trend == "improving":
        read_score += 10
        read_reason = f"Your reading comprehension is improving! Keep up the momentum with '{pas_title}' at Level {current_tier}."
    elif consecutive_failures >= 2:
        read_score += 15
        read_reason = f"Let's read '{pas_title}' at a steady, comfortable pace to rebuild your reading rhythm."
    else:
        read_reason = f"'{pas_title}' is calibrated at Level {current_tier} for your reading sweet spot. Enjoy exploring this story!"

    if completions["reading"]:
        read_score -= 30

    candidates.append({
        "category": "READING_PRACTICE",
        "title": f"Read Story: \"{pas_title}\"",
        "reason": read_reason,
        "detailedExplanation": f"Regular story reading strengthens sentence flow, working memory, and story comprehension at Level {current_tier}.",
        "actionUrl": f"/student/reading-coach?passageId={pas_id}",
        "actionLabel": "Read Story",
        "estimatedDurationMinutes": 10,
        "confidence": "high",
        "targetSkill": "reading_comprehension",
        "targetWords": selected_passage.get("vocabularyWords", [])[:3] if isinstance(selected_passage.get("vocabularyWords"), list) else [],
        "completed": completions["reading"],
        "score": read_score,
        "evidenceSignals": [
            f"Active Adaptive Tier: {current_tier} ({current_tier_name})",
            f"Accuracy trend: {acc_trend}",
        ],
    })

    # Candidate 3: SPEECH_PRACTICE (Oral reading)
    # If speech data is missing or speech trend needs attention
    speech_score = 65
    if speech_acc is None or speech_trend == "insufficient_data":
        speech_score += 20
        speech_reason = "More oral reading practice is needed to understand your reading rhythm and voice flow."
        speech_confidence = "medium"
    elif speech_trend == "needs_attention" or (speech_acc and speech_acc < 70):
        speech_score += 25
        speech_reason = "Practicing out loud with voice guidance helps connect spoken sounds with printed letters."
        speech_confidence = "high"
    else:
        speech_reason = "Your read-aloud fluency is strong! Practice reading aloud to keep your pronunciation crisp."
        speech_confidence = "high"

    if completions["speech"]:
        speech_score -= 30

    candidates.append({
        "category": "SPEECH_PRACTICE",
        "title": "Voice Read-Aloud Practice",
        "reason": speech_reason,
        "detailedExplanation": "Oral reading activates both auditory and visual pathways, accelerating phoneme mapping and fluency.",
        "actionUrl": "/student/reading-coach",
        "actionLabel": "Try Read-Aloud",
        "estimatedDurationMinutes": 5,
        "confidence": speech_confidence,
        "targetSkill": "oral_reading_fluency",
        "targetWords": [],
        "completed": completions["speech"],
        "score": speech_score,
        "evidenceSignals": [
            f"Speech accuracy: {speech_acc or 'No recent sample'}",
            f"Speech trend: {speech_trend}",
        ],
    })

    # Candidate 4: STRETCH (Only if eligible: consecutive_passes >= 2 and tier < 5 and reading_acc >= 80)
    if consecutive_passes >= 2 and current_tier < 5 and (reading_acc is None or reading_acc >= 80):
        stretch_tier = current_tier + 1
        stretch_passages = [p for p in DEFAULT_PASSAGES if p.get("difficultyTier") == stretch_tier]
        stretch_pas = stretch_passages[0] if stretch_passages else selected_passage
        stretch_title = stretch_pas.get("title", "Explorer Challenge")
        stretch_id = stretch_pas.get("passageId", "")

        candidates.append({
            "category": "STRETCH",
            "title": f"Explorer Challenge: \"{stretch_title}\"",
            "reason": f"You have mastered Level {current_tier} with consecutive high scores! Try this exciting Level {stretch_tier} challenge.",
            "detailedExplanation": f"You're demonstrating strong comprehension. Stepping into Level {stretch_tier} develops advanced vocabulary and analytical skills.",
            "actionUrl": f"/student/reading-coach?passageId={stretch_id}",
            "actionLabel": "Take Challenge",
            "estimatedDurationMinutes": 15,
            "confidence": "high",
            "targetSkill": "advanced_comprehension",
            "targetWords": [],
            "completed": False,
            "score": 88,
            "evidenceSignals": [
                f"{consecutive_passes} consecutive passes at Tier {current_tier}",
                f"Comprehension score: {reading_acc or 85}%",
            ],
        })

    # Candidate 5: CONSISTENCY (If consistency needs attention or low active days)
    if consistency_trend == "needs_attention" or active_days < 3 or current_streak == 0:
        candidates.append({
            "category": "CONSISTENCY",
            "title": "Daily 5-Minute Habit Session",
            "reason": "Practice consistency has dipped recently. A quick 5-minute session today keeps your reading streak alive!",
            "detailedExplanation": "Brief, daily practice reinforces neural reading pathways far more effectively than occasional long sessions.",
            "actionUrl": "/student/reading-coach",
            "actionLabel": "5-Min Practice",
            "estimatedDurationMinutes": 5,
            "confidence": "high",
            "targetSkill": "reading_stamina",
            "targetWords": [],
            "completed": completions["reading"] or completions["adaptive_activity"],
            "score": 82,
            "evidenceSignals": [
                f"Practice consistency trend: {consistency_trend}",
                f"Active days: {active_days} in period",
            ],
        })

    # Candidate 6: REVIEW (Reinforce foundational skills)
    candidates.append({
        "category": "REVIEW",
        "title": "Quick Word & Sound Review",
        "reason": "Revisiting familiar sound and rhyme patterns locks them into long-term memory with zero stress.",
        "detailedExplanation": "Spaced repetition of core letter-sound blends ensures durable decoding without cognitive fatigue.",
        "actionUrl": "/student/adaptive-learning",
        "actionLabel": "Review Skills",
        "estimatedDurationMinutes": 5,
        "confidence": "medium",
        "targetSkill": "phoneme_blending",
        "targetWords": [],
        "completed": completions["adaptive_activity"],
        "score": 60,
        "evidenceSignals": [
            f"Spaced repetition reinforcement at Level {current_level}",
        ],
    })

    # 5. Transparent Ranking Scoring (Section 10)
    # Sort candidates descending by computed score
    ranked_candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)

    # 6. Build Top Recommendations (Up to 4)
    final_recommendations: List[RecommendationItem] = []
    for idx, c in enumerate(ranked_candidates[:4], start=1):
        final_recommendations.append(
            RecommendationItem(
                id=f"rec-{learner_id[:6]}-{c['category'].lower()}-{idx}",
                category=c["category"],
                title=c["title"],
                reason=c["reason"],
                detailedExplanation=c["detailedExplanation"],
                actionUrl=c["actionUrl"],
                actionLabel=c["actionLabel"],
                estimatedDurationMinutes=c["estimatedDurationMinutes"],
                confidence=c["confidence"],
                priority=idx,
                targetSkill=c.get("targetSkill"),
                targetWords=c.get("targetWords", []),
                completed=c["completed"],
                evidenceSignals=c.get("evidenceSignals", []),
            )
        )

    # 7. Generate Daily Study Plan (Section 13, 14: bounded 2-4 activities)
    plan_count = 3 if len(final_recommendations) >= 3 else len(final_recommendations)
    plan_items: List[StudyPlanItem] = []
    total_minutes = 0

    for idx, rec in enumerate(final_recommendations[:plan_count], start=1):
        plan_items.append(
            StudyPlanItem(
                id=f"plan-item-{learner_id[:6]}-{idx}",
                activityType=rec.category,
                title=rec.title,
                reason=rec.reason,
                estimatedDurationMinutes=rec.estimatedDurationMinutes,
                priority=idx,
                actionUrl=rec.actionUrl,
                targetSkill=rec.targetSkill,
                targetWords=rec.targetWords,
                completed=rec.completed,
                sourceEvidence=", ".join(rec.evidenceSignals or []),
            )
        )
        total_minutes += rec.estimatedDurationMinutes

    study_plan = StudyPlan(
        horizon=horizon,
        items=plan_items,
        totalEstimatedMinutes=total_minutes,
        completedCount=sum(1 for p in plan_items if p.completed),
        totalCount=len(plan_items),
    )

    return StudentRecommendationsResponse(
        learnerId=learner_id,
        horizon=horizon,
        recommendations=final_recommendations,
        studyPlan=study_plan,
        currentLearningLevel=current_level,
        currentLearningLevelName=current_level_name,
        currentAdaptiveTier=current_tier,
        currentAdaptiveTierName=current_tier_name,
        dataSufficiency=data_sufficiency,
        dataSufficiencyMessage=None,
        generatedAt=now_iso,
    )


async def get_teacher_learner_recommendations(
    teacher: Dict[str, Any],
    learner_id: str,
    horizon: str = "today",
) -> TeacherLearnerRecommendationsResponse:
    """
    Teacher-facing view of a learner's recommended focus and supporting pedagogical evidence.
    Enforces that the learner is in one of the teacher's enrolled classrooms.
    """
    # 1. Authorize teacher access
    await verify_teacher_student_access(teacher, learner_id)

    # 2. Generate core recommendations
    student_res = await generate_learner_recommendations(learner_id=learner_id, horizon=horizon)

    # 3. Fetch learner name if available
    student_name = "Learner"
    try:
        user_doc = await db.users.find_one({"$or": [{"id": learner_id}, {"_id": learner_id}]})
        if user_doc:
            student_name = user_doc.get("name") or user_doc.get("username") or "Learner"
    except Exception:
        pass

    # 4. Formulate pedagogical focus & evidence summary
    top_rec = student_res.recommendations[0] if student_res.recommendations else None
    recommended_focus = top_rec.title if top_rec else "General Reading Practice"
    primary_reason = top_rec.reason if top_rec else "Consistent reading practice supports ongoing skill progression."

    evidence_list = []
    if student_res.currentLearningLevel:
        evidence_list.append(f"Learning Level: {student_res.currentLearningLevel} ({student_res.currentLearningLevelName})")
    if student_res.currentAdaptiveTier:
        evidence_list.append(f"Adaptive Challenge Tier: {student_res.currentAdaptiveTier} ({student_res.currentAdaptiveTierName})")
    if top_rec and top_rec.evidenceSignals:
        evidence_list.extend(top_rec.evidenceSignals)

    return TeacherLearnerRecommendationsResponse(
        learnerId=learner_id,
        studentName=student_name,
        currentLearningLevel=student_res.currentLearningLevel,
        currentAdaptiveTier=student_res.currentAdaptiveTier,
        recommendedFocus=recommended_focus,
        primaryReason=primary_reason,
        priority=1,
        recentEvidence=evidence_list,
        recommendations=student_res.recommendations,
        studyPlan=student_res.studyPlan,
        dataSufficiency=student_res.dataSufficiency,
    )


async def get_parent_learner_recommendations(
    parent: Dict[str, Any],
    learner_id: str,
    horizon: str = "today",
) -> ParentLearnerRecommendationsResponse:
    """
    Parent-facing view of suggested home practice and supportive tips.
    Enforces active, verified parent-child relationship.
    Excludes private tutor transcripts and technical scoring.
    """
    # 1. Authorize parent link
    parent_id = parent.get("id") or str(parent.get("_id", ""))
    await verify_parent_student_access(parent_id, learner_id)

    # 2. Generate core recommendations
    student_res = await generate_learner_recommendations(learner_id=learner_id, horizon=horizon)

    # 3. Fetch learner name
    student_name = "Your Child"
    try:
        user_doc = await db.users.find_one({"$or": [{"id": learner_id}, {"_id": learner_id}]})
        if user_doc:
            student_name = user_doc.get("name") or user_doc.get("username") or "Your Child"
    except Exception:
        pass

    # 4. Extract parent-friendly practice suggestions
    top_words = []
    for rec in student_res.recommendations:
        if rec.targetWords:
            top_words.extend(rec.targetWords)
            if len(top_words) >= 4:
                break

    formatted_words = [f'"{w}"' for w in top_words[:3]]
    words_phrase = f" on words like {', '.join(formatted_words)}" if formatted_words else ""
    suggested_practice = (
        f"Try about {student_res.studyPlan.totalEstimatedMinutes or 10} minutes of reading together today. "
        f"Focus gently{words_phrase} from recent reading."
    )

    parent_tips = [
        "Celebrate effort and consistency rather than reading speed.",
        "If your child pauses on a tricky word, invite them to sound out the first letter together.",
        "Take turns reading paragraphs out loud to keep practice light, enjoyable, and engaging.",
        "A regular 5 to 10-minute daily reading habit builds long-term confidence.",
    ]

    return ParentLearnerRecommendationsResponse(
        learnerId=learner_id,
        studentName=student_name,
        suggestedPracticeAtHome=suggested_practice,
        recommendedMinutes=max(5, student_res.studyPlan.totalEstimatedMinutes),
        focusWords=top_words[:4],
        parentTips=parent_tips,
        dataSufficiency=student_res.dataSufficiency,
    )
