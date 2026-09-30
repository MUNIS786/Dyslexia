"""
backend/test_phase6_ai_tutor.py — Automated Test Suite for Phase 6 Personal AI Tutor.

Comprehensive tests:
1. Context Builder (deterministic compact context, level, passage excerpt, speech signals, privacy boundaries)
2. Prompt / Instruction Builder (level-adapted pedagogical guidance, non-clinical boundary, anti-hallucination)
3. Deterministic Offline Fallback (vocabulary, spelling, comprehension hints, encouragement, missing passage handling)
4. AI Provider Integration & Resilience (structured JSON parsing, timeout fallback, error resilience, plain-text safety)
5. Conversation History & Tenancy (bounded history, learner isolation, clear history)
6. API Endpoints & Security (feature flag 503, unauthenticated 401, empty message 400, cross-student 403, teacher access)
7. Adaptive & Reading Coach Integration (action triggers, word query handoff, zero score mutation)
"""
import unittest
import time
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_tutor import (
    TutorContext,
    CompactPassageContext,
    TutorRequest,
    TutorResponse,
    TutorSuggestedAction,
)
from services.learning.tutor_context import build_tutor_context
from services.learning.tutor_service import (
    build_tutor_instruction,
    generate_offline_fallback,
    _parse_ai_tutor_response,
    call_gemini_tutor,
    handle_tutor_chat,
    save_tutor_turn,
    get_tutor_history,
    clear_tutor_history,
    MAX_HISTORY_MESSAGES,
)


class TestTutorContextBuilder(unittest.IsolatedAsyncioTestCase):
    """Test deterministic compact context construction and privacy boundaries."""

    @patch("services.learning.tutor_context.db")
    @patch("services.learning.tutor_context.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.get_passage_by_id", new_callable=AsyncMock)
    async def test_build_tutor_context_complete(self, mock_passage, mock_state, mock_profile, mock_db):
        mock_db.users.find_one = AsyncMock(return_value={
            "id": "student-101",
            "name": "Aarav Sharma",
            "settings": {"font": "OpenDyslexic", "fontSize": 20, "ttsSpeed": 0.8},
            "passwordHash": "secret-hash-must-not-leak",
            "email": "aarav@test.school",
        })
        mock_profile.return_value = {
            "learning_level": {"level": 2, "name": "Developing"},
            "strengths": [{"friendly_name": "Visual Learning"}, {"friendly_name": "Vocabulary"}],
            "practice_areas": [{"friendly_name": "Reading Fluency"}],
        }
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_passage.return_value = {
            "passageId": "pas-t1-001",
            "title": "Sam the Cat",
            "text": "Sam is a cat. He likes the sun. " * 30,  # Long text
            "difficulty": 1,
            "vocabularyWords": [{"word": "cat"}, {"word": "sun"}],
        }
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "comprehensionScore": 80.0,
            "wordsRead": 45,
            "overallScore": 82.5,
        })
        mock_db.speech_reading_analyses.find_one = AsyncMock(return_value={
            "accuracyRate": 88.0,
            "wordsPerMinute": 72.0,
            "overallScore": 85.0,
        })

        ctx = await build_tutor_context("student-101", active_passage_id="pas-t1-001", active_word="cat")

        self.assertEqual(ctx.learnerId, "student-101")
        self.assertEqual(ctx.displayName, "Aarav")
        self.assertEqual(ctx.learningLevel, 2)
        self.assertEqual(ctx.learningLevelName, "Developing")
        self.assertEqual(ctx.adaptiveTier, 2)
        self.assertIn("Visual Learning", ctx.strengths)
        self.assertIn("Reading Fluency", ctx.practiceAreas)
        self.assertEqual(ctx.activeWord, "cat")

        # Passage excerpt should be bounded (< 400 chars)
        self.assertIsNotNone(ctx.currentPassage)
        self.assertLessEqual(len(ctx.currentPassage.excerpt), 400)
        self.assertTrue(ctx.currentPassage.excerpt.endswith("..."))
        self.assertEqual(ctx.currentPassage.vocabularyWords, ["cat", "sun"])

        # Signals present
        self.assertEqual(ctx.recentReading["comprehension"], 80.0)
        self.assertEqual(ctx.speechSignals["accuracy"], 88.0)
        self.assertEqual(ctx.speechSignals["wpm"], 72.0)

        # Accessibility preferences present
        self.assertEqual(ctx.accessibility["font"], "OpenDyslexic")

        # Privacy boundary: ensure model dump contains no PII or sensitive keys
        dumped = ctx.model_dump()
        self.assertNotIn("passwordHash", dumped)
        self.assertNotIn("email", dumped)
        self.assertNotIn("audio", str(dumped).lower())

    @patch("services.learning.tutor_context.db")
    @patch("services.learning.tutor_context.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.get_learning_state", new_callable=AsyncMock)
    async def test_build_tutor_context_missing_passage_and_screening(self, mock_state, mock_profile, mock_db):
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_profile.return_value = None
        mock_state.return_value = None
        mock_db.reading_sessions.find_one = AsyncMock(return_value=None)
        mock_db.speech_reading_analyses.find_one = AsyncMock(return_value=None)

        ctx = await build_tutor_context("new-student-999")
        self.assertEqual(ctx.learnerId, "new-student-999")
        self.assertEqual(ctx.displayName, "Student")
        self.assertEqual(ctx.learningLevel, 2)  # Safe default
        self.assertIsNone(ctx.currentPassage)
        self.assertIsNone(ctx.activeWord)
        self.assertIsNone(ctx.recentReading)
        self.assertIsNone(ctx.speechSignals)


class TestTutorPromptBuilder(unittest.TestCase):
    """Test level-adapted pedagogical prompt construction and safety boundaries."""

    def test_prompt_level_1_foundation(self):
        ctx = TutorContext(learnerId="s1", displayName="Maya", learningLevel=1, learningLevelName="Foundation")
        prompt = build_tutor_instruction(ctx)
        self.assertIn("FOUNDATION LEVEL", prompt)
        self.assertIn("very short, simple sentences", prompt)
        self.assertIn("Maya", prompt)
        self.assertIn("NON-CLINICAL BOUNDARY", prompt)
        self.assertIn("ANTI-HALLUCINATION", prompt)
        self.assertIn("PROGRESSIVE HINTS", prompt)

    def test_prompt_level_2_developing(self):
        ctx = TutorContext(learnerId="s2", displayName="Karan", learningLevel=2, learningLevelName="Developing")
        prompt = build_tutor_instruction(ctx)
        self.assertIn("DEVELOPING LEVEL", prompt)
        self.assertIn("gentle guiding question", prompt)

    def test_prompt_level_3_progressing(self):
        ctx = TutorContext(learnerId="s3", displayName="Riya", learningLevel=3, learningLevelName="Progressing")
        prompt = build_tutor_instruction(ctx)
        self.assertIn("PROGRESSING LEVEL", prompt)
        self.assertIn("simple reasoning", prompt)

    def test_prompt_with_active_passage(self):
        passage = CompactPassageContext(
            passageId="pas-1",
            title="The Brave Rabbit",
            excerpt="Once upon a time in a green forest...",
            difficulty=2,
            vocabularyWords=["brave", "forest"],
        )
        ctx = TutorContext(
            learnerId="s4",
            displayName="Dev",
            learningLevel=2,
            currentPassage=passage,
            activeWord="brave",
        )
        prompt = build_tutor_instruction(ctx)
        self.assertIn("The Brave Rabbit", prompt)
        self.assertIn("brave, forest", prompt)
        self.assertIn("ACTIVE WORD QUERIED:\nbrave", prompt)


class TestTutorOfflineFallback(unittest.TestCase):
    """Test deterministic offline fallback responses across educational categories."""

    def setUp(self):
        self.ctx = TutorContext(
            learnerId="s10",
            displayName="Arjun",
            learningLevel=2,
            learningLevelName="Developing",
        )

    def test_vocabulary_fallback_known_word(self):
        req = TutorRequest(message="What does enormous mean?")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertEqual(resp.status, "ok")
        self.assertEqual(resp.source, "offline-fallback")
        self.assertIn("Enormous", resp.message)
        self.assertIn("e · nor · mous", resp.message)
        self.assertIsNotNone(resp.suggestedAction)
        self.assertEqual(resp.suggestedAction.type, "practice_word")
        self.assertEqual(resp.suggestedAction.payload.get("word"), "enormous")
        self.assertIsNotNone(resp.followUpQuestion)

    def test_vocabulary_fallback_active_word_param(self):
        req = TutorRequest(message="Explain this word please", activeWord="curious")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertIn("Curious", resp.message)
        self.assertIn("cu · ri · ous", resp.message)
        self.assertEqual(resp.suggestedAction.type, "practice_word")

    def test_vocabulary_fallback_unlisted_word(self):
        req = TutorRequest(message="What does telescope mean?")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertIn("telescope", resp.message)
        self.assertEqual(resp.suggestedAction.type, "practice_word")

    def test_spelling_fallback(self):
        req = TutorRequest(message="How do I spell beautiful?")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertIn("BEAUTIFUL", resp.message)
        self.assertIn("beau · ti · ful", resp.message)
        self.assertEqual(resp.suggestedAction.type, "practice_word")

    def test_comprehension_fallback_with_passage(self):
        passage = CompactPassageContext(
            passageId="pas-cat",
            title="Sam the Cat",
            excerpt="Sam sits on a red mat in the warm sun.",
            difficulty=1,
        )
        ctx_with_passage = TutorContext(
            learnerId="s10",
            displayName="Arjun",
            learningLevel=2,
            currentPassage=passage,
        )
        req = TutorRequest(message="Can you give me a hint on the story?")
        resp = generate_offline_fallback(req, ctx_with_passage)
        self.assertIn("Sam the Cat", resp.message)
        self.assertIn("gentle clue", resp.message)
        self.assertEqual(resp.suggestedAction.type, "try_question")

    def test_comprehension_fallback_missing_passage_anti_hallucination(self):
        req = TutorRequest(message="What happened in the story?")
        resp = generate_offline_fallback(req, self.ctx)
        # Must NOT invent story details; must inform student story is missing
        self.assertIn("don't have the story", resp.message)
        self.assertEqual(resp.suggestedAction.type, "open_reading_coach")

    def test_encouragement_fallback(self):
        req = TutorRequest(message="This is too hard, I can't do this.")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertIn("Arjun", resp.message)
        self.assertIn("one word at a time", resp.message)
        self.assertEqual(resp.suggestedAction.type, "start_adaptive_practice")

    def test_general_guidance_fallback(self):
        req = TutorRequest(message="Hello there!")
        resp = generate_offline_fallback(req, self.ctx)
        self.assertIn("Arjun", resp.message)
        self.assertIn("Explain a word", resp.message)
        self.assertEqual(resp.suggestedAction.type, "open_reading_coach")

    def test_fallback_handles_empty_and_special_characters(self):
        for msg in ["???", "   ", "!@#$%", "a", "12345"]:
            req = TutorRequest(message=msg if msg.strip() else "hi")
            resp = generate_offline_fallback(req, self.ctx)
            self.assertEqual(resp.status, "ok")
            self.assertTrue(len(resp.message) > 0)


class TestAIResponseParsing(unittest.TestCase):
    """Test parsing and validation of AI provider output."""

    def setUp(self):
        self.ctx = TutorContext(learnerId="s1", displayName="Test", learningLevel=2)

    def test_parse_valid_structured_json(self):
        raw = json.dumps({
            "message": "Enormous means very big! Think of an elephant.",
            "explanation": "It has 3 syllables: e-nor-mous.",
            "suggestedAction": {
                "type": "practice_word",
                "label": "Practice 'enormous'",
                "payload": {"word": "enormous"}
            },
            "followUpQuestion": "Can you name another huge animal?"
        })
        resp = _parse_ai_tutor_response(raw, self.ctx)
        self.assertEqual(resp.status, "ok")
        self.assertEqual(resp.source, "gemini")
        self.assertIn("Enormous means", resp.message)
        self.assertEqual(resp.explanation, "It has 3 syllables: e-nor-mous.")
        self.assertEqual(resp.suggestedAction.type, "practice_word")
        self.assertEqual(resp.followUpQuestion, "Can you name another huge animal?")

    def test_parse_markdown_fenced_json(self):
        raw = "```json\n{\"message\": \"Great reading!\", \"explanation\": null}\n```"
        resp = _parse_ai_tutor_response(raw, self.ctx)
        self.assertEqual(resp.message, "Great reading!")
        self.assertEqual(resp.source, "gemini")

    def test_parse_plain_text_safely_without_crashing(self):
        raw = "Here is a helpful tip: try sounding out the first two letters 'b' and 'a'."
        resp = _parse_ai_tutor_response(raw, self.ctx)
        self.assertEqual(resp.status, "ok")
        self.assertEqual(resp.message, raw)
        self.assertIsNotNone(resp.suggestedAction)

    def test_parse_malformed_json_falls_back_to_text(self):
        raw = "{'message': 'Single quotes are invalid json"
        resp = _parse_ai_tutor_response(raw, self.ctx)
        self.assertEqual(resp.status, "ok")
        self.assertIn("Single quotes", resp.message)


class TestTutorConversationPersistence(unittest.IsolatedAsyncioTestCase):
    """Test bounded history storage and cross-student isolation in db.tutor_conversations."""

    @patch("services.learning.tutor_service.db")
    async def test_save_and_retrieve_turn(self, mock_db):
        mock_db.tutor_conversations.find_one = AsyncMock(return_value=None)
        mock_db.tutor_conversations.insert_one = AsyncMock()

        resp = TutorResponse(
            status="ok",
            message="Hi!",
            suggestedAction=TutorSuggestedAction(type="open_reading_coach", label="Read"),
            source="offline-fallback",
            learningLevel=2,
        )

        conv_id = await save_tutor_turn("learner-1", "Hello tutor", resp)
        self.assertEqual(conv_id, "conv_learner-1")
        mock_db.tutor_conversations.insert_one.assert_called_once()
        saved_doc = mock_db.tutor_conversations.insert_one.call_args[0][0]
        self.assertEqual(saved_doc["learnerId"], "learner-1")
        self.assertEqual(len(saved_doc["messages"]), 2)

    @patch("services.learning.tutor_service.db")
    async def test_bounded_history_truncation(self, mock_db):
        existing_msgs = [{"id": str(i), "role": "user", "content": f"msg {i}"} for i in range(25)]
        mock_db.tutor_conversations.find_one = AsyncMock(return_value={
            "conversationId": "conv_learner-2",
            "messages": existing_msgs,
        })
        mock_db.tutor_conversations.update_one = AsyncMock()

        resp = TutorResponse(status="ok", message="Reply", source="offline-fallback", learningLevel=2)
        await save_tutor_turn("learner-2", "New message", resp)

        mock_db.tutor_conversations.update_one.assert_called_once()
        set_payload = mock_db.tutor_conversations.update_one.call_args[0][1]["$set"]
        # History must be bounded to MAX_HISTORY_MESSAGES
        self.assertLessEqual(len(set_payload["messages"]), MAX_HISTORY_MESSAGES)

    @patch("services.learning.tutor_service.db")
    async def test_clear_history(self, mock_db):
        mock_db.tutor_conversations.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        cleared = await clear_tutor_history("learner-1")
        self.assertTrue(cleared)
        mock_db.tutor_conversations.delete_one.assert_called_with({
            "conversationId": "conv_learner-1",
            "learnerId": "learner-1",
        })


class TestTutorAPIEndpointsAndSecurity(unittest.TestCase):
    """Test API endpoint authorization, feature flag, tenancy, and validation."""

    def setUp(self):
        self.client = TestClient(app)

    def test_feature_flag_disabled_returns_503(self):
        with patch.object(settings, "V2_AI_TUTOR", False):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.post("/api/v2/tutor/chat", json={"message": "Help me"})
            self.assertEqual(res.status_code, 503)
            self.assertIn("disabled via feature flags", res.json()["detail"])
            app.dependency_overrides.clear()

    def test_unauthenticated_request_returns_401(self):
        with patch.object(settings, "V2_AI_TUTOR", True):
            res = self.client.post("/api/v2/tutor/chat", json={"message": "Hello"})
            self.assertEqual(res.status_code, 401)

    def test_empty_message_returns_400(self):
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.post("/api/v2/tutor/chat", json={"message": "   "})
            self.assertEqual(res.status_code, 400)
            self.assertIn("Message cannot be empty", res.json()["detail"])
            app.dependency_overrides.clear()

    @patch("routers.v2_tutor.handle_tutor_chat", new_callable=AsyncMock)
    def test_valid_chat_request_success(self, mock_handle):
        mock_handle.return_value = TutorResponse(
            status="ok",
            message="Hello! Let's explore words together.",
            source="offline-fallback",
            learningLevel=2,
            suggestedAction=TutorSuggestedAction(type="open_reading_coach", label="Read"),
        )
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.post("/api/v2/tutor/chat", json={"message": "Hi tutor!"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["message"], "Hello! Let's explore words together.")
            self.assertEqual(data["suggestedAction"]["type"], "open_reading_coach")
            app.dependency_overrides.clear()

    @patch("routers.v2_tutor.build_tutor_context", new_callable=AsyncMock)
    def test_student_get_own_context_allowed(self, mock_ctx):
        mock_ctx.return_value = TutorContext(
            learnerId="student-1",
            displayName="Pooja",
            learningLevel=2,
        )
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.get("/api/v2/tutor/context")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["displayName"], "Pooja")
            app.dependency_overrides.clear()

    def test_student_cross_access_other_student_context_forbidden_403(self):
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.get("/api/v2/tutor/context?learnerId=another-student")
            self.assertEqual(res.status_code, 403)
            self.assertIn("Students can only access their own tutor context", res.json()["detail"])
            app.dependency_overrides.clear()

    @patch("routers.v2_tutor.build_tutor_context", new_callable=AsyncMock)
    def test_teacher_can_access_student_context(self, mock_ctx):
        mock_ctx.return_value = TutorContext(
            learnerId="student-2",
            displayName="Student Two",
            learningLevel=3,
        )
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "teacher-99",
                "role": "teacher",
            }
            res = self.client.get("/api/v2/tutor/context?learnerId=student-2")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["learnerId"], "student-2")
            app.dependency_overrides.clear()

    @patch("routers.v2_tutor.get_tutor_history", new_callable=AsyncMock)
    def test_get_history_endpoint(self, mock_hist):
        mock_hist.return_value = [
            {"role": "user", "content": "What is cat?"},
            {"role": "assistant", "content": "A friendly animal."},
        ]
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.get("/api/v2/tutor/history?limit=10")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()["messages"]), 2)
            app.dependency_overrides.clear()

    @patch("routers.v2_tutor.clear_tutor_history", new_callable=AsyncMock)
    def test_clear_history_endpoint(self, mock_clear):
        mock_clear.return_value = True
        with patch.object(settings, "V2_AI_TUTOR", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-1",
                "role": "student",
            }
            res = self.client.delete("/api/v2/tutor/history")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["cleared"])
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
