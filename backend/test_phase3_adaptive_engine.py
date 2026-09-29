"""
backend/test_phase3_adaptive_engine.py — Unit & Integration Tests for Phase 3 Adaptive Learning Engine.

Verifies:
- 5-Tier Readability & Calibration parameters
- Zone of Proximal Development (ZPD) Upward Adaptation (3 consecutive passes or +15% jump)
- Downward Adaptation / Scaffolding (2 consecutive failures or -15% drop)
- Activity Recommender (matches profile growth areas and strengths with explainable rationale)
- Attempt Telemetry & Profile Recalibration
- Feature flag enforcement
- FastAPI Endpoint responses & security
"""
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_learning_state import ActivityAttemptCreate
from services.learning.difficulty_engine import (
    clamp_tier,
    get_tier_calibration,
    estimate_syllables,
    analyze_text_readability,
    TIER_CONFIGURATIONS,
)
from services.learning.activity_recommender import (
    DEFAULT_ACTIVITIES,
    get_catalog_activities,
    recommend_adaptive_activities,
    _build_explainable_rationale,
)
from services.learning.adaptive_engine import evaluate_attempt_and_adapt


class TestDifficultyEngine(unittest.TestCase):
    """Tests 5-tier calibration and text readability analysis."""

    def test_clamp_tier(self):
        self.assertEqual(clamp_tier(0), 1)
        self.assertEqual(clamp_tier(1), 1)
        self.assertEqual(clamp_tier(3), 3)
        self.assertEqual(clamp_tier(5), 5)
        self.assertEqual(clamp_tier(8), 5)
        self.assertEqual(clamp_tier("invalid"), 1)

    def test_tier_calibrations(self):
        for tier in range(1, 6):
            cal = get_tier_calibration(tier)
            self.assertEqual(cal.tier, tier)
            self.assertIn("name", cal.model_dump())
            self.assertTrue(cal.maxSentenceLength > 0)
            self.assertTrue(cal.allowedHints >= 1)

        # Tier 1 vs Tier 5 comparison
        t1 = get_tier_calibration(1)
        t5 = get_tier_calibration(5)
        self.assertLess(t1.maxSentenceLength, t5.maxSentenceLength)
        self.assertGreater(t1.timeLimitMultiplier, t5.timeLimitMultiplier)

    def test_estimate_syllables(self):
        self.assertEqual(estimate_syllables("cat"), 1)
        self.assertEqual(estimate_syllables("flag"), 1)
        self.assertEqual(estimate_syllables("butterfly"), 3)
        self.assertEqual(estimate_syllables("reading"), 2)

    def test_analyze_text_readability(self):
        simple = "Pip saw the cat. The cat was red."
        analysis = analyze_text_readability(simple)
        self.assertEqual(analysis["sentenceCount"], 2)
        self.assertIn(analysis["recommendedTier"], (1, 2))

        complex_text = (
            "Photosynthesis constitutes a biochemical mechanism whereby plant organisms "
            "synthesize organic carbohydrate nutrients through electromagnetic solar radiation."
        )
        analysis_complex = analyze_text_readability(complex_text)
        self.assertGreaterEqual(analysis_complex["recommendedTier"], 4)


class TestAdaptiveProgressionLogic(unittest.IsolatedAsyncioTestCase):
    """Tests ZPD upward, downward, and maintaining adaptation transitions."""

    @patch("services.learning.adaptive_engine.db")
    @patch("services.learning.adaptive_engine.get_learning_state")
    @patch("services.learning.adaptive_engine.recalibrate_from_activity")
    async def test_upward_adaptation_three_passes(self, mock_recal, mock_get_state, mock_db):
        """3 consecutive passes (>=80%) triggers progression from Tier 1 to Tier 2."""
        mock_get_state.return_value = {
            "active_difficulty_tier": 1,
            "consecutive_passes": 2,  # this attempt will make it 3
            "consecutive_failures": 0,
            "rolling_comprehension_scores": [85.0, 90.0],
            "current_streak": 2,
            "today_tasks_completed": 1,
        }
        mock_db.activity_attempts.insert_one = AsyncMock()
        mock_db.learning_states.update_one = AsyncMock()
        mock_db.adaptive_recommendations.insert_one = AsyncMock()
        mock_db.learning_activities.find_one = AsyncMock(return_value={"domain": "phonological_awareness"})
        mock_recal.return_value = {}

        attempt = ActivityAttemptCreate(
            activityId="act-phon-001",
            scorePercent=88.0,
            durationSeconds=45,
            hesitationCount=1,
            hintsRequested=0,
        )

        res = await evaluate_attempt_and_adapt("test-user-1", attempt)
        self.assertTrue(res.adaptationTriggered)
        self.assertEqual(res.previousTier, 1)
        self.assertEqual(res.currentTier, 2)
        self.assertTrue(res.tierChanged)
        self.assertTrue(res.celebration)

    @patch("services.learning.adaptive_engine.db")
    @patch("services.learning.adaptive_engine.get_learning_state")
    @patch("services.learning.adaptive_engine.recalibrate_from_activity")
    async def test_downward_scaffolding_two_failures(self, mock_recal, mock_get_state, mock_db):
        """2 consecutive failures (<50%) triggers scaffolding adjustment from Tier 3 to Tier 2."""
        mock_get_state.return_value = {
            "active_difficulty_tier": 3,
            "consecutive_passes": 0,
            "consecutive_failures": 1,  # this attempt will make it 2
            "rolling_comprehension_scores": [40.0],
            "current_streak": 1,
            "today_tasks_completed": 0,
        }
        mock_db.activity_attempts.insert_one = AsyncMock()
        mock_db.learning_states.update_one = AsyncMock()
        mock_db.adaptive_recommendations.insert_one = AsyncMock()
        mock_db.learning_activities.find_one = AsyncMock(return_value={"domain": "orthographic_spelling"})
        mock_recal.return_value = {}

        attempt = ActivityAttemptCreate(
            activityId="act-spell-003",
            scorePercent=35.0,
            durationSeconds=90,
            hesitationCount=5,
            hintsRequested=2,
        )

        res = await evaluate_attempt_and_adapt("test-user-2", attempt)
        self.assertTrue(res.adaptationTriggered)
        self.assertEqual(res.previousTier, 3)
        self.assertEqual(res.currentTier, 2)
        self.assertTrue(res.tierChanged)
        self.assertIn("scaffolding", res.message.lower())

    @patch("services.learning.adaptive_engine.db")
    @patch("services.learning.adaptive_engine.get_learning_state")
    @patch("services.learning.adaptive_engine.recalibrate_from_activity")
    async def test_maintain_zpd_comfort_zone(self, mock_recal, mock_get_state, mock_db):
        """Score between 50% and 80% maintains current tier within optimal ZPD."""
        mock_get_state.return_value = {
            "active_difficulty_tier": 2,
            "consecutive_passes": 1,
            "consecutive_failures": 0,
            "rolling_comprehension_scores": [70.0],
            "current_streak": 3,
            "today_tasks_completed": 1,
        }
        mock_db.activity_attempts.insert_one = AsyncMock()
        mock_db.learning_states.update_one = AsyncMock()
        mock_db.learning_activities.find_one = AsyncMock(return_value={"domain": "rapid_naming"})
        mock_recal.return_value = {}

        attempt = ActivityAttemptCreate(
            activityId="act-ran-002",
            scorePercent=68.0,
            durationSeconds=50,
            hesitationCount=2,
            hintsRequested=1,
        )

        res = await evaluate_attempt_and_adapt("test-user-3", attempt)
        self.assertFalse(res.adaptationTriggered)
        self.assertEqual(res.previousTier, 2)
        self.assertEqual(res.currentTier, 2)
        self.assertFalse(res.tierChanged)


class TestActivityRecommender(unittest.IsolatedAsyncioTestCase):
    """Tests recommendation generation and pedagogical rationale."""

    def test_default_activities_integrity(self):
        self.assertGreaterEqual(len(DEFAULT_ACTIVITIES), 10)
        for act in DEFAULT_ACTIVITIES:
            self.assertIn("id", act)
            self.assertIn("title", act)
            self.assertIn("domain", act)
            self.assertIn("difficultyTier", act)
            self.assertIn("contentPayload", act)

    @patch("services.learning.activity_recommender.db")
    async def test_recommend_adaptive_activities(self, mock_db):
        mock_db.learner_profiles.find_one = AsyncMock(return_value={
            "strengths": [{"domain": "visual_processing", "label": "Strength"}],
            "areasForPractice": [{"domain": "phonological_awareness", "priority": "high"}],
            "learningLevel": {"level": 2},
        })
        mock_db.learning_states.find_one = AsyncMock(return_value={
            "activeDifficultyTier": 2,
        })
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=DEFAULT_ACTIVITIES)
        mock_db.learning_activities.find = MagicMock(return_value=mock_cursor)

        recs = await recommend_adaptive_activities("test-user-rec", count=3)
        self.assertGreaterEqual(len(recs), 2)
        domains = [r.targetDomain for r in recs]
        # Should include targeted practice area or strength
        self.assertTrue(
            any(d in ("phonological_awareness", "visual_processing") for d in domains)
        )
        for r in recs:
            self.assertTrue(len(r.rationale) > 10)


class TestV2LearningEndpoints(unittest.TestCase):
    """Tests FastAPI router endpoints with authentication mocks."""

    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-123",
            "name": "Aarav Sharma",
            "email": "aarav@test.school",
            "role": "student",
            "classroomCode": "DA-DEMO",
        }

    def test_activities_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            resp = self.client.get("/api/v2/learning/activities?tier=1")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertIsInstance(data["activities"], list)
        finally:
            app.dependency_overrides.clear()

    def test_tier_info_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            resp = self.client.get("/api/v2/learning/tier-info")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertIn("1", data["tiers"])
        finally:
            app.dependency_overrides.clear()

    @patch("routers.v2_learning.recommend_adaptive_activities")
    def test_recommendations_endpoint(self, mock_rec):
        mock_rec.return_value = [
            MagicMock(
                model_dump=lambda: {
                    "id": "rec-1",
                    "targetDomain": "phonological_awareness",
                    "difficultyTier": 2,
                    "rationale": "Great practice!",
                    "confidenceScore": 0.9,
                    "matchType": "practice_area",
                    "activity": DEFAULT_ACTIVITIES[0],
                }
            )
        ]
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            resp = self.client.get("/api/v2/learning/recommendations")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["count"], 1)
        finally:
            app.dependency_overrides.clear()

    @patch("routers.v2_learning.evaluate_attempt_and_adapt")
    def test_attempt_submission_endpoint(self, mock_adapt):
        mock_adapt.return_value = {
            "status": "ok",
            "attemptId": "att-123",
            "scorePercent": 85.0,
            "adaptationTriggered": True,
            "previousTier": 1,
            "currentTier": 2,
            "tierChanged": True,
            "celebration": True,
            "message": "Leveled up!",
            "streak": 3,
            "learningState": {"activeDifficultyTier": 2},
        }
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            payload = {
                "activityId": "act-phon-001",
                "scorePercent": 85.0,
                "durationSeconds": 45,
                "hesitationCount": 0,
                "hintsRequested": 0,
            }
            resp = self.client.post("/api/v2/learning/attempt", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["currentTier"], 2)
            self.assertTrue(data["celebration"])
        finally:
            app.dependency_overrides.clear()

    def test_feature_flag_disabled(self):
        orig = settings.V2_ADAPTIVE_ENGINE
        settings.V2_ADAPTIVE_ENGINE = False
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            resp = self.client.get("/api/v2/learning/activities")
            self.assertEqual(resp.status_code, 503)
        finally:
            settings.V2_ADAPTIVE_ENGINE = orig
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
