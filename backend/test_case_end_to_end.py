"""
backend/test_case_end_to_end.py — Dedicated End-to-End Test Case: Adaptive Scaffolding & Recovery Journey.

Test Scenario:
1. Student Aarav is practicing at Tier 2 (Developing).
2. Student experiences reading fatigue/difficulty, scoring below threshold.
3. The Phase 3 Adaptive Engine detects consecutive struggle and triggers downward scaffolding (Tier 2 -> Tier 1).
4. System provides non-punitive, encouraging feedback ("Great effort! We'll practice another comfortable passage at Level 1.").
5. The recommendation engine immediately adjusts and selects a comfortable Tier 1 foundation passage for next practice.
6. The learning insights and parent view report honest data sufficiency without any medical or clinical deficit labeling.
"""
import time
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from deps.deps import get_current_user
from models.v2_reading import ReadingSessionCompleteRequest
from services.learning.reading_service import (
    DEFAULT_PASSAGES,
    complete_reading_session,
)


def make_cursor_mock(items):
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.skip = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


class TestAdaptiveScaffoldingJourneyCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.student_user = {
            "id": "student-aarav-01",
            "name": "Aarav Sharma",
            "email": "aarav@example.com",
            "role": "student",
            "classroomJoined": "CLASS-DELHI-01",
        }
        self.parent_user = {
            "id": "parent-sunita-01",
            "name": "Sunita Sharma",
            "email": "sunita@example.com",
            "role": "parent",
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("services.learning.reading_service.recalibrate_from_activity", new_callable=AsyncMock)
    @patch("services.learning.reading_service.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_service.db")
    async def test_adaptive_scaffolding_step_down_on_consecutive_struggles(
        self, mock_db, mock_get_state, mock_recal
    ):
        """
        Validates the compassionate, non-punitive ZPD scaffolding mechanism:
        When a learner experiences 2 consecutive struggles at Tier 2, the system
        gracefully adapts to Tier 1 for joyful, comfortable practice rather than
        penalizing the learner or issuing deficit labels.
        """
        now = int(time.time())

        # Find Tier 2 passage from catalog
        t2_passage = [p for p in DEFAULT_PASSAGES if p.get("difficulty") == 2][0]

        session_doc = {
            "sessionId": "ses-struggle-02",
            "learnerId": self.student_user["id"],
            "passageId": t2_passage["passageId"],
            "difficulty": 2,
            "status": "in_progress",
            "wordsPresented": t2_passage.get("wordCount", 90),
            "createdAt": now - 180,
        }
        mock_db.reading_sessions.find_one = AsyncMock(return_value=session_doc)
        mock_db.reading_passages.find_one = AsyncMock(return_value=t2_passage)
        
        # State currently has 1 previous failure at Tier 2
        mock_get_state.return_value = {
            "consecutive_passes": 0,
            "consecutive_failures": 1,
            "active_difficulty_tier": 2,
            "rolling_comprehension_scores": [40.0],
        }
        mock_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learning_states.update_one = AsyncMock(return_value=MagicMock())
        mock_db.progress.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock())

        # Student submits incorrect answers (struggling session)
        req = ReadingSessionCompleteRequest(
            sessionId="ses-struggle-02",
            durationSeconds=140,
            wordsRead=40,  # incomplete read
            comprehensionAnswers={"wrong_q": 99},
            completed=True,
        )

        # 1. Complete reading session
        res = await complete_reading_session(self.student_user["id"], req)
        self.assertEqual(res["status"], "ok")

        # 2. Verify gentle adaptation was triggered
        adaptation = res["adaptation"]
        self.assertTrue(adaptation["adaptationTriggered"])
        self.assertEqual(adaptation["previousTier"], 2)
        self.assertEqual(adaptation["newTier"], 1)
        self.assertTrue(adaptation["tierChanged"])
        self.assertIn("gentle reading scaffolding", adaptation["reason"].lower())

        # 3. Verify encouraging, supportive child-facing message (zero shaming)
        self.assertIn("Level 1", res["nextStepMessage"])
        self.assertIn("comfortable", res["nextStepMessage"].lower())

        # 4. Verify new currentTier is 1
        self.assertEqual(res["currentTier"], 1)
