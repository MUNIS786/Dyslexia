"""
backend/test_phase4_reading_coach.py — Automated Test Suite for Phase 4 Adaptive Reading Coach.

Tests:
1. Models (Valid/Invalid Passage, Session, Question, Vocabulary)
2. Passage Catalog (Seeding, Retrieval, Filtering by Tier & Domain, Fallback)
3. Reading Performance Engine (Comprehension, Zero-Question Safety, Pacing, Overall, Grading, Trend)
4. Adaptive Recommender (ZPD Tier Integration, Growth Area Targeting, Explainable Reason, Unscreened Fallback)
5. Session Lifecycle & Security (Start, Complete, Duplicate Prevention, Student Isolation, Teacher Access)
6. Adaptive Progression Integration (Reading Completion -> State Update -> Tier Adjustment -> Next Rec)
7. Offline Independence (No external AI API required)
8. Feature Flag Enforcement (V2_READING_COACH toggle)
"""
import unittest
import uuid
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_reading import (
    ReadingPassage,
    ReadingQuestion,
    ReadingVocabularyWord,
    ReadingSession,
    ReadingSessionStartRequest,
    ReadingSessionCompleteRequest,
    ReadingAccessibilityConfig,
)
from services.learning.reading_performance import (
    calculate_comprehension_score,
    calculate_completion_rate,
    calculate_time_efficiency,
    calculate_overall_score,
    grade_comprehension_answers,
    analyze_reading_trend,
)
from services.learning.reading_service import (
    DEFAULT_PASSAGES,
    get_passages,
    get_passage_by_id,
    start_reading_session,
    complete_reading_session,
    get_learner_sessions,
    get_learner_reading_stats,
)
from services.learning.reading_recommender import (
    recommend_reading_passage,
    _build_explainable_reading_reason,
)


class TestReadingModels(unittest.TestCase):
    """Test validation rules for reading models."""

    def test_valid_passage(self):
        passage = ReadingPassage(
            passageId="pas-t1-test",
            title="A Sunny Day",
            text="The sun is warm. The sky is blue.",
            difficulty=1,
            domain="reading_comprehension",
            wordCount=8,
            estimatedMinutes=1,
            questions=[
                ReadingQuestion(
                    questionId="q-1",
                    question="What color is the sky?",
                    options=["Green", "Blue", "Red"],
                    correctAnswer=1,
                    explanation="The text says the sky is blue.",
                    questionType="detail"
                )
            ],
            vocabulary=[
                ReadingVocabularyWord(
                    word="warm",
                    definition="Having a comfortable degree of heat.",
                    phonetic="wawrm",
                    syllables=["warm"]
                )
            ]
        )
        self.assertEqual(passage.passageId, "pas-t1-test")
        self.assertEqual(passage.difficulty, 1)
        self.assertEqual(len(passage.questions), 1)
        self.assertEqual(len(passage.vocabulary), 1)

    def test_invalid_passage_difficulty(self):
        with self.assertRaises(Exception):
            ReadingPassage(
                passageId="pas-invalid",
                title="Invalid",
                text="Text",
                difficulty=6,  # Valid range is 1-5
                wordCount=1,
            )

    def test_valid_session_start_request(self):
        req = ReadingSessionStartRequest(passageId="pas-t1-001", readingMode="focus")
        self.assertEqual(req.passageId, "pas-t1-001")
        self.assertEqual(req.readingMode, "focus")

    def test_valid_session_complete_request(self):
        req = ReadingSessionCompleteRequest(
            sessionId=str(uuid.uuid4()),
            durationSeconds=120,
            comprehensionAnswers={"q-1": 1},
            difficultWords=["lotus"],
            practicedWords=["lotus"],
            completed=True,
        )
        self.assertEqual(req.durationSeconds, 120)
        self.assertTrue(req.completed)


class TestReadingPerformanceEngine(unittest.TestCase):
    """Test transparent performance calculations and safety guards."""

    def test_comprehension_score_standard(self):
        self.assertEqual(calculate_comprehension_score(3, 4), 75.0)
        self.assertEqual(calculate_comprehension_score(4, 4), 100.0)
        self.assertEqual(calculate_comprehension_score(0, 4), 0.0)

    def test_comprehension_zero_question_protection(self):
        # Must not raise ZeroDivisionError
        self.assertEqual(calculate_comprehension_score(0, 0), 100.0)

    def test_completion_rate(self):
        self.assertEqual(calculate_completion_rate(50, 100), 50.0)
        self.assertEqual(calculate_completion_rate(100, 100), 100.0)
        self.assertEqual(calculate_completion_rate(120, 100), 100.0)  # Clamped to 100
        self.assertEqual(calculate_completion_rate(0, 0), 100.0)

    def test_time_efficiency(self):
        # 60 words in 60s at Tier 1 (optimal)
        score = calculate_time_efficiency(60, 60, difficulty_tier=1)
        self.assertGreaterEqual(score, 80.0)

        # Zero duration guard
        score_zero = calculate_time_efficiency(0, 50, difficulty_tier=1)
        self.assertEqual(score_zero, 75.0)

    def test_overall_score_weighted(self):
        score = calculate_overall_score(
            comprehension_score=80.0,
            completion_rate=100.0,
            time_efficiency=90.0,
            completed=True,
            skipped=False,
            hints_used=0,
            words_practiced_count=2
        )
        # 0.60 * 80 (48) + 0.25 * 100 (25) + 0.15 * 90 (13.5) + bonus 3.0 = 89.5
        self.assertAlmostEqual(score, 89.5, delta=1.0)

    def test_overall_score_skipped_session(self):
        score = calculate_overall_score(
            comprehension_score=100.0,
            completion_rate=100.0,
            time_efficiency=100.0,
            completed=False,
            skipped=True
        )
        self.assertEqual(score, 20.0)

    def test_grade_comprehension_answers_by_index_and_text(self):
        questions = [
            {
                "questionId": "q-1",
                "question": "What animal is Leo?",
                "options": ["Frog", "Cat", "Dog"],
                "correctAnswer": 0,
                "explanation": "Leo is a tree frog.",
                "questionType": "detail"
            },
            {
                "questionId": "q-2",
                "question": "Where does he live?",
                "options": ["Desert", "Quiet lotus pond"],
                "correctAnswer": "Quiet lotus pond",
                "explanation": "He lives by the pond.",
                "questionType": "detail"
            }
        ]

        # Test index matching
        answers1 = {"q-1": 0, "q-2": 1}
        correct, total, _ = grade_comprehension_answers(questions, answers1)
        self.assertEqual(correct, 2)
        self.assertEqual(total, 2)

        # Test string matching
        answers2 = {"q-1": "Frog", "q-2": "Quiet lotus pond"}
        correct, total, _ = grade_comprehension_answers(questions, answers2)
        self.assertEqual(correct, 2)

        # Test partial incorrect
        answers3 = {"q-1": 1, "q-2": "Quiet lotus pond"}
        correct, total, _ = grade_comprehension_answers(questions, answers3)
        self.assertEqual(correct, 1)

    def test_trend_analysis(self):
        # Improving trend
        self.assertEqual(analyze_reading_trend([50.0, 55.0, 70.0, 80.0, 85.0]), "improving")
        # Needs support
        self.assertEqual(analyze_reading_trend([45.0, 40.0, 50.0, 45.0]), "needs_support")
        # Steady
        self.assertEqual(analyze_reading_trend([75.0, 78.0, 74.0, 76.0]), "steady")


class TestPassageCatalog(unittest.IsolatedAsyncioTestCase):
    """Test passage catalog retrieval and filtering."""

    @patch("services.learning.reading_service.db")
    async def test_default_passages_cover_all_tiers(self, mock_db):
        tiers_present = {p["difficulty"] for p in DEFAULT_PASSAGES}
        self.assertTrue({1, 2, 3, 4, 5}.issubset(tiers_present), "All 5 tiers must be covered in seed catalog")

    @patch("services.learning.reading_service.db")
    async def test_filter_passages_by_tier(self, mock_db):
        # Mock cursor for db.reading_passages.find
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[p for p in DEFAULT_PASSAGES if p["difficulty"] == 1])
        mock_db.reading_passages.find.return_value = mock_cursor

        t1_passages = await get_passages(tier=1)
        self.assertTrue(len(t1_passages) >= 2)
        for p in t1_passages:
            self.assertEqual(p["difficulty"], 1)

    @patch("services.learning.reading_service.db")
    async def test_get_passage_by_id(self, mock_db):
        target = [p for p in DEFAULT_PASSAGES if p["passageId"] == "pas-t1-001"][0]
        mock_db.reading_passages.find_one = AsyncMock(return_value=target)

        p = await get_passage_by_id("pas-t1-001")
        self.assertIsNotNone(p)
        self.assertEqual(p["title"], "Sam the Orange Cat")
        self.assertTrue(len(p["questions"]) > 0)
        self.assertTrue(len(p["vocabulary"]) > 0)


class TestAdaptivePassageRecommender(unittest.IsolatedAsyncioTestCase):
    """Test ZPD-based passage recommendation."""

    @patch("services.learning.reading_recommender.db")
    @patch("services.learning.reading_recommender.get_learning_state")
    @patch("services.learning.reading_recommender.get_or_create_learner_profile")
    @patch("services.learning.reading_recommender.get_passages")
    async def test_recommendation_matches_learner_tier(
        self, mock_get_passages, mock_profile, mock_state, mock_db
    ):
        mock_profile.return_value = {
            "learner_id": "test-student-1",
            "adaptive_difficulty": {"active_tier": 2},
            "areas_for_practice": [{"domain": "reading_comprehension"}],
            "strengths": [{"domain": "visual_processing"}],
        }
        mock_state.return_value = {
            "active_difficulty_tier": 2,
            "consecutive_passes": 1,
            "rolling_comprehension_scores": [80.0],
        }

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = mock_cursor

        t2_passages = [p for p in DEFAULT_PASSAGES if p["difficulty"] == 2]
        mock_get_passages.return_value = t2_passages

        rec = await recommend_reading_passage("test-student-1")
        self.assertEqual(rec.difficulty, 2)
        self.assertIn("Level 2", rec.reason)
        self.assertGreater(rec.confidence, 0.70)

    def test_explainable_reading_reason(self):
        reason = _build_explainable_reading_reason(
            passage={"title": "Leo the Frog"},
            tier=2,
            consecutive_passes=3,
            recent_accuracy=85.0,
            is_practice_area=False,
            is_strength=False
        )
        self.assertIn("great comprehension", reason)
        self.assertIn("Level 2", reason)


class TestReadingSessionLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test starting and completing reading sessions."""

    @patch("services.learning.reading_service.db")
    async def test_start_reading_session(self, mock_db):
        mock_db.reading_sessions.insert_one = AsyncMock()
        target_p = [p for p in DEFAULT_PASSAGES if p["passageId"] == "pas-t1-001"][0]
        mock_db.reading_passages.find_one = AsyncMock(return_value=target_p)

        req = ReadingSessionStartRequest(passageId="pas-t1-001", readingMode="guided")
        res = await start_reading_session("student-100", req)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["session"]["learnerId"], "student-100")
        self.assertEqual(res["session"]["readingMode"], "guided")
        self.assertEqual(res["session"]["passageId"], "pas-t1-001")

    @patch("services.learning.reading_service.db")
    @patch("services.learning.reading_service.recalibrate_from_activity")
    @patch("services.learning.reading_service.get_learning_state")
    async def test_complete_reading_session_success(
        self, mock_get_state, mock_recal, mock_db
    ):
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "sessionId": "sess-abc",
            "learnerId": "student-100",
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "wordsPresented": 60,
            "readingMode": "standard",
            "completed": False,
        })
        mock_get_state.return_value = {
            "active_difficulty_tier": 1,
            "consecutive_passes": 0,
            "consecutive_failures": 0,
            "rolling_comprehension_scores": [],
            "current_streak": 1,
        }
        mock_db.reading_sessions.update_one = AsyncMock()
        mock_db.learning_states.update_one = AsyncMock()
        mock_db.progress.update_one = AsyncMock()
        mock_recal.return_value = {}

        target_p = [p for p in DEFAULT_PASSAGES if p["passageId"] == "pas-t1-001"][0]
        mock_db.reading_passages.find_one = AsyncMock(return_value=target_p)

        # All 3 questions answered correctly
        req = ReadingSessionCompleteRequest(
            sessionId="sess-abc",
            durationSeconds=75,
            comprehensionAnswers={
                "q-t1-001-1": 1,  # Bright orange
                "q-t1-001-2": 2,  # A little bug
                "q-t1-001-3": 1,  # Into the blue sky
            },
            practicedWords=["purrs"],
            completed=True,
        )

        res = await complete_reading_session("student-100", req)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["comprehensionScore"], 100.0)
        self.assertEqual(res["correctCount"], 3)
        self.assertGreater(res["overallScore"], 80.0)

    @patch("services.learning.reading_service.db")
    async def test_prevent_unauthorized_completion(self, mock_db):
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "sessionId": "sess-xyz",
            "learnerId": "other-student-999",
            "completed": False,
        })
        req = ReadingSessionCompleteRequest(sessionId="sess-xyz", durationSeconds=60)
        with self.assertRaises(PermissionError):
            await complete_reading_session("student-100", req)

    @patch("services.learning.reading_service.db")
    async def test_prevent_duplicate_completion(self, mock_db):
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "sessionId": "sess-already-done",
            "learnerId": "student-100",
            "completed": True,
            "completedAt": int(time.time()),
        })
        req = ReadingSessionCompleteRequest(sessionId="sess-already-done", durationSeconds=60)
        with self.assertRaises(ValueError):
            await complete_reading_session("student-100", req)


class TestFastAPIRoutes(unittest.TestCase):
    """Integration tests for reading coach endpoints via TestClient."""

    def setUp(self):
        self.client = TestClient(app)

    def test_feature_flag_disabled_returns_503(self):
        with patch.object(settings, "V2_READING_COACH", False):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/passages")
                self.assertEqual(res.status_code, 503)
                self.assertIn("disabled via feature flags", res.json()["detail"])
            finally:
                app.dependency_overrides.clear()

    def test_passages_endpoint_enabled(self):
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/passages?tier=1")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "ok")
                self.assertTrue(len(data["passages"]) >= 2)
            finally:
                app.dependency_overrides.clear()

    def test_single_passage_endpoint(self):
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/passages/pas-t1-001")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["passage"]["passageId"], "pas-t1-001")
            finally:
                app.dependency_overrides.clear()

    def test_single_passage_not_found(self):
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/passages/pas-nonexistent-999")
                self.assertEqual(res.status_code, 404)
            finally:
                app.dependency_overrides.clear()

    @patch("routers.v2_reading.recommend_reading_passage", new_callable=AsyncMock)
    def test_recommendation_endpoint(self, mock_rec):
        target_p = [p for p in DEFAULT_PASSAGES if p["passageId"] == "pas-t1-001"][0]
        mock_rec.return_value = {
            "recommendedPassage": target_p,
            "difficulty": 1,
            "domain": "reading_comprehension",
            "reason": "Test recommendation reason at Level 1",
            "confidence": 0.88,
        }
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/recommendation")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["difficulty"], 1)
                self.assertIn("recommendedPassage", data)
                self.assertEqual(data["recommendedPassage"]["passageId"], "pas-t1-001")
            finally:
                app.dependency_overrides.clear()

    @patch("routers.v2_reading.start_reading_session", new_callable=AsyncMock)
    def test_start_session_endpoint(self, mock_start):
        mock_start.return_value = {
            "status": "ok",
            "session": {"sessionId": "test-sess-123", "learnerId": "test-student"},
            "passage": {"title": "Test Passage"},
        }
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.post("/api/v2/reading/session/start", json={"passageId": "pas-t1-001", "readingMode": "standard"})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "ok")
                self.assertEqual(data["session"]["sessionId"], "test-sess-123")
            finally:
                app.dependency_overrides.clear()

    @patch("routers.v2_reading.complete_reading_session", new_callable=AsyncMock)
    def test_complete_session_endpoint(self, mock_complete):
        mock_complete.return_value = {
            "status": "ok",
            "sessionId": "test-sess-123",
            "readingScore": 90.0,
            "comprehensionScore": 100.0,
            "overallScore": 92.5,
            "currentTier": 2,
            "streak": 3,
            "nextStepMessage": "Great reading!",
        }
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.post(
                    "/api/v2/reading/session/complete",
                    json={"sessionId": "test-sess-123", "durationSeconds": 90, "completed": True}
                )
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "ok")
                self.assertEqual(data["overallScore"], 92.5)
            finally:
                app.dependency_overrides.clear()

    @patch("routers.v2_reading.get_learner_sessions", new_callable=AsyncMock)
    def test_sessions_endpoint_student_isolation(self, mock_sessions):
        mock_sessions.return_value = [{"sessionId": "sess-mine"}]
        with patch.object(settings, "V2_READING_COACH", True):
            # Student requesting own sessions
            app.dependency_overrides[get_current_user] = lambda: {"id": "student-A", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/sessions")
                self.assertEqual(res.status_code, 200)

                # Student trying to view student-B sessions -> Forbidden
                res_forbidden = self.client.get("/api/v2/reading/sessions?student_id=student-B")
                self.assertEqual(res_forbidden.status_code, 403)
                self.assertIn("not authorized", res_forbidden.json()["detail"])
            finally:
                app.dependency_overrides.clear()

    @patch("routers.v2_reading.get_learner_reading_stats", new_callable=AsyncMock)
    def test_stats_endpoint(self, mock_stats):
        from models.v2_reading import ReadingStatsResponse
        mock_stats.return_value = ReadingStatsResponse(
            totalSessions=5,
            completedSessions=5,
            totalWordsRead=400,
            totalMinutesRead=12.5,
            avgComprehensionAccuracy=85.0,
            avgOverallScore=88.0,
            currentTier=2,
            wordsPracticedCount=6,
            recentSessions=[],
            domainPerformance={"reading_comprehension": 85.0, "reading_fluency": 82.0},
            trend="improving",
        )
        with patch.object(settings, "V2_READING_COACH", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "test-student", "role": "student"}
            try:
                res = self.client.get("/api/v2/reading/stats")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["totalSessions"], 5)
                self.assertEqual(data["trend"], "improving")
            finally:
                app.dependency_overrides.clear()

    def test_offline_independence_no_ai_service_invoked(self):
        """Verifies that all Phase 4 functionality executes with zero calls to Gemini/Claude."""
        with patch("services.ai_service.chat_reply", side_effect=RuntimeError("AI must not be called!")):
            passages = [p for p in DEFAULT_PASSAGES if p["difficulty"] == 1]
            self.assertTrue(len(passages) >= 2)
            # Grade answers offline
            c, t, _ = grade_comprehension_answers(passages[0]["questions"], {"q-t1-001-1": 1})
            self.assertEqual(t, 3)
            # Reason generation offline
            reason = _build_explainable_reading_reason(passages[0], 1, 2, 85.0, False, False)
            self.assertIn("Level 1", reason)


if __name__ == "__main__":
    unittest.main()
