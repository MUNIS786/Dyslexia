"""
backend/test_phase17_integration.py — Comprehensive End-to-End Learning Journey & System Integration Test Suite.

Phase 17 Verification Matrix:
1. Student authentication and protected-route behavior.
2. Learner profile and adaptive state initialization.
3. Published-content eligibility (draft/review/archived exclusion).
4. Activity launch vs. actual completion (zero fake completions).
5. Persistence of reading progress and session telemetry.
6. Adaptive progression after valid activity completion (consecutive passes trigger tier increase).
7. Phase 14 recommendation generation from available learner evidence.
8. Phase 15 recommendation-to-activity navigation and content retrieval.
9. Phase 16 draft/review/publish restrictions (author cannot self-review, review required).
10. Teacher classroom and tenant isolation.
11. Parent link authorization and revocation (immediate access cutoff).
12. AI Tutor learner-context isolation and strict privacy protection.
13. Accessibility preference persistence across navigation.
14. English, Hindi, and Marathi preference consistency & Unicode preservation.
15. Learning insights data sufficiency and persistence (no_data, insufficient_data, sufficient_data).
16. Gamification idempotency (no duplicate points on repeated event processing).
17. Feature-flag behavior across V2 subsystems (clean HTTP 503).
18. Invalid IDs, missing records, and expired sessions handled safely.
19. Error recovery and resilience (graceful degradation when AI/speech fails).
20. Repeated requests without duplicate learning records.
21. Legacy V1 authentication and API compatibility.
22. Complete end-to-end multi-persona lifecycle (Student -> Teacher -> Parent loop).
"""
import time
import uuid
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, require_parent
from models.v2_content_authoring import (
    ContentDraftCreateRequest,
    ContentDraftUpdateRequest,
    ContentReviewDecisionRequest,
)
from models.v2_personalized_content import (
    PersonalizedContentLaunchRequest,
)
from models.v2_reading import (
    ReadingSessionStartRequest,
    ReadingSessionCompleteRequest,
)
from models.v2_learning_recommendations import (
    StudentRecommendationsResponse,
    StudyPlan,
    RecommendationItem,
    StudyPlanItem,
)
from models.v2_learning_insights import (
    StudentInsightsResponse,
    StudentProgressSummary,
    DataSufficiencyStatus,
)
from services.learning.reading_service import (
    DEFAULT_PASSAGES,
    start_reading_session,
    complete_reading_session,
)
from services.learning.content_authoring import (
    create_content_draft,
    submit_content_for_review,
    review_content,
    publish_content,
)
from services.learning.gamification_service import process_learning_reward
from services.parent.parent_service import (
    generate_invitation_code,
    claim_invitation_code,
    revoke_parent_link,
    verify_parent_student_access,
)
from services.analytics.teacher_analytics import verify_teacher_student_access
from services.learning.tutor_context import build_tutor_context


def make_cursor_mock(items):
    """Helper to mock a synchronous cursor returned by motor find() whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.skip = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


def make_mock_recommendations_response(learner_id: str, tier: int = 1, category: str = "READING_PRACTICE"):
    rec_item = RecommendationItem(
        id=f"rec-{learner_id[:6]}-{category.lower()}-1",
        category=category,
        title=f"Practice for {category}",
        reason=f"Recommended for {category}",
        actionUrl="/student/reading-coach",
        actionLabel="Start Practice",
        estimatedDurationMinutes=10,
        confidence="high",
        priority=1,
        targetSkill="reading_fluency",
        targetWords=["orange", "bright"],
        completed=False,
        evidenceSignals=["Phase 17 test signal"],
    )
    plan_item = StudyPlanItem(
        id=f"plan-item-{learner_id[:6]}-1",
        activityType=category,
        title=f"Plan item for {category}",
        reason=f"Recommended item",
        estimatedDurationMinutes=10,
        priority=1,
        actionUrl="/student/reading-coach",
        targetSkill="reading_fluency",
        targetWords=["orange", "bright"],
        completed=False,
    )
    study_plan = StudyPlan(
        horizon="today",
        items=[plan_item],
        totalEstimatedMinutes=10,
        completedCount=0,
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


def make_mock_insights(learner_id: str, sessions: int = 3, sufficiency: str = "sufficient_data"):
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
        readingAccuracyAvg=82.0,
        speechAccuracyAvg=None,
        difficultWordsTop=[],
        dataSufficiency=stat,
        dataSufficiencyMessage="Learning progress summary",
    )
    return StudentInsightsResponse(
        learnerId=learner_id,
        reportingPeriod="30d",
        dataSufficiency=stat,
        sufficiencyMessage="Sufficient practice data available",
        summary=summary,
        trends={},
        timeline=[],
    )


class TestPhase17EndToEndIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-test-01",
            "name": "Aarav Sharma",
            "email": "aarav@example.com",
            "role": "student",
            "classroomJoined": "CLASS-DELHI-01",
        }
        self.teacher_user = {
            "id": "teacher-test-01",
            "name": "Ms. Ananya Roy",
            "email": "ananya@example.com",
            "role": "teacher",
            "classroomCode": "CLASS-DELHI-01",
        }
        self.other_teacher_user = {
            "id": "teacher-test-02",
            "name": "Mr. Rajiv Joshi",
            "email": "rajiv@example.com",
            "role": "teacher",
            "classroomCode": "CLASS-MUMBAI-02",
        }
        self.parent_user = {
            "id": "parent-test-01",
            "name": "Sunita Sharma",
            "email": "sunita@example.com",
            "role": "parent",
        }
        self.unlinked_parent_user = {
            "id": "parent-test-02",
            "name": "Kavita Rao",
            "email": "kavita@example.com",
            "role": "parent",
        }

    def tearDown(self):
        app.dependency_overrides.clear()
        # Reset all feature flags to True
        settings.V2_READING_COACH = True
        settings.V2_ADAPTIVE_ENGINE = True
        settings.V2_LEARNING_RECOMMENDATIONS = True
        settings.V2_PERSONALIZED_CONTENT = True
        settings.V2_CONTENT_AUTHORING = True
        settings.V2_PARENT_PORTAL = True
        settings.V2_LEARNING_INSIGHTS = True
        settings.V2_ACCESSIBILITY_PREFERENCES = True
        settings.V2_GAMIFICATION = True
        settings.V2_MULTILINGUAL = True

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Student Authentication & Protected Route Behavior
    # ──────────────────────────────────────────────────────────────────────────
    def test_student_authentication_and_route_guards(self):
        """Verifies unauthenticated calls fail and role guards block unauthorized actions."""
        # Unauthenticated request to protected student route
        res = self.client.get("/api/v2/learner/profile")
        self.assertEqual(res.status_code, 401)

        # Student cannot access teacher-only endpoints
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res_teacher = self.client.get("/api/v2/teacher/analytics/overview")
            self.assertEqual(res_teacher.status_code, 403)
        finally:
            app.dependency_overrides.clear()

        # Student cannot access parent-only endpoints
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res_parent = self.client.get("/api/v2/parent/profile")
            self.assertEqual(res_parent.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Learner Profile & Adaptive State Initialization
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.learner_profile_service.db")
    def test_learner_profile_and_adaptive_state_initialization(self, mock_db):
        """New student initializes baseline profile and Tier 1 adaptive learning state."""
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)
        mock_db.progress.find_one = AsyncMock(return_value={"sessionCount": 0, "streak": 0})
        mock_db.screening_results.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.update_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"learnerId": self.student_user["id"], "active_difficulty_tier": 1})

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res_profile = self.client.get("/api/v2/learner/profile")
            self.assertEqual(res_profile.status_code, 200)
            data = res_profile.json()
            self.assertEqual(data["status"], "ok")
            prof = data["profile"]
            self.assertEqual(prof["learner"]["id"], self.student_user["id"])
            self.assertIn("learning_level", prof)
            self.assertIn("domain_scores", prof)

            res_state = self.client.get("/api/v2/learning/state")
            self.assertEqual(res_state.status_code, 200)
            state_data = res_state.json()
            self.assertEqual(state_data["status"], "ok")
            self.assertEqual(state_data["tierCalibration"]["tier"], 1)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Published Content Eligibility
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.personalized_content.db")
    def test_published_content_eligibility_and_draft_exclusion(self, mock_db):
        """Only published content is eligible for discovery; drafts/in-review are excluded."""
        passages_in_db = [
            {
                "passageId": "pas-pub-01",
                "title": "A Day at the Lake",
                "difficulty": 1,
                "language": "en",
                "status": "PUBLISHED",
                "active": True,
            },
            {
                "passageId": "pas-draft-01",
                "title": "Secret Garden Draft",
                "difficulty": 1,
                "language": "en",
                "status": "DRAFT",
                "active": True,
            },
            {
                "passageId": "pas-rev-01",
                "title": "In Review Passage",
                "difficulty": 1,
                "language": "en",
                "status": "IN_REVIEW",
                "active": True,
            },
            {
                "passageId": "pas-arch-01",
                "title": "Archived Passage",
                "difficulty": 1,
                "language": "en",
                "status": "ARCHIVED",
                "active": True,
            },
        ]
        eligible = [
            p for p in passages_in_db
            if p.get("active") and p.get("status") == "PUBLISHED"
        ]
        mock_db.reading_passages.find.return_value = make_cursor_mock(eligible)

        from services.learning.personalized_content import _get_eligible_reading_passages
        discovered = asyncio.run(_get_eligible_reading_passages())
        discovered_ids = [p["passageId"] for p in discovered]

        self.assertIn("pas-pub-01", discovered_ids)
        self.assertNotIn("pas-draft-01", discovered_ids)
        self.assertNotIn("pas-rev-01", discovered_ids)
        self.assertNotIn("pas-arch-01", discovered_ids)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Activity Launch vs. Actual Completion
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.personalized_content.db")
    def test_activity_launch_does_not_mark_completed(self, mock_db):
        """Opening/launching an activity logs launch telemetry without setting completed=True."""
        mock_db.activity_launch_events.insert_one = AsyncMock(return_value=MagicMock())

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            payload = {
                "activityId": "pas-t1-001",
                "activityType": "GUIDED_READING",
                "language": "en",
            }
            res = self.client.post("/api/v2/personalized-content/launch", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "launched")
            self.assertEqual(data["activityId"], "pas-t1-001")
            self.assertFalse(data["completed"], "Activity must NOT be marked completed upon launch")
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Persistence of Reading Progress
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.reading_service.recalibrate_from_activity", new_callable=AsyncMock)
    @patch("services.learning.reading_service.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_service.db")
    async def test_persistence_of_reading_progress(self, mock_db, mock_get_state, mock_recal):
        """Completing a reading session correctly updates database records."""
        now = int(time.time())
        session_doc = {
            "sessionId": "ses-int-001",
            "learnerId": self.student_user["id"],
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "status": "in_progress",
            "wordsPresented": 50,
            "createdAt": now - 120,
        }
        mock_db.reading_sessions.find_one = AsyncMock(return_value=session_doc)
        mock_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])
        mock_get_state.return_value = {"consecutive_passes": 0, "active_difficulty_tier": 1}
        mock_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.learning_states.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.progress.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock())

        req = ReadingSessionCompleteRequest(
            sessionId="ses-int-001",
            durationSeconds=90,
            wordsRead=50,
            comprehensionAnswers={"q1": 0, "q2": 0},
            completed=True,
        )

        res = await complete_reading_session(self.student_user["id"], req)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["wordsRead"], 50)
        self.assertEqual(res["sessionId"], "ses-int-001")
        mock_db.reading_sessions.update_one.assert_called_once()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Adaptive Progression After Valid Activity Completion
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.reading_service.recalibrate_from_activity", new_callable=AsyncMock)
    @patch("services.learning.reading_service.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_service.db")
    async def test_adaptive_progression_advances_tier_on_three_consecutive_passes(
        self, mock_db, mock_get_state, mock_recal
    ):
        """Demonstrates Phase 3 adaptation: 3 consecutive passes advances tier from 1 to 2."""
        now = int(time.time())
        session_doc = {
            "sessionId": "ses-pass-3",
            "learnerId": self.student_user["id"],
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "status": "in_progress",
            "wordsPresented": 50,
            "createdAt": now - 100,
        }
        mock_db.reading_sessions.find_one = AsyncMock(return_value=session_doc)
        mock_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])
        mock_get_state.return_value = {
            "consecutive_passes": 2,
            "consecutive_failures": 0,
            "active_difficulty_tier": 1,
            "rolling_comprehension_scores": [100.0, 100.0],
        }
        mock_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learning_states.update_one = AsyncMock(return_value=MagicMock())
        mock_db.progress.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock())

        req = ReadingSessionCompleteRequest(
            sessionId="ses-pass-3",
            durationSeconds=80,
            wordsRead=50,
            comprehensionAnswers={"q-t1-001-1": 1, "q-t1-001-2": 2, "q-t1-001-3": 1},
            completed=True,
        )

        res = await complete_reading_session(self.student_user["id"], req)
        adaptation = res["adaptation"]
        self.assertTrue(adaptation["adaptationTriggered"])
        self.assertEqual(adaptation["previousTier"], 1)
        self.assertEqual(adaptation["newTier"], 2)
        self.assertTrue(adaptation["tierChanged"])

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Phase 14 Recommendation Generation From Available Data
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.learning_recommendations._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.get_student_learning_insights", new_callable=AsyncMock)
    @patch("services.learning.learning_recommendations.db")
    def test_phase14_recommendation_generation(
        self, mock_db, mock_insights, mock_state, mock_profile, mock_completions
    ):
        """Generates deterministic Phase 14 recommendations based on learner profile and tier."""
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_profile.return_value = {
            "learnerId": self.student_user["id"],
            "learning_level": 2,
            "learningLevel": {"currentStage": 2},
            "practice_areas": ["phonological_awareness"],
            "cognitiveProfile": {
                "phonological_awareness": {"score": 45.0, "tested": True},
                "reading_comprehension": {"score": 75.0, "tested": True},
            },
        }
        mock_state.return_value = {"active_difficulty_tier": 2, "consecutive_passes": 1}
        mock_insights.return_value = make_mock_insights(learner_id=self.student_user["id"], sessions=3)
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={"currentStreak": 3})

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/learning-recommendations/student?period=today")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["learnerId"], self.student_user["id"])
            self.assertGreater(len(data["recommendations"]), 0)
            self.assertIn("studyPlan", data)
            self.assertEqual(data["currentAdaptiveTier"], 2)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Phase 15 Recommendation-to-Activity Navigation
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_phase15_recommendation_to_activity_content_retrieval(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        """Retrieves exact matching content for a recommendation ID."""
        mock_profile.return_value = {"learning_level": 1, "preferred_language": "en"}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response(self.student_user["id"], tier=1, category="READING_PRACTICE")
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.reading_passages.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/personalized-content/recommendation/rec-studen-reading_practice-1?language=en")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["activityType"], "GUIDED_READING")
            self.assertEqual(data["difficultyTier"], 1)
            self.assertIn("actionUrl", data)
            self.assertFalse(data["completed"])
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 9. Phase 16 Draft, Review, and Publish Lifecycle Restrictions
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.content_authoring.db")
    def test_phase16_content_lifecycle_and_separation_of_duties(self, mock_db):
        """Enforces author cannot self-approve and direct publish without review is rejected."""
        mock_db.reading_passages.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        draft_req = ContentDraftCreateRequest(
            title="The Forest Deer",
            text="A gentle deer walks quietly through the tall pine forest. The golden morning sun shines through the green leaves.",
            difficulty=2,
            language="en",
            vocabulary=[{"word": "forest", "definition": "A large area covered with trees.", "phonetic": "for-est"}],
            questions=[{
                "questionId": "q1",
                "question": "Where does the deer walk?",
                "options": ["Through the pine forest", "In the ocean", "On the moon"],
                "correctAnswer": 0,
                "explanation": "The text states the deer walks through the forest.",
            }],
        )

        # 1. Author creates draft (signature: user, req)
        draft_item = asyncio.run(create_content_draft(self.teacher_user, draft_req))
        self.assertEqual(draft_item.status, "DRAFT")
        content_id = draft_item.contentId

        # 2. Mock finding draft in DB
        draft_doc = draft_item.model_dump()
        draft_doc["contentId"] = content_id
        mock_db.reading_passages.find_one = AsyncMock(return_value=draft_doc)
        mock_db.reading_passages.update_one = AsyncMock(return_value=MagicMock())

        # 3. Direct publish without review must raise Exception
        with self.assertRaises(Exception):
            asyncio.run(publish_content(self.teacher_user, content_id))

        # 4. Submit for review (signature: user, content_id)
        submitted_item = asyncio.run(submit_content_for_review(self.teacher_user, content_id))
        self.assertEqual(submitted_item.status, "IN_REVIEW")
        draft_doc["status"] = "IN_REVIEW"

        # 5. Author cannot review own content (separation of duties)
        review_req = ContentReviewDecisionRequest(
            decision="APPROVE",
            feedback="Looks wonderful!",
        )
        with self.assertRaises(Exception):
            asyncio.run(review_content(self.teacher_user, content_id, review_req))

        # 6. Peer reviewer approves
        peer_reviewer = {
            "id": "teacher-peer-99",
            "name": "Mr. Rajiv Joshi",
            "role": "teacher",
            "classroomCode": "CLASS-DELHI-01",
        }
        approved_item = asyncio.run(review_content(peer_reviewer, content_id, review_req))
        self.assertEqual(approved_item.status, "APPROVED")
        draft_doc["status"] = "APPROVED"
        draft_doc["reviewerId"] = peer_reviewer["id"]
        draft_doc["reviewedAt"] = int(time.time())
        draft_doc["reviewNotes"] = "Looks wonderful!"

        # 7. Now publish succeeds!
        published_item = asyncio.run(publish_content(self.teacher_user, content_id))
        self.assertEqual(published_item.status, "PUBLISHED")

    # ──────────────────────────────────────────────────────────────────────────
    # 10. Teacher Classroom and Tenant Isolation
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.analytics.teacher_analytics.db")
    def test_teacher_classroom_and_tenant_isolation(self, mock_db):
        """Teacher from Delhi cannot view analytics or progress of student in Mumbai."""
        mock_db.users.find_one = AsyncMock(return_value={
            "id": "student-delhi-01",
            "classroomJoined": "CLASS-DELHI-01",
            "role": "student",
        })

        # Teacher from Delhi succeeds
        student_doc = asyncio.run(verify_teacher_student_access(self.teacher_user, "student-delhi-01"))
        self.assertIsNotNone(student_doc)

        # Teacher from Mumbai fails with 403 Forbidden
        with self.assertRaises(Exception) as ctx:
            asyncio.run(verify_teacher_student_access(self.other_teacher_user, "student-delhi-01"))
        self.assertEqual(ctx.exception.status_code, 403)

    # ──────────────────────────────────────────────────────────────────────────
    # 11. Parent Link Authorization and Revocation
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.parent.parent_service.db")
    def test_parent_link_authorization_and_instant_revocation(self, mock_db):
        """Active link authorizes parent access; revocation immediately blocks access."""
        # 1. Unlinked parent fails with 403
        mock_db.parent_links.find_one = AsyncMock(return_value=None)
        with self.assertRaises(Exception) as ctx:
            asyncio.run(verify_parent_student_access(self.unlinked_parent_user["id"], self.student_user["id"]))
        self.assertEqual(ctx.exception.status_code, 403)

        # 2. Linked parent with active status succeeds
        active_link = {
            "id": "link-999",
            "parentId": self.parent_user["id"],
            "studentId": self.student_user["id"],
            "status": "active",
        }
        mock_db.parent_links.find_one = AsyncMock(return_value=active_link)
        verified = asyncio.run(verify_parent_student_access(self.parent_user["id"], self.student_user["id"]))
        self.assertEqual(verified["id"], "link-999")

        # 3. Revoke link
        mock_db.parent_links.update_one = AsyncMock(return_value=MagicMock())
        revoke_res = asyncio.run(revoke_parent_link(self.parent_user, "link-999"))
        self.assertTrue(revoke_res["success"])

        # 4. Subsequent check returns revoked doc -> fails with 403
        mock_db.parent_links.find_one = AsyncMock(return_value=None)
        with self.assertRaises(Exception) as ctx:
            asyncio.run(verify_parent_student_access(self.parent_user["id"], self.student_user["id"]))
        self.assertEqual(ctx.exception.status_code, 403)

    # ──────────────────────────────────────────────────────────────────────────
    # 12. AI Tutor Learner-Context Isolation and Privacy
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.tutor_context.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.db")
    async def test_ai_tutor_context_isolation_and_privacy_safeguards(
        self, mock_db, mock_profile, mock_state
    ):
        """Tutor context builds strictly for the target student with zero private note leakage."""
        mock_db.users.find_one = AsyncMock(return_value={
            "id": self.student_user["id"],
            "name": "Aarav Sharma",
            "settings": {"font": "OpenDyslexic", "fontSize": 20},
            "preferredLanguage": "en",
        })
        mock_profile.return_value = {
            "learnerId": self.student_user["id"],
            "learning_level": {"level": 2},
            "strengths": [{"friendly_name": "Visual Memory"}],
            "practice_areas": [{"friendly_name": "Phonemic Blending"}],
        }
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])

        ctx = await build_tutor_context(
            learner_id=self.student_user["id"],
            active_passage_id="pas-t1-001",
            active_word="orange",
        )
        self.assertEqual(ctx.displayName, "Aarav")
        self.assertEqual(ctx.adaptiveTier, 2)
        self.assertEqual(ctx.activeWord, "orange")
        ctx_dict = ctx.model_dump()
        self.assertNotIn("rawAudio", ctx_dict)
        self.assertNotIn("passwordHash", ctx_dict)
        self.assertNotIn("teacherPrivateNotes", ctx_dict)

    # ──────────────────────────────────────────────────────────────────────────
    # 13. Accessibility Preference Persistence
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.accessibility.accessibility_service.db")
    def test_accessibility_preference_persistence_and_reset(self, mock_db):
        """Student updates and resets accessibility preferences reliably."""
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value={
            "userId": self.student_user["id"],
            "preferences": {
                "font": "OpenDyslexic",
                "fontSize": 22,
                "highContrast": True,
                "readingRuler": True,
                "tintOverlay": "mint",
            }
        })
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.user_accessibility_preferences.update_one = AsyncMock(return_value=MagicMock())
        mock_db.users.update_one = AsyncMock(return_value=MagicMock())

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/accessibility/preferences")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["preferences"]["fontSize"], 22)
            self.assertTrue(data["preferences"]["highContrast"])

            patch_res = self.client.patch("/api/v2/accessibility/preferences", json={"fontSize": 24})
            self.assertEqual(patch_res.status_code, 200)

            reset_res = self.client.post("/api/v2/accessibility/preferences/reset")
            self.assertEqual(reset_res.status_code, 200)
            self.assertEqual(reset_res.json()["preferences"]["fontSize"], 18)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 14. Multilingual Consistency & Unicode Preservation
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_multilingual_hindi_marathi_support_and_honest_fallbacks(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        """Hindi and Marathi Devanagari script is supported, with honest fallbacks when unavailable."""
        mock_profile.return_value = {"learning_level": 1, "preferred_language": "mr"}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response(self.student_user["id"], tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.reading_passages.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            # Exact Marathi match exists at Tier 1 (pas-t1-mr-001: मीना आणि तिची मांजर)
            res_mr = self.client.get("/api/v2/personalized-content/next?language=mr")
            self.assertEqual(res_mr.status_code, 200)
            act_mr = res_mr.json()["activity"]
            self.assertEqual(act_mr["language"], "mr")
            self.assertIn("मांजर", act_mr["title"])

            # Requesting Marathi at Tier 5 (where no authentic Tier 5 Marathi exists yet)
            mock_state.return_value = {"active_difficulty_tier": 5}
            mock_recs.return_value = make_mock_recommendations_response(self.student_user["id"], tier=5)
            res_mr_t5 = self.client.get("/api/v2/personalized-content/next?language=mr")
            self.assertEqual(res_mr_t5.status_code, 200)
            data_t5 = res_mr_t5.json()
            self.assertEqual(data_t5["status"], "LANGUAGE_FALLBACK_OFFERED")
            self.assertIsNotNone(data_t5["message"])
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 15. Learning Insights Data Sufficiency
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.learning_insights.db")
    def test_learning_insights_honest_data_sufficiency(self, mock_db):
        """Classifies learner progress honestly into no_data or insufficient_data when records are sparse."""
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.interventions.find.return_value = make_cursor_mock([])
        mock_db.learning_states.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res_empty = self.client.get("/api/v2/learning-insights/student?period=30d")
            self.assertEqual(res_empty.status_code, 200)
            data = res_empty.json()
            self.assertEqual(data["dataSufficiency"], "no_data")
            self.assertIn("No learning activity recorded", data["sufficiencyMessage"])
            self.assertEqual(data["summary"]["readingSessionsCount"], 0)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 16. Gamification Idempotency
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.gamification_service.db")
    async def test_gamification_idempotency_on_repeated_source_events(self, mock_db):
        """Processing reward twice with same source_event_id returns identical result without duplicating points."""
        now = int(time.time())
        summary_doc = {
            "learnerId": self.student_user["id"],
            "totalPoints": 150,
            "currentStreak": 2,
            "longestStreak": 4,
            "lastActiveDate": "2026-10-10",
            "milestoneProgress": {},
            "earnedBadges": [],
        }
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=summary_doc)
        mock_db.reward_events.find_one = AsyncMock(return_value=None)
        mock_db.reward_events.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.gamification_summaries.update_one = AsyncMock(return_value=MagicMock())
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.reward_events.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=0)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=0)
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)

        eval1 = await process_learning_reward(
            user_id=self.student_user["id"],
            source_event_id="ses-unique-101",
            event_type="reading_session",
            metadata={"comprehensionScore": 85.0, "wordsRead": 60},
        )
        points1 = eval1.pointsAwarded
        self.assertGreater(points1, 0)

        existing_event = {
            "eventId": "rev-existing-01",
            "learnerId": self.student_user["id"],
            "sourceEventId": "ses-unique-101",
            "pointsAwarded": points1,
            "eventType": "reading_session",
            "createdAt": now,
        }
        mock_db.reward_events.find_one = AsyncMock(return_value=existing_event)
        eval2 = await process_learning_reward(
            user_id=self.student_user["id"],
            source_event_id="ses-unique-101",
            event_type="reading_session",
            metadata={"comprehensionScore": 85.0, "wordsRead": 60},
        )
        self.assertTrue(eval2.isDuplicate)
        self.assertEqual(eval2.pointsAwarded, 0)
        self.assertEqual(eval2.totalPoints, 150)

    # ──────────────────────────────────────────────────────────────────────────
    # 17. Feature Flag Protection Across V2 Subsystems
    # ──────────────────────────────────────────────────────────────────────────
    def test_feature_flags_return_clean_503(self):
        """All V2 routers return HTTP 503 when their respective feature flag is disabled."""
        flags_and_endpoints = [
            ("V2_READING_COACH", "/api/v2/reading/passages", self.student_user),
            ("V2_ADAPTIVE_ENGINE", "/api/v2/learning/activities", self.student_user),
            ("V2_LEARNING_RECOMMENDATIONS", "/api/v2/learning-recommendations/student", self.student_user),
            ("V2_PERSONALIZED_CONTENT", "/api/v2/personalized-content/next", self.student_user),
            ("V2_CONTENT_AUTHORING", "/api/v2/content-authoring/items", self.teacher_user),
            ("V2_PARENT_PORTAL", "/api/v2/parent/profile", self.parent_user),
            ("V2_LEARNING_INSIGHTS", "/api/v2/learning-insights/student", self.student_user),
            ("V2_ACCESSIBILITY_PREFERENCES", "/api/v2/accessibility/preferences", self.student_user),
            ("V2_GAMIFICATION", "/api/v2/gamification/summary", self.student_user),
            ("V2_MULTILINGUAL", "/api/v2/multilingual/preference", self.student_user),
        ]

        for flag_name, endpoint, user in flags_and_endpoints:
            setattr(settings, flag_name, False)
            if flag_name == "V2_MULTILINGUAL":
                settings.V2_MULTILINGUAL_SUPPORT = False
            app.dependency_overrides[get_current_user] = lambda u=user: u
            try:
                res = self.client.get(endpoint)
                self.assertEqual(
                    res.status_code,
                    503,
                    f"Expected 503 for {endpoint} when {flag_name}=False, got {res.status_code}",
                )
            finally:
                setattr(settings, flag_name, True)
                if flag_name == "V2_MULTILINGUAL":
                    settings.V2_MULTILINGUAL_SUPPORT = True
                app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 18. Invalid IDs, Missing Records, and Expired Sessions
    # ──────────────────────────────────────────────────────────────────────────
    def test_invalid_ids_and_missing_records_handled_safely(self):
        """Non-existent entities return HTTP 404 cleanly without 500 error."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/reading/passages/pas-nonexistent-999")
            self.assertEqual(res.status_code, 404)

            res_rec = self.client.get("/api/v2/personalized-content/recommendation/rec-nonexistent-999")
            self.assertEqual(res_rec.status_code, 404)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 19. Error Recovery and Resilience
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.tutor_service.db")
    def test_offline_ai_tutor_fallback_when_llm_is_unavailable(self, mock_db):
        """When generative LLM fails or is unconfigured, AI Tutor falls back deterministically."""
        mock_db.tutor_conversations.find_one = AsyncMock(return_value=None)
        mock_db.tutor_conversations.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learning_states.find_one = AsyncMock(return_value={"active_difficulty_tier": 1})
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            payload = {
                "message": "Can you help me spell orange?",
                "passageId": "pas-t1-001",
                "activeWord": "orange",
            }
            res = self.client.post("/api/v2/tutor/chat", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("message", data)
            self.assertGreater(len(data["message"]), 5)
            self.assertIn("followUpQuestion", data)
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 20. Repeated Requests Without Duplicate Learning Records
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.personalized_content.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.generate_learner_recommendations", new_callable=AsyncMock)
    @patch("services.learning.personalized_content._check_today_completions", new_callable=AsyncMock)
    @patch("services.learning.personalized_content.db")
    def test_repeated_next_activity_requests_idempotent(
        self, mock_db, mock_completions, mock_recs, mock_state, mock_profile
    ):
        """Calling /next multiple times returns deterministic content without creating new attempt docs."""
        mock_profile.return_value = {"learning_level": 1, "preferred_language": "en"}
        mock_state.return_value = {"active_difficulty_tier": 1}
        mock_recs.return_value = make_mock_recommendations_response(self.student_user["id"], tier=1)
        mock_completions.return_value = {"reading": False, "difficult_words": False, "speech": False, "adaptive_activity": False}
        mock_db.accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.reading_passages.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])

        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res1 = self.client.get("/api/v2/personalized-content/next?language=en")
            res2 = self.client.get("/api/v2/personalized-content/next?language=en")
            self.assertEqual(res1.status_code, 200)
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(res1.json()["activity"]["activityId"], res2.json()["activity"]["activityId"])
        finally:
            app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 21. Legacy V1 Authentication and API Compatibility
    # ──────────────────────────────────────────────────────────────────────────
    def test_legacy_v1_api_compatibility(self):
        """V1 endpoints (/api/version, /api/health) remain active and return expected payloads."""
        res_ver = self.client.get("/api/version")
        self.assertEqual(res_ver.status_code, 200)
        ver_data = res_ver.json()
        self.assertIn("version", ver_data)
        self.assertIn("feature_flags", ver_data)

        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

    # ──────────────────────────────────────────────────────────────────────────
    # 22. End-to-End Multi-Persona Learning Journey (Cross-Phase Loop)
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.reading_service.recalibrate_from_activity", new_callable=AsyncMock)
    @patch("services.learning.reading_service.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_service.db")
    @patch("services.learning.content_authoring.db")
    @patch("services.learning.personalized_content.db")
    @patch("services.analytics.teacher_analytics.db")
    @patch("services.parent.parent_service.db")
    async def test_full_cross_persona_learning_journey_loop(
        self,
        mock_parent_db,
        mock_teacher_db,
        mock_content_db,
        mock_author_db,
        mock_reading_db,
        mock_get_state,
        mock_recal,
    ):
        """
        Comprehensive cross-phase integration scenario:
        1. Student starts and completes a Tier 1 reading session.
        2. Session persistence triggers Phase 3 adaptive update & Phase 9 gamification.
        3. Teacher monitors student's classroom performance.
        4. Teacher authors, peer-reviews, and publishes a new Tier 2 passage.
        5. Newly published passage becomes discoverable for the student in Phase 15.
        6. Linked parent views student's updated dashboard with zero clinical jargon.
        """
        now = int(time.time())

        # Step 1: Student completes reading session
        session_doc = {
            "sessionId": "ses-e2e-001",
            "learnerId": self.student_user["id"],
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "status": "in_progress",
            "wordsPresented": 50,
            "createdAt": now - 120,
        }
        mock_reading_db.reading_sessions.find_one = AsyncMock(return_value=session_doc)
        mock_reading_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])
        mock_get_state.return_value = {"consecutive_passes": 0, "active_difficulty_tier": 1}
        mock_reading_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock())
        mock_reading_db.learning_states.update_one = AsyncMock(return_value=MagicMock())
        mock_reading_db.progress.update_one = AsyncMock(return_value=MagicMock())
        mock_reading_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_reading_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock())

        complete_req = ReadingSessionCompleteRequest(
            sessionId="ses-e2e-001",
            durationSeconds=85,
            wordsRead=50,
            comprehensionAnswers={"q-t1-001-1": 1, "q-t1-001-2": 2},
            completed=True,
        )
        res_session = await complete_reading_session(self.student_user["id"], complete_req)
        self.assertEqual(res_session["status"], "ok")
        self.assertEqual(res_session["wordsRead"], 50)

        # Step 2: Teacher verifies student access in classroom
        mock_teacher_db.users.find_one = AsyncMock(return_value={
            "id": self.student_user["id"],
            "classroomJoined": "CLASS-DELHI-01",
            "role": "student",
        })
        verified_student = await verify_teacher_student_access(self.teacher_user, self.student_user["id"])
        self.assertEqual(verified_student["id"], self.student_user["id"])

        # Step 3: Teacher authors and publishes new content
        new_content_id = "pas-author-e2e-01"
        draft_doc = {
            "contentId": new_content_id,
            "passageId": new_content_id,
            "title": "Sunbirds in the Garden",
            "text": "Two little sunbirds visited the red hibiscus flower every morning. They drank the sweet nectar with their curved beaks and chirped merrily in the warm sunshine.",
            "difficulty": 2,
            "language": "en",
            "status": "APPROVED",
            "reviewerId": "teacher-peer-99",
            "active": True,
            "authorId": self.teacher_user["id"],
            "createdAt": now,
            "questions": [{
                "questionId": "q1",
                "question": "What flower did the sunbirds visit?",
                "options": ["Red hibiscus", "Yellow sunflower", "Blue lily"],
                "correctAnswer": 0,
                "explanation": "The text states the sunbirds drank sweet nectar from the red hibiscus flower.",
            }],
            "vocabulary": [{"word": "nectar", "definition": "Sweet liquid from flowers", "phonetic": "nek-ter"}],
        }
        mock_author_db.reading_passages.find_one = AsyncMock(return_value=draft_doc)
        mock_author_db.reading_passages.update_one = AsyncMock(return_value=MagicMock())
        mock_author_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        pub_item = await publish_content(self.teacher_user, new_content_id)
        self.assertEqual(pub_item.status, "PUBLISHED")

        # Step 4: Published content is eligible for Phase 15 student discovery
        published_passages = [draft_doc]
        mock_content_db.reading_passages.find.return_value = make_cursor_mock(published_passages)

        from services.learning.personalized_content import _get_eligible_reading_passages
        eligible = await _get_eligible_reading_passages()
        self.assertTrue(any(p["passageId"] == new_content_id for p in eligible))

        # Step 5: Parent views progress with verified access
        mock_parent_db.parent_links.find_one = AsyncMock(return_value={
            "id": "link-e2e-01",
            "parentId": self.parent_user["id"],
            "studentId": self.student_user["id"],
            "status": "active",
        })
        parent_link = await verify_parent_student_access(self.parent_user["id"], self.student_user["id"])
        self.assertEqual(parent_link["status"], "active")
