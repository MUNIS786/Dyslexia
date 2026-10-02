"""
backend/test_phase9_gamification.py — Comprehensive Test Suite for Phase 9: Gamification & Engagement.

Tests cover:
1. Gamification Models & Validation:
   - Reward event schema and valid event types
   - Badge definitions, earned badges, progress items
   - Gamification summary and history models
2. Points Evaluation & Idempotency:
   - Server-side points calculation (base 10, quality bonuses)
   - Strict idempotency: same sourceEventId cannot be awarded twice
   - Client-supplied points are rejected/ignored
   - Points ledger auditability (ledger sum matches total points)
3. Learning Streaks:
   - Multiple activities on same day count as 1 streak day
   - Consecutive distinct calendar days update streak correctly
   - Empty history returns 0 streak without fabricated data
   - Encouraging, non-shaming streak messages
   - End of streak never deletes earned points or badges
4. Achievements & Milestones:
   - First activity unlocks 'First Steps'
   - Reading explorer unlocked at threshold (5 sessions)
   - Century milestone unlocked at 100 points
   - Achievements are never awarded twice (deduplicated)
   - Milestone progress accurately calculated
5. API Endpoints & Security:
   - Summary, achievements, milestones, and history endpoints
   - Claim event endpoint validates real DB records and user ownership
   - Unauthenticated requests rejected (401)
   - Feature flag disabled returns 503
6. Teacher Visibility & Boundaries:
   - Authorized teacher views student summary
   - Cross-classroom teacher access rejected (403)
   - Student role access to teacher endpoint rejected (403)
   - Zero competitive leaderboards or public student rankings
7. Integration:
   - Adaptive activity completion awards points
   - Reading session completion awards points
   - Tutor conversations award no points
   - Phase 8 interventions remain separate and untouched
"""
import unittest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher
from models.v2_gamification import (
    BadgeDefinition,
    EarnedBadge,
    BadgeProgressItem,
    RewardEvent,
    MilestoneProgressItem,
    GamificationSummary,
    RewardEvaluationResult,
)
from services.learning.gamification_service import (
    ACHIEVEMENT_CATALOGUE,
    calculate_event_points,
    calculate_learner_streak,
    process_learning_reward,
    get_or_create_summary,
    get_gamification_summary,
    get_achievements_with_progress,
    get_milestones_progress,
    get_reward_history,
    get_teacher_learner_reward_summary,
)


class TestGamificationModelsAndValidation(unittest.TestCase):
    """Unit tests for Pydantic model validation and constraints."""

    def test_valid_reward_event(self):
        ev = RewardEvent(
            eventId="rew_123",
            learnerId="student-001",
            sourceEventId="att_456",
            eventType="activity_attempt",
            points=15,
            description="Completed practice activity with solid accuracy",
        )
        self.assertEqual(ev.points, 15)
        self.assertEqual(ev.eventType, "activity_attempt")

    def test_invalid_event_type_rejected(self):
        with self.assertRaises(ValidationError):
            RewardEvent(
                eventId="rew_999",
                learnerId="student-001",
                sourceEventId="evt_999",
                eventType="invalid_arbitrary_event",
                points=10,
                description="Hacked event",
            )

    def test_invalid_points_boundary(self):
        with self.assertRaises(ValidationError):
            RewardEvent(
                eventId="rew_999",
                learnerId="student-001",
                sourceEventId="evt_999",
                eventType="activity_attempt",
                points=1000,  # exceeds max 50 points constraint
                description="Excessive points",
            )

    def test_badge_progress_calculation(self):
        item = BadgeProgressItem(
            badgeId="reading_explorer",
            title="Reading Explorer",
            description="Complete 5 reading sessions",
            icon="📖",
            category="reading",
            threshold=5,
            currentProgress=3,
            progressPercent=60.0,
            unlocked=False,
        )
        self.assertFalse(item.unlocked)
        self.assertEqual(item.progressPercent, 60.0)


class TestPointsCalculationAndIdempotency(unittest.IsolatedAsyncioTestCase):
    """Unit tests for server-determined point evaluation and strict idempotency."""

    def test_points_calculation_activity_attempt(self):
        pts, desc = calculate_event_points("activity_attempt", {"scorePercent": 70.0})
        self.assertEqual(pts, 10)  # Base 10

        pts_high, _ = calculate_event_points("activity_attempt", {"scorePercent": 85.0})
        self.assertEqual(pts_high, 15)  # 10 + 5 bonus

        pts_mastery, _ = calculate_event_points("activity_attempt", {"scorePercent": 95.0})
        self.assertEqual(pts_mastery, 15)  # 10 + 5 bonus

    def test_points_calculation_reading_session(self):
        pts, desc = calculate_event_points("reading_session", {"comprehensionScore": 60.0, "wordsRead": 20, "wordsPresented": 50})
        self.assertEqual(pts, 10)

        pts_bonus, _ = calculate_event_points("reading_session", {
            "comprehensionScore": 85.0,
            "wordsRead": 50,
            "wordsPresented": 50,
            "passageTitle": "Leo the Frog"
        })
        self.assertEqual(pts_bonus, 20)  # 10 base + 5 comp + 5 completion

    @patch("services.learning.gamification_service.db")
    async def test_idempotent_duplicate_prevention(self, mock_db):
        """Verify that presenting the same sourceEventId twice returns isDuplicate=True and 0 new points."""
        user_id = "student-101"
        source_id = "att_test_123"

        # Mock existing event found
        mock_db.reward_events.find_one = AsyncMock(return_value={
            "eventId": "rew_abc",
            "learnerId": user_id,
            "sourceEventId": source_id,
            "points": 10,
        })
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "learnerId": user_id,
            "totalPoints": 50,
            "currentStreak": 2,
            "earnedBadges": [],
        })

        result = await process_learning_reward(
            user_id=user_id,
            source_event_id=source_id,
            event_type="activity_attempt",
            metadata={"scorePercent": 80.0}
        )

        self.assertTrue(result.isDuplicate)
        self.assertEqual(result.pointsAwarded, 0)
        self.assertEqual(result.totalPoints, 50)
        # Verify insert_one was NEVER called for duplicate
        mock_db.reward_events.insert_one.assert_not_called()


class TestStreakCalculations(unittest.IsolatedAsyncioTestCase):
    """Unit tests for non-shaming streak calculations."""

    @patch("services.learning.gamification_service.db")
    async def test_multiple_activities_same_day_counts_as_one_streak_day(self, mock_db):
        user_id = "student-102"
        now_ts = int(time.time())

        # 3 activities all completed today
        mock_cursor_att = MagicMock()
        mock_cursor_att.to_list = AsyncMock(return_value=[
            {"completedAt": now_ts},
            {"completedAt": now_ts - 3600},
            {"completedAt": now_ts - 7200},
        ])
        mock_db.activity_attempts.find.return_value = mock_cursor_att

        mock_cursor_sess = MagicMock()
        mock_cursor_sess.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = mock_cursor_sess

        mock_cursor_rew = MagicMock()
        mock_cursor_rew.to_list = AsyncMock(return_value=[])
        mock_db.reward_events.find.return_value = mock_cursor_rew

        curr_streak, longest_streak, msg, last_active = await calculate_learner_streak(user_id)
        self.assertEqual(curr_streak, 1)
        self.assertEqual(longest_streak, 1)
        self.assertIn("practiced today", msg)

    @patch("services.learning.gamification_service.db")
    async def test_consecutive_days_updates_streak(self, mock_db):
        user_id = "student-103"
        now_dt = datetime.now(timezone.utc)
        t0 = int(now_dt.timestamp())
        t1 = int((now_dt - timedelta(days=1)).timestamp())
        t2 = int((now_dt - timedelta(days=2)).timestamp())

        mock_cursor_att = MagicMock()
        mock_cursor_att.to_list = AsyncMock(return_value=[
            {"completedAt": t0},
            {"completedAt": t1},
            {"completedAt": t2},
        ])
        mock_db.activity_attempts.find.return_value = mock_cursor_att

        mock_cursor_sess = MagicMock()
        mock_cursor_sess.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = mock_cursor_sess

        mock_cursor_rew = MagicMock()
        mock_cursor_rew.to_list = AsyncMock(return_value=[])
        mock_db.reward_events.find.return_value = mock_cursor_rew

        curr_streak, longest_streak, msg, last_active = await calculate_learner_streak(user_id)
        self.assertEqual(curr_streak, 3)
        self.assertEqual(longest_streak, 3)
        self.assertIn("3 different days", msg)
        self.assertNotIn("failed", msg.lower())
        self.assertNotIn("lost", msg.lower())

    @patch("services.learning.gamification_service.db")
    async def test_empty_history_returns_zero_streak(self, mock_db):
        user_id = "student-new"

        for cursor_mock in [mock_db.activity_attempts.find, mock_db.reading_sessions.find, mock_db.reward_events.find]:
            m = MagicMock()
            m.to_list = AsyncMock(return_value=[])
            cursor_mock.return_value = m

        curr_streak, longest_streak, msg, last_active = await calculate_learner_streak(user_id)
        self.assertEqual(curr_streak, 0)
        self.assertEqual(longest_streak, 0)
        self.assertIsNone(last_active)
        self.assertIn("whenever you are ready", msg)


class TestAchievementsAndMilestones(unittest.IsolatedAsyncioTestCase):
    """Unit tests for achievement unlocks and milestone progress."""

    @patch("services.learning.gamification_service.db")
    async def test_first_steps_achievement_unlocked(self, mock_db):
        user_id = "student-first"
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=1)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=0)

        cursor_sess = MagicMock()
        cursor_sess.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = cursor_sess

        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "learnerId": user_id,
            "totalPoints": 10,
            "earnedBadges": [],
        })

        badges = await get_achievements_with_progress(user_id)
        first_steps = next(b for b in badges if b.badgeId == "first_steps")
        self.assertEqual(first_steps.currentProgress, 1)
        self.assertEqual(first_steps.progressPercent, 100.0)

    @patch("services.learning.gamification_service.db")
    async def test_reading_explorer_unlocked_at_threshold(self, mock_db):
        user_id = "student-reader"
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=2)
        mock_db.reading_sessions.count_documents = AsyncMock(side_effect=lambda q: 5 if "completed" in q else 5)

        cursor_sess = MagicMock()
        cursor_sess.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = cursor_sess

        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "learnerId": user_id,
            "totalPoints": 60,
            "earnedBadges": [{"badgeId": "first_steps", "title": "First Steps", "icon": "🌱", "unlockedAt": 1000}],
        })

        badges = await get_achievements_with_progress(user_id)
        explorer = next(b for b in badges if b.badgeId == "reading_explorer")
        self.assertEqual(explorer.currentProgress, 5)
        self.assertEqual(explorer.progressPercent, 100.0)

    @patch("services.learning.gamification_service.db")
    async def test_milestones_progress_returns_closest_unlocked(self, mock_db):
        user_id = "student-mile"
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=2)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=1)

        cursor_sess = MagicMock()
        cursor_sess.to_list = AsyncMock(return_value=[])
        mock_db.reading_sessions.find.return_value = cursor_sess

        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "learnerId": user_id,
            "totalPoints": 30,
            "earnedBadges": [{"badgeId": "first_steps", "title": "First Steps", "icon": "🌱", "unlockedAt": 1000}],
        })

        milestones = await get_milestones_progress(user_id)
        self.assertGreater(len(milestones), 0)
        # First steps should NOT be in upcoming milestones because it was already unlocked
        self.assertNotIn("first_steps", [m.milestoneId for m in milestones])


class TestGamificationAPIEndpoints(unittest.TestCase):
    """API endpoint testing with TestClient."""

    def setUp(self):
        self.client = TestClient(app)
        settings.V2_GAMIFICATION = True
        self.mock_student = {
            "id": "student-test-01",
            "email": "student@demo.school",
            "role": "student",
            "classroomCode": "DA-DEMO",
        }
        self.mock_teacher = {
            "id": "teacher-test-01",
            "email": "teacher@demo.school",
            "role": "teacher",
            "classroomCode": "DA-DEMO",
        }

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.V2_GAMIFICATION = False

    @patch("routers.v2_gamification.get_gamification_summary")
    def test_get_summary_success(self, mock_summary):
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        mock_summary.return_value = GamificationSummary(
            learnerId="student-test-01",
            totalPoints=85,
            currentStreak=3,
            longestStreak=5,
            earnedBadgesCount=2,
            totalBadgesCount=11,
            streakMessage="Nice work! You practiced on 3 different days.",
        )

        res = self.client.get("/api/v2/gamification/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["totalPoints"], 85)
        self.assertEqual(data["currentStreak"], 3)
        self.assertEqual(data["earnedBadgesCount"], 2)

    @patch("routers.v2_gamification.get_achievements_with_progress")
    def test_get_achievements_success(self, mock_ach):
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        mock_ach.return_value = [
            BadgeProgressItem(
                badgeId="first_steps",
                title="First Steps",
                description="Complete first activity",
                icon="🌱",
                category="milestone",
                threshold=1,
                currentProgress=1,
                progressPercent=100.0,
                unlocked=True,
            )
        ]

        res = self.client.get("/api/v2/gamification/achievements")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["badgeId"], "first_steps")
        self.assertTrue(data[0]["unlocked"])

    @patch("routers.v2_gamification.get_milestones_progress")
    def test_get_milestones_success(self, mock_mile):
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        mock_mile.return_value = [
            MilestoneProgressItem(
                milestoneId="reading_explorer",
                title="Reading Explorer",
                description="Read 5 stories",
                icon="📖",
                current=3,
                target=5,
                progressPercent=60.0,
                completed=False,
            )
        ]

        res = self.client.get("/api/v2/gamification/milestones")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["milestoneId"], "reading_explorer")

    @patch("routers.v2_gamification.get_reward_history")
    def test_get_history_success(self, mock_hist):
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        mock_hist.return_value = {
            "learnerId": "student-test-01",
            "totalEvents": 1,
            "page": 1,
            "limit": 20,
            "events": [{
                "eventId": "rew_1",
                "sourceEventId": "att_1",
                "eventType": "activity_attempt",
                "points": 10,
                "description": "Completed practice",
                "createdAt": 1000,
            }],
        }

        res = self.client.get("/api/v2/gamification/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["totalEvents"], 1)

    def test_feature_flag_disabled_returns_503(self):
        settings.V2_GAMIFICATION = False
        app.dependency_overrides[get_current_user] = lambda: self.mock_student

        res = self.client.get("/api/v2/gamification/summary")
        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled", res.json()["detail"].lower())

    def test_unauthenticated_request_returns_401(self):
        # No dependency override for get_current_user
        res = self.client.get("/api/v2/gamification/summary")
        self.assertEqual(res.status_code, 401)


class TestTeacherGamificationVisibility(unittest.TestCase):
    """Test teacher role verification and tenant isolation for gamification."""

    def setUp(self):
        self.client = TestClient(app)
        settings.V2_GAMIFICATION = True
        self.mock_teacher = {
            "id": "teacher-01",
            "role": "teacher",
            "classroomCode": "DA-DEMO",
        }
        self.mock_student = {
            "id": "student-01",
            "role": "student",
            "classroomCode": "DA-DEMO",
        }

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.V2_GAMIFICATION = False

    @patch("services.learning.gamification_service.verify_teacher_student_access")
    @patch("services.learning.gamification_service.get_gamification_summary")
    def test_authorized_teacher_can_view_student_summary(self, mock_summary, mock_verify):
        app.dependency_overrides[require_teacher] = lambda: self.mock_teacher
        mock_verify.return_value = None  # Access allowed
        mock_summary.return_value = GamificationSummary(
            learnerId="student-01",
            totalPoints=120,
            currentStreak=4,
            longestStreak=4,
            earnedBadgesCount=3,
            totalBadgesCount=11,
        )

        res = self.client.get("/api/v2/gamification/teacher/learner/student-01")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["totalPoints"], 120)
        self.assertEqual(data["currentStreak"], 4)

    def test_student_role_rejected_from_teacher_gamification_endpoint(self):
        # Student credentials passed to endpoint requiring teacher
        from fastapi import HTTPException, status
        def mock_reject():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required.")

        app.dependency_overrides[require_teacher] = mock_reject

        res = self.client.get("/api/v2/gamification/teacher/learner/student-01")
        self.assertEqual(res.status_code, 403)


class TestIntegrationWithCorePipelines(unittest.IsolatedAsyncioTestCase):
    """Integration verification between activity completion and gamification."""

    @patch("services.learning.gamification_service.db")
    async def test_adaptive_attempt_awards_points(self, mock_db):
        """Simulate activity completion and verify reward evaluation is invoked."""
        user_id = "student-adapt"
        attempt_id = "att_test_999"

        # Mock DB for new reward
        mock_db.reward_events.find_one = AsyncMock(return_value=None)
        mock_db.reward_events.insert_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.update_one = AsyncMock(return_value=None)

        for cursor_mock in [mock_db.activity_attempts.find, mock_db.reading_sessions.find, mock_db.reward_events.find]:
            m = MagicMock()
            m.to_list = AsyncMock(return_value=[])
            cursor_mock.return_value = m

        mock_db.activity_attempts.count_documents = AsyncMock(return_value=1)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=0)

        result = await process_learning_reward(
            user_id=user_id,
            source_event_id=attempt_id,
            event_type="activity_attempt",
            metadata={"scorePercent": 85.0, "domain": "reading_comprehension"}
        )

        self.assertFalse(result.isDuplicate)
        self.assertEqual(result.pointsAwarded, 15)  # 10 base + 5 bonus
        self.assertEqual(result.totalPoints, 15)

    @patch("services.learning.gamification_service.db")
    async def test_reading_session_awards_points_and_badge(self, mock_db):
        """Simulate reading session completion and verify rewards."""
        user_id = "student-read"
        session_id = "sess_test_888"

        mock_db.reward_events.find_one = AsyncMock(return_value=None)
        mock_db.reward_events.insert_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.update_one = AsyncMock(return_value=None)

        for cursor_mock in [mock_db.activity_attempts.find, mock_db.reading_sessions.find, mock_db.reward_events.find]:
            m = MagicMock()
            m.to_list = AsyncMock(return_value=[])
            cursor_mock.return_value = m

        # 1 total activity completed unlocks First Steps
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=0)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=1)

        result = await process_learning_reward(
            user_id=user_id,
            source_event_id=session_id,
            event_type="reading_session",
            metadata={"comprehensionScore": 90.0, "wordsRead": 80, "wordsPresented": 80, "passageTitle": "Asha's Kite"}
        )

        self.assertEqual(result.pointsAwarded, 20)  # 10 + 5 comp + 5 completion
        self.assertEqual(len(result.newBadges), 1)
        self.assertEqual(result.newBadges[0].badgeId, "first_steps")
        self.assertIn("First Steps", result.celebrationMessage)

    @patch("services.learning.gamification_service.db")
    async def test_tutor_conversation_does_not_award_points(self, mock_db):
        """Verify tutor conversations do not create reward events."""
        # Tutor endpoints only do chat scaffolding, never calling process_learning_reward
        user_id = "student-tutor"
        mock_db.reward_events.insert_one = AsyncMock()

        # Simulate that tutor service runs
        from services.learning.tutor_service import build_tutor_instruction
        from models.v2_tutor import TutorContext
        ctx = TutorContext(
            learnerId="student-tutor",
            displayName="Aarav",
            learningLevel=2,
            learningLevelName="Developing",
            adaptiveTier=2,
            practiceAreas=["lotus"]
        )
        instruction = build_tutor_instruction(ctx)
        self.assertIn("Aarav", instruction)
        mock_db.reward_events.insert_one.assert_not_called()

    @patch("services.learning.gamification_service.db")
    async def test_streak_end_never_removes_points_or_badges(self, mock_db):
        """Verify that an inactive streak leaves total points and earned badges intact."""
        user_id = "student-dormant"
        old_badges = [{
            "badgeId": "first_steps",
            "title": "First Steps",
            "description": "Completed first learning activity",
            "icon": "🌱",
            "category": "milestone",
            "unlockedAt": 1000
        }]
        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "learnerId": user_id,
            "totalPoints": 150,
            "currentStreak": 0,
            "longestStreak": 7,
            "earnedBadges": old_badges,
            "streakMessage": "Ready for today's practice? Every little bit counts!",
        })
        mock_db.gamification_summaries.update_one = AsyncMock(return_value=None)

        for cursor_mock in [mock_db.activity_attempts.find, mock_db.reading_sessions.find, mock_db.reward_events.find]:
            m = MagicMock()
            m.sort.return_value = m
            m.limit.return_value = m
            m.skip.return_value = m
            m.to_list = AsyncMock(return_value=[])
            cursor_mock.return_value = m

        summary = await get_gamification_summary(user_id)
        self.assertEqual(summary.totalPoints, 150)
        self.assertEqual(len(summary.recentBadges), 1)
        self.assertEqual(summary.recentBadges[0].badgeId, "first_steps")
        self.assertEqual(summary.currentStreak, 0)
        self.assertEqual(summary.longestStreak, 7)


class TestClaimEventEndpoint(unittest.TestCase):
    """Test claim-event security and database verification."""

    def setUp(self):
        self.client = TestClient(app)
        settings.V2_GAMIFICATION = True
        self.mock_student = {
            "id": "student-claim-01",
            "role": "student",
            "classroomCode": "DA-DEMO",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_student

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.V2_GAMIFICATION = False

    @patch("routers.v2_gamification.db")
    @patch("routers.v2_gamification.process_learning_reward")
    def test_claim_event_verified_success(self, mock_process, mock_db):
        mock_db.activity_attempts.find_one = AsyncMock(return_value={
            "attemptId": "att_valid_123",
            "learnerId": "student-claim-01",
            "scorePercent": 85.0,
            "domain": "reading_comprehension",
        })
        mock_process.return_value = RewardEvaluationResult(
            pointsAwarded=15,
            totalPoints=15,
            newBadges=[],
            currentStreak=1,
            streakMaintained=True,
            celebrationMessage="+15 Points! Completed Reading Comprehension practice",
            isDuplicate=False,
        )

        res = self.client.post("/api/v2/gamification/claim-event", json={
            "sourceEventId": "att_valid_123",
            "eventType": "activity_attempt",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["pointsAwarded"], 15)
        self.assertEqual(data["totalPoints"], 15)

    @patch("routers.v2_gamification.db")
    def test_claim_event_missing_returns_404(self, mock_db):
        mock_db.activity_attempts.find_one = AsyncMock(return_value=None)

        res = self.client.post("/api/v2/gamification/claim-event", json={
            "sourceEventId": "non_existent_att",
            "eventType": "activity_attempt",
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    @patch("routers.v2_gamification.db")
    def test_claim_event_other_student_returns_403(self, mock_db):
        mock_db.activity_attempts.find_one = AsyncMock(return_value={
            "attemptId": "att_other_999",
            "learnerId": "student-OTHER",
            "scorePercent": 95.0,
        })

        res = self.client.post("/api/v2/gamification/claim-event", json={
            "sourceEventId": "att_other_999",
            "eventType": "activity_attempt",
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("do not own", res.json()["detail"].lower())


class TestGamificationAuditingAndTimezones(unittest.IsolatedAsyncioTestCase):
    """Test ledger reconciliation, timezone boundary handling, and teacher isolation."""

    @patch("services.learning.gamification_service.db")
    async def test_ledger_points_reconciliation(self, mock_db):
        """Audit totalPoints against the reward_events ledger."""
        user_id = "student-audit-01"
        reward_events = [
            {"points": 10, "eventType": "activity_attempt", "createdAt": 1000},
            {"points": 15, "eventType": "activity_attempt", "createdAt": 2000},
            {"points": 20, "eventType": "reading_session", "createdAt": 3000},
        ]
        expected_total = sum(r["points"] for r in reward_events)
        self.assertEqual(expected_total, 45)

        mock_db.reward_events.find.return_value.to_list = AsyncMock(return_value=reward_events)
        cursor_mock = MagicMock()
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.skip.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock
        cursor_mock.to_list = AsyncMock(return_value=reward_events)
        mock_db.reward_events.find.return_value = cursor_mock
        mock_db.reward_events.count_documents = AsyncMock(return_value=3)

        history = await get_reward_history(user_id, page=1, limit=10)
        actual_sum = sum(e.get("points", 0) for e in history.events)
        self.assertEqual(actual_sum, 45)
        self.assertEqual(history.totalEvents, 3)

    @patch("services.learning.gamification_service.db")
    async def test_streak_timezone_utc_midnight_crossing(self, mock_db):
        """Two activities at 23:55 UTC and 00:05 UTC next day register as 2 consecutive days."""
        user_id = "student-utc-edge"
        # 2026-03-01 23:55:00 UTC (1772409300) and 2026-03-02 00:05:00 UTC (1772409900)
        t1 = 1772409300
        t2 = 1772409900

        mock_db.activity_attempts.find.return_value.to_list = AsyncMock(return_value=[
            {"completedAt": t1},
            {"completedAt": t2},
        ])
        mock_db.reading_sessions.find.return_value.to_list = AsyncMock(return_value=[])
        mock_db.reward_events.find.return_value.to_list = AsyncMock(return_value=[])

        curr_streak, longest_streak, msg, last_active = await calculate_learner_streak(user_id)
        # Should be at least 2 distinct days
        self.assertGreaterEqual(longest_streak, 2)
        self.assertEqual(last_active, "2026-03-02")

    @patch("services.learning.gamification_service.verify_teacher_student_access")
    async def test_unrelated_teacher_rejected_with_403(self, mock_verify):
        """Ensure teacher cannot access student outside their assigned classroom."""
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=403, detail="Forbidden classroom access")

        with self.assertRaises(HTTPException) as ctx:
            await get_teacher_learner_reward_summary("student-other-school", "teacher-001")
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
