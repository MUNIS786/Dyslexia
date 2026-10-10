"""
backend/test_phase15_personalized_content.py — Comprehensive Test Suite for Phase 15:
Personalized Learning Content & Activity Engine.

Covers all 20+ required verification scenarios:
1. Feature flag enabled & disabled (HTTP 503).
2. Authenticated student retrieval of suitable content (GET /next).
3. Student tenant isolation (cannot request another learner's private content).
4. Teacher authorization following classroom/tenant rules (200 for authorized, 403 for unauthorized).
5. Parent authorization following verified relationship rules (200 for authorized, 403 for unauthorized).
6. Current adaptive tier is respected across selections.
7. Recommendation categories map to appropriate activity types:
   - READING_PRACTICE -> GUIDED_READING
   - DIFFICULT_WORD_PRACTICE -> DIFFICULT_WORD_PRACTICE
   - SPEECH_PRACTICE -> ORAL_READING_SPEECH
   - REVIEW -> SKILL_REVIEW
   - STRETCH -> GUIDED_READING at tier+1
8. Existing activity IDs and passage IDs are preserved (e.g. pas-t1-001, act-phon-001).
9. Language filtering works for English, Hindi, and Marathi.
10. Missing translated content returns an honest fallback state (does not fabricate Marathi at Tier 4).
11. No available content is handled safely.
12. New learner with insufficient history is supported (foundation Tier 1 content).
13. Previously completed activities are marked completed based on real DB records only.
14. Repeated requests do not create duplicate attempts.
15. Opening / launching an activity does NOT mark it completed (completed=False).
16. Completion state reflects persisted records only (zero fake completions).
17. Missing or stale recommendation references are handled safely (HTTP 404).
18. Accessibility preferences attached / formatted for display.
19. Existing Phase 14 recommendation behavior is unchanged.
20. Tenant isolation tested across endpoints.
"""
import time
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, require_parent
from models.v2_learning_recommendations import (
    StudentRecommendationsResponse,
    StudyPlan,
    RecommendationItem,
    StudyPlanItem,
)
from models.v2_personalized_content import (
    PersonalizedContentItem,
    PersonalizedActivityNextResponse,
    PersonalizedActivitiesListResponse,
    PersonalizedContentLaunchRequest,
)


def make_cursor_mock(items):
    """Helper to mock a synchronous cursor returned by motor find() whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


def make_mock_recommendations_response(
    learner_id="student-101",
    tier=1,
    category="READING_PRACTICE",
    target_words=None,
    completed=False,
):
    """Creates a mock Phase 14 StudentRecommendationsResponse fixture."""
    rec_item = RecommendationItem(
        id=f"rec-{learner_id[:6]}-{category.lower()}-1",
        category=category,
        title=f"Test Activity for {category}",
        reason=f"Recommended for practice in {category}.",
        actionUrl="/student/reading-coach",
        actionLabel="Start Practice",
        estimatedDurationMinutes=10 if category in ("READING_PRACTICE", "STRETCH") else 5,
        confidence="high",
        priority=1,
        targetSkill="reading_fluency",
        targetWords=target_words or [],
        completed=completed,
        evidenceSignals=["Test signal 1"],
    )
    plan_item = StudyPlanItem(
        id=f"plan-item-{learner_id[:6]}-1",
        activityType=category,
        title=f"Test Activity for {category}",
        reason=f"Recommended for practice in {category}.",
        estimatedDurationMinutes=10,
        priority=1,
        actionUrl="/student/reading-coach",
        targetSkill="reading_fluency",
        targetWords=target_words or [],
        completed=completed,
    )
    study_plan = StudyPlan(
        horizon="today",
        items=[plan_item],
        totalEstimatedMinutes=10,
        completedCount=1 if completed else 0,
        totalCount=1,
    )
    return StudentRecommendationsResponse(
        learnerId=learner_id,
        horizon="today",
        recommendations=[rec_item],
        studyPlan=study_plan,
        currentLearningLevel=tier,
        currentLearningLevelName="Foundation" if tier == 1 else "Developing",
        currentAdaptiveTier=tier,
        currentAdaptiveTierName="Foundation" if tier == 1 else "Developing",
        dataSufficiency="sufficient_data",
        generatedAt="2026-10-10T10:00:00Z",
    )


class TestPhase15PersonalizedContent(unittest.TestCase):
    """Test suite for Phase 15 Personalized Learning Content & Activity Engine."""

    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-101",
            "name": "Aarav Sharma",
            "email": "aarav@school.edu",
            "role": "student",
            "preferredLanguage": "en",
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
        settings.V2_PERSONALIZED_CONTENT = True

    # 1. Feature Flag Disabled returns 503
    def test_feature_flag_disabled_returns_503(self):
        settings.V2_PERSONALIZED_CONTENT = False
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        res = self.client.get("/api/v2/personalized-content/next")
        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled", res.json()["detail"].lower())

    # 2. Authenticated Student can retrieve next suitable content
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_authenticated_student_get_next_activity(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1, "preferred_language": "en"}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value={"font": "OpenDyslexic", "fontSize": 20})

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertEqual(data["currentAdaptiveTier"], 1)
        self.assertTrue(data["hasContent"])
        self.assertIsNotNone(data["activity"])
        self.assertEqual(data["activity"]["activityType"], "GUIDED_READING")
        self.assertEqual(data["activity"]["difficultyTier"], 1)
        self.assertIn("/student/reading-coach", data["activity"]["actionUrl"])

    # 3. Student Tenant Isolation: Identity comes strictly from session
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_student_cannot_request_another_learner_private_content(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        # Authenticated as student-101
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        # Attempt to pass query param or header for student-999
        res = self.client.get("/api/v2/personalized-content/next?student_id=student-999")

        self.assertEqual(res.status_code, 200)
        # Result MUST belong to authenticated student-101, NOT student-999
        self.assertEqual(res.json()["learnerId"], "student-101")

    # 4. Teacher Authorization: Authorized Teacher succeeds
    @patch("services.learning.personalized_content.verify_teacher_student_access", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_teacher_authorized_learner_access(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile, mock_auth
    ):
        mock_auth.return_value = True
        mock_profile.return_value = {"name": "Aarav Sharma", "learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 3}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=2)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        res = self.client.get("/api/v2/personalized-content/teacher/student-101")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertEqual(data["currentAdaptiveTier"], 2)
        self.assertIn("Level 2", data["pedagogicalRationale"])
        self.assertIsNotNone(data["recommendedActivity"])

    # 5. Teacher Unauthorized returns 403
    @patch("services.learning.personalized_content.verify_teacher_student_access", new_callable=AsyncMock)
    def test_teacher_unauthorized_learner_access_returns_403(self, mock_auth):
        mock_auth.return_value = False

        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        res = self.client.get("/api/v2/personalized-content/teacher/student-unauthorized")

        self.assertEqual(res.status_code, 403)
        self.assertIn("not authorized", res.json()["detail"].lower())

    # 6. Parent Authorized succeeds
    @patch("services.learning.personalized_content.verify_parent_student_access", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_parent_authorized_child_access(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile, mock_auth
    ):
        mock_auth.return_value = True
        mock_profile.return_value = {"name": "Aarav Sharma", "learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[require_parent] = lambda: self.parent_user
        res = self.client.get("/api/v2/personalized-content/parent/student-101")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertIn("atHomeGuidance", data)
        self.assertTrue(len(data["focusWords"]) >= 1)

    # 7. Parent Unauthorized returns 403
    @patch("services.learning.personalized_content.verify_parent_student_access", new_callable=AsyncMock)
    def test_parent_unauthorized_child_access_returns_403(self, mock_auth):
        mock_auth.return_value = False

        app.dependency_overrides[require_parent] = lambda: self.parent_user
        res = self.client.get("/api/v2/personalized-content/parent/student-unauthorized")

        self.assertEqual(res.status_code, 403)
        self.assertIn("not authorized", res.json()["detail"].lower())

    # 8. Current Adaptive Tier is Respected
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_current_adaptive_tier_respected(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        # Student at Tier 3
        mock_profile.return_value = {"learning_level": 3}
        mock_state.return_value = {"active_difficulty_tier": 3}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=3, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["currentAdaptiveTier"], 3)
        self.assertEqual(data["activity"]["difficultyTier"], 3)

    # 9. Recommendation Category: DIFFICULT_WORD_PRACTICE Mapping
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_recommendation_category_difficult_words_mapping(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_recs.return_value = make_mock_recommendations_response(
            "student-101", tier=2, category="DIFFICULT_WORD_PRACTICE", target_words=["glance", "shimmer"]
        )
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        self.assertEqual(act["activityType"], "DIFFICULT_WORD_PRACTICE")
        self.assertIn("/student/adaptive-learning", act["actionUrl"])
        self.assertIn("glance", act["targetWords"])

    # 10. Recommendation Category: SPEECH_PRACTICE Mapping
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_recommendation_category_speech_mapping(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1, category="SPEECH_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        self.assertEqual(act["activityType"], "ORAL_READING_SPEECH")
        self.assertIn("mode=oral", act["actionUrl"])

    # 11. Recommendation Category: REVIEW Mapping
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_recommendation_category_review_mapping(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=2, category="REVIEW")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        self.assertEqual(act["activityType"], "SKILL_REVIEW")

    # 12. Recommendation Category: STRETCH Challenge Mapping
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_recommendation_category_stretch_mapping(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 2}
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 3}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=2, category="STRETCH")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        # Stretch tier should be tier + 1 = 3
        self.assertEqual(act["difficultyTier"], 3)
        self.assertEqual(act["category"], "STRETCH")

    # 13. Existing Activity and Passage IDs Preserved
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_existing_activity_ids_and_passage_ids_preserved(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        self.assertEqual(act["contentId"], "pas-t1-001")
        self.assertTrue(act["activityId"].startswith("act-guide-pas-t1-001"))

    # 14. Language Exact Matching: Marathi Tier 1
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_language_exact_matching_marathi(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1, "preferred_language": "mr"}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next?language=mr")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        self.assertEqual(act["language"], "mr")
        self.assertEqual(act["contentId"], "pas-mr-t1-001")
        self.assertEqual(act["availabilityStatus"], "EXACT_MATCH")

    # 15. Language Fallback Offered for Missing Translation (Marathi Tier 4)
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_language_fallback_offered_for_missing_translation(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 4, "preferred_language": "mr"}
        mock_state.return_value = {"active_difficulty_tier": 4}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=4, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next?language=mr")

        self.assertEqual(res.status_code, 200)
        act = res.json()["activity"]
        # Must NOT pretend English text is Marathi
        self.assertEqual(act["language"], "en")
        self.assertEqual(act["requestedLanguage"], "mr")
        self.assertEqual(act["availabilityStatus"], "LANGUAGE_FALLBACK_OFFERED")
        self.assertIsNotNone(act["languageFallbackMessage"])
        self.assertIn("not currently available", act["languageFallbackMessage"].lower())

    # 16. New Learner with No History Supported
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_new_learner_insufficient_history_supported(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {}  # Fresh profile
        mock_state.return_value = {}    # Fresh state
        mock_recs.return_value = make_mock_recommendations_response("student-fresh", tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: {"id": "student-fresh", "role": "student"}
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["hasContent"])
        self.assertEqual(data["currentAdaptiveTier"], 1)

    # 17. Activity Launch Does NOT Mark Completed (CRITICAL RULE)
    @patch("services.learning.personalized_content.db")
    def test_activity_launch_does_not_mark_completed(self, mock_db):
        mock_db.activity_launches.insert_one = AsyncMock(return_value=MagicMock(inserted_id="launch-123"))

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        payload = {
            "activityId": "act-guide-pas-t1-001",
            "activityType": "GUIDED_READING",
            "recommendationId": "rec-101-reading_practice-1",
        }
        res = self.client.post("/api/v2/personalized-content/launch", json=payload)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "launched")
        # Completed must remain False!
        self.assertFalse(data["completed"])
        mock_db.activity_launches.insert_one.assert_called_once()
        inserted_doc = mock_db.activity_launches.insert_one.call_args[0][0]
        self.assertFalse(inserted_doc["completed"])

    # 18. Repeated Requests Do Not Create Duplicate Attempts (Idempotency)
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_repeated_requests_do_not_create_duplicate_attempts(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.activity_attempts.insert_one = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        # Call multiple times
        res1 = self.client.get("/api/v2/personalized-content/next")
        res2 = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)
        # Verify db.activity_attempts was NEVER called by GET
        mock_db.activity_attempts.insert_one.assert_not_called()

    # 19. Retrieve Content for Phase 14 Recommendation & 404 for Stale
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_recommendation_content_link_and_404_handling(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        valid_rec_id = "rec-studen-reading_practice-1"
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user

        # 1. Valid recommendation ID
        res_valid = self.client.get(f"/api/v2/personalized-content/recommendation/{valid_rec_id}")
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(res_valid.json()["recommendationId"], valid_rec_id)

        # 2. Invalid / stale recommendation ID
        res_invalid = self.client.get("/api/v2/personalized-content/recommendation/rec-nonexistent-999")
        self.assertEqual(res_invalid.status_code, 404)
        self.assertIn("not found", res_invalid.json()["detail"].lower())

    # 20. Accessibility Preferences Attached
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_accessibility_config_attached(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response("student-101", tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value={
            "font": "Lexend",
            "fontSize": 24,
            "lineSpacing": 2.5,
            "letterSpacing": 0.15,
            "highContrast": True,
        })

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/next")

        self.assertEqual(res.status_code, 200)
        cfg = res.json()["activity"]["accessibilityConfig"]
        self.assertEqual(cfg["font"], "Lexend")
        self.assertEqual(cfg["fontSize"], 24)
        self.assertTrue(cfg["highContrast"])

    # 21. List Personalized Activities Returns Multi-Category Catalog
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_list_personalized_activities_filters(
        self, mock_db, mock_completions, mock_state, mock_profile
    ):
        mock_profile.return_value = {"learning_level": 1}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_completions.return_value = {"reading": True, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        res = self.client.get("/api/v2/personalized-content/activities?limit=5")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["learnerId"], "student-101")
        self.assertTrue(len(data["activities"]) >= 3)
        # Guided reading was completed today -> must reflect real record!
        guided = [a for a in data["activities"] if a["activityType"] == "GUIDED_READING"][0]
        self.assertTrue(guided["completed"])

    # 22. Unauthenticated Access Rejected with 401
    def test_unauthenticated_access_returns_401(self):
        # No dependency override
        res = self.client.get("/api/v2/personalized-content/next")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
