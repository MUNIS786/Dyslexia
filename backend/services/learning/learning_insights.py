"""
backend/services/learning/learning_insights.py — Learning Insights & Progress Reports Core Service.

Coordinates:
1. Multi-window time aggregation (7d, 30d, 90d) using UTC timestamps
2. Data extraction from existing collections:
   - reading_sessions (Phase 4)
   - speech_reading_analyses (Phase 5)
   - activity_attempts (Phase 3)
   - learning_states (Phase 3)
   - learner_profiles (Phase 2)
   - gamification_summaries (Phase 9)
   - interventions (Phase 8)
   - parent_links (Phase 11)
3. Explainable trend calculations (Improving, Stable, Needs Attention, Insufficient Data)
4. Data sufficiency classification (No Data, Insufficient Data, Sufficient Data)
5. Accessible daily timeline series for frontend SVG charts
6. Teacher classroom overview aggregation and drill-downs
7. Simplified, non-jargon parent progress summaries
8. Non-clinical educational language and safeguards
"""
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status

from database.database import db
from models.v2_learning_insights import (
    TrendDirection,
    DataSufficiencyStatus,
    MetricTrend,
    TimelineDataPoint,
    StudentProgressSummary,
    StudentInsightsResponse,
    LearnerInsightCardItem,
    ClassInsightsOverviewResponse,
    ParentInsightsResponse,
)
from services.analytics.teacher_analytics import (
    verify_teacher_student_access,
    get_teacher_classroom_code,
)
from services.parent.parent_service import (
    verify_parent_student_access,
)

logger = logging.getLogger("dyslexaid.learning_insights")

VALID_PERIODS = ("7d", "30d", "90d")


def parse_reporting_period(period_str: str) -> Tuple[int, int, int, int]:
    """
    Validates and parses reporting period.
    Returns: (days, period_start_ts, period_end_ts, prior_start_ts)
    """
    if period_str not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid reporting period '{period_str}'. Allowed periods: {list(VALID_PERIODS)}",
        )
    days = int(period_str.replace("d", ""))
    now_ts = int(time.time())
    period_seconds = days * 86400
    period_start = now_ts - period_seconds
    prior_start = period_start - period_seconds
    return days, period_start, now_ts, prior_start


def _calculate_trend(
    metric_key: str,
    unit: str,
    curr_val: Optional[float],
    prior_val: Optional[float],
    improving_threshold: float = 3.0,
    higher_is_better: bool = True,
    metric_name_human: str = "Metric",
) -> MetricTrend:
    """
    Computes delta and direction between current and prior windows.
    Returns a standardized MetricTrend instance.
    """
    if curr_val is None or prior_val is None:
        return MetricTrend(
            metric=metric_key,
            currentValue=curr_val,
            previousValue=prior_val,
            change=None,
            unit=unit,
            direction=TrendDirection.INSUFFICIENT_DATA,
            label="Not Enough Data",
            message=f"Complete more practice sessions across periods to determine your {metric_name_human.lower()} trend.",
        )

    delta = round(curr_val - prior_val, 1)

    if higher_is_better:
        if delta >= improving_threshold:
            direction = TrendDirection.IMPROVING
            label = f"Improving (+{delta}{unit})"
            message = f"Your {metric_name_human.lower()} is improving! Great dedication."
        elif delta <= -improving_threshold:
            direction = TrendDirection.NEEDS_ATTENTION
            label = f"Needs Practice ({delta}{unit})"
            message = f"Your {metric_name_human.lower()} dipped slightly. A bit of extra practice will build confidence."
        else:
            direction = TrendDirection.STABLE
            label = f"Steady ({delta:+}{unit})"
            message = f"Your {metric_name_human.lower()} is steady and consistent."
    else:
        # Lower is better (e.g. hesitation, mistakes)
        if delta <= -improving_threshold:
            direction = TrendDirection.IMPROVING
            label = f"Improving ({delta}{unit})"
            message = f"Your {metric_name_human.lower()} is improving with fewer interruptions!"
        elif delta >= improving_threshold:
            direction = TrendDirection.NEEDS_ATTENTION
            label = f"Needs Practice (+{delta}{unit})"
            message = f"Take your time and focus on one sentence at a time."
        else:
            direction = TrendDirection.STABLE
            label = f"Steady ({delta:+}{unit})"
            message = f"Your {metric_name_human.lower()} is steady."

    return MetricTrend(
        metric=metric_key,
        currentValue=curr_val,
        previousValue=prior_val,
        change=delta,
        unit=unit,
        direction=direction,
        label=label,
        message=message,
    )


async def get_student_learning_insights(
    learner_id: Optional[str] = None,
    period: str = "30d",
    student_id: Optional[str] = None,
) -> StudentInsightsResponse:
    """
    Aggregates learning records for a student across all V2 domains
    and computes descriptive progress summaries, trends, timeline, and suggestions.
    """
    lid = learner_id or student_id or ""
    days, period_start, now_ts, prior_start = parse_reporting_period(period)

    query = {"$or": [{"learnerId": lid}, {"student_id": lid}, {"studentId": lid}, {"learner_id": lid}]}

    # 1. Query reading sessions
    sessions_cursor = db.reading_sessions.find(query)
    sessions = await sessions_cursor.to_list(length=500) if hasattr(sessions_cursor, "to_list") else []

    # 2. Query speech reading analyses
    speech_cursor = db.speech_reading_analyses.find(query)
    speech_analyses = await speech_cursor.to_list(length=500) if hasattr(speech_cursor, "to_list") else []

    # 3. Query activity attempts
    attempts_cursor = db.activity_attempts.find(query)
    attempts = await attempts_cursor.to_list(length=500) if hasattr(attempts_cursor, "to_list") else []

    # 4. Query current adaptive state
    state_doc = await db.learning_states.find_one(query)
    tier = 1
    tier_name = "Foundation"
    level = 1
    level_name = "Foundation"
    if state_doc:
        tier = state_doc.get("activeDifficultyTier") or state_doc.get("adaptive_tier") or state_doc.get("tier") or 1
        tier_name = state_doc.get("tierName") or state_doc.get("tier_name") or "Foundation"
        level = state_doc.get("currentLevel") or state_doc.get("current_level") or state_doc.get("level") or 1
        level_name = state_doc.get("levelName") or state_doc.get("level_name") or "Foundation"

    # 5. Query learner profile
    profile_doc = await db.learner_profiles.find_one(query)
    if profile_doc:
        lvl_data = profile_doc.get("learningLevel", {})
        if isinstance(lvl_data, dict):
            level = lvl_data.get("level", level)
            level_name = lvl_data.get("name", level_name)
        elif isinstance(lvl_data, int):
            level = lvl_data

    # 6. Query gamification summary
    gamification_doc = await db.gamification_summaries.find_one(query)
    streak = 0
    if gamification_doc:
        streak = gamification_doc.get("currentStreak") or gamification_doc.get("streak_days") or gamification_doc.get("streak") or 0
    elif state_doc:
        streak = state_doc.get("currentStreak", 0)

    # 7. Query active interventions
    interventions_cursor = db.interventions.find(query)
    all_interventions = await interventions_cursor.to_list(length=100) if hasattr(interventions_cursor, "to_list") else []
    active_interventions_count = len([i for i in all_interventions if i.get("status") in ("active", "review")])

    def get_ts(item):
        return item.get("completedAt") or item.get("completed_at") or item.get("created_at") or item.get("createdAt") or 0

    # Split sessions into current and prior periods
    curr_sessions = [s for s in sessions if get_ts(s) >= period_start]
    prior_sessions = [s for s in sessions if prior_start <= get_ts(s) < period_start]

    curr_speech = [s for s in speech_analyses if get_ts(s) >= period_start]
    prior_speech = [s for s in speech_analyses if prior_start <= get_ts(s) < period_start]

    curr_attempts = [a for a in attempts if get_ts(a) >= period_start]
    prior_attempts = [a for a in attempts if prior_start <= get_ts(a) < period_start]

    # Calculate Current Window Metrics
    reading_sessions_count = len(curr_sessions)
    words_attempted = sum(s.get("wordsRead") or s.get("wordsPresented", 0) for s in curr_sessions)

    def get_acc(item):
        for k in ("comprehensionAccuracy", "accuracy_score", "accuracyScore", "readingAccuracy", "accuracy", "overallScore", "score"):
            val = item.get(k)
            if val is not None and isinstance(val, (int, float)) and val > 0:
                return float(val)
        return None

    def get_wpm(item):
        for k in ("wordsPerMinute", "speed_wpm", "speedWpm", "wpm", "reading_speed_wpm"):
            val = item.get(k)
            if val is not None and isinstance(val, (int, float)) and val > 0:
                return float(val)
        return None

    def get_speech_acc(item):
        for k in ("wordAccuracy", "overall_accuracy", "accuracy_score", "accuracyScore", "accuracy"):
            val = item.get(k)
            if val is not None and isinstance(val, (int, float)) and val > 0:
                return float(val)
        return None

    # Reading Accuracy
    acc_scores = [get_acc(s) for s in curr_sessions if get_acc(s) is not None]
    curr_acc_avg = round(sum(acc_scores) / len(acc_scores), 1) if acc_scores else None

    prior_acc_scores = [get_acc(s) for s in prior_sessions if get_acc(s) is not None]
    prior_acc_avg = round(sum(prior_acc_scores) / len(prior_acc_scores), 1) if prior_acc_scores else None

    # Intra-window comparison if student has sessions in current window but none in prior
    if prior_acc_avg is None and len(acc_scores) >= 2:
        mid = len(acc_scores) // 2
        prior_acc_avg = round(sum(acc_scores[:mid]) / mid, 1)
        curr_acc_avg = round(sum(acc_scores[mid:]) / (len(acc_scores) - mid), 1)

    # Reading Speed (WPM)
    wpm_list = [get_wpm(s) for s in curr_speech if get_wpm(s) is not None]
    if not wpm_list:
        wpm_list = [get_wpm(s) for s in curr_sessions if get_wpm(s) is not None]
    if not wpm_list:
        for s in curr_sessions:
            words = s.get("wordsRead") or s.get("words_read_count") or 0
            duration = s.get("durationSeconds") or s.get("duration_seconds") or 0
            if words > 0 and duration >= 10:
                wpm_list.append(round((words / duration) * 60, 1))
    curr_wpm_avg = round(sum(wpm_list) / len(wpm_list), 1) if wpm_list else None

    prior_wpm_list = [get_wpm(s) for s in prior_speech if get_wpm(s) is not None]
    if not prior_wpm_list:
        prior_wpm_list = [get_wpm(s) for s in prior_sessions if get_wpm(s) is not None]
    prior_wpm_avg = round(sum(prior_wpm_list) / len(prior_wpm_list), 1) if prior_wpm_list else None
    if prior_wpm_avg is None and len(wpm_list) >= 2:
        mid = len(wpm_list) // 2
        prior_wpm_avg = round(sum(wpm_list[:mid]) / mid, 1)
        curr_wpm_avg = round(sum(wpm_list[mid:]) / (len(wpm_list) - mid), 1)

    # Speech Accuracy
    speech_acc_list = [get_speech_acc(s) for s in curr_speech if get_speech_acc(s) is not None]
    curr_speech_acc_avg = round(sum(speech_acc_list) / len(speech_acc_list), 1) if speech_acc_list else None

    prior_speech_acc_list = [get_speech_acc(s) for s in prior_speech if get_speech_acc(s) is not None]
    prior_speech_acc_avg = round(sum(prior_speech_acc_list) / len(prior_speech_acc_list), 1) if prior_speech_acc_list else None
    if prior_speech_acc_avg is None and len(speech_acc_list) >= 2:
        mid = len(speech_acc_list) // 2
        prior_speech_acc_avg = round(sum(speech_acc_list[:mid]) / mid, 1)
        curr_speech_acc_avg = round(sum(speech_acc_list[mid:]) / (len(speech_acc_list) - mid), 1)

    # Coverage Rate
    coverage_list = [s.get("coverageRate") for s in curr_speech if s.get("coverageRate") is not None]
    speech_cov_avg = round(sum(coverage_list) / len(coverage_list), 1) if coverage_list else None

    # Practice Score
    practice_scores = [s.get("readingPracticeScore") for s in curr_speech if s.get("readingPracticeScore") is not None]
    if not practice_scores:
        practice_scores = [s.get("overallScore") for s in curr_sessions if s.get("overallScore") is not None]
    practice_score_avg = round(sum(practice_scores) / len(practice_scores), 1) if practice_scores else None

    # Active Practice Days (unique calendar dates in UTC)
    unique_dates = set()
    for s in curr_sessions:
        ts = s.get("completedAt") or s.get("createdAt", 0)
        if ts:
            unique_dates.add(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
    for a in curr_attempts:
        ts = a.get("completedAt", 0)
        if ts:
            unique_dates.add(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
    active_days_count = len(unique_dates)

    prior_unique_dates = set()
    for s in prior_sessions:
        ts = s.get("completedAt") or s.get("createdAt", 0)
        if ts:
            prior_unique_dates.add(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
    for a in prior_attempts:
        ts = a.get("completedAt", 0)
        if ts:
            prior_unique_dates.add(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
    prior_active_days_count = len(prior_unique_dates)

    # Difficult words
    difficult_words_set = set()
    for s in curr_sessions:
        for w in s.get("difficultWords", []):
            if isinstance(w, str) and w.strip():
                difficult_words_set.add(w.strip().lower())
    difficult_words_top = sorted(list(difficult_words_set))[:8]

    # Data Sufficiency Assessment
    total_lifetime = len(sessions) + len(attempts) + len(speech_analyses)
    total_window_events = reading_sessions_count + len(curr_attempts) + len(curr_speech)

    if total_lifetime == 0:
        data_sufficiency = DataSufficiencyStatus.NO_DATA
        sufficiency_msg = (
            "No learning activity recorded yet. Complete a reading session in the Reading Coach "
            "to begin building your progress history and insights!"
        )
    elif total_lifetime == 1 or total_window_events < 2:
        data_sufficiency = DataSufficiencyStatus.INSUFFICIENT_DATA
        sufficiency_msg = (
            "Great start on your reading journey! Complete a few more sessions to build "
            "clear progress trends and personalized insights."
        )
    else:
        data_sufficiency = DataSufficiencyStatus.SUFFICIENT_DATA
        sufficiency_msg = (
            f"You have active practice logged over the last {days} days. "
            "Here are your personalized reading trends and skill progress!"
        )

    # Trends computation
    trends: Dict[str, MetricTrend] = {}

    # 1. Reading Accuracy Trend
    trends["reading_accuracy"] = _calculate_trend(
        metric_key="reading_accuracy",
        unit="%",
        curr_val=curr_acc_avg,
        prior_val=prior_acc_avg,
        improving_threshold=3.0,
        higher_is_better=True,
        metric_name_human="Reading Accuracy",
    )

    # 2. Reading Speed Trend
    speed_trend = _calculate_trend(
        metric_key="reading_speed_wpm",
        unit=" WPM",
        curr_val=curr_wpm_avg,
        prior_val=prior_wpm_avg,
        improving_threshold=3.0,
        higher_is_better=True,
        metric_name_human="Reading Speed",
    )
    trends["reading_speed"] = speed_trend
    trends["reading_speed_wpm"] = speed_trend

    # 3. Speech Reading Accuracy Trend
    trends["speech_accuracy"] = _calculate_trend(
        metric_key="speech_accuracy",
        unit="%",
        curr_val=curr_speech_acc_avg,
        prior_val=prior_speech_acc_avg,
        improving_threshold=3.0,
        higher_is_better=True,
        metric_name_human="Speech Accuracy",
    )

    # 4. Practice Consistency Trend
    if data_sufficiency == DataSufficiencyStatus.SUFFICIENT_DATA:
        active_days_curr = float(active_days_count)
        active_days_prior = float(prior_active_days_count) if prior_active_days_count > 0 else (active_days_curr / 2.0)
        trends["practice_consistency"] = _calculate_trend(
            metric_key="practice_consistency",
            unit=" days",
            curr_val=active_days_curr,
            prior_val=active_days_prior,
            improving_threshold=1.0,
            higher_is_better=True,
            metric_name_human="Practice Consistency",
        )
    else:
        trends["practice_consistency"] = MetricTrend(
            metric="practice_consistency",
            currentValue=float(active_days_count),
            previousValue=None,
            change=None,
            unit=" days",
            direction=TrendDirection.INSUFFICIENT_DATA,
            label="Building Habit",
            message="Keep logging daily sessions to see your practice consistency grow.",
        )

    # 5. Timeline Generation (Continuous daily series for charts)
    timeline_dict: Dict[str, Dict[str, Any]] = {}
    for s in curr_sessions:
        ts = get_ts(s)
        if not ts:
            continue
        dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if dt_str not in timeline_dict:
            timeline_dict[dt_str] = {
                "date": dt_str,
                "timestamp": ts,
                "acc_scores": [],
                "words": 0,
                "wpms": [],
                "activities": 0,
                "speech_acc": [],
            }
        acc = s.get("comprehensionAccuracy") or s.get("readingAccuracy") or s.get("accuracy_score") or s.get("accuracyScore") or s.get("accuracy") or s.get("overallScore")
        if acc is not None:
            timeline_dict[dt_str]["acc_scores"].append(acc)
        words_r = s.get("wordsRead") or s.get("words_read_count") or s.get("wordsPresented") or s.get("words_read") or 0
        timeline_dict[dt_str]["words"] += words_r
        timeline_dict[dt_str]["activities"] += 1
        wpm_val = s.get("wordsPerMinute") or s.get("speed_wpm") or s.get("speedWpm") or s.get("wpm")
        if wpm_val is not None:
            timeline_dict[dt_str]["wpms"].append(wpm_val)

    for a in curr_attempts:
        ts = get_ts(a)
        if not ts:
            continue
        dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if dt_str not in timeline_dict:
            timeline_dict[dt_str] = {
                "date": dt_str,
                "timestamp": ts,
                "acc_scores": [],
                "words": 0,
                "wpms": [],
                "activities": 0,
                "speech_acc": [],
            }
        timeline_dict[dt_str]["activities"] += 1
        score = a.get("scorePercent") or a.get("score")
        if score is not None:
            timeline_dict[dt_str]["acc_scores"].append(score)

    for sp in curr_speech:
        ts = get_ts(sp)
        if not ts:
            continue
        dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if dt_str not in timeline_dict:
            timeline_dict[dt_str] = {
                "date": dt_str,
                "timestamp": ts,
                "acc_scores": [],
                "words": 0,
                "wpms": [],
                "activities": 0,
                "speech_acc": [],
            }
        if sp.get("wordsPerMinute"):
            timeline_dict[dt_str]["wpms"].append(sp["wordsPerMinute"])
        sp_acc_val = sp.get("wordAccuracy") or sp.get("overall_accuracy") or sp.get("accuracy_score")
        if sp_acc_val is not None:
            timeline_dict[dt_str]["speech_acc"].append(sp_acc_val)

    timeline_points: List[TimelineDataPoint] = []
    for day_idx in range(days):
        day_epoch = period_start + (day_idx * 86400)
        dt_str = datetime.fromtimestamp(day_epoch, tz=timezone.utc).strftime("%Y-%m-%d")
        if dt_str in timeline_dict:
            item = timeline_dict[dt_str]
            avg_acc = round(sum(item["acc_scores"]) / len(item["acc_scores"]), 1) if item["acc_scores"] else None
            avg_wpm = round(sum(item["wpms"]) / len(item["wpms"]), 1) if item["wpms"] else None
            avg_sp_acc = round(sum(item["speech_acc"]) / len(item["speech_acc"]), 1) if item["speech_acc"] else None
            timeline_points.append(
                TimelineDataPoint(
                    date=dt_str,
                    timestamp=day_epoch,
                    readingAccuracy=avg_acc,
                    wordsRead=item["words"],
                    readingSpeedWpm=avg_wpm,
                    activitiesCompleted=item["activities"],
                    speechAccuracy=avg_sp_acc,
                )
            )
        else:
            timeline_points.append(
                TimelineDataPoint(
                    date=dt_str,
                    timestamp=day_epoch,
                    readingAccuracy=None,
                    wordsRead=0,
                    readingSpeedWpm=None,
                    activitiesCompleted=0,
                    speechAccuracy=None,
                )
            )

    # 6. Real Metric-Derived Strengths
    strengths: List[str] = []
    if streak >= 3:
        strengths.append(f"Dedicated Consistency: You have maintained an active {streak}-day practice streak!")
    if curr_acc_avg and curr_acc_avg >= 75.0:
        strengths.append(f"Comprehension Star: Strong understanding with an average of {curr_acc_avg}% across stories.")
    if curr_wpm_avg and curr_wpm_avg >= 50.0:
        strengths.append(f"Fluent Reader: Comfortable pace averaging {curr_wpm_avg} words per minute.")
    if len(curr_attempts) >= 3:
        strengths.append(f"Active Practice: Completed {len(curr_attempts)} adaptive micro-learning activities.")
    if active_days_count >= 4:
        strengths.append(f"Regular Learner: Logged practice across {active_days_count} different days.")
    if not strengths:
        strengths.append("Building Reading Stamina: Taking regular steps to practice reading at your own pace.")

    # 7. Real Metric-Derived Focus Areas
    focus_areas: List[str] = []
    if len(difficult_words_set) >= 3:
        focus_areas.append(f"Challenging Words: Review {len(difficult_words_set)} difficult words you encountered in recent stories.")
    if curr_acc_avg and curr_acc_avg < 70.0:
        focus_areas.append("Story Recall: Try Focus Mode or Guided Sentence Highlighting to slow down and absorb details.")
    if active_days_count < 2 and days >= 7:
        focus_areas.append("Practice Rhythm: Aim for 2 to 3 short 5-minute reading sessions per week.")
    if curr_speech_acc_avg and curr_speech_acc_avg < 75.0:
        focus_areas.append("Read Aloud Confidence: Practice tricky phonemes using the speech-assisted reading coach.")
    if not focus_areas:
        focus_areas.append("Keep Going: Continue daily reading sessions to unlock new story levels and badges!")

    recommended_action = "daily_reading_practice"
    if len(difficult_words_set) >= 4:
        recommended_action = "difficult_words_review"
    elif curr_acc_avg and curr_acc_avg < 65:
        recommended_action = "guided_reading_mode"

    summary = StudentProgressSummary(
        learnerId=lid,
        reportingPeriod=period,
        periodStart=period_start,
        periodEnd=now_ts,
        currentLearningLevel=level,
        currentLearningLevelName=level_name,
        currentAdaptiveTier=tier,
        currentAdaptiveTierName=tier_name,
        readingSessionsCount=reading_sessions_count,
        readingWordsAttempted=words_attempted,
        readingAccuracyAvg=curr_acc_avg,
        readingSpeedWpmAvg=curr_wpm_avg,
        speechAccuracyAvg=curr_speech_acc_avg,
        speechCoverageAvg=speech_cov_avg,
        practiceScoreAvg=practice_score_avg,
        activePracticeDays=active_days_count,
        currentStreak=streak,
        completedLearningActivities=len(curr_attempts),
        difficultWordsCount=len(difficult_words_set),
        difficultWordsTop=difficult_words_top,
        dataSufficiency=data_sufficiency,
        dataSufficiencyMessage=sufficiency_msg,
    )

    return StudentInsightsResponse(
        learnerId=lid,
        reportingPeriod=period,
        dataSufficiency=data_sufficiency,
        sufficiencyMessage=sufficiency_msg,
        summary=summary,
        trends=trends,
        timeline=timeline_points,
        strengths=strengths,
        focusAreas=focus_areas,
        recommendedNextAction=recommended_action,
        activeInterventionsCount=active_interventions_count,
    )


async def get_teacher_student_insights(
    teacher: dict,
    student_id: str,
    period: str = "30d",
) -> StudentInsightsResponse:
    """Teacher drill-down with student authorization check."""
    await verify_teacher_student_access(teacher, student_id)
    return await get_student_learning_insights(student_id, period)


async def get_teacher_class_insights_overview(
    teacher: dict,
    period: str = "30d",
) -> ClassInsightsOverviewResponse:
    """
    Cohort-wide learning insights overview for an educator's classroom.
    Computes distribution of student trajectories and identifies students needing support.
    """
    teacher_code = await get_teacher_classroom_code(teacher)
    if not teacher_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher does not have an active classroom assigned.",
        )

    # Find students enrolled in teacher's classroom
    students_cursor = db.users.find(
        {"classroomJoined": teacher_code, "role": "student"},
        {"_id": 0, "id": 1, "name": 1, "email": 1},
    )
    students = await students_cursor.to_list(length=300)

    if not students:
        return ClassInsightsOverviewResponse(
            classroomCode=teacher_code,
            reportingPeriod=period,
            totalStudents=0,
            improvingCount=0,
            stableCount=0,
            needsAttentionCount=0,
            insufficientDataCount=0,
            averageAccuracy=None,
            averageSpeedWpm=None,
            topStrengths=[],
            commonFocusAreas=[],
            students=[],
        )

    student_cards: List[LearnerInsightCardItem] = []
    improving_c = 0
    stable_c = 0
    needs_attn_c = 0
    insufficient_c = 0

    all_accuracies: List[float] = []
    all_wpms: List[float] = []

    for s in students:
        s_id = s["id"]
        s_name = s.get("name", "Student")

        try:
            insights = await get_student_learning_insights(s_id, period)
            summary = insights.summary
            acc_trend = insights.trends.get("reading_accuracy")
            acc_dir = acc_trend.direction if acc_trend else TrendDirection.INSUFFICIENT_DATA

            # Classify overall trend
            if summary.dataSufficiency != DataSufficiencyStatus.SUFFICIENT_DATA:
                overall_trend = TrendDirection.INSUFFICIENT_DATA
                insufficient_c += 1
            elif acc_dir == TrendDirection.IMPROVING:
                overall_trend = TrendDirection.IMPROVING
                improving_c += 1
            elif acc_dir == TrendDirection.NEEDS_ATTENTION or (summary.activePracticeDays == 0 and summary.readingSessionsCount == 0):
                overall_trend = TrendDirection.NEEDS_ATTENTION
                needs_attn_c += 1
            else:
                overall_trend = TrendDirection.STABLE
                stable_c += 1

            if summary.readingAccuracyAvg:
                all_accuracies.append(summary.readingAccuracyAvg)
            if summary.readingSpeedWpmAvg:
                all_wpms.append(summary.readingSpeedWpmAvg)

            last_active_date = None
            if insights.timeline:
                last_active_date = insights.timeline[-1].date

            card = LearnerInsightCardItem(
                studentId=s_id,
                studentName=s_name,
                level=summary.currentLearningLevel,
                tier=summary.currentAdaptiveTier,
                overallTrend=overall_trend,
                readingAccuracy=summary.readingAccuracyAvg,
                accuracyTrend=acc_dir,
                readingSpeedWpm=summary.readingSpeedWpmAvg,
                activeDays=summary.activePracticeDays,
                sessionsCount=summary.readingSessionsCount,
                needsAttention=(overall_trend == TrendDirection.NEEDS_ATTENTION),
                lastActive=last_active_date,
                topStrength=insights.strengths[0] if insights.strengths else None,
                topFocusArea=insights.focusAreas[0] if insights.focusAreas else None,
            )
            student_cards.append(card)
        except Exception as e:
            logger.warning("Error generating insights for student %s: %s", s_id, e)
            card = LearnerInsightCardItem(
                studentId=s_id,
                studentName=s_name,
                overallTrend=TrendDirection.INSUFFICIENT_DATA,
                needsAttention=False,
            )
            student_cards.append(card)
            insufficient_c += 1

    avg_class_acc = round(sum(all_accuracies) / len(all_accuracies), 1) if all_accuracies else None
    avg_class_wpm = round(sum(all_wpms) / len(all_wpms), 1) if all_wpms else None

    # Common strengths & focus areas
    common_strengths = ["Active reading practice participation", "Positive practice streak consistency"]
    common_focus = ["Regular story reading practice", "Difficult vocabulary review"]

    return ClassInsightsOverviewResponse(
        classroomCode=teacher_code,
        reportingPeriod=period,
        totalStudents=len(students),
        improvingCount=improving_c,
        stableCount=stable_c,
        needsAttentionCount=needs_attn_c,
        insufficientDataCount=insufficient_c,
        averageAccuracy=avg_class_acc,
        averageSpeedWpm=avg_class_wpm,
        topStrengths=common_strengths,
        commonFocusAreas=common_focus,
        students=student_cards,
    )


# Alias for router convenience
get_class_insights_overview = get_teacher_class_insights_overview


async def get_parent_student_insights(
    parent: dict,
    student_id: str,
    period: str = "30d",
) -> ParentInsightsResponse:
    """
    Parent-facing progress summary with non-jargon language,
    verifying verified parent link access.
    """
    await verify_parent_student_access(parent["id"], student_id)

    student_doc = await db.users.find_one({"id": student_id}, {"_id": 0, "name": 1})
    student_name = student_doc.get("name", "Your Child") if student_doc else "Your Child"

    insights = await get_student_learning_insights(student_id, period)
    summary = insights.summary

    # Practice consistency message
    if summary.activePracticeDays == 0:
        practice_msg = f"{student_name} has not logged any practice sessions in the past {summary.reportingPeriod}. Encouraging short 5-minute sessions can help build momentum."
    elif summary.activePracticeDays == 1:
        practice_msg = f"{student_name} practiced on 1 day. Starting a regular reading routine will help build confidence."
    else:
        practice_msg = f"{student_name} practiced on {summary.activePracticeDays} different days with an active {summary.currentStreak}-day practice streak!"

    # Reading accuracy trend
    acc_trend = insights.trends.get("reading_accuracy")
    if acc_trend and acc_trend.direction == TrendDirection.IMPROVING:
        reading_trend = TrendDirection.IMPROVING
        trend_msg = f"{student_name}'s story comprehension has shown positive improvement over this period."
    elif acc_trend and acc_trend.direction == TrendDirection.NEEDS_ATTENTION:
        reading_trend = TrendDirection.NEEDS_ATTENTION
        trend_msg = f"{student_name} encountered some harder stories recently. Gentle practice with shorter passages will help."
    elif acc_trend and acc_trend.direction == TrendDirection.STABLE:
        reading_trend = TrendDirection.STABLE
        trend_msg = f"{student_name} is reading with steady, consistent understanding."
    else:
        reading_trend = TrendDirection.INSUFFICIENT_DATA
        trend_msg = f"{student_name} is still building practice history. More sessions will show clear progress."

    # Parent home encouragement tips
    home_tips = [
        "Celebrate effort and practice persistence rather than speed or perfect reading.",
        "Ask curious questions like 'What was your favorite part of that story?' to build comprehension naturally.",
        "Keep daily reading sessions short and positive (5–10 minutes is wonderful).",
        "If they find a word tricky, praise them for tapping it in DyslexAid to hear the pronunciation.",
    ]

    return ParentInsightsResponse(
        studentId=student_id,
        studentName=student_name,
        reportingPeriod=period,
        learningLevelName=summary.currentLearningLevelName,
        practiceConsistencyMessage=practice_msg,
        readingAccuracyTrend=reading_trend,
        readingTrendMessage=trend_msg,
        activePracticeDays=summary.activePracticeDays,
        currentStreak=summary.currentStreak,
        totalWordsRead=summary.readingWordsAttempted,
        strengths=insights.strengths,
        homeSupportTips=home_tips,
    )
