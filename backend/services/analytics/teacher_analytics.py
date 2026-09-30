"""
backend/services/analytics/teacher_analytics.py — V2 Teacher Analytics Core Service.

Coordinates:
1. Classroom-scoped authorization & tenant isolation
2. Multi-domain cohort overview & aggregation pipelines
3. Individual learner drill-down combining Profile, Adaptive Engine, Reading Coach, and Speech Analysis
4. Longitudinal trend calculation with explicit insufficient-data rules
5. Descriptive educational insights and actionable pedagogical next steps

IMPORTANT:
All analytics are descriptive and educational ONLY.
Zero clinical, neurological, or medical diagnoses are generated or stored.
"""
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status

from database.database import db
from models.v2_teacher_analytics import (
    ClassOverviewMetrics,
    ClassAnalyticsResponse,
    LearnerAnalyticsSummary,
    LearnerAnalyticsDetail,
    DomainPerformanceItem,
    ProgressTrendPoint,
    ProgressTrendSummary,
    TeacherInsight,
    TeacherAction,
)
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    get_learning_state,
    DOMAIN_METADATA,
)

logger = logging.getLogger("dyslexaid.teacher_analytics")

# ─── Time Range Helper ────────────────────────────────────────────────────────

def get_time_cutoff(time_range: str) -> Optional[int]:
    """Returns minimum epoch timestamp for the given time range string."""
    now = int(time.time())
    if time_range == "7d":
        return now - (7 * 86400)
    elif time_range == "30d":
        return now - (30 * 86400)
    elif time_range == "90d":
        return now - (90 * 86400)
    return None  # "all" or unrecognized


# ─── Teacher Authorization & Scoping ──────────────────────────────────────────

async def get_teacher_classroom_code(teacher: dict) -> Optional[str]:
    """Retrieves the active classroom code for an authenticated teacher."""
    code = teacher.get("classroomCode")
    if code:
        return code
    # Fallback lookup in classrooms collection
    c = await db.classrooms.find_one({"teacherId": teacher.get("id")}, {"_id": 0, "code": 1})
    return c.get("code") if c else None


async def verify_teacher_student_access(teacher: dict, student_id: str) -> dict:
    """
    Verifies that the target student is enrolled in the teacher's classroom.
    Raises 403 Forbidden or 404 Not Found if access is unauthorized.
    """
    teacher_code = await get_teacher_classroom_code(teacher)
    if not teacher_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher does not have an active classroom assigned."
        )

    student = await db.users.find_one(
        {"id": student_id, "role": "student"},
        {"_id": 0, "passwordHash": 0}
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    student_classroom = student.get("classroomJoined")
    if student_classroom != teacher_code:
        logger.warning(
            f"Unauthorized teacher analytics access attempt: Teacher {teacher.get('id')} "
            f"(code: {teacher_code}) requested Student {student_id} (code: {student_classroom})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Student is not enrolled in your classroom."
        )

    return student


# ─── Longitudinal Trend Calculation ───────────────────────────────────────────

def evaluate_trend_direction(values: List[float], threshold: float = 3.0) -> str:
    """
    Evaluates trend direction across chronological numerical scores:
    - Fewer than 2 points -> 'insufficient_data'
    - Change > +threshold -> 'improving'
    - Change < -threshold -> 'declining'
    - Otherwise -> 'stable'
    """
    if len(values) < 2:
        return "insufficient_data"

    half = len(values) // 2
    if half == 0:
        first_half = [values[0]]
        second_half = [values[-1]]
    else:
        first_half = values[:half]
        second_half = values[half:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    delta = avg_second - avg_first

    if delta > threshold:
        return "improving"
    elif delta < -threshold:
        return "declining"
    return "stable"


async def calculate_progress_trends(student_id: str, time_range: str = "all") -> ProgressTrendSummary:
    """
    Assembles a chronological timeline of performance across:
    1. Reading comprehension sessions
    2. Speech reading accuracy analyses
    3. Adaptive learning activity attempts
    """
    cutoff = get_time_cutoff(time_range)
    time_filter = {"$gte": cutoff} if cutoff else None

    # 1. Fetch reading sessions
    r_query = {"learnerId": student_id, "completed": True}
    if time_filter:
        r_query["createdAt"] = time_filter
    reading_docs = await db.reading_sessions.find(r_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    # 2. Fetch speech analyses
    s_query = {"learnerId": student_id}
    if time_filter:
        s_query["createdAt"] = time_filter
    speech_docs = await db.speech_reading_analyses.find(s_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    # 3. Fetch activity attempts
    a_query = {"learnerId": student_id}
    if time_filter:
        a_query["completedAt"] = time_filter
    activity_docs = await db.activity_attempts.find(a_query, {"_id": 0}).sort("completedAt", 1).to_list(100)

    # Combine into chronological trend points
    points_by_time: Dict[int, Dict[str, Any]] = {}

    comp_values: List[float] = []
    speech_values: List[float] = []
    activity_values: List[float] = []

    for r in reading_docs:
        ts = int(r.get("createdAt", 0))
        comp = float(r.get("comprehensionScore", 0.0))
        comp_values.append(comp)
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d")
        if ts not in points_by_time:
            points_by_time[ts] = {
                "timestamp": ts,
                "date": date_str,
                "comprehensionScore": comp,
                "difficultyTier": r.get("difficultyTier", 1),
            }
        else:
            points_by_time[ts]["comprehensionScore"] = comp

    for s in speech_docs:
        ts = int(s.get("createdAt", 0))
        acc = float(s.get("accuracyRate", 0.0))
        speech_values.append(acc)
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d")
        if ts not in points_by_time:
            points_by_time[ts] = {"timestamp": ts, "date": date_str, "speechAccuracy": acc}
        else:
            points_by_time[ts]["speechAccuracy"] = acc

    for a in activity_docs:
        ts = int(a.get("completedAt", 0))
        score = float(a.get("scorePercent", 0.0))
        activity_values.append(score)
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d")
        if ts not in points_by_time:
            points_by_time[ts] = {
                "timestamp": ts,
                "date": date_str,
                "activityScore": score,
                "difficultyTier": a.get("difficultyTier", 1),
            }
        else:
            points_by_time[ts]["activityScore"] = score

    sorted_points = [
        ProgressTrendPoint(
            timestamp=p["timestamp"],
            date=p["date"],
            comprehensionScore=p.get("comprehensionScore"),
            speechAccuracy=p.get("speechAccuracy"),
            activityScore=p.get("activityScore"),
            difficultyTier=p.get("difficultyTier"),
        )
        for ts, p in sorted(points_by_time.items())
    ]

    return ProgressTrendSummary(
        readingTrend=evaluate_trend_direction(comp_values),
        speechTrend=evaluate_trend_direction(speech_values),
        adaptiveTrend=evaluate_trend_direction(activity_values),
        points=sorted_points[-20:],  # keep last 20 chronological points
    )


# ─── Educational Insights & Actions Builder ───────────────────────────────────

def build_learner_insights(
    profile: dict,
    learning_state: dict,
    reading_stats: dict,
    speech_signals: dict,
    trends: ProgressTrendSummary,
) -> Tuple[List[TeacherInsight], List[TeacherAction]]:
    """
    Generates descriptive, non-clinical instructional insights and suggested teacher actions
    grounded purely in observed practice data.
    """
    insights: List[TeacherInsight] = []
    actions: List[TeacherAction] = []

    level_info = profile.get("learning_level") or profile.get("learningLevel") or {}
    level_num = int(level_info.get("level") or 2)
    level_name = level_info.get("name", "Developing")
    tier = int(learning_state.get("active_difficulty_tier", 1))

    # 1. Reading Comprehension Insight
    avg_comp = float(reading_stats.get("avgComprehensionAccuracy", 0.0))
    total_sessions = int(reading_stats.get("completedSessions", 0))

    if total_sessions >= 2:
        if avg_comp >= 75.0:
            insights.append(TeacherInsight(
                id="ins-comp-high",
                category="reading",
                type="success",
                title="Strong Reading Comprehension",
                description=f"Demonstrating consistent story comprehension ({avg_comp:.1f}%) across {total_sessions} reading sessions.",
                evidence=f"Average comprehension: {avg_comp:.1f}% across {total_sessions} completed sessions."
            ))
        elif avg_comp < 55.0:
            insights.append(TeacherInsight(
                id="ins-comp-needs-focus",
                category="reading",
                type="warning",
                title="Comprehension Support Opportunity",
                description=f"Story understanding is currently averaging {avg_comp:.1f}%. Guided reading check-ins or pre-reading vocabulary support may help.",
                evidence=f"Recent average: {avg_comp:.1f}% across {total_sessions} completed sessions."
            ))
            actions.append(TeacherAction(
                id="act-comp-guide",
                category="review",
                label="Conduct Guided Story Check-in",
                description="Pair the student with short, interactive questions to break down paragraphs before reading the entire story.",
                target="/teacher/students"
            ))
    else:
        insights.append(TeacherInsight(
            id="ins-comp-limited",
            category="reading",
            type="info",
            title="Early Reading Stage",
            description=f"The learner has completed {total_sessions} reading session(s). Additional sessions will help establish a reliable comprehension trend.",
            evidence=f"Sessions completed: {total_sessions}."
        ))

    # 2. Speech Reading & Word Accuracy Signals
    speech_acc = float(speech_signals.get("avgAccuracyRate") or 0.0)
    wpm = float(speech_signals.get("avgWpm") or 0.0)
    speech_count = int(speech_signals.get("sessionCount") or 0)

    if speech_count >= 2:
        if speech_acc >= 80.0:
            insights.append(TeacherInsight(
                id="ins-speech-strong",
                category="speech",
                type="success",
                title="Solid Read-Aloud Accuracy",
                description=f"Word recognition during read-aloud practice is strong ({speech_acc:.1f}% word accuracy at ~{wpm:.0f} WPM).",
                evidence=f"Speech accuracy: {speech_acc:.1f}% across {speech_count} oral practice sessions."
            ))
        elif speech_acc < 65.0:
            insights.append(TeacherInsight(
                id="ins-speech-focus",
                category="speech",
                type="warning",
                title="Oral Reading Fluency Practice Needed",
                description=f"Read-aloud word recognition is averaging {speech_acc:.1f}%. Phonics drills or syllable highlighting can reinforce tricky words.",
                evidence=f"Word accuracy: {speech_acc:.1f}% at {wpm:.0f} WPM."
            ))
            actions.append(TeacherAction(
                id="act-speech-phonics",
                category="practice",
                label="Assign Phonics & Word Sound Practice",
                description="Encourage the learner to use Focus Mode with syllable highlighting on shorter reading passages.",
                target="/teacher/assignments"
            ))

    # 3. Adaptive Tier & Consistency
    consecutive_passes = int(learning_state.get("consecutive_passes", 0))
    consecutive_failures = int(learning_state.get("consecutive_failures", 0))

    if consecutive_passes >= 3:
        insights.append(TeacherInsight(
            id="ins-adaptive-ready",
            category="adaptive",
            type="success",
            title="Consistently Excelling in Tier Practice",
            description=f"Completed {consecutive_passes} consecutive activities with high mastery. The Adaptive Engine is calibrated appropriately.",
            evidence=f"Current Tier: Tier {tier}. Consecutive passes: {consecutive_passes}."
        ))
        actions.append(TeacherAction(
            id="act-tier-encourage",
            category="assign",
            label="Provide Challenge Story",
            description="Consider recommending a passage one difficulty level higher to explore new vocabulary.",
            target="/teacher/assignments"
        ))
    elif consecutive_failures >= 2:
        insights.append(TeacherInsight(
            id="ins-adaptive-scaffold",
            category="adaptive",
            type="warning",
            title="Scaffolding Active",
            description=f"The learner encountered difficulty on {consecutive_failures} recent tasks. The system has automatically introduced reinforcement practice.",
            evidence=f"Current Tier: Tier {tier}. Consecutive attempts needing practice: {consecutive_failures}."
        ))

    # 4. Top Practice Areas Action
    practice_areas = profile.get("practice_areas") or profile.get("practiceAreas") or []
    if practice_areas:
        top_area = practice_areas[0]
        area_name = top_area.get("friendly_name") or top_area.get("domain") or "Word Practice"
        actions.append(TeacherAction(
            id="act-practice-domain",
            category="review",
            label=f"Review '{area_name}' Goals",
            description=f"Check student engagement in activities targeting '{area_name}' to reinforce core foundational confidence.",
            target="/teacher/students"
        ))

    # Default action if list is empty
    if not actions:
        actions.append(TeacherAction(
            id="act-general-reading",
            category="practice",
            label="Encourage Daily Reading Practice",
            description="Invite the learner to explore a short story in Reading Coach to maintain reading momentum.",
            target="/teacher/students"
        ))

    return insights, actions


# ─── Classroom Overview Aggregation ──────────────────────────────────────────

async def get_class_overview(teacher: dict, time_range: str = "all") -> ClassAnalyticsResponse:
    """
    Computes class-wide overview statistics across all enrolled students
    for an authenticated teacher.
    """
    classroom_code = await get_teacher_classroom_code(teacher)
    if not classroom_code:
        return ClassAnalyticsResponse(
            classroomCode="NONE",
            classroomName=None,
            timeRange=time_range,
            overview=ClassOverviewMetrics(),
            learners=[],
            commonPracticeAreas=[],
            classInsights=[TeacherInsight(
                id="ins-no-class",
                category="engagement",
                type="info",
                title="No Classroom Active",
                description="Create or assign a classroom code to view class analytics."
            )],
        )

    # Fetch classroom metadata
    class_doc = await db.classrooms.find_one({"code": classroom_code}, {"_id": 0})
    class_name = class_doc.get("schoolName") if class_doc else f"Classroom {classroom_code}"

    # Fetch enrolled students
    students = await db.users.find(
        {"role": "student", "classroomJoined": classroom_code},
        {"_id": 0, "passwordHash": 0}
    ).to_list(500)

    if not students:
        return ClassAnalyticsResponse(
            classroomCode=classroom_code,
            classroomName=class_name,
            timeRange=time_range,
            overview=ClassOverviewMetrics(),
            learners=[],
            commonPracticeAreas=[],
            classInsights=[TeacherInsight(
                id="ins-empty-class",
                category="engagement",
                type="info",
                title="Classroom Ready for Students",
                description=f"Share code '{classroom_code}' with students to begin tracking reading and learning analytics."
            )],
        )

    student_ids = [s["id"] for s in students]
    cutoff = get_time_cutoff(time_range)
    time_filter = {"$gte": cutoff} if cutoff else None

    # Aggregated metrics accumulators
    total_learners = len(students)
    screened_count = 0
    active_count = 0
    needs_attention_count = 0
    on_track_count = 0

    level_sum = 0
    tier_sum = 0
    comprehension_scores: List[float] = []
    speech_accuracy_scores: List[float] = []
    wpm_scores: List[float] = []
    total_words_read = 0
    total_minutes_read = 0.0

    practice_area_counts: Dict[str, int] = {}
    learner_summaries: List[LearnerAnalyticsSummary] = []

    for s in students:
        s_id = s["id"]
        # Profile & state
        profile = await get_or_create_learner_profile(s_id)
        state = await get_learning_state(s_id)
        
        is_screened = bool(profile.get("screeningCompleted") or profile.get("screening_completed"))
        if is_screened:
            screened_count += 1

        level_info = profile.get("learning_level") or profile.get("learningLevel") or {}
        level_num = int(level_info.get("level") or 2)
        level_name = level_info.get("name", "Developing")
        level_sum += level_num

        tier = int(state.get("active_difficulty_tier", 1))
        tier_sum += tier

        # Strengths & practice areas
        raw_strengths = profile.get("strengths") or []
        s_strengths = [st.get("friendly_name") or st.get("domain") for st in raw_strengths if isinstance(st, dict)]
        if not s_strengths:
            s_strengths = [str(st) for st in raw_strengths if isinstance(st, str)]

        raw_practice = profile.get("practice_areas") or []
        s_practice = [pr.get("friendly_name") or pr.get("domain") for pr in raw_practice if isinstance(pr, dict)]
        if not s_practice:
            s_practice = [str(pr) for pr in raw_practice if isinstance(pr, str)]

        for pa in s_practice:
            practice_area_counts[pa] = practice_area_counts.get(pa, 0) + 1

        # Reading sessions
        r_query = {"learnerId": s_id, "completed": True}
        if time_filter:
            r_query["createdAt"] = time_filter
        sessions = await db.reading_sessions.find(r_query, {"_id": 0}).sort("createdAt", -1).to_list(100)

        s_words = sum(sess.get("wordsRead", 0) for sess in sessions)
        s_duration = sum(sess.get("durationSeconds", 0) for sess in sessions)
        total_words_read += s_words
        total_minutes_read += round(float(s_duration) / 60.0, 1)

        s_comp_scores = [sess.get("comprehensionScore", 0.0) for sess in sessions]
        avg_comp = round(sum(s_comp_scores) / len(s_comp_scores), 1) if s_comp_scores else 0.0
        if s_comp_scores:
            comprehension_scores.append(avg_comp)

        # Speech readings
        sp_query = {"learnerId": s_id}
        if time_filter:
            sp_query["createdAt"] = time_filter
        speech_docs = await db.speech_reading_analyses.find(sp_query, {"_id": 0}).sort("createdAt", -1).to_list(50)

        s_acc_list = [sp.get("accuracyRate", 0.0) for sp in speech_docs]
        s_wpm_list = [sp.get("wordsPerMinute", 0.0) for sp in speech_docs]
        latest_acc = round(sum(s_acc_list) / len(s_acc_list), 1) if s_acc_list else None
        latest_wpm = round(sum(s_wpm_list) / len(s_wpm_list), 1) if s_wpm_list else None

        if latest_acc is not None:
            speech_accuracy_scores.append(latest_acc)
        if latest_wpm is not None:
            wpm_scores.append(latest_wpm)

        # Activity presence
        has_activity = bool(sessions or speech_docs)
        if has_activity:
            active_count += 1

        # Evaluate learner status
        if not is_screened:
            learner_status = "not_screened"
        elif (avg_comp > 0 and avg_comp < 50.0) or (latest_acc and latest_acc < 60.0):
            learner_status = "needs_attention"
            needs_attention_count += 1
        elif avg_comp >= 65.0 or (latest_acc and latest_acc >= 75.0):
            learner_status = "on_track"
            on_track_count += 1
        else:
            learner_status = "progressing"

        # Reading trend
        reading_trend = evaluate_trend_direction(s_comp_scores)

        # Last active date string
        last_active_str = "Never"
        if sessions:
            last_ts = sessions[0].get("createdAt", 0)
            last_active_str = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%b %d, %Y")
        elif s.get("createdAt"):
            last_active_str = datetime.fromtimestamp(s["createdAt"], tz=timezone.utc).strftime("%b %d, %Y")

        learner_summaries.append(LearnerAnalyticsSummary(
            studentId=s_id,
            name=s.get("name", "Student"),
            email=s.get("email", ""),
            learningLevel=level_num,
            learningLevelName=level_name,
            adaptiveTier=tier,
            screeningCompleted=is_screened,
            avgComprehension=avg_comp,
            speechAccuracy=latest_acc,
            wordsPerMinute=latest_wpm,
            totalSessions=len(sessions),
            wordsRead=s_words,
            streak=int(state.get("current_streak", 0)),
            lastActive=last_active_str,
            status=learner_status,
            strengths=s_strengths[:3],
            practiceAreas=s_practice[:3],
            readingTrend=reading_trend,
        ))

    # Activity attempts count in classroom
    act_query = {"learnerId": {"$in": student_ids}}
    if time_filter:
        act_query["completedAt"] = time_filter
    total_attempts = await db.activity_attempts.count_documents(act_query)

    # Class-wide averages
    avg_learning_lvl = round(level_sum / total_learners, 1) if total_learners else 2.0
    avg_adaptive_tr = round(tier_sum / total_learners, 1) if total_learners else 1.0
    avg_comp_overall = round(sum(comprehension_scores) / len(comprehension_scores), 1) if comprehension_scores else 0.0
    avg_speech_acc = round(sum(speech_accuracy_scores) / len(speech_accuracy_scores), 1) if speech_accuracy_scores else 0.0
    avg_wpm_overall = round(sum(wpm_scores) / len(wpm_scores), 1) if wpm_scores else 0.0

    overview_metrics = ClassOverviewMetrics(
        totalLearners=total_learners,
        activeLearners=active_count,
        screenedLearners=screened_count,
        needsAttentionCount=needs_attention_count,
        onTrackCount=on_track_count,
        avgLearningLevel=avg_learning_lvl,
        avgAdaptiveTier=avg_adaptive_tr,
        avgReadingComprehension=avg_comp_overall,
        avgSpeechAccuracy=avg_speech_acc,
        avgWordsPerMinute=avg_wpm_overall,
        totalWordsRead=total_words_read,
        totalMinutesRead=round(total_minutes_read, 1),
        activityAttemptsCount=total_attempts,
    )

    # Top class-wide common practice areas
    sorted_practice = sorted(practice_area_counts.items(), key=lambda x: x[1], reverse=True)
    common_practice_list = [
        {"area": name, "learnerCount": count, "percentage": round((count / total_learners) * 100)}
        for name, count in sorted_practice[:5]
    ]

    # Generate Class-wide Educational Insights
    class_insights: List[TeacherInsight] = []

    if screened_count == total_learners and total_learners > 0:
        class_insights.append(TeacherInsight(
            id="ins-class-screened",
            category="engagement",
            type="success",
            title="All Learners Screened",
            description=f"100% of learners in {class_name} have established baseline learning profiles.",
            evidence=f"{screened_count}/{total_learners} students screened."
        ))
    elif screened_count < total_learners:
        unscreened = total_learners - screened_count
        class_insights.append(TeacherInsight(
            id="ins-class-unscreened",
            category="engagement",
            type="warning",
            title="Screening Check Recommended",
            description=f"{unscreened} student(s) have not yet completed the initial learning check.",
            evidence=f"{screened_count} of {total_learners} learners screened."
        ))

    if common_practice_list:
        top_focus = common_practice_list[0]["area"]
        class_insights.append(TeacherInsight(
            id="ins-class-focus",
            category="reading",
            type="info",
            title=f"Common Cohort Focus: {top_focus}",
            description=f"'{top_focus}' is the most frequent growth focus across the class ({common_practice_list[0]['percentage']}% of students).",
            evidence=f"Appears in {common_practice_list[0]['learnerCount']} student profiles."
        ))

    if total_words_read > 0:
        class_insights.append(TeacherInsight(
            id="ins-class-volume",
            category="reading",
            type="success",
            title="Active Reading Practice",
            description=f"The class has read a cumulative {total_words_read:,} words across {round(total_minutes_read, 1)} minutes of practice.",
            evidence=f"Total practice minutes: {round(total_minutes_read, 1)} min."
        ))

    return ClassAnalyticsResponse(
        classroomCode=classroom_code,
        classroomName=class_name,
        timeRange=time_range,
        overview=overview_metrics,
        learners=learner_summaries,
        commonPracticeAreas=common_practice_list,
        classInsights=class_insights,
    )


# ─── Individual Learner Analytics Detail ──────────────────────────────────────

async def get_classroom_learners(teacher: dict, time_range: str = "all") -> List[LearnerAnalyticsSummary]:
    """Retrieves learner summary roster for the teacher."""
    overview_resp = await get_class_overview(teacher, time_range=time_range)
    return overview_resp.learners


async def get_learner_analytics_detail(
    teacher: dict,
    student_id: str,
    time_range: str = "all",
) -> LearnerAnalyticsDetail:
    """
    Assembles a comprehensive, multi-domain analytics drill-down for a single authorized learner.
    Enforces classroom tenant isolation.
    """
    student = await verify_teacher_student_access(teacher, student_id)
    classroom_code = student.get("classroomJoined", "")

    # 1. Profile and Learning State
    profile = await get_or_create_learner_profile(student_id)
    state = await get_learning_state(student_id)

    level_info = profile.get("learning_level") or profile.get("learningLevel") or {}
    level_num = int(level_info.get("level") or 2)
    level_name = level_info.get("name", "Developing")
    tier = int(state.get("active_difficulty_tier", 1))
    screening_completed = bool(profile.get("screeningCompleted") or profile.get("screening_completed"))

    # Strengths & practice areas
    strengths = profile.get("strengths") or []
    practice_areas = profile.get("practice_areas") or []

    # Domain interpretations & scores
    domain_items: List[DomainPerformanceItem] = []
    interpretations = profile.get("domain_interpretations") or {}
    domain_scores = profile.get("domain_scores") or {}

    strength_keys = {s.get("domain") for s in strengths if isinstance(s, dict)}
    practice_keys = {p.get("domain") for p in practice_areas if isinstance(p, dict)}

    # Iterate over active domains dynamically
    for d_key, meta in DOMAIN_METADATA.items():
        interp = interpretations.get(d_key) or {}
        score = float(domain_scores.get(d_key, 60.0))
        label = interp.get("label", "Developing")
        friendly_name = interp.get("friendly_name") or meta.get("friendly_name", d_key.replace("_", " ").title())
        desc = interp.get("description") or meta.get("description", "")

        domain_items.append(DomainPerformanceItem(
            domainKey=d_key,
            domainName=friendly_name,
            score=round(score, 1),
            label=label,
            description=desc,
            isStrength=d_key in strength_keys,
            isPracticeArea=d_key in practice_keys,
        ))

    # 2. Reading sessions and metrics
    cutoff = get_time_cutoff(time_range)
    time_filter = {"$gte": cutoff} if cutoff else None

    r_query = {"learnerId": student_id, "completed": True}
    if time_filter:
        r_query["createdAt"] = time_filter
    reading_sessions = await db.reading_sessions.find(r_query, {"_id": 0}).sort("createdAt", -1).to_list(100)

    total_reading_sessions = len(reading_sessions)
    total_words = sum(s.get("wordsRead", 0) for s in reading_sessions)
    total_duration_sec = sum(s.get("durationSeconds", 0) for s in reading_sessions)
    comp_list = [s.get("comprehensionScore", 0.0) for s in reading_sessions]
    avg_comp = round(sum(comp_list) / len(comp_list), 1) if comp_list else 0.0

    reading_metrics = {
        "completedSessions": total_reading_sessions,
        "totalWordsRead": total_words,
        "totalMinutesRead": round(float(total_duration_sec) / 60.0, 1),
        "avgComprehensionAccuracy": avg_comp,
        "currentTier": tier,
        "trend": evaluate_trend_direction(comp_list),
    }

    # Format recent 5 reading sessions
    recent_reading_sessions = []
    for s in reading_sessions[:5]:
        ts = int(s.get("createdAt", 0))
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d, %Y")
        recent_reading_sessions.append({
            "sessionId": s.get("sessionId"),
            "passageId": s.get("passageId"),
            "date": date_str,
            "comprehensionScore": round(float(s.get("comprehensionScore", 0.0)), 1),
            "wordsRead": s.get("wordsRead", 0),
            "durationSeconds": s.get("durationSeconds", 0),
            "readingMode": s.get("readingMode", "silent"),
            "overallScore": round(float(s.get("overallScore", 0.0)), 1),
        })

    # 3. Speech reading signals (Derived signals only, zero raw audio)
    sp_query = {"learnerId": student_id}
    if time_filter:
        sp_query["createdAt"] = time_filter
    speech_docs = await db.speech_reading_analyses.find(sp_query, {"_id": 0}).sort("createdAt", -1).to_list(50)

    acc_list = [sp.get("accuracyRate", 0.0) for sp in speech_docs]
    wpm_list = [sp.get("wordsPerMinute", 0.0) for sp in speech_docs]
    avg_acc = round(sum(acc_list) / len(acc_list), 1) if acc_list else None
    avg_wpm = round(sum(wpm_list) / len(wpm_list), 1) if wpm_list else None

    speech_signals = {
        "sessionCount": len(speech_docs),
        "avgAccuracyRate": avg_acc,
        "avgWpm": avg_wpm,
        "latestScore": round(float(speech_docs[0].get("readingPracticeScore", 0.0)), 1) if speech_docs else None,
        "latestCoverage": round(float(speech_docs[0].get("coverageRate", 0.0)), 1) if speech_docs else None,
    }

    # 4. Adaptive learning state
    adaptive_state_dict = {
        "activeDifficultyTier": tier,
        "currentModule": state.get("current_module", "reading_foundations"),
        "todayTasksCompleted": state.get("today_tasks_completed", 0),
        "todayTasksAssigned": state.get("today_tasks_assigned", 3),
        "currentStreak": state.get("current_streak", 0),
        "consecutivePasses": state.get("consecutive_passes", 0),
        "consecutiveFailures": state.get("consecutive_failures", 0),
        "recommendedNextAction": state.get("recommended_next_action", "daily_reading_practice"),
    }

    # Recent activity attempts
    act_query = {"learnerId": student_id}
    if time_filter:
        act_query["completedAt"] = time_filter
    attempts_docs = await db.activity_attempts.find(act_query, {"_id": 0}).sort("completedAt", -1).to_list(5)
    recent_attempts = []
    for a in attempts_docs:
        ts = int(a.get("completedAt", 0))
        recent_attempts.append({
            "activityId": a.get("activityId"),
            "domain": a.get("domain", ""),
            "difficultyTier": a.get("difficultyTier", 1),
            "scorePercent": round(float(a.get("scorePercent", 0.0)), 1),
            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d, %Y"),
        })

    # 5. Longitudinal progress trends
    trends = await calculate_progress_trends(student_id, time_range=time_range)

    # 6. Educational insights and teacher actions
    insights, actions = build_learner_insights(
        profile=profile,
        learning_state=state,
        reading_stats=reading_metrics,
        speech_signals=speech_signals,
        trends=trends,
    )

    return LearnerAnalyticsDetail(
        studentId=student_id,
        name=student.get("name", "Student"),
        email=student.get("email", ""),
        classroomCode=classroom_code,
        learningLevel=level_num,
        learningLevelName=level_name,
        adaptiveTier=tier,
        screeningCompleted=screening_completed,
        confidence=profile.get("confidence"),
        strengths=strengths,
        practiceAreas=practice_areas,
        domainScores=domain_items,
        readingMetrics=reading_metrics,
        speechSignals=speech_signals,
        adaptiveState=adaptive_state_dict,
        recentReadingSessions=recent_reading_sessions,
        recentActivityAttempts=recent_attempts,
        trends=trends,
        insights=insights,
        suggestedActions=actions,
    )
