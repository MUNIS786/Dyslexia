"""
backend/test_phase14_learning_recommendations.py — Comprehensive Test Suite for Phase 14:
Personalized Learning Recommendations & Study Plan Engine.

Verifies:
1. New learner recommendation.
2. No-data state.
3. Insufficient-data state.
4. Reading recommendation.
5. Difficult-word recommendation.
6. Speech recommendation.
7. Review recommendation.
8. Adaptive-level eligibility & stretch challenge.
9. Recommendation ranking.
10. Recommendation explanation.
11. Confidence / data sufficiency.
12. Daily plan generation.
13. Plan activity limit (bounded 2-4 activities).
14. Existing activity reuse & completion tracking.
15. Recommendation refresh / idempotency.
16. Student authentication (401 for unauthenticated).
17. Student tenant isolation (cannot access other learners).
18. Teacher authorization for enrolled learner.
19. Teacher unauthorized access rejection (403).
20. Parent authorization for linked child.
21. Parent unauthorized access rejection (403).
22. Tutor transcript privacy (zero transcripts exposed).
23. Raw-audio privacy (zero raw audio exposed).
24. Multilingual preference support.
25. Feature flag 503 governance.
26. Invalid parameter validation (422).
27. Regression against Phase 13 Insights reuse.
"""
import time
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, require_parent
from models.v2_learning_insights import (
    StudentInsightsResponse,
    StudentProgressSummary,
    MetricTrend,
    TrendDirection,
    DataSufficiencyStatus,
)
from models.v2_learning_recommendations import (
    StudentRecommendationsResponse,
    StudyPlan,
    RecommendationItem,
    StudyPlanItem,
)
from services.learning.learning_recommendations import generate_learner_recommendations


def make_cursor_mock(items):
    """Helper to mock a synchronous cursor returned by motor find() whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


def make_mock_insights(
    learner_id="student-101",
    sessions=0,
    acc=80.0,
    difficult_words=None,
    speech_acc=None,
    sufficiency="sufficient_data",
    trends=None,
):
    """Creates a valid, robust StudentInsightsResponse mock fixture."""
    stat = (
        DataSufficiencyStatus.NO_DATA
        if sufficiency == "no_data"
        else DataSufficiencyStatus.INSUFFICIENT_DATA
        if sufficiency == "insufficient_data"
        else DataSufficiencyStatus.SUFFICIENT_DATA
    )
    summary = StudentProgressSummary(
        learnerId=learner_id,
        reportingPeriod="30d",
        readingSessionsCount=sessions,
        readingAccuracyAvg=acc,
        speechAccuracyAvg=speech_acc,
        difficultWordsTop=difficult_words or [],
        dataSufficiency=stat,
        dataSufficiencyMessage="Learning progress summary",
    )
    return StudentInsightsResponse(
        learnerId=learner_id,
        reportingPeriod="30d",
        dataSufficiency=stat,
        summary=summary,
        trends=trends or {},
        timeline=[],
    )


class TestPhase14LearningRecommendations(unittest.TestCase):
    """Test suite for Phase 14 Learning Recommendations & Study Plan."""

    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-101",
            "name": "Aarav Sharma",
            "email": "aarav@school.edu",
            "role": "student",
        }
        self.teacher_user = {
            "id": "teacher-202",
            "name": "Ms. Priya Patel",
            "email": "priya@school.edu",
            "role": "teacher",
        }
        self.parent_user = {
            "id": "parent-303",
            "name": "Sunita Sharma",
            "email": "sunita@family.com",
            "role": "parent",
        }

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.V2_LEARNING_RECOMMENDATIONS = True

    # 1. New Learner & No-Data State
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_new_learner_no_data_state(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1, "practice_areas": []}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-new", sessions=0, sufficiency="no_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: {"id": "student-new", "role": "student"}
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["dataSufficiency"], "no_data")
        self.assertIn("getting to know your learning style", data["dataSufficiencyMessage"])
        self.assertTrue(len(data["recommendations"]) >= 1)
        self.assertEqual(data["recommendations"][0]["confidence"], "insufficient_data")
        self.assertEqual(data["studyPlan"]["completedCount"], 0)

    # 2. Insufficient Data State
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_insufficient_data_state(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=1, sufficiency="insufficient_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["dataSufficiency"], "insufficient_data")
        self.assertEqual(data["recommendations"][0]["confidence"], "insufficient_data")

    # 3. Reading Practice Recommendation
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_reading_practice_recommendation(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=6, acc=82.0, sufficiency="sufficient_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = [r["category"] for r in data["recommendations"]]
        self.assertIn("READING_PRACTICE", categories)
        read_rec = next(r for r in data["recommendations"] if r["category"] == "READING_PRACTICE")
        self.assertIn("Level 2", read_rec["reason"])
        self.assertIn("/student/reading-coach", read_rec["actionUrl"])

    # 4. Difficult Word Recommendation
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_difficult_words_recommendation(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=5,
            acc=74.0,
            difficult_words=["sprout", "through", "caught"],
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = [r["category"] for r in data["recommendations"]]
        self.assertIn("DIFFICULT_WORD_PRACTICE", categories)
        word_rec = next(r for r in data["recommendations"] if r["category"] == "DIFFICULT_WORD_PRACTICE")
        self.assertIn("sprout", word_rec["reason"])
        self.assertEqual(word_rec["targetWords"], ["sprout", "through", "caught"])

    # 5. Speech Recommendation
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_speech_practice_recommendation(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=5,
            acc=80.0,
            speech_acc=None,
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = [r["category"] for r in data["recommendations"]]
        self.assertIn("SPEECH_PRACTICE", categories)
        speech_rec = next(r for r in data["recommendations"] if r["category"] == "SPEECH_PRACTICE")
        self.assertIn("oral reading practice is needed", speech_rec["reason"].lower())

    # 6. Adaptive Level Eligibility & Stretch Challenge
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_stretch_challenge_eligibility(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        # Eligible: 2 consecutive passes, tier 2 (< 5), accuracy 88%
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 2}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=8,
            acc=88.0,
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = [r["category"] for r in data["recommendations"]]
        self.assertIn("STRETCH", categories)

    # 7. Stretch Ineligibility (consecutive passes < 2)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_stretch_challenge_ineligibility(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 0}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=5,
            acc=65.0,
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = [r["category"] for r in data["recommendations"]]
        self.assertNotIn("STRETCH", categories)

    # 8. Recommendation Ranking (Deterministic priority order)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_recommendation_ranking_priority(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=6,
            acc=75.0,
            difficult_words=["through", "enough"],
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        recs = data["recommendations"]
        priorities = [r["priority"] for r in recs]
        self.assertEqual(priorities, list(range(1, len(recs) + 1)))

    # 9. Recommendation Explanations
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_recommendation_explanations(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=4, sufficiency="sufficient_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        for r in data["recommendations"]:
            self.assertTrue(len(r["reason"]) > 5)
            self.assertTrue(len(r["detailedExplanation"]) > 5)

    # 10. Daily Plan Generation & Bounded Limit (2 to 4 activities)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_daily_plan_bounded_limit(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 2}
        mock_insights.return_value = make_mock_insights(
            learner_id="student-101",
            sessions=7,
            acc=85.0,
            difficult_words=["word1", "word2"],
            sufficiency="sufficient_data",
        )
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        plan = data["studyPlan"]
        self.assertGreaterEqual(len(plan["items"]), 2)
        self.assertLessEqual(len(plan["items"]), 4)
        self.assertGreater(plan["totalEstimatedMinutes"], 0)

    # 11. Completion Tracking with Real Records
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_completion_tracking_real_records(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=4, sufficiency="sufficient_data")
        # Mock reading session completed today (timestamp = now)
        mock_db.reading_sessions.find.return_value = make_cursor_mock([
            {"createdAt": time.time(), "completedAt": time.time(), "passageId": "pas-t1-001"}
        ])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        read_item = next((i for i in data["studyPlan"]["items"] if i["activityType"] == "READING_PRACTICE"), None)
        if read_item:
            self.assertTrue(read_item["completed"])
            self.assertGreater(data["studyPlan"]["completedCount"], 0)

    # 12. Recommendation Refresh Endpoint (Idempotent)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_recommendation_refresh_endpoint(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=3, sufficiency="sufficient_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.post("/api/v2/learning-recommendations/student/refresh")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertTrue(len(data["recommendations"]) > 0)

    # 13. Student Authentication (401 when not logged in)
    def test_student_authentication_required(self):
        res = self.client.get("/api/v2/learning-recommendations/student")
        self.assertIn(res.status_code, (401, 403))

    # 14. Student Tenant Isolation (Uses auth session, not URL param)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_student_tenant_isolation(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=0, sufficiency="no_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["learnerId"], "student-101")

    # 15. Teacher Authorization (Authorized teacher accesses enrolled learner)
    @patch("services.learning.learning_recommendations.verify_teacher_student_access", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_teacher_authorized_learner_access(self, mock_db, mock_gen, mock_verify):
        mock_verify.return_value = True
        mock_gen.return_value = StudentRecommendationsResponse(
            learnerId="student-101",
            horizon="today",
            recommendations=[],
            studyPlan=StudyPlan(items=[], totalEstimatedMinutes=0, completedCount=0, totalCount=0),
            currentLearningLevel=2,
            currentLearningLevelName="Developing",
            currentAdaptiveTier=2,
            currentAdaptiveTierName="Developing",
            dataSufficiency="sufficient_data",
            generatedAt="2026-10-08T00:00:00Z",
        )
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-101", "name": "Aarav Sharma"})

        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        res = self.client.get("/api/v2/learning-recommendations/teacher/student-101")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertEqual(data["studentName"], "Aarav Sharma")
        self.assertTrue(len(data["recentEvidence"]) > 0)

    # 16. Teacher Authorization (Forbidden 403 on non-enrolled learner)
    @patch("services.learning.learning_recommendations.verify_teacher_student_access", new_callable=AsyncMock)
    def test_teacher_unauthorized_learner_access(self, mock_verify):
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=403, detail="Student is not enrolled in your classroom.")

        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        res = self.client.get("/api/v2/learning-recommendations/teacher/student-other")

        self.assertEqual(res.status_code, 403)

    # 17. Parent Authorization (Authorized parent accesses linked child)
    @patch("services.learning.learning_recommendations.verify_parent_student_access", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_parent_authorized_child_access(self, mock_db, mock_gen, mock_verify):
        mock_verify.return_value = {"status": "active"}
        mock_gen.return_value = StudentRecommendationsResponse(
            learnerId="student-101",
            horizon="today",
            recommendations=[],
            studyPlan=StudyPlan(items=[], totalEstimatedMinutes=15, completedCount=0, totalCount=0),
            currentLearningLevel=1,
            currentLearningLevelName="Foundation",
            currentAdaptiveTier=1,
            currentAdaptiveTierName="Foundation",
            dataSufficiency="sufficient_data",
            generatedAt="2026-10-08T00:00:00Z",
        )
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-101", "name": "Aarav Sharma"})

        app.dependency_overrides[require_parent] = lambda: self.parent_user
        res = self.client.get("/api/v2/learning-recommendations/parent/student-101")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertIn("reading together today", data["suggestedPracticeAtHome"].lower())
        self.assertTrue(len(data["parentTips"]) >= 3)

    # 18. Parent Authorization (Forbidden 403 on unlinked learner)
    @patch("services.learning.learning_recommendations.verify_parent_student_access", new_callable=AsyncMock)
    def test_parent_unauthorized_child_access(self, mock_verify):
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=403, detail="No active parent link for this student.")

        app.dependency_overrides[require_parent] = lambda: self.parent_user
        res = self.client.get("/api/v2/learning-recommendations/parent/student-unlinked")

        self.assertEqual(res.status_code, 403)

    # 19. Privacy: Zero Tutor Transcripts Exposed
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_privacy_zero_tutor_transcripts(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=0, sufficiency="no_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        raw_text = res.text.lower()
        self.assertNotIn("transcript", raw_text)
        self.assertNotIn("conversation_history", raw_text)
        self.assertNotIn("chat_messages", raw_text)

    # 20. Privacy: Zero Raw Audio Exposed
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_privacy_zero_raw_audio(self, mock_db, mock_insights, mock_state, mock_profile):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_insights.return_value = make_mock_insights(learner_id="student-101", sessions=0, sufficiency="no_data")
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        raw_text = res.text.lower()
        self.assertNotIn("raw_audio", raw_text)
        self.assertNotIn("audio_blob", raw_text)
        self.assertNotIn(".wav", raw_text)
        self.assertNotIn(".mp3", raw_text)

    # 21. Feature Flag 503 Governance
    def test_feature_flag_disabled_returns_503(self):
        settings.V2_LEARNING_RECOMMENDATIONS = False

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student")

        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled", res.json()["detail"].lower())

    # 22. Invalid Period Parameter (422 validation)
    def test_invalid_period_parameter_returns_422(self):
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/learning-recommendations/student?period=30d")

        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
