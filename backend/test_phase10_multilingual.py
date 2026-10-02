"""
backend/test_phase10_multilingual.py — Comprehensive Test Suite for Phase 10: Multilingual Support.

Tests cover:
1. Supported Languages Catalog:
   - Catalog returns supported languages: English (en), Marathi (mr), Hindi (hi)
   - Native display names: 'English', 'मराठी', 'हिन्दी'
   - Correct direction (ltr) and support flags
2. User Language Preference Endpoints:
   - GET /api/v2/multilingual/preference returns default 'en' when user has no preference
   - GET returns persisted preference when set
   - PUT/PATCH updates preference for authenticated caller
   - Supported locale validation: rejects unsupported codes ('fr', 'de', 'es') with 400
   - Flexible normalization: 'marathi' -> 'mr', 'hindi' -> 'hi', 'en-IN' -> 'en'
   - Unauthenticated requests rejected with 401
   - Caller isolation: endpoint operates strictly on current_user, cannot modify another user's preference
3. Reading Passages Language Metadata & Filtering:
   - Passages catalog correctly tags passages with language metadata ('en', 'mr', 'hi')
   - Filter passages by language (GET /api/v2/reading/passages?language=mr)
   - Filter passages by language (GET /api/v2/reading/passages?language=hi)
   - Non-existent language returns empty list with safe fallback, never crashes
   - Recommendation endpoint accepts language parameter
4. Speech & Reading Alignment with Devanagari Text:
   - Normalization preserves Devanagari script while stripping punctuation (e.g. Danda '।')
   - Word token matching handles Marathi and Hindi correctly
5. AI Tutor Multilingual Integration:
   - TutorContext contains language field
   - Tutor prompt instructions include Marathi/Hindi pedagogical guidance
   - Deterministic offline fallback returns child-friendly Marathi/Hindi responses
   - Maintains non-clinical safety boundaries
6. Feature Flag Behavior:
   - When V2_MULTILINGUAL = False, endpoints return 503 Service Unavailable
   - When V2_MULTILINGUAL = True, endpoints operate normally
7. Backward Compatibility:
   - Existing user profiles without preferredLanguage load seamlessly with 'en' fallback
"""
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_multilingual import (
    LanguageInfo,
    LanguagePreferenceUpdate,
    LanguagePreferenceResponse,
    SUPPORTED_LANGUAGES,
    normalize_language_code,
)
from services.learning.reading_service import (
    DEFAULT_PASSAGES as PASSAGE_CATALOG,
    get_passages,
    get_passage_by_id,
)
from services.learning.reading_recommender import recommend_reading_passage
from services.learning.speech_analysis import normalize_text_to_tokens
from services.learning.tutor_context import build_tutor_context
from services.learning.tutor_service import (
    build_tutor_instruction,
    generate_offline_fallback,
)
from models.v2_tutor import TutorContext, TutorRequest, CompactPassageContext


class TestMultilingualModelsAndNormalization(unittest.TestCase):
    """Unit tests for models and language normalization utility."""

    def test_supported_languages_list(self):
        codes = [lang.code for lang in SUPPORTED_LANGUAGES.values()]
        self.assertIn("en", codes)
        self.assertIn("mr", codes)
        self.assertIn("hi", codes)

        mr_info = SUPPORTED_LANGUAGES["mr"]
        self.assertEqual(mr_info.native_name, "मराठी")
        self.assertEqual(mr_info.direction, "ltr")
        self.assertTrue(mr_info.interface_supported)
        self.assertTrue(mr_info.learning_content_supported)

        hi_info = SUPPORTED_LANGUAGES["hi"]
        self.assertEqual(hi_info.native_name, "हिन्दी")
        self.assertEqual(hi_info.direction, "ltr")

    def test_normalize_language_code(self):
        # Valid standard codes
        self.assertEqual(normalize_language_code("en"), "en")
        self.assertEqual(normalize_language_code("mr"), "mr")
        self.assertEqual(normalize_language_code("hi"), "hi")

        # Extended regional codes
        self.assertEqual(normalize_language_code("en-US"), "en")
        self.assertEqual(normalize_language_code("en-IN"), "en")
        self.assertEqual(normalize_language_code("mr-IN"), "mr")
        self.assertEqual(normalize_language_code("hi-IN"), "hi")

        # Full names
        self.assertEqual(normalize_language_code("English"), "en")
        self.assertEqual(normalize_language_code("marathi"), "mr")
        self.assertEqual(normalize_language_code("HINDI"), "hi")

        # Unsupported codes return None
        self.assertIsNone(normalize_language_code("fr"))
        self.assertIsNone(normalize_language_code("es"))
        self.assertIsNone(normalize_language_code("de"))
        self.assertIsNone(normalize_language_code("unknown"))

    def test_language_preference_update_model(self):
        update = LanguagePreferenceUpdate(language="mr")
        self.assertEqual(update.language, "mr")
        self.assertEqual(update.get_target_code(), "mr")

        update_named = LanguagePreferenceUpdate(language="marathi")
        self.assertEqual(update_named.language, "marathi")
        self.assertEqual(update_named.get_target_code(), "marathi")


class TestMultilingualEndpoints(unittest.TestCase):
    """Integration tests for /api/v2/multilingual router."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_student = {
            "id": "student-101",
            "name": "Aarav Sharma",
            "role": "student",
            "email": "aarav@example.com",
            "preferredLanguage": "en",
        }

    def test_get_languages_catalog(self):
        with patch.object(settings, "V2_MULTILINGUAL", True):
            res = self.client.get("/api/v2/multilingual/languages")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsInstance(data, list)
            codes = [l["code"] for l in data]
            self.assertIn("en", codes)
            self.assertIn("mr", codes)
            self.assertIn("hi", codes)

    def test_get_preference_default_fallback(self):
        """When user document has no language set, safely fall back to 'en'."""
        with patch.object(settings, "V2_MULTILINGUAL", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "student-101", "role": "student"}
            with patch("routers.v2_multilingual.db") as mock_db:
                mock_db.users.find_one = AsyncMock(return_value={"id": "student-101"})
                res = self.client.get("/api/v2/multilingual/preference")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["preferredLanguage"], "en")
                self.assertEqual(data["status"], "ok")
            app.dependency_overrides.clear()

    def test_get_preference_stored(self):
        """When user document has preferredLanguage set to 'mr', return it."""
        with patch.object(settings, "V2_MULTILINGUAL", True):
            app.dependency_overrides[get_current_user] = lambda: {"id": "student-101", "role": "student"}
            with patch("routers.v2_multilingual.db") as mock_db:
                mock_db.users.find_one = AsyncMock(return_value={
                    "id": "student-101",
                    "preferredLanguage": "mr",
                })
                res = self.client.get("/api/v2/multilingual/preference")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["preferredLanguage"], "mr")
                self.assertEqual(data["activeLanguage"]["nativeName"], "मराठी")
            app.dependency_overrides.clear()

    def test_update_preference_valid(self):
        """PUT /api/v2/multilingual/preference updates preference to Hindi."""
        with patch.object(settings, "V2_MULTILINGUAL", True):
            app.dependency_overrides[get_current_user] = lambda: self.mock_student
            with patch("routers.v2_multilingual.db") as mock_db:
                mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
                mock_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

                res = self.client.put("/api/v2/multilingual/preference", json={"language": "hi"})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["preferredLanguage"], "hi")
                self.assertEqual(data["activeLanguage"]["nativeName"], "हिन्दी")
                self.assertEqual(data["status"], "ok")

                # Verify db.users was called with student's ID only
                mock_db.users.update_one.assert_called_once()
                call_args = mock_db.users.update_one.call_args
                self.assertEqual(call_args[0][0], {"id": "student-101"})
                self.assertEqual(call_args[0][1]["$set"]["preferredLanguage"], "hi")
            app.dependency_overrides.clear()

    def test_update_preference_unsupported_rejected(self):
        """Updating to unsupported locale like 'fr' returns 400 Bad Request."""
        with patch.object(settings, "V2_MULTILINGUAL", True):
            app.dependency_overrides[get_current_user] = lambda: self.mock_student
            res = self.client.put("/api/v2/multilingual/preference", json={"language": "fr"})
            self.assertEqual(res.status_code, 400)
            data = res.json()
            self.assertIn("Unsupported language", data["detail"])
            app.dependency_overrides.clear()

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests to preference endpoints return 401."""
        with patch.object(settings, "V2_MULTILINGUAL", True):
            app.dependency_overrides.clear()
            res = self.client.get("/api/v2/multilingual/preference")
            self.assertEqual(res.status_code, 401)

            res_put = self.client.put("/api/v2/multilingual/preference", json={"language": "mr"})
            self.assertEqual(res_put.status_code, 401)

    def test_feature_flag_disabled_returns_503(self):
        """When V2_MULTILINGUAL is False, router endpoints return 503."""
        with patch.object(settings, "V2_MULTILINGUAL", False), \
             patch.object(settings, "V2_MULTILINGUAL_SUPPORT", False):
            res = self.client.get("/api/v2/multilingual/languages")
            self.assertEqual(res.status_code, 503)
            self.assertIn("Multilingual Support is currently disabled", res.json()["detail"])


class TestReadingContentLanguageSupport(unittest.IsolatedAsyncioTestCase):
    """Tests for language metadata on reading passages and language-aware recommendations."""

    def test_passages_have_language_metadata(self):
        """All catalog passages have valid language metadata."""
        for p in PASSAGE_CATALOG:
            self.assertIn("language", p)
            self.assertIn(p["language"], ["en", "mr", "hi"])

    def test_marathi_passages_exist_with_comprehension_and_vocab(self):
        """Verify authentic Marathi passages exist with questions and vocabulary."""
        mr_passages = [p for p in PASSAGE_CATALOG if p.get("language") == "mr"]
        self.assertGreaterEqual(len(mr_passages), 2)
        for p in mr_passages:
            self.assertTrue(len(p["text"]) > 0)
            self.assertTrue(len(p["vocabulary"]) > 0)
            self.assertTrue(len(p["questions"]) > 0)

    def test_hindi_passages_exist_with_comprehension_and_vocab(self):
        """Verify authentic Hindi passages exist with questions and vocabulary."""
        hi_passages = [p for p in PASSAGE_CATALOG if p.get("language") == "hi"]
        self.assertGreaterEqual(len(hi_passages), 2)
        for p in hi_passages:
            self.assertTrue(len(p["text"]) > 0)
            self.assertTrue(len(p["vocabulary"]) > 0)
            self.assertTrue(len(p["questions"]) > 0)

    async def test_get_passages_filtered_by_language(self):
        """Filter get_passages by language."""
        with patch("services.learning.reading_service.db") as mock_db:
            mock_db.reading_passages.find.side_effect = Exception("DB unavailable")
            mr_list = await get_passages(language="mr")
            self.assertTrue(len(mr_list) >= 2)
            for p in mr_list:
                self.assertEqual(p["language"], "mr")

            hi_list = await get_passages(language="hi")
            self.assertTrue(len(hi_list) >= 2)
            for p in hi_list:
                self.assertEqual(p["language"], "hi")

            en_list = await get_passages(language="en")
            self.assertTrue(len(en_list) > 0)
            for p in en_list:
                self.assertEqual(p["language"], "en")

    async def test_unsupported_language_filter_returns_empty(self):
        """Filtering by an unsupported language safely returns empty list without error."""
        with patch("services.learning.reading_service.db") as mock_db:
            mock_db.reading_passages.find.side_effect = Exception("DB unavailable")
            res = await get_passages(language="es")
            self.assertEqual(res, [])

    async def test_recommend_reading_passage_with_language(self):
        """recommend_reading_passage returns appropriate story for requested language."""
        with patch("services.learning.reading_recommender.db") as mock_db, \
             patch("services.learning.reading_recommender.get_learning_state") as mock_state, \
             patch("services.learning.reading_recommender.get_or_create_learner_profile") as mock_profile:
            mock_db.reading_sessions.find.side_effect = Exception("DB unavailable")
            mock_state.return_value = {"activeDifficultyTier": 1}
            mock_profile.return_value = {"areas_for_practice": [], "strengths": []}
            rec_mr = await recommend_reading_passage(learner_id="student-101", preferred_language="mr")
            self.assertIsNotNone(rec_mr)
            self.assertEqual(rec_mr.recommendedPassage.language, "mr")

            mock_state.return_value = {"activeDifficultyTier": 2}
            rec_hi = await recommend_reading_passage(learner_id="student-101", preferred_language="hi")
            self.assertIsNotNone(rec_hi)
            self.assertEqual(rec_hi.recommendedPassage.language, "hi")


class TestDevanagariSpeechNormalization(unittest.TestCase):
    """Tests for Devanagari text processing and tokenization."""

    def test_normalize_devanagari_punctuation(self):
        """Devanagari Danda (।) and double Danda (॥) are cleanly normalized."""
        sample_mr = "सोनू नावाचा एक छोटा मुलगा होता। तो बागेत खेळत होता॥"
        tokens = normalize_text_to_tokens(sample_mr)
        self.assertNotIn("।", tokens)
        self.assertNotIn("॥", tokens)
        self.assertIn("सोनू", tokens)
        self.assertIn("मुलगा", tokens)
        self.assertIn("खेळत", tokens)

    def test_normalize_hindi_sentence(self):
        """Hindi sentence retains Unicode characters and tokenizes cleanly."""
        sample_hi = "रोहन को किताबें पढ़ना बहुत पसंद था! क्या आपको पसंद है?"
        tokens = normalize_text_to_tokens(sample_hi)
        self.assertIn("रोहन", tokens)
        self.assertIn("किताबें", tokens)
        self.assertIn("पढ़ना", tokens)


class TestAITutorMultilingual(unittest.IsolatedAsyncioTestCase):
    """Tests for AI Tutor multilingual instructions and offline fallbacks."""

    async def test_build_tutor_context_sets_language(self):
        """build_tutor_context extracts or falls back to correct language."""
        with patch("services.learning.tutor_context.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value={
                "id": "student-101",
                "name": "Meera",
                "preferredLanguage": "mr",
            })
            mock_db.reading_sessions.find_one = AsyncMock(return_value=None)
            mock_db.speech_reading_analyses.find_one = AsyncMock(return_value=None)

            ctx = await build_tutor_context("student-101")
            self.assertEqual(ctx.language, "mr")

    def test_build_tutor_instruction_includes_marathi_guidance(self):
        """Prompt instruction contains explicit Marathi language directives when language='mr'."""
        ctx = TutorContext(
            learnerId="student-101",
            displayName="Meera",
            learningLevel=2,
            learningLevelName="Developing",
            adaptiveTier=1,
            language="mr",
        )
        instruction = build_tutor_instruction(ctx)
        self.assertIn("LANGUAGE REQUIREMENT (MARATHI / मराठी)", instruction)
        self.assertIn("Devanagari script", instruction)

    def test_build_tutor_instruction_includes_hindi_guidance(self):
        """Prompt instruction contains explicit Hindi language directives when language='hi'."""
        ctx = TutorContext(
            learnerId="student-102",
            displayName="Rohan",
            learningLevel=3,
            learningLevelName="Progressing",
            adaptiveTier=2,
            language="hi",
        )
        instruction = build_tutor_instruction(ctx)
        self.assertIn("LANGUAGE REQUIREMENT (HINDI / हिन्दी)", instruction)
        self.assertIn("Devanagari script", instruction)

    def test_offline_fallback_marathi_encouragement(self):
        """When child sends message indicating difficulty in Marathi, tutor responds in Marathi."""
        ctx = TutorContext(
            learnerId="student-101",
            displayName="Meera",
            learningLevel=2,
            learningLevelName="Developing",
            adaptiveTier=1,
            language="mr",
        )
        req = TutorRequest(message="मला खूप कठीण वाटत आहे")
        res = generate_offline_fallback(req, ctx)
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.source, "offline-fallback")
        self.assertIn("छान प्रयत्न करत आहात", res.message)
        self.assertIn("सावकाश शिकूया", res.message)

    def test_offline_fallback_hindi_guidance(self):
        """When learner asks for general guidance in Hindi, tutor responds in Hindi."""
        ctx = TutorContext(
            learnerId="student-102",
            displayName="Rohan",
            learningLevel=2,
            learningLevelName="Developing",
            adaptiveTier=1,
            language="hi",
        )
        req = TutorRequest(message="नमस्ते")
        res = generate_offline_fallback(req, ctx)
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.source, "offline-fallback")
        self.assertIn("नमस्ते Rohan!", res.message)
        self.assertIn("DyslexAid पठन मित्र", res.message)


if __name__ == "__main__":
    unittest.main()
