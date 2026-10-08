"""
backend/test_phase13_learning_insights.py — Comprehensive Test Suite for Phase 13: Learning Insights & Progress Reports.

Verifies:
1. Default / empty report handling (0 sessions -> NO_DATA)
2. 7-day reporting period
3. 30-day reporting period
4. 90-day reporting period
5. Reading accuracy trend calculation (improving, stable, needs_attention)
6. Reading speed (WPM) trend calculation
7. Speech-reading analysis trend integration
8. Practice frequency & active practice days calculation
9. Current adaptive learning level and tier extraction
10. Real-metric strength identification
11. Actionable focus-area identification
12. Insufficient data behavior (1 session -> INSUFFICIENT_DATA)
13. No data behavior (0 sessions -> NO_DATA with clear guidance message)
14. Authentication (401 for unauthenticated requests)
15. Student tenancy isolation (student cannot request arbitrary learner IDs)
16. Teacher authorization (valid teacher accesses enrolled student)
17. Parent authorization (valid parent accesses linked child)
18. Unauthorized learner access (teacher unauthorized -> 403, parent unauthorized -> 403)
19. Tutor transcript privacy (no AI tutor conversation transcripts exposed)
20. Raw speech audio privacy (no raw audio/recordings exposed)
21. Feature flag governance (V2_LEARNING_INSIGHTS=False -> 503)
22. Invalid period parameter handling (e.g. 14d -> 422)
23. Missing/incomplete data graceful degradation
24. Regression against teacher analytics and parent portal
"""
import time
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, require_parent
from models.v2_learning_insights import TrendDirection, DataSufficiencyStatus, StudentInsightsResponse, StudentProgressSummary


def make_cursor_mock(items):
    """Helper to mock a synchronous cursor returned by motor find() whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.sort = MagicMock(return_value=c)
    return c


class TestPhase13LearningInsights(unittest.TestCase):
    """Test suite for Phase 13 Learning Insights & Progress Reports."""

    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-101",
            "name": "Aarav Sharma",
            "email": "aarav@school.edu",
            "role": "student",
        }
        self.teacher_user = {
            "id": "teacher-99",
            "name": "Ms. Kapoor",
            "email": "kapoor@school.edu",
            "role": "teacher",
            "classroom_code": "CLASS-A",
        }
        self.parent_user = {
            "id": "parent-55",
            "name": "Priya Sharma",
            "email": "priya@gmail.com",
            "role": "parent",
        }
        app.dependency_overrides = {}

    def tearDown(self):
        app.dependency_overrides = {}

    # 14. Authentication
    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must return 401 Unauthorized."""
        res_stu = self.client.get("/api/v2/learning-insights/student")
        self.assertEqual(res_stu.status_code, 401)

        res_tch_ov = self.client.get("/api/v2/learning-insights/teacher/overview")
        self.assertEqual(res_tch_ov.status_code, 401)

        res_tch_ln = self.client.get("/api/v2/learning-insights/teacher/student-101")
        self.assertEqual(res_tch_ln.status_code, 401)

        res_par = self.client.get("/api/v2/learning-insights/parent/student-101")
        self.assertEqual(res_par.status_code, 401)

    # 21. Feature flag behavior
    def test_feature_flag_disabled_returns_503(self):
        """When V2_LEARNING_INSIGHTS is False, endpoints return 503 Service Unavailable."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        original_flag = getattr(settings, "V2_LEARNING_INSIGHTS", True)
        try:
            settings.V2_LEARNING_INSIGHTS = False
            res = self.client.get("/api/v2/learning-insights/student")
            self.assertEqual(res.status_code, 503)
            self.assertIn("disabled", res.json()["detail"].lower())
        finally:
            settings.V2_LEARNING_INSIGHTS = original_flag
            app.dependency_overrides.clear()

    # 22. Invalid period handling
    def test_invalid_period_rejected_with_422(self):
        """Unsupported period values must return 422 Unprocessable Entity."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/learning-insights/student?period=14d")
            self.assertEqual(res.status_code, 422)

            res2 = self.client.get("/api/v2/learning-insights/student?period=1y")
            self.assertEqual(res2.status_code, 422)
        finally:
            app.dependency_overrides.clear()

    # 1 & 13. Default/empty report & No-data behavior
    @patch("services.learning.learning_insights.db")
    def test_empty_student_insights_no_data(self, mock_db):
        """When student has 0 sessions, status is NO_DATA with encouraging message."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 2, "adaptive_tier": "developing"})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 0})

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["learnerId"], "student-101")
            self.assertEqual(data["reportingPeriod"], "30d")
            self.assertEqual(data["dataSufficiency"], "no_data")
            self.assertIn("No learning activity recorded yet", data["sufficiencyMessage"])
            self.assertEqual(data["summary"]["readingSessionsCount"], 0)
            self.assertEqual(data["summary"]["currentLearningLevel"], 2)
            self.assertEqual(len(data["timeline"]), 30)
            self.assertIn("not constitute a medical", data["disclaimer"])
        finally:
            app.dependency_overrides.clear()

    # 12. Insufficient data behavior (1 session)
    @patch("services.learning.learning_insights.db")
    def test_single_session_insufficient_data(self, mock_db):
        """When student has 1 session, status is INSUFFICIENT_DATA and trends are INSUFFICIENT_DATA."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 1, "adaptive_tier": 1})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 1})

        now_ts = int(time.time())
        single_session = [{
            "id": "session-1",
            "student_id": "student-101",
            "created_at": now_ts - 3600,
            "accuracy_score": 75.0,
            "words_read_count": 80,
            "speed_wpm": 45.0,
            "comprehension_score": 80.0,
        }]

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock(single_session))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["dataSufficiency"], "insufficient_data")
            self.assertIn("start", data["sufficiencyMessage"].lower())
            self.assertEqual(data["summary"]["readingSessionsCount"], 1)
            self.assertEqual(data["summary"]["readingAccuracyAvg"], 75.0)
            self.assertEqual(data["trends"]["reading_accuracy"]["direction"], "insufficient_data")
        finally:
            app.dependency_overrides.clear()

    # 5, 6, 8, 9, 10, 11. Multi-session trends, speeds, consistency, strengths & focus areas
    @patch("services.learning.learning_insights.db")
    def test_populated_student_insights_improving_trend(self, mock_db):
        """Multi-session activity with accuracy and speed improvements over baseline."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        mock_db.learner_profiles.find_one = AsyncMock(return_value={
            "preferred_domains": ["phonological", "visual"],
            "support_needs": ["multisyllabic words"]
        })
        mock_db.learning_states.find_one = AsyncMock(return_value={
            "current_level": 3,
            "adaptive_tier": 3
        })
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 5})

        now_ts = int(time.time())
        day = 86400
        sessions = [
            # Prior period (between 30d and 60d ago)
            {"id": "s1", "student_id": "student-101", "created_at": now_ts - 40 * day, "accuracy_score": 68.0, "words_read_count": 50, "speed_wpm": 38.0},
            {"id": "s2", "student_id": "student-101", "created_at": now_ts - 38 * day, "accuracy_score": 72.0, "words_read_count": 60, "speed_wpm": 42.0},
            {"id": "s3", "student_id": "student-101", "created_at": now_ts - 35 * day, "accuracy_score": 70.0, "words_read_count": 70, "speed_wpm": 40.0},
            # Current period (within last 30d)
            {"id": "s4", "student_id": "student-101", "created_at": now_ts - 20 * day, "accuracy_score": 82.0, "words_read_count": 80, "speed_wpm": 50.0},
            {"id": "s5", "student_id": "student-101", "created_at": now_ts - 12 * day, "accuracy_score": 85.0, "words_read_count": 90, "speed_wpm": 54.0},
            {"id": "s6", "student_id": "student-101", "created_at": now_ts - 5 * day, "accuracy_score": 88.0, "words_read_count": 100, "speed_wpm": 58.0},
            {"id": "s7", "student_id": "student-101", "created_at": now_ts - 1 * day, "accuracy_score": 85.0, "words_read_count": 80, "speed_wpm": 56.0},
        ]

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock(sessions))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["dataSufficiency"], "sufficient_data")
            self.assertEqual(data["summary"]["readingSessionsCount"], 4)
            self.assertEqual(data["summary"]["currentLearningLevel"], 3)

            # Check trends
            acc_trend = data["trends"]["reading_accuracy"]
            self.assertEqual(acc_trend["direction"], "improving")
            self.assertGreater(acc_trend["currentValue"], acc_trend["previousValue"])

            speed_trend = data["trends"]["reading_speed_wpm"]
            self.assertEqual(speed_trend["direction"], "improving")

            # Check strengths
            self.assertTrue(len(data["strengths"]) > 0)
            self.assertTrue(any("understanding" in s.lower() or "comprehension" in s.lower() for s in data["strengths"]))

            # Check focus areas
            self.assertTrue(len(data["focusAreas"]) > 0)
        finally:
            app.dependency_overrides.clear()

    # 2 & 4. Seven-day and Ninety-day reports
    @patch("services.learning.learning_insights.db")
    def test_different_period_windows(self, mock_db):
        """Supports 7d and 90d query parameters."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 1, "adaptive_tier": 1})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 0})

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res7 = self.client.get("/api/v2/learning-insights/student?period=7d")
            self.assertEqual(res7.status_code, 200)
            self.assertEqual(res7.json()["reportingPeriod"], "7d")
            self.assertEqual(len(res7.json()["timeline"]), 7)

            res90 = self.client.get("/api/v2/learning-insights/student?period=90d")
            self.assertEqual(res90.status_code, 200)
            self.assertEqual(res90.json()["reportingPeriod"], "90d")
            self.assertEqual(len(res90.json()["timeline"]), 90)
        finally:
            app.dependency_overrides.clear()

    # 7. Speech-reading analysis trend integration
    @patch("services.learning.learning_insights.db")
    def test_speech_analysis_trend_integration(self, mock_db):
        """Speech analysis records populate speech_accuracy trend."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 2, "adaptive_tier": 2})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 2})

        now_ts = int(time.time())
        day = 86400

        speech_analyses = [
            # Prior window
            {"id": "sp1", "student_id": "student-101", "created_at": now_ts - 40 * day, "overall_accuracy": 65.0, "words_spoken_count": 40},
            {"id": "sp2", "student_id": "student-101", "created_at": now_ts - 35 * day, "overall_accuracy": 68.0, "words_spoken_count": 45},
            # Current window
            {"id": "sp3", "student_id": "student-101", "created_at": now_ts - 15 * day, "overall_accuracy": 82.0, "words_spoken_count": 50},
            {"id": "sp4", "student_id": "student-101", "created_at": now_ts - 3 * day, "overall_accuracy": 85.0, "words_spoken_count": 55},
        ]

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock(speech_analyses))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            sp_trend = data["trends"]["speech_accuracy"]
            self.assertEqual(sp_trend["direction"], "improving")
            self.assertEqual(sp_trend["currentValue"], 83.5)
        finally:
            app.dependency_overrides.clear()

    # 15. Student tenancy isolation
    @patch("services.learning.learning_insights.db")
    def test_student_cannot_pass_arbitrary_student_id(self, mock_db):
        """Student endpoint binds to authenticated user id and ignores spoof attempts."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)
        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?learner_id=student-999")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["learnerId"], "student-101")
        finally:
            app.dependency_overrides.clear()

    # 16 & 18. Teacher authorization and unauthorized learner access
    @patch("routers.v2_learning_insights.verify_teacher_student_access", new_callable=AsyncMock)
    @patch("routers.v2_learning_insights.get_student_learning_insights", new_callable=AsyncMock)
    def test_teacher_accesses_authorized_student(self, mock_get_insights, mock_verify):
        """Teacher can inspect student when verify_teacher_student_access succeeds."""
        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        mock_verify.return_value = True

        mock_get_insights.return_value = StudentInsightsResponse(
            learnerId="student-101",
            reportingPeriod="30d",
            dataSufficiency=DataSufficiencyStatus.SUFFICIENT_DATA,
            summary=StudentProgressSummary(learnerId="student-101", reportingPeriod="30d"),
        )

        try:
            res = self.client.get("/api/v2/learning-insights/teacher/student-101")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["learnerId"], "student-101")
        finally:
            app.dependency_overrides.clear()

    @patch("routers.v2_learning_insights.verify_teacher_student_access", new_callable=AsyncMock)
    def test_teacher_unauthorized_student_returns_403(self, mock_verify):
        """Teacher inspecting unassigned student receives 403 Forbidden."""
        from fastapi import HTTPException
        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        mock_verify.side_effect = HTTPException(status_code=403, detail="Student is not in your classroom roster.")

        try:
            res = self.client.get("/api/v2/learning-insights/teacher/student-foreign")
            self.assertEqual(res.status_code, 403)
            self.assertIn("not in your classroom", res.json()["detail"].lower())
        finally:
            app.dependency_overrides.clear()

    # 17 & 18. Parent authorization and unauthorized child access
    @patch("services.learning.learning_insights.verify_parent_student_access", new_callable=AsyncMock)
    @patch("services.learning.learning_insights.db")
    def test_parent_accesses_linked_child(self, mock_db, mock_verify):
        """Parent with verified link receives parent-friendly progress report."""
        app.dependency_overrides[require_parent] = lambda: self.parent_user
        mock_verify.return_value = True
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-101", "name": "Aarav Sharma"})
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 2, "adaptive_tier": 2})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 3})

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/parent/student-101")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["studentId"], "student-101")
            self.assertEqual(data["studentName"], "Aarav Sharma")
            self.assertIn("homeSupportTips", data)
            self.assertTrue(len(data["homeSupportTips"]) > 0)
        finally:
            app.dependency_overrides.clear()

    @patch("services.learning.learning_insights.verify_parent_student_access", new_callable=AsyncMock)
    def test_parent_unauthorized_child_returns_403(self, mock_verify):
        """Parent accessing unlinked child receives 403 Forbidden."""
        from fastapi import HTTPException
        app.dependency_overrides[require_parent] = lambda: self.parent_user
        mock_verify.side_effect = HTTPException(status_code=403, detail="No active parent-learner link.")

        try:
            res = self.client.get("/api/v2/learning-insights/parent/student-unlinked")
            self.assertEqual(res.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # 19. Tutor transcript privacy
    @patch("services.learning.learning_insights.db")
    def test_no_tutor_transcripts_exposed(self, mock_db):
        """Verify responses never expose AI tutor transcripts or chat messages."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 1, "adaptive_tier": 1})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 0})

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student")
            self.assertEqual(res.status_code, 200)
            text_body = res.text.lower()
            self.assertNotIn("transcript", text_body)
            self.assertNotIn("chat_history", text_body)
            self.assertNotIn("messages", text_body)
        finally:
            app.dependency_overrides.clear()

    # 20. Raw speech audio privacy
    @patch("services.learning.learning_insights.db")
    def test_no_raw_audio_exposed(self, mock_db):
        """Verify responses never expose audio blobs, recording URLs, or waveform bytes."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 1, "adaptive_tier": 1})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 0})

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student")
            self.assertEqual(res.status_code, 200)
            text_body = res.text.lower()
            self.assertNotIn("audio_data", text_body)
            self.assertNotIn("audio_url", text_body)
            self.assertNotIn("recording_base64", text_body)
        finally:
            app.dependency_overrides.clear()

    # 23. Missing/incomplete data graceful degradation
    @patch("services.learning.learning_insights.db")
    def test_missing_data_degrades_gracefully(self, mock_db):
        """Ensure None values in sessions or missing fields do not cause 500 error."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)

        now_ts = int(time.time())
        malformed_sessions = [
            {"id": "m1", "student_id": "student-101", "created_at": now_ts - 500, "accuracy_score": None, "speed_wpm": None},
            {"id": "m2", "student_id": "student-101", "created_at": now_ts - 200},
        ]
        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock(malformed_sessions))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["summary"]["currentLearningLevel"], 1)
        finally:
            app.dependency_overrides.clear()

    # 24. Regression against existing analytics
    def test_existing_analytics_routes_still_accessible(self):
        """Ensure /api/v2/teacher/analytics/overview and /api/v2/parent/profile routes remain intact."""
        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        app.dependency_overrides[require_parent] = lambda: self.parent_user

        with patch("routers.v2_teacher_analytics.get_class_overview", new_callable=AsyncMock) as mock_tch_ov:
            mock_tch_ov.return_value = {
                "classroomCode": "CLASS-A",
                "classroomName": "Room 101",
                "timeRange": "all",
                "overview": {
                    "totalLearners": 0,
                    "activeLearners": 0,
                    "screenedLearners": 0,
                    "needsAttentionCount": 0,
                    "onTrackCount": 0,
                    "avgLearningLevel": 0.0,
                    "avgAdaptiveTier": 1.0,
                    "avgReadingComprehension": 0.0,
                    "avgSpeechAccuracy": 0.0,
                    "avgWordsPerMinute": 0.0,
                    "totalWordsRead": 0,
                    "totalMinutesRead": 0.0,
                    "activityAttemptsCount": 0,
                },
                "learners": [],
                "commonPracticeAreas": [],
                "classInsights": [],
            }
            res_tch = self.client.get("/api/v2/teacher/analytics/overview")
            self.assertEqual(res_tch.status_code, 200)

        with patch("routers.v2_parent.get_parent_profile_summary", new_callable=AsyncMock) as mock_par_prof:
            mock_par_prof.return_value = {
                "id": "parent-55",
                "name": "Priya Sharma",
                "email": "priya@gmail.com",
                "role": "parent",
                "linkedLearnersCount": 0,
                "pendingRequestsCount": 0,
                "preferredLanguage": "en",
            }
            res_par = self.client.get("/api/v2/parent/profile")
            self.assertEqual(res_par.status_code, 200)

        app.dependency_overrides.clear()

    # Teacher class overview endpoint
    @patch("routers.v2_learning_insights.get_class_insights_overview", new_callable=AsyncMock)
    def test_teacher_class_overview(self, mock_overview):
        """Teacher accesses class-wide aggregated insights overview."""
        from models.v2_learning_insights import ClassInsightsOverviewResponse
        app.dependency_overrides[require_teacher] = lambda: self.teacher_user

        mock_overview.return_value = ClassInsightsOverviewResponse(
            classroomCode="CLASS-A",
            reportingPeriod="30d",
            totalStudents=2,
            improvingCount=1,
            stableCount=1,
            needsAttentionCount=0,
            insufficientDataCount=0,
            averageAccuracy=82.5,
            averageSpeedWpm=55.0,
            topStrengths=["Regular reading practice"],
            commonFocusAreas=["Difficult words review"],
            students=[],
        )

        try:
            res = self.client.get("/api/v2/learning-insights/teacher/overview?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["classroomCode"], "CLASS-A")
            self.assertEqual(data["totalStudents"], 2)
            self.assertEqual(data["improvingCount"], 1)
        finally:
            app.dependency_overrides.clear()

    # Needs attention trend
    @patch("services.learning.learning_insights.db")
    def test_accuracy_trend_needs_attention(self, mock_db):
        """When accuracy drops significantly below previous window, trend is needs_attention."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 2, "adaptive_tier": 2})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 1})

        now_ts = int(time.time())
        day = 86400
        # Prior period: 85% accuracy; Current period: 70% accuracy
        sessions = [
            {"id": "p1", "student_id": "student-101", "created_at": now_ts - 40 * day, "accuracy_score": 85.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "p2", "student_id": "student-101", "created_at": now_ts - 35 * day, "accuracy_score": 85.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "c1", "student_id": "student-101", "created_at": now_ts - 10 * day, "accuracy_score": 70.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "c2", "student_id": "student-101", "created_at": now_ts - 5 * day, "accuracy_score": 70.0, "words_read_count": 60, "speed_wpm": 40.0},
        ]

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock(sessions))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            acc_trend = data["trends"]["reading_accuracy"]
            self.assertEqual(acc_trend["direction"], "needs_attention")
            self.assertIn("practice", acc_trend["label"].lower())
        finally:
            app.dependency_overrides.clear()

    # Stable trend
    @patch("services.learning.learning_insights.db")
    def test_accuracy_trend_stable(self, mock_db):
        """When accuracy delta is within threshold (+-3%), trend is stable."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"current_level": 2, "adaptive_tier": 2})
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"streak_days": 1})

        now_ts = int(time.time())
        day = 86400
        # Prior: 80%; Current: 81%
        sessions = [
            {"id": "p1", "student_id": "student-101", "created_at": now_ts - 40 * day, "accuracy_score": 80.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "p2", "student_id": "student-101", "created_at": now_ts - 35 * day, "accuracy_score": 80.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "c1", "student_id": "student-101", "created_at": now_ts - 10 * day, "accuracy_score": 81.0, "words_read_count": 60, "speed_wpm": 40.0},
            {"id": "c2", "student_id": "student-101", "created_at": now_ts - 5 * day, "accuracy_score": 81.0, "words_read_count": 60, "speed_wpm": 40.0},
        ]

        mock_db.reading_sessions.find = MagicMock(return_value=make_cursor_mock(sessions))
        mock_db.speech_reading_analyses.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.activity_attempts.find = MagicMock(return_value=make_cursor_mock([]))
        mock_db.interventions.find = MagicMock(return_value=make_cursor_mock([]))

        try:
            res = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            acc_trend = data["trends"]["reading_accuracy"]
            self.assertEqual(acc_trend["direction"], "stable")
        finally:
            app.dependency_overrides.clear()

    # Role separation & 403 Forbidden checks
    def test_student_blocked_from_teacher_insights(self):
        """Student token must be rejected with 403 when trying to access teacher overview."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-insights/teacher/overview")
        self.assertEqual(res.status_code, 403)
        app.dependency_overrides.clear()

    def test_student_blocked_from_parent_insights(self):
        """Student token must be rejected with 403 when trying to access parent insights."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-insights/parent/student-101")
        self.assertEqual(res.status_code, 403)
        app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
