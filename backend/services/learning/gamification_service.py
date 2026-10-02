"""
backend/services/learning/gamification_service.py — V2 Gamification & Positive Engagement Service.

Coordinates:
1. Transparent, effort-based points system (server-evaluated only).
2. Idempotent reward processing using unique source event identifiers (attemptId, sessionId).
3. Encouraging, non-shaming learning streak calculations across distinct calendar days.
4. Child-friendly achievement badge catalogue with real-time milestone progress.
5. Classroom-tenant-aware teacher summary inspection (without competitive leaderboards).
"""
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

from database.database import db
from core.config import settings
from models.v2_gamification import (
    BadgeDefinition,
    EarnedBadge,
    BadgeProgressItem,
    RewardEvent,
    MilestoneProgressItem,
    GamificationSummary,
    GamificationHistoryResponse,
    RewardEvaluationResult,
)
from services.analytics.teacher_analytics import verify_teacher_student_access

logger = logging.getLogger("dyslexaid.services.gamification")

# ─── Static Achievement Catalogue ─────────────────────────────────────────────

ACHIEVEMENT_CATALOGUE: List[BadgeDefinition] = [
    BadgeDefinition(
        badgeId="first_steps",
        title="First Steps",
        description="Completed your first reading or practice activity.",
        icon="🌱",
        category="milestone",
        threshold=1,
        metricKey="total_activities",
    ),
    BadgeDefinition(
        badgeId="reading_explorer",
        title="Reading Explorer",
        description="Completed 5 guided Reading Coach sessions.",
        icon="📖",
        category="reading",
        threshold=5,
        metricKey="reading_sessions_count",
    ),
    BadgeDefinition(
        badgeId="story_champion",
        title="Story Champion",
        description="Completed 10 guided Reading Coach sessions.",
        icon="📚",
        category="reading",
        threshold=10,
        metricKey="reading_sessions_count",
    ),
    BadgeDefinition(
        badgeId="practice_builder",
        title="Practice Builder",
        description="Completed 10 adaptive learning activities.",
        icon="🧱",
        category="practice",
        threshold=10,
        metricKey="adaptive_attempts_count",
    ),
    BadgeDefinition(
        badgeId="practice_champion",
        title="Practice Champion",
        description="Completed 25 adaptive learning activities.",
        icon="🌟",
        category="practice",
        threshold=25,
        metricKey="adaptive_attempts_count",
    ),
    BadgeDefinition(
        badgeId="word_detective",
        title="Word Detective",
        description="Practiced 10 vocabulary words or spelling patterns.",
        icon="🔍",
        category="vocabulary",
        threshold=10,
        metricKey="vocabulary_words_count",
    ),
    BadgeDefinition(
        badgeId="comprehension_star",
        title="Comprehension Star",
        description="Completed 5 comprehension activities with great understanding (80%+).",
        icon="🧠",
        category="comprehension",
        threshold=5,
        metricKey="high_comprehension_count",
    ),
    BadgeDefinition(
        badgeId="consistency_spark",
        title="Consistency Spark",
        description="Practiced on 3 different days.",
        icon="✨",
        category="streak",
        threshold=3,
        metricKey="streak_days_count",
    ),
    BadgeDefinition(
        badgeId="streak_hero",
        title="Dedicated Learner",
        description="Practiced on 7 different days.",
        icon="🏅",
        category="streak",
        threshold=7,
        metricKey="streak_days_count",
    ),
    BadgeDefinition(
        badgeId="century_club",
        title="Century Milestone",
        description="Earned 100 total learning points through practice.",
        icon="💯",
        category="points",
        threshold=100,
        metricKey="total_points",
    ),
    BadgeDefinition(
        badgeId="super_learner",
        title="Super Learner",
        description="Earned 250 total learning points through practice.",
        icon="🚀",
        category="points",
        threshold=250,
        metricKey="total_points",
    ),
]

ACHIEVEMENT_MAP: Dict[str, BadgeDefinition] = {b.badgeId: b for b in ACHIEVEMENT_CATALOGUE}


# ─── Points Calculation Engine ───────────────────────────────────────────────

def calculate_event_points(
    event_type: str,
    metadata: Dict[str, Any]
) -> Tuple[int, str]:
    """
    Evaluates server-determined points and child-friendly description.
    Never accepts client-specified points.
    """
    base_points = 10
    bonus_points = 0
    desc = "Completed learning practice"

    if event_type == "activity_attempt":
        score = float(metadata.get("scorePercent", metadata.get("score", 0.0)))
        domain = metadata.get("domain", "practice").replace("_", " ").title()
        desc = f"Completed {domain} practice activity"

        if score >= 90.0:
            bonus_points += 5
            desc += " with outstanding accuracy (+5 bonus)"
        elif score >= 80.0:
            bonus_points += 5
            desc += " with solid accuracy (+5 bonus)"

    elif event_type == "reading_session":
        comp_score = float(metadata.get("comprehensionScore", 0.0))
        passage_title = metadata.get("passageTitle", "story")
        desc = f"Finished reading '{passage_title}'"

        if comp_score >= 80.0:
            bonus_points += 5
            desc += " with high comprehension (+5 bonus)"

        words_read = metadata.get("wordsRead", 0)
        words_presented = metadata.get("wordsPresented", 0)
        if words_presented > 0 and words_read >= words_presented:
            bonus_points += 5
            desc += " and completed the entire story (+5 bonus)"

    total = min(25, base_points + bonus_points)
    return total, desc


# ─── Non-Shaming Streak Calculation ──────────────────────────────────────────

async def calculate_learner_streak(user_id: str) -> Tuple[int, int, str, Optional[str]]:
    """
    Calculates current streak and longest streak by inspecting distinct calendar days
    (UTC YYYY-MM-DD) with at least 1 completed learning event.

    Returns:
        (current_streak, longest_streak, encouraging_message, last_active_date)
    """
    # 1. Fetch timestamps from activity_attempts and reading_sessions
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    yesterday_str = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")

    # Fetch attempts
    att_cursor = db.activity_attempts.find(
        {"learnerId": user_id, "completedAt": {"$exists": True}},
        {"completedAt": 1, "_id": 0}
    )
    attempts = await att_cursor.to_list(1000)

    # Fetch reading sessions
    sess_cursor = db.reading_sessions.find(
        {"learnerId": user_id, "completed": True},
        {"createdAt": 1, "completedAt": 1, "_id": 0}
    )
    sessions = await sess_cursor.to_list(1000)

    # Also check reward_events ledger for any legacy/direct records
    rew_cursor = db.reward_events.find(
        {"learnerId": user_id},
        {"createdAt": 1, "_id": 0}
    )
    rewards = await rew_cursor.to_list(1000)

    unique_dates = set()
    for a in attempts:
        ts = a.get("completedAt")
        if ts:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            unique_dates.add(dt)

    for s in sessions:
        ts = s.get("completedAt") or s.get("createdAt")
        if ts:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            unique_dates.add(dt)

    for r in rewards:
        ts = r.get("createdAt")
        if ts:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            unique_dates.add(dt)

    if not unique_dates:
        return 0, 0, "Start your practice journey whenever you are ready!", None

    sorted_dates = sorted(list(unique_dates))
    last_active = sorted_dates[-1]

    # Calculate longest streak across all history
    date_objs = [datetime.strptime(d, "%Y-%m-%d").date() for d in sorted_dates]
    longest = 1
    current_run = 1
    for i in range(1, len(date_objs)):
        if (date_objs[i] - date_objs[i - 1]).days == 1:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    # Calculate active current streak (valid if practiced today or yesterday)
    current_streak = 0
    if today_str in sorted_dates or yesterday_str in sorted_dates:
        start_date = today_str if today_str in sorted_dates else yesterday_str
        ref_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        date_set = set(date_objs)

        curr = ref_date
        while curr in date_set:
            current_streak += 1
            curr -= timedelta(days=1)

    # Construct encouraging, non-punitive message
    if current_streak == 0:
        msg = "Ready for today's practice? Every little bit counts!"
    elif current_streak == 1:
        msg = "Great effort! You practiced today."
    elif current_streak in (2, 3, 4):
        msg = f"Nice work! You practiced on {current_streak} different days. Keep learning at your own pace."
    else:
        msg = f"Awesome dedication! {current_streak} practice days logged. You are doing fantastic!"

    return current_streak, max(longest, current_streak), msg, last_active


# ─── Idempotent Reward Processing ───────────────────────────────────────────

async def process_learning_reward(
    user_id: str,
    source_event_id: str,
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> RewardEvaluationResult:
    """
    Core entrypoint called when an activity or reading session completes:
    1. Checks if source_event_id was already rewarded (idempotency guarantee).
    2. Calculates points and creates an immutable reward event ledger item.
    3. Updates learner's total points and recalculates streaks.
    4. Evaluates achievement badge unlocks.
    5. Returns celebration payload.
    """
    if not metadata:
        metadata = {}

    now = int(time.time())

    # 1. Idempotency Check: Was this source event already processed?
    existing_event = await db.reward_events.find_one(
        {"learnerId": user_id, "sourceEventId": source_event_id}
    )
    if existing_event:
        logger.info(f"Duplicate reward request for event {source_event_id} from user {user_id}. Returning existing state.")
        summary = await get_or_create_summary(user_id)
        return RewardEvaluationResult(
            pointsAwarded=0,
            totalPoints=summary.get("totalPoints", 0),
            newBadges=[],
            currentStreak=summary.get("currentStreak", 0),
            streakMaintained=True,
            celebrationMessage="Activity already recorded. Keep up the good work!",
            isDuplicate=True,
        )

    # 2. Determine points server-side
    points, desc = calculate_event_points(event_type, metadata)
    event_id = f"rew_{uuid.uuid4().hex[:12]}"

    reward_doc = RewardEvent(
        eventId=event_id,
        learnerId=user_id,
        sourceEventId=source_event_id,
        eventType=event_type,
        points=points,
        description=desc,
        metadata=metadata,
        createdAt=now,
    ).model_dump()

    # Insert into ledger
    try:
        await db.reward_events.insert_one(reward_doc)
    except Exception as e:
        # Check if another concurrent call inserted this sourceEventId
        if "duplicate key" in str(e).lower():
            logger.warning(f"Concurrent insert detected for event {source_event_id} user {user_id}.")
            summary = await get_or_create_summary(user_id)
            return RewardEvaluationResult(
                pointsAwarded=0,
                totalPoints=summary.get("totalPoints", 0),
                newBadges=[],
                currentStreak=summary.get("currentStreak", 0),
                streakMaintained=True,
                celebrationMessage=None,
                isDuplicate=True,
            )
        raise

    # 3. Update summary point totals and recalculate streaks
    curr_streak, longest_streak, streak_msg, last_active = await calculate_learner_streak(user_id)

    summary = await get_or_create_summary(user_id)
    longest_streak = max(longest_streak, summary.get("longestStreak", 0))
    new_total_points = summary.get("totalPoints", 0) + points

    # 4. Evaluate achievement unlocks
    new_badges = await evaluate_achievements(
        user_id=user_id,
        current_summary=summary,
        new_total_points=new_total_points,
        current_streak=curr_streak,
    )

    # 5. Persist updated summary
    earned_badge_dicts = summary.get("earnedBadges", [])
    for b in new_badges:
        earned_badge_dicts.append(b.model_dump())

    await db.gamification_summaries.update_one(
        {"learnerId": user_id},
        {
            "$set": {
                "totalPoints": new_total_points,
                "currentStreak": curr_streak,
                "longestStreak": longest_streak,
                "lastActiveDate": last_active,
                "streakMessage": streak_msg,
                "earnedBadges": earned_badge_dicts,
                "updatedAt": now,
            }
        },
        upsert=True
    )

    celebration = f"+{points} Points! {desc}"
    if new_badges:
        badge_titles = ", ".join([b.title for b in new_badges])
        celebration += f" 🏆 New Badge: {badge_titles}!"

    return RewardEvaluationResult(
        pointsAwarded=points,
        totalPoints=new_total_points,
        newBadges=new_badges,
        currentStreak=curr_streak,
        streakMaintained=curr_streak > 0,
        celebrationMessage=celebration,
        isDuplicate=False,
    )


# ─── Achievement Unlock Evaluator ────────────────────────────────────────────

async def evaluate_achievements(
    user_id: str,
    current_summary: Dict[str, Any],
    new_total_points: int,
    current_streak: int,
) -> List[EarnedBadge]:
    """
    Evaluates whether any locked achievements have met their threshold.
    """
    already_earned_ids = {
        b.get("badgeId") if isinstance(b, dict) else b.badgeId
        for b in current_summary.get("earnedBadges", [])
    }

    # Query counts for metrics
    att_count = await db.activity_attempts.count_documents({"learnerId": user_id})
    sess_count = await db.reading_sessions.count_documents({"learnerId": user_id, "completed": True})
    high_comp_count = await db.reading_sessions.count_documents({
        "learnerId": user_id,
        "completed": True,
        "comprehensionAccuracy": {"$gte": 80.0}
    })

    # Count practiced words from completed reading sessions
    sess_cursor = db.reading_sessions.find(
        {"learnerId": user_id, "completed": True},
        {"practicedWords": 1, "_id": 0}
    )
    sessions = await sess_cursor.to_list(100)
    practiced_words_set = set()
    for s in sessions:
        words = s.get("practicedWords") or []
        for w in words:
            practiced_words_set.add(w.lower())
    vocab_count = len(practiced_words_set)

    total_activities = att_count + sess_count

    metrics = {
        "total_activities": total_activities,
        "reading_sessions_count": sess_count,
        "adaptive_attempts_count": att_count,
        "vocabulary_words_count": vocab_count,
        "high_comprehension_count": high_comp_count,
        "streak_days_count": current_streak,
        "total_points": new_total_points,
    }

    now = int(time.time())
    newly_unlocked: List[EarnedBadge] = []

    for badge in ACHIEVEMENT_CATALOGUE:
        if badge.badgeId in already_earned_ids:
            continue

        val = metrics.get(badge.metricKey, 0)
        if val >= badge.threshold:
            newly_unlocked.append(EarnedBadge(
                badgeId=badge.badgeId,
                title=badge.title,
                description=badge.description,
                icon=badge.icon,
                category=badge.category,
                unlockedAt=now,
            ))

    return newly_unlocked


# ─── Summaries, Milestones & History ─────────────────────────────────────────

async def get_or_create_summary(user_id: str) -> Dict[str, Any]:
    """Retrieves or creates initial gamification summary record."""
    summary = await db.gamification_summaries.find_one({"learnerId": user_id}, {"_id": 0})
    if not summary:
        curr_streak, longest_streak, streak_msg, last_active = await calculate_learner_streak(user_id)
        now = int(time.time())
        summary = {
            "learnerId": user_id,
            "totalPoints": 0,
            "currentStreak": curr_streak,
            "longestStreak": longest_streak,
            "lastActiveDate": last_active,
            "streakMessage": streak_msg,
            "earnedBadges": [],
            "updatedAt": now,
        }
        await db.gamification_summaries.update_one(
            {"learnerId": user_id},
            {"$set": summary},
            upsert=True
        )
    return summary


async def get_gamification_summary(user_id: str) -> GamificationSummary:
    """
    Builds the high-level summary response for the learner rewards dashboard.
    """
    summary = await get_or_create_summary(user_id)

    # Re-evaluate streak to ensure it's up to date with the calendar day
    curr_streak, longest_streak, streak_msg, last_active = await calculate_learner_streak(user_id)
    longest_streak = max(longest_streak, summary.get("longestStreak", 0))
    if (curr_streak != summary.get("currentStreak") or
            longest_streak != summary.get("longestStreak") or
            last_active != summary.get("lastActiveDate")):
        summary["currentStreak"] = curr_streak
        summary["longestStreak"] = longest_streak
        summary["lastActiveDate"] = last_active
        summary["streakMessage"] = streak_msg
        await db.gamification_summaries.update_one(
            {"learnerId": user_id},
            {"$set": {
                "currentStreak": curr_streak,
                "longestStreak": longest_streak,
                "lastActiveDate": last_active,
                "streakMessage": streak_msg,
                "updatedAt": int(time.time())
            }}
        )

    earned = [
        EarnedBadge(**b) if isinstance(b, dict) else b
        for b in summary.get("earnedBadges", [])
    ]
    # Sort earned badges by most recent unlock
    earned.sort(key=lambda x: x.unlockedAt, reverse=True)

    # Fetch 5 most recent reward events for quick dashboard celebration feed
    recent_events_cursor = db.reward_events.find(
        {"learnerId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).limit(5)
    recent_events = await recent_events_cursor.to_list(5)

    return GamificationSummary(
        learnerId=user_id,
        totalPoints=summary.get("totalPoints", 0),
        currentStreak=summary.get("currentStreak", 0),
        longestStreak=summary.get("longestStreak", 0),
        lastActiveDate=summary.get("lastActiveDate"),
        streakMessage=summary.get("streakMessage", "Keep learning at your own pace!"),
        earnedBadgesCount=len(earned),
        totalBadgesCount=len(ACHIEVEMENT_CATALOGUE),
        recentBadges=earned[:4],
        recentEvents=recent_events,
        updatedAt=summary.get("updatedAt", int(time.time())),
    )


async def get_achievements_with_progress(user_id: str) -> List[BadgeProgressItem]:
    """
    Returns the complete achievement catalogue with the student's current progress
    and unlock status for each badge.
    """
    summary = await get_or_create_summary(user_id)
    earned_map = {
        (b.get("badgeId") if isinstance(b, dict) else b.badgeId): (b.get("unlockedAt") if isinstance(b, dict) else b.unlockedAt)
        for b in summary.get("earnedBadges", [])
    }

    # Query current metric counts
    att_count = await db.activity_attempts.count_documents({"learnerId": user_id})
    sess_count = await db.reading_sessions.count_documents({"learnerId": user_id, "completed": True})
    high_comp_count = await db.reading_sessions.count_documents({
        "learnerId": user_id,
        "completed": True,
        "comprehensionAccuracy": {"$gte": 80.0}
    })

    sess_cursor = db.reading_sessions.find(
        {"learnerId": user_id, "completed": True},
        {"practicedWords": 1, "_id": 0}
    )
    sessions = await sess_cursor.to_list(100)
    practiced_words_set = set()
    for s in sessions:
        words = s.get("practicedWords") or []
        for w in words:
            practiced_words_set.add(w.lower())
    vocab_count = len(practiced_words_set)

    metrics = {
        "total_activities": att_count + sess_count,
        "reading_sessions_count": sess_count,
        "adaptive_attempts_count": att_count,
        "vocabulary_words_count": vocab_count,
        "high_comprehension_count": high_comp_count,
        "streak_days_count": summary.get("currentStreak", 0),
        "total_points": summary.get("totalPoints", 0),
    }

    result: List[BadgeProgressItem] = []
    for badge in ACHIEVEMENT_CATALOGUE:
        is_unlocked = badge.badgeId in earned_map
        unlocked_at = earned_map.get(badge.badgeId)
        raw_progress = metrics.get(badge.metricKey, 0)
        capped_progress = min(badge.threshold, raw_progress)
        percent = round(min(100.0, (raw_progress / badge.threshold) * 100.0), 1)

        result.append(BadgeProgressItem(
            badgeId=badge.badgeId,
            title=badge.title,
            description=badge.description,
            icon=badge.icon,
            category=badge.category,
            threshold=badge.threshold,
            currentProgress=capped_progress,
            progressPercent=percent,
            unlocked=is_unlocked,
            unlockedAt=unlocked_at,
        ))

    return result


async def get_milestones_progress(user_id: str) -> List[MilestoneProgressItem]:
    """
    Returns upcoming, in-progress milestone targets to motivate next steps.
    """
    badges = await get_achievements_with_progress(user_id)

    # Filter in-progress badges (not yet unlocked) and sort by closest to completion
    in_progress = [b for b in badges if not b.unlocked]
    in_progress.sort(key=lambda x: x.progressPercent, reverse=True)

    milestones: List[MilestoneProgressItem] = []
    for b in in_progress[:3]:
        milestones.append(MilestoneProgressItem(
            milestoneId=b.badgeId,
            title=b.title,
            description=b.description,
            icon=b.icon,
            current=b.currentProgress,
            target=b.threshold,
            progressPercent=b.progressPercent,
            completed=False,
        ))

    # If all badges are unlocked, show completed state
    if not milestones:
        milestones.append(MilestoneProgressItem(
            milestoneId="all_completed",
            title="Mastery Champion",
            description="You have unlocked all current milestone achievements! Keep reading for pure joy!",
            icon="🏆",
            current=100,
            target=100,
            progressPercent=100.0,
            completed=True,
        ))

    return milestones


async def get_reward_history(
    user_id: str,
    page: int = 1,
    limit: int = 20
) -> GamificationHistoryResponse:
    """
    Returns paginated, auditable reward ledger entries for the student.
    """
    page = max(1, page)
    limit = max(1, min(50, limit))
    skip = (page - 1) * limit

    total = await db.reward_events.count_documents({"learnerId": user_id})
    cursor = db.reward_events.find(
        {"learnerId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit)

    events = await cursor.to_list(limit)

    return GamificationHistoryResponse(
        learnerId=user_id,
        totalEvents=total,
        page=page,
        limit=limit,
        events=events,
    )


async def get_teacher_learner_reward_summary(
    teacher: dict,
    student_id: str
) -> Dict[str, Any]:
    """
    Provides an authorized teacher with limited descriptive visibility into a student's
    gamification achievements and practice consistency (without leaderboards).
    """
    await verify_teacher_student_access(teacher, student_id)

    summary = await get_gamification_summary(student_id)
    return {
        "learnerId": student_id,
        "totalPoints": summary.totalPoints,
        "currentStreak": summary.currentStreak,
        "longestStreak": summary.longestStreak,
        "earnedBadgesCount": summary.earnedBadgesCount,
        "recentBadges": [b.model_dump() for b in summary.recentBadges],
        "streakMessage": summary.streakMessage,
        "lastActiveDate": summary.lastActiveDate,
    }
