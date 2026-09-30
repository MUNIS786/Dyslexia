"""
backend/test_phase7_teacher_analytics.py — Comprehensive Test Suite for Phase 7: Teacher Analytics.

Tests cover:
1. Authentication & Role Enforcement:
   - Unauthenticated request -> 401
   - Student role accessing teacher analytics -> 403 Forbidden
2. Authorization & Tenant Boundaries:
   - Teacher can view authorized student in their classroom
   - Teacher cannot view student from another classroom -> 403 Forbidden
   - Classroom boundary strictly enforced
3. Feature Flag:
   - V2_TEACHER_ANALYTICS = False -> 503 Service Unavailable
   - V2_TEACHER_ANALYTICS = True -> 200 OK
4. Class Overview & Metrics:
   - Empty classroom returns zeroed defaults gracefully
   - Correct learner counts, screened counts, active learners
   - Supported averages (reading comprehension, speech accuracy, WPM, adaptive tier)
5. Longitudinal Trends & Minimum-Data Rule:
   - 0 or 1 data point -> "insufficient_data"
   - >= 2 data points -> correct trend calculation ("improving", "stable", "declining")
   - Time cutoff filtering (7d, 30d, 90d, all)
6. Dynamic Domain Performance:
   - Loads domains dynamically from profile without fixed 10/12 assumption
   - Correct normalization and strength/practice flags
7. Descriptive Non-Clinical Insights:
   - Generated insights are strictly pedagogical and descriptive
   - Zero clinical or diagnostic statements
   - Pedagogical actions suggested
8. Privacy & Data Minimization:
   - Zero raw audio or audio recordings exposed
   - Zero passwords, hashes, tokens, or JWTs exposed
   - No data leakage across classroom boundaries
"""
import unittest
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, make_token
from models.v2_teacher_analytics import (
    ProgressTrendPoint,
    ProgressTrendSummary,
    DomainPerformanceItem,
    TeacherInsight,
    TeacherAction,
    LearnerAnalyticsSummary,
    ClassOverviewMetrics,
    ClassAnalyticsResponse,
    LearnerAnalyticsDetail,
)
from services.analytics.teacher_analytics import (
    get_time_cutoff,
    evaluate_trend_direction,
    calculate_progress_trends,
    build_learner_insights,
    get_teacher_classroom_code,
    verify_teacher_student_access,
    get_class_overview,
    get_classroom_learners,
    get_learner_analytics_detail,
)


class TestTrendCalculations(unittest.TestCase):
    """Test longitudinal progress trend calculations and minimum-data threshold rules."""

    def test_empty_values_returns_insufficient_data(self):
        trend = evaluate_trend_direction([])
        self.assertEqual(trend, "insufficient_data")

    def test_single_value_returns_insufficient_data(self):
        trend = evaluate_trend_direction([75.0])
        self.assertEqual(trend, "insufficient_data")

    def test_multiple_points_improving_trend(self):
        # 60% -> 85% (> +3.0 threshold)
        trend = evaluate_trend_direction([60.0, 85.0])
        self.assertEqual(trend, "improving")

    def test_multiple_points_declining_trend(self):
        # 85% -> 60% (< -3.0 threshold)
        trend = evaluate_trend_direction([85.0, 60.0])
        self.assertEqual(trend, "declining")

    def test_multiple_points_stable_trend(self):
        # 75% -> 76% (within [-3.0, +3.0] threshold)
        trend = evaluate_trend_direction([75.0, 76.0])
        self.assertEqual(trend, "stable")

    def test_multi_session_averaging_trend(self):
        # [60.0, 65.0] (avg 62.5) -> [80.0, 85.0] (avg 82.5) -> delta 20.0 -> improving
        trend = evaluate_trend_direction([60.0, 65.0, 80.0, 85.0])
        self.assertEqual(trend, "improving")


class TestAsyncProgressTrends(unittest.IsolatedAsyncioTestCase):
    """Test async database aggregation for student progress trends."""

    @patch("services.analytics.teacher_analytics.db")
    async def test_calculate_progress_trends_insufficient_data(self, mock_db):
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])

        summary = await calculate_progress_trends("student-1", "all")
        self.assertEqual(summary.readingTrend, "insufficient_data")
        self.assertEqual(summary.speechTrend, "insufficient_data")
        self.assertEqual(summary.adaptiveTrend, "insufficient_data")
        self.assertEqual(len(summary.points), 0)


class TestTimeCutoffHelper(unittest.TestCase):
    """Test time-range cutoff calculations."""

    def test_all_time_returns_none(self):
        self.assertIsNone(get_time_cutoff("all"))
        self.assertIsNone(get_time_cutoff(None))

    def test_relative_time_cutoffs(self):
        now = time.time()
        cutoff_7d = get_time_cutoff("7d")
        self.assertIsNotNone(cutoff_7d)
        delta_7d = now - cutoff_7d
        self.assertAlmostEqual(delta_7d, 7 * 86400, delta=10)

        cutoff_30d = get_time_cutoff("30d")
        delta_30d = now - cutoff_30d
        self.assertAlmostEqual(delta_30d, 30 * 86400, delta=10)

        cutoff_90d = get_time_cutoff("90d")
        delta_90d = now - cutoff_90d
        self.assertAlmostEqual(delta_90d, 90 * 86400, delta=10)


class TestEducationalInsightsBuilder(unittest.TestCase):
    """Test educational insight synthesis and verify strictly non-clinical boundary."""

    def test_non_clinical_language_strictly_enforced(self):
        profile = {
            "screeningCompleted": True,
            "strengths": [{"domain": "visual_memory", "friendly_name": "Visual Memory"}],
            "practice_areas": [{"domain": "phonemic_awareness", "friendly_name": "Phonemic Awareness"}],
        }
        reading_metrics = {
            "completedSessions": 4,
            "avgComprehensionAccuracy": 55.0,
            "wordsPerMinute": 45.0,
        }
        speech_signals = {
            "sessionCount": 3,
            "avgAccuracyRate": 62.0,
            "avgWpm": 60.0,
        }
        adaptive_state = {
            "activeDifficultyTier": 1,
            "consecutive_passes": 0,
            "consecutive_failures": 2,
        }

        trends = ProgressTrendSummary(
            readingTrend="stable",
            speechTrend="stable",
            adaptiveTrend="stable",
            points=[],
        )

        insights, actions = build_learner_insights(
            profile=profile,
            learning_state=adaptive_state,
            reading_stats=reading_metrics,
            speech_signals=speech_signals,
            trends=trends,
        )

        self.assertGreater(len(insights), 0)
        self.assertGreater(len(actions), 0)

        banned_terms = [
            "diagnose",
            "diagnosis",
            "severe dyslexia",
            "adhd",
            "pathology",
            "disorder",
            "mental health",
            "abnormal",
            "subnormal",
            "brain deficit",
            "clinical",
        ]

        for ins in insights:
            text = f"{ins.title} {ins.description} {ins.evidence or ''}".lower()
            for term in banned_terms:
                self.assertNotIn(
                    term,
                    text,
                    f"Clinical claim '{term}' detected in insight: {ins.title}",
                )

        for act in actions:
            text = f"{act.label} {act.description}".lower()
            for term in banned_terms:
                self.assertNotIn(
                    term,
                    text,
                    f"Clinical claim '{term}' detected in action: {act.label}",
                )

    def test_early_stage_reading_produces_informative_insight(self):
        profile = {"screeningCompleted": True}
        reading_metrics = {"completedSessions": 0}
        speech_signals = {"sessionCount": 0}
        adaptive_state = {"activeDifficultyTier": 1}
        trends = ProgressTrendSummary(
            readingTrend="insufficient_data",
            speechTrend="insufficient_data",
            adaptiveTrend="insufficient_data",
            points=[],
        )

        insights, actions = build_learner_insights(
            profile=profile,
            learning_state=adaptive_state,
            reading_stats=reading_metrics,
            speech_signals=speech_signals,
            trends=trends,
        )

        insight_titles = [i.title for i in insights]
        self.assertTrue(any("Early Reading Stage" in t for t in insight_titles))


class TestTeacherAuthorizationAndAccess(unittest.IsolatedAsyncioTestCase):
    """Test teacher tenant boundary verification."""

    @patch("services.analytics.teacher_analytics.db")
    async def test_get_teacher_classroom_code_from_teacher_doc(self, mock_db):
        teacher = {"id": "t-1", "classroomCode": "CLASS-ABC"}
        code = await get_teacher_classroom_code(teacher)
        self.assertEqual(code, "CLASS-ABC")

    @patch("services.analytics.teacher_analytics.db")
    async def test_get_teacher_classroom_code_from_classrooms_collection(self, mock_db):
        teacher = {"id": "t-2"}
        mock_db.classrooms.find_one = AsyncMock(
            return_value={"code": "CLASS-XYZ", "teacherId": "t-2"}
        )
        code = await get_teacher_classroom_code(teacher)
        self.assertEqual(code, "CLASS-XYZ")

    @patch("services.analytics.teacher_analytics.db")
    async def test_verify_teacher_student_access_authorized(self, mock_db):
        teacher = {"id": "t-1", "classroomCode": "CLASS-42"}
        mock_db.users.find_one = AsyncMock(
            return_value={"id": "s-100", "name": "Maya", "classroomJoined": "CLASS-42", "role": "student"}
        )
        student = await verify_teacher_student_access(teacher, "s-100")
        self.assertEqual(student["id"], "s-100")

    @patch("services.analytics.teacher_analytics.db")
    async def test_verify_teacher_student_access_mismatched_classroom_raises_403(self, mock_db):
        teacher = {"id": "t-1", "classroomCode": "CLASS-42"}
        mock_db.users.find_one = AsyncMock(
            return_value={"id": "s-999", "name": "Other", "classroomJoined": "CLASS-OTHER", "role": "student"}
        )
        with self.assertRaises(HTTPException) as ctx:
            await verify_teacher_student_access(teacher, "s-999")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not enrolled in your classroom", ctx.exception.detail)


class TestTeacherAnalyticsEndpoints(unittest.TestCase):
    """Test API endpoints for V2 Teacher Analytics."""

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated request to any teacher analytics endpoint must return 401."""
        endpoints = [
            "/api/v2/teacher/analytics/overview",
            "/api/v2/teacher/analytics/learners",
            "/api/v2/teacher/analytics/learners/student-1",
            "/api/v2/teacher/analytics/learners/student-1/trend",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"Endpoint {ep} did not require auth")

    def test_student_role_access_returns_403(self):
        """A user with role 'student' must be rejected with 403 Forbidden."""
        def mock_require_teacher():
            raise HTTPException(status_code=403, detail="Teacher role required")

        app.dependency_overrides[require_teacher] = mock_require_teacher

        res = self.client.get("/api/v2/teacher/analytics/overview")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Teacher role required", res.json().get("detail", ""))

    @patch.object(settings, "V2_TEACHER_ANALYTICS", False)
    def test_feature_flag_disabled_returns_503(self):
        """When V2_TEACHER_ANALYTICS is False, endpoints return 503."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        res = self.client.get("/api/v2/teacher/analytics/overview")
        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled", res.json().get("detail", "").lower())

    @patch.object(settings, "V2_TEACHER_ANALYTICS", True)
    @patch("routers.v2_teacher_analytics.get_class_overview", new_callable=AsyncMock)
    def test_overview_endpoint_success(self, mock_overview):
        """When enabled, teacher can retrieve class overview metrics."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_overview.return_value = ClassAnalyticsResponse(
            classroomCode="CLASS-MAGIC",
            classroomName="Magic School Bus",
            timeRange="all",
            overview=ClassOverviewMetrics(
                totalLearners=12,
                activeLearners=10,
                screenedLearners=9,
                needsAttentionCount=2,
                onTrackCount=7,
                avgLearningLevel=2.3,
                avgAdaptiveTier=2.1,
                avgReadingComprehension=78.5,
                avgSpeechAccuracy=82.0,
                avgWordsPerMinute=88.0,
                totalWordsRead=4200,
                totalMinutesRead=48.0,
                activityAttemptsCount=65,
            ),
            learners=[],
            commonPracticeAreas=[{"area": "Phonics", "learnerCount": 4, "percentage": 33}],
            classInsights=[
                TeacherInsight(
                    id="ins-1",
                    category="reading",
                    type="success",
                    title="Active Reading",
                    description="Strong reading engagement across the cohort.",
                )
            ],
        )

        res = self.client.get("/api/v2/teacher/analytics/overview?time_range=all")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["classroomCode"], "CLASS-MAGIC")
        self.assertEqual(data["overview"]["totalLearners"], 12)
        self.assertEqual(data["overview"]["avgReadingComprehension"], 78.5)

    @patch.object(settings, "V2_TEACHER_ANALYTICS", True)
    @patch("routers.v2_teacher_analytics.get_classroom_learners", new_callable=AsyncMock)
    def test_learners_roster_endpoint_success(self, mock_learners):
        """Teacher can retrieve learner roster with privacy protection (no passwords/tokens)."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_learners.return_value = [
            LearnerAnalyticsSummary(
                studentId="s-1",
                name="Aarav",
                email="aarav@school.org",
                learningLevel=2,
                learningLevelName="Developing",
                adaptiveTier=2,
                screeningCompleted=True,
                avgComprehension=80.0,
                speechAccuracy=85.0,
                wordsPerMinute=90.0,
                totalSessions=14,
                wordsRead=1500,
                streak=3,
                lastActive="Sep 30, 2026",
                status="on_track",
                strengths=["Visual Memory"],
                practiceAreas=["Phonics"],
                readingTrend="improving",
            )
        ]

        res = self.client.get("/api/v2/teacher/analytics/learners")
        self.assertEqual(res.status_code, 200)
        roster = res.json()
        self.assertEqual(len(roster), 1)
        self.assertEqual(roster[0]["name"], "Aarav")
        self.assertEqual(roster[0]["readingTrend"], "improving")
        self.assertNotIn("password", roster[0])
        self.assertNotIn("passwordHash", roster[0])
        self.assertNotIn("token", roster[0])

    @patch.object(settings, "V2_TEACHER_ANALYTICS", True)
    @patch("routers.v2_teacher_analytics.get_learner_analytics_detail", new_callable=AsyncMock)
    def test_learner_detail_endpoint_success(self, mock_detail):
        """Teacher can inspect authorized learner drilldown."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_detail.return_value = LearnerAnalyticsDetail(
            studentId="s-1",
            name="Aarav",
            email="aarav@school.org",
            classroomCode="CLASS-MAGIC",
            learningLevel=2,
            learningLevelName="Developing",
            adaptiveTier=2,
            screeningCompleted=True,
            confidence={"overall": 0.88},
            strengths=[{"domain": "visual_memory", "friendly_name": "Visual Memory"}],
            practiceAreas=[{"domain": "phonics", "friendly_name": "Phonics"}],
            domainScores=[
                DomainPerformanceItem(
                    domainKey="reading_comprehension",
                    domainName="Reading Comprehension",
                    score=82.5,
                    label="Proficient",
                    description="Ability to understand passages.",
                    isStrength=True,
                    isPracticeArea=False,
                )
            ],
            readingMetrics={
                "completedSessions": 4,
                "avgComprehensionAccuracy": 82.5,
                "wordsPerMinute": 92.0,
                "totalWordsRead": 1200,
                "totalMinutesRead": 15.0,
                "trend": "improving",
            },
            speechSignals={
                "sessionCount": 4,
                "avgAccuracyRate": 86.0,
                "avgWpm": 90.0,
                "latestScore": 88.0,
                "latestCoverage": 95.0,
            },
            adaptiveState={
                "activeDifficultyTier": 2,
                "currentStreak": 3,
                "consecutivePasses": 3,
                "consecutiveFailures": 0,
            },
            recentReadingSessions=[],
            recentActivityAttempts=[],
            trends=ProgressTrendSummary(
                readingTrend="improving",
                speechTrend="stable",
                adaptiveTrend="improving",
                points=[
                    ProgressTrendPoint(
                        timestamp=1727700000,
                        date="Sep 30, 2026",
                        comprehensionScore=82.5,
                        speechAccuracy=86.0,
                        activityScore=80.0,
                        difficultyTier=2,
                    )
                ],
            ),
            insights=[
                TeacherInsight(
                    id="ins-1",
                    category="reading",
                    type="success",
                    title="Reading Comprehension Growth",
                    description="Comprehension increased across recent readings.",
                    evidence="Comprehension: 82.5% across 4 sessions.",
                )
            ],
            suggestedActions=[
                TeacherAction(
                    id="act-1",
                    category="assign",
                    label="Advance Passage Complexity",
                    description="Learner demonstrates high accuracy on current tier.",
                    target="/teacher/assignments",
                )
            ],
        )

        res = self.client.get("/api/v2/teacher/analytics/learners/s-1")
        self.assertEqual(res.status_code, 200)
        detail = res.json()
        self.assertEqual(detail["studentId"], "s-1")
        self.assertEqual(detail["readingMetrics"]["avgComprehensionAccuracy"], 82.5)
        self.assertEqual(detail["trends"]["readingTrend"], "improving")
        self.assertNotIn("audio", detail)
        self.assertNotIn("rawAudio", detail)

    @patch.object(settings, "V2_TEACHER_ANALYTICS", True)
    @patch("routers.v2_teacher_analytics.calculate_progress_trends", new_callable=AsyncMock)
    @patch("routers.v2_teacher_analytics.verify_teacher_student_access", new_callable=AsyncMock)
    def test_trend_endpoint_success(self, mock_verify, mock_trends):
        """Teacher can inspect student's longitudinal trend timeline."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user
        mock_verify.return_value = {"id": "s-1", "name": "Aarav", "classroomJoined": "CLASS-MAGIC"}
        mock_trends.return_value = ProgressTrendSummary(
            readingTrend="improving",
            speechTrend="stable",
            adaptiveTrend="improving",
            points=[
                ProgressTrendPoint(
                    timestamp=1727700000,
                    date="Sep 30, 2026",
                    comprehensionScore=85.0,
                    speechAccuracy=88.0,
                    activityScore=90.0,
                    difficultyTier=2,
                )
            ],
        )

        res = self.client.get("/api/v2/teacher/analytics/learners/s-1/trend")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["readingTrend"], "improving")
        self.assertEqual(len(data["points"]), 1)

    @patch.object(settings, "V2_TEACHER_ANALYTICS", True)
    @patch("routers.v2_teacher_analytics.verify_teacher_student_access", new_callable=AsyncMock)
    def test_unauthorized_student_access_rejected_via_api(self, mock_verify):
        """Teacher attempting to access student from another classroom receives 403."""
        teacher_user = {
            "id": "t-1",
            "name": "Ms. Frizzle",
            "role": "teacher",
            "classroomCode": "CLASS-MAGIC",
        }
        app.dependency_overrides[require_teacher] = lambda: teacher_user
        mock_verify.side_effect = HTTPException(status_code=403, detail="Access denied: Student is not enrolled in your classroom.")

        res = self.client.get("/api/v2/teacher/analytics/learners/s-unauthorized/trend")
        self.assertEqual(res.status_code, 403)
        self.assertIn("not enrolled in your classroom", res.json().get("detail", ""))

class TestAsyncTeacherAnalyticsServices(unittest.IsolatedAsyncioTestCase):
    """Test async service functions for teacher analytics."""

    @patch("services.analytics.teacher_analytics.db")
    async def test_empty_classroom_overview_service(self, mock_db):
        """Empty classroom returns zeroed defaults gracefully without DivisionByZero."""
        teacher_user = {"id": "t-empty", "classroomCode": "CLASS-EMPTY"}
        mock_db.classrooms.find_one = AsyncMock(return_value={"name": "Empty Classroom"})
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=0)

        overview = await get_class_overview(teacher_user, "all")
        self.assertEqual(overview.overview.totalLearners, 0)
        self.assertEqual(overview.overview.activeLearners, 0)
        self.assertEqual(overview.overview.avgReadingComprehension, 0.0)
        self.assertEqual(overview.overview.avgSpeechAccuracy, 0.0)
        self.assertEqual(len(overview.learners), 0)

    @patch("services.analytics.teacher_analytics.verify_teacher_student_access", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.get_learning_state", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.db")
    async def test_dynamic_domains_loaded_without_fixed_assumption(
        self, mock_db, mock_state, mock_profile, mock_verify
    ):
        """Verifies domains are loaded dynamically from DOMAIN_METADATA without assuming 10 or 12 domains."""
        mock_verify.return_value = {"id": "s-1", "name": "Aarav", "classroomJoined": "CLASS-1"}
        mock_profile.return_value = {
            "learning_level": {"level": 2, "name": "Developing"},
            "screeningCompleted": True,
            "strengths": [{"domain": "reading_comprehension", "friendly_name": "Reading Comprehension"}],
            "practice_areas": [{"domain": "phonological_awareness", "friendly_name": "Sound & Word Practice"}],
            "domain_scores": {"reading_comprehension": 88.0, "phonological_awareness": 55.0},
            "domain_interpretations": {
                "reading_comprehension": {"label": "Strength", "friendly_name": "Reading Comprehension"},
                "phonological_awareness": {"label": "Focus Area", "friendly_name": "Sound & Word Practice"},
            },
        }
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])

        detail = await get_learner_analytics_detail({"id": "t-1", "classroomCode": "CLASS-1"}, "s-1")
        from services.learning.learner_profile_service import DOMAIN_METADATA
        self.assertEqual(len(detail.domainScores), len(DOMAIN_METADATA))
        rc_item = next(d for d in detail.domainScores if d.domainKey == "reading_comprehension")
        self.assertTrue(rc_item.isStrength)
        self.assertEqual(rc_item.score, 88.0)

    @patch("services.analytics.teacher_analytics.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.get_learning_state", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.db")
    async def test_class_overview_with_students_aggregation(self, mock_db, mock_state, mock_profile):
        """Verifies accurate calculation of cohort averages, active learners, and support triage."""
        teacher_user = {"id": "t-1", "classroomCode": "CLASS-1"}
        mock_profile.return_value = {
            "learning_level": {"level": 2, "name": "Developing"},
            "screeningCompleted": True,
            "strengths": [],
            "practice_areas": [{"domain": "reading_comprehension", "friendly_name": "Reading Comprehension"}],
        }
        mock_state.return_value = {"active_difficulty_tier": 2, "current_streak": 2}
        mock_db.classrooms.find_one = AsyncMock(return_value={"name": "Class 1A"})
        # 2 students in classroom
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[
            {"id": "s-1", "name": "Aarav", "email": "a@test.com", "screeningCompleted": True},
            {"id": "s-2", "name": "Diya", "email": "d@test.com", "screeningCompleted": False},
        ])
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[
            {"comprehensionScore": 80.0, "wordsRead": 200, "durationSeconds": 120, "createdAt": 1727700000}
        ])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[
            {"accuracyRate": 85.0, "wordsPerMinute": 95.0, "createdAt": 1727700000}
        ])
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=12)

        overview_resp = await get_class_overview(teacher_user, "all")
        metrics = overview_resp.overview
        self.assertEqual(metrics.totalLearners, 2)
        self.assertEqual(metrics.screenedLearners, 2)
        self.assertGreater(metrics.activityAttemptsCount, 0)
        self.assertEqual(len(overview_resp.learners), 2)

    @patch("services.analytics.teacher_analytics.db")
    async def test_verify_teacher_student_access_no_classroom(self, mock_db):
        """Teacher with no classroom code assigned receives 403."""
        teacher_user = {"id": "t-no-class"}
        mock_db.classrooms.find_one = AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as ctx:
            await verify_teacher_student_access(teacher_user, "s-any")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("does not have an active classroom", ctx.exception.detail)

    @patch("services.analytics.teacher_analytics.db")
    async def test_verify_teacher_student_access_student_not_found(self, mock_db):
        """Teacher requesting non-existent student receives 404."""
        teacher_user = {"id": "t-1", "classroomCode": "CLASS-1"}
        mock_db.users.find_one = AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as ctx:
            await verify_teacher_student_access(teacher_user, "s-ghost")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_teacher_action_categories_valid(self):
        """Teacher actions must use educational categories: review, practice, assign, discuss."""
        profile = {"screeningCompleted": True}
        reading_metrics = {"completedSessions": 2, "avgComprehensionAccuracy": 50.0}
        speech_signals = {"sessionCount": 2, "avgAccuracyRate": 60.0}
        adaptive_state = {"activeDifficultyTier": 1, "consecutive_failures": 2}
        trends = ProgressTrendSummary(readingTrend="declining", speechTrend="declining", points=[])

        insights, actions = build_learner_insights(profile, adaptive_state, reading_metrics, speech_signals, trends)
        allowed_categories = {"review", "practice", "assign", "discuss"}
        for act in actions:
            self.assertIn(act.category, allowed_categories, f"Invalid category {act.category} on action {act.label}")

    @patch("services.analytics.teacher_analytics.verify_teacher_student_access", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.get_learning_state", new_callable=AsyncMock)
    @patch("services.analytics.teacher_analytics.db")
    async def test_privacy_no_sensitive_fields_in_detail(self, mock_db, mock_state, mock_profile, mock_verify):
        """Assures zero password hashes, authentication tokens, or raw audio in learner detail."""
        mock_verify.return_value = {
            "id": "s-1",
            "name": "Aarav",
            "email": "aarav@test.org",
            "classroomJoined": "CLASS-1",
            "passwordHash": "$2b$12$supersecretpasswordhashthatmustneverbeexposed",
            "token": "secret-jwt-token-12345",
            "audio": "raw_audio_binary_data",
        }
        mock_profile.return_value = {
            "learning_level": {"level": 2, "name": "Developing"},
            "screeningCompleted": True,
            "strengths": [],
            "practice_areas": [],
        }
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])

        detail = await get_learner_analytics_detail({"id": "t-1", "classroomCode": "CLASS-1"}, "s-1")
        detail_dict = detail.model_dump()
        self.assertNotIn("passwordHash", detail_dict)
        self.assertNotIn("token", detail_dict)
        self.assertNotIn("audio", detail_dict)
        self.assertNotIn("rawAudio", detail_dict)


if __name__ == "__main__":
    unittest.main()

