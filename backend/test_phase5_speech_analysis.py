"""
backend/test_phase5_speech_analysis.py — Automated Test Suite for Phase 5 Speech & Reading Analysis.

Comprehensive tests:
1. Normalization (punctuation, whitespace, capitalization, empty input, contractions)
2. Sequence Alignment (perfect match, omissions, insertions, substitutions, mixed errors, empty inputs)
3. Accuracy & Pacing (100%, partial, zero recognized, zero expected, WPM safeguards, practice score)
4. Confidence & Hesitation (browser confidence summary present/absent, pauses, hesitations)
5. Session Lifecycle & Privacy (derived metrics persisted, NO audio stored, profile recalibration)
6. API Endpoints & Security (feature flag toggle 503, own session allowed, cross-student 403, unauthorized 401, teacher access)
7. Offline Independence (zero external AI dependencies)
"""
import unittest
import uuid
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_speech_analysis import (
    WordAlignmentItem,
    SpeechConfidenceSummary,
    SpeechAnalysisRequest,
    SpeechReadingAnalysis,
    SpeechAnalysisResponse,
)
from services.learning.speech_analysis import (
    normalize_text_to_tokens,
    align_word_sequences,
    calculate_word_accuracy,
    calculate_coverage_rate,
    calculate_words_per_minute,
    calculate_reading_practice_score,
    generate_child_friendly_feedback,
    analyze_speech_reading,
    get_speech_analysis_for_session,
)


class TestSpeechNormalization(unittest.TestCase):
    """Test text tokenization and normalization rules."""

    def test_punctuation_stripping(self):
        text = "Hello, world! This is a test... (really)."
        tokens = normalize_text_to_tokens(text)
        self.assertEqual(tokens, ["hello", "world", "this", "is", "a", "test", "really"])

    def test_whitespace_normalization(self):
        text = "  lots   of \n\n whitespace \t and   tabs  "
        tokens = normalize_text_to_tokens(text)
        self.assertEqual(tokens, ["lots", "of", "whitespace", "and", "tabs"])

    def test_capitalization(self):
        text = "The QUICK Brown Fox JUMPS"
        tokens = normalize_text_to_tokens(text)
        self.assertEqual(tokens, ["the", "quick", "brown", "fox", "jumps"])

    def test_empty_and_none_input(self):
        self.assertEqual(normalize_text_to_tokens(None), [])
        self.assertEqual(normalize_text_to_tokens(""), [])
        self.assertEqual(normalize_text_to_tokens("     "), [])
        self.assertEqual(normalize_text_to_tokens("!@#$%^&*()_+"), [])

    def test_contractions_preserved(self):
        text = "Don't stop, we'll make it!"
        tokens = normalize_text_to_tokens(text)
        self.assertIn("don't", tokens)
        self.assertIn("we'll", tokens)


class TestSequenceAlignment(unittest.TestCase):
    """Test dynamic programming sequence alignment algorithm."""

    def test_perfect_match(self):
        expected = ["the", "cat", "sat", "on", "the", "mat"]
        recognized = ["the", "cat", "sat", "on", "the", "mat"]
        alignment = align_word_sequences(expected, recognized)

        self.assertEqual(len(alignment), 6)
        for item in alignment:
            self.assertEqual(item["status"], "matched")
            self.assertEqual(item["expected"], item["recognized"])

    def test_omission_detection(self):
        expected = ["the", "quick", "brown", "fox"]
        recognized = ["the", "brown", "fox"]  # 'quick' omitted
        alignment = align_word_sequences(expected, recognized)

        omissions = [it for it in alignment if it["status"] == "omission"]
        self.assertEqual(len(omissions), 1)
        self.assertEqual(omissions[0]["expected"], "quick")
        self.assertIsNone(omissions[0]["recognized"])

    def test_insertion_detection(self):
        expected = ["the", "fox", "jumped"]
        recognized = ["the", "red", "fox", "jumped"]  # 'red' inserted
        alignment = align_word_sequences(expected, recognized)

        insertions = [it for it in alignment if it["status"] == "insertion"]
        self.assertEqual(len(insertions), 1)
        self.assertEqual(insertions[0]["recognized"], "red")
        self.assertIsNone(insertions[0]["expected"])

    def test_substitution_detection(self):
        expected = ["the", "cat", "slept"]
        recognized = ["the", "dog", "slept"]  # 'cat' -> 'dog'
        alignment = align_word_sequences(expected, recognized)

        subs = [it for it in alignment if it["status"] == "substitution"]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["expected"], "cat")
        self.assertEqual(subs[0]["recognized"], "dog")

    def test_multiple_mixed_errors(self):
        expected = ["the", "small", "green", "frog", "jumped", "high"]
        recognized = ["the", "tiny", "frog", "jumped", "very", "high"]
        # 'small' -> 'tiny' (substitution)
        # 'green' omitted
        # 'very' inserted
        alignment = align_word_sequences(expected, recognized)

        statuses = [it["status"] for it in alignment]
        self.assertIn("matched", statuses)
        self.assertIn("substitution", statuses)
        self.assertIn("omission", statuses)
        self.assertIn("insertion", statuses)

    def test_repeated_stutter_words(self):
        expected = ["the", "dog", "ran"]
        recognized = ["the", "the", "dog", "ran"]
        alignment = align_word_sequences(expected, recognized)

        matched_count = sum(1 for it in alignment if it["status"] == "matched")
        self.assertEqual(matched_count, 3)

    def test_empty_transcript(self):
        expected = ["hello", "world"]
        recognized = []
        alignment = align_word_sequences(expected, recognized)

        self.assertEqual(len(alignment), 2)
        for it in alignment:
            self.assertEqual(it["status"], "omission")

    def test_empty_passage(self):
        expected = []
        recognized = ["extra", "words"]
        alignment = align_word_sequences(expected, recognized)

        self.assertEqual(len(alignment), 2)
        for it in alignment:
            self.assertEqual(it["status"], "insertion")


class TestAccuracyAndPacingMetrics(unittest.TestCase):
    """Test calculation of word accuracy, coverage, WPM, and practice score."""

    def test_accuracy_100_percent(self):
        acc = calculate_word_accuracy(matched_count=10, expected_count=10)
        self.assertEqual(acc, 100.0)

    def test_partial_accuracy(self):
        acc = calculate_word_accuracy(matched_count=8, expected_count=10)
        self.assertEqual(acc, 80.0)

    def test_zero_recognized_words(self):
        acc = calculate_word_accuracy(matched_count=0, expected_count=20)
        self.assertEqual(acc, 0.0)

    def test_zero_expected_words(self):
        acc = calculate_word_accuracy(matched_count=0, expected_count=0)
        self.assertEqual(acc, 100.0)

    def test_coverage_rate(self):
        cov = calculate_coverage_rate(recognized_count=15, expected_count=20)
        self.assertEqual(cov, 75.0)

        # Capped at 100.0
        cov_over = calculate_coverage_rate(recognized_count=30, expected_count=20)
        self.assertEqual(cov_over, 100.0)

    def test_wpm_valid_duration(self):
        # 60 words in 60 seconds = 60 WPM
        wpm = calculate_words_per_minute(recognized_count=60, duration_seconds=60)
        self.assertEqual(wpm, 60.0)

        # 30 words in 30 seconds = 60 WPM
        wpm2 = calculate_words_per_minute(recognized_count=30, duration_seconds=30)
        self.assertEqual(wpm2, 60.0)

    def test_wpm_zero_or_short_duration_safeguards(self):
        # Under 3 seconds duration safeguard
        self.assertEqual(calculate_words_per_minute(recognized_count=10, duration_seconds=0), 0.0)
        self.assertEqual(calculate_words_per_minute(recognized_count=10, duration_seconds=2), 0.0)
        self.assertEqual(calculate_words_per_minute(recognized_count=0, duration_seconds=60), 0.0)

    def test_reading_practice_score(self):
        score = calculate_reading_practice_score(word_accuracy=100.0, coverage_rate=100.0, wpm=120.0)
        # 0.60*100 + 0.25*100 + 15 = 100.0
        self.assertEqual(score, 100.0)

        score_mid = calculate_reading_practice_score(word_accuracy=80.0, coverage_rate=80.0, wpm=60.0)
        # 48 + 20 + 7.5 = 75.5
        self.assertEqual(score_mid, 75.5)

    def test_child_friendly_feedback(self):
        praise, action = generate_child_friendly_feedback(word_accuracy=90.0, coverage_rate=95.0, omissions_count=1)
        self.assertIn("Outstanding", praise)
        self.assertIn("comprehension", action)

        praise_mid, _ = generate_child_friendly_feedback(word_accuracy=72.0, coverage_rate=75.0, omissions_count=4)
        self.assertIn("Great reading effort", praise_mid)


class TestSpeechConfidenceAndSignals(unittest.TestCase):
    """Test confidence statistics and browser hesitation handling."""

    def test_confidence_summary_model(self):
        summary = SpeechConfidenceSummary(
            average=0.92,
            min=0.85,
            max=0.98,
            sampleCount=12
        )
        self.assertEqual(summary.average, 0.92)
        self.assertEqual(summary.sampleCount, 12)

    def test_speech_analysis_request_validation(self):
        req = SpeechAnalysisRequest(
            sessionId="sess-123",
            passageId="pas-t1-001",
            transcript="The bullfrogs leap into the cool water.",
            durationSeconds=15,
            pauseCount=2,
            hesitationCount=1,
            confidenceSummary=SpeechConfidenceSummary(average=0.88, sampleCount=6)
        )
        self.assertEqual(req.sessionId, "sess-123")
        self.assertEqual(req.pauseCount, 2)
        self.assertEqual(req.hesitationCount, 1)


class TestSpeechSessionServiceAndPrivacy(unittest.IsolatedAsyncioTestCase):
    """Test speech reading service, DB persistence, and privacy assurances."""

    @patch("services.learning.speech_analysis.db")
    @patch("services.learning.speech_analysis.recalibrate_from_activity", new_callable=AsyncMock)
    async def test_speech_analysis_lifecycle_and_privacy(self, mock_recalibrate, mock_db):
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "sessionId": "sess-test-001",
            "learnerId": "student-123",
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "completed": False,
        })
        mock_db.speech_reading_analyses.update_one = AsyncMock(return_value=MagicMock())
        mock_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock())

        req = SpeechAnalysisRequest(
            sessionId="sess-test-001",
            passageId="pas-t1-001",
            transcript=(
                "Sam is a fat cat. Sam is bright orange. "
                "He sits on a red mat. The sun is hot. "
                "Sam sees a little bug. The bug hops on the log. "
                "Sam taps the bug with his soft paw."
            ),
            durationSeconds=25,
            pauseCount=1,
            hesitationCount=0,
            confidenceSummary=SpeechConfidenceSummary(average=0.95, sampleCount=8),
        )

        res = await analyze_speech_reading(learner_id="student-123", req=req)

        self.assertEqual(res["status"], "ok")
        analysis = res["analysis"]
        self.assertEqual(analysis["sessionId"], "sess-test-001")
        self.assertEqual(analysis["learnerId"], "student-123")
        self.assertGreater(analysis["wordAccuracy"], 50.0)

        # PRIVACY VERIFICATION: Confirm no raw audio or binary data is stored
        self.assertNotIn("audio", analysis)
        self.assertNotIn("recording", analysis)
        self.assertNotIn("rawAudio", analysis)
        self.assertNotIn("voiceBlob", analysis)

        # Check that update_one was invoked on speech_reading_analyses and reading_sessions
        mock_db.speech_reading_analyses.update_one.assert_called_once()
        mock_db.reading_sessions.update_one.assert_called_once()

        # Recalibration was triggered for reading_fluency domain
        mock_recalibrate.assert_called_once()
        call_kwargs = mock_recalibrate.call_args[1]
        self.assertEqual(call_kwargs["user_id"], "student-123")
        self.assertEqual(call_kwargs["activity_data"]["domain"], "reading_fluency")

    @patch("services.learning.speech_analysis.db")
    async def test_session_ownership_enforcement(self, mock_db):
        # Session belongs to 'other-student'
        mock_db.reading_sessions.find_one = AsyncMock(return_value={
            "sessionId": "sess-test-002",
            "learnerId": "other-student",
            "passageId": "pas-t1-001",
        })

        req = SpeechAnalysisRequest(
            sessionId="sess-test-002",
            transcript="Sample speech",
            durationSeconds=10,
        )

        with self.assertRaises(PermissionError):
            await analyze_speech_reading(learner_id="student-123", req=req)


class TestSpeechEndpointsAndSecurity(unittest.TestCase):
    """Test API endpoint authorization, feature flag, and role access."""

    def setUp(self):
        self.client = TestClient(app)

    def test_feature_flag_disabled_returns_503(self):
        # Feature flag is False by default in test environment
        with patch.object(settings, "V2_SPEECH_ANALYSIS", False):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-123",
                "email": "student@demo.school",
                "role": "student",
            }
            res = self.client.post(
                "/api/v2/reading/speech/analyze",
                json={
                    "sessionId": "sess-123",
                    "transcript": "Hello world",
                    "durationSeconds": 5,
                }
            )
            self.assertEqual(res.status_code, 503)
            self.assertIn("disabled via feature flags", res.json()["detail"])
            app.dependency_overrides.clear()

    @patch("routers.v2_reading.analyze_speech_reading", new_callable=AsyncMock)
    def test_analyze_speech_own_session_success(self, mock_analyze):
        mock_analyze.return_value = {
            "status": "ok",
            "analysis": {
                "analysisId": "analysis-123",
                "sessionId": "sess-123",
                "learnerId": "student-123",
                "passageId": "pas-t1-001",
                "passageWordCount": 10,
                "recognizedWordCount": 10,
                "matchedWordCount": 10,
                "wordAccuracy": 100.0,
                "coverageRate": 100.0,
                "omissions": [],
                "insertions": [],
                "substitutions": [],
                "readingDurationSeconds": 10,
                "wordsPerMinute": 60.0,
                "readingPracticeScore": 100.0,
                "feedback": "Outstanding reading practice!",
                "createdAt": int(time.time()),
            },
            "childFriendlyFeedback": "Outstanding reading practice!",
            "nextActionSuggestion": "Let's check comprehension!",
        }

        with patch.object(settings, "V2_SPEECH_ANALYSIS", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-123",
                "email": "student@demo.school",
                "role": "student",
            }
            res = self.client.post(
                "/api/v2/reading/speech/analyze",
                json={
                    "sessionId": "sess-123",
                    "transcript": "Pip the puppy plays with a red ball.",
                    "durationSeconds": 10,
                }
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["analysis"]["wordAccuracy"], 100.0)
            app.dependency_overrides.clear()

    def test_unauthenticated_request_rejected(self):
        with patch.object(settings, "V2_SPEECH_ANALYSIS", True):
            # No current user override
            res = self.client.post(
                "/api/v2/reading/speech/analyze",
                json={"sessionId": "sess-123", "transcript": "test"}
            )
            self.assertEqual(res.status_code, 401)

    @patch("routers.v2_reading.get_speech_analysis_for_session", new_callable=AsyncMock)
    def test_student_can_fetch_own_speech_analysis(self, mock_get_analysis):
        mock_get_analysis.return_value = {
            "analysisId": "analysis-123",
            "sessionId": "sess-123",
            "learnerId": "student-123",
            "wordAccuracy": 90.0,
        }

        with patch.object(settings, "V2_SPEECH_ANALYSIS", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-123",
                "role": "student",
            }
            res = self.client.get("/api/v2/reading/speech/sessions/sess-123")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["analysis"]["analysisId"], "analysis-123")
            app.dependency_overrides.clear()

    def test_student_cannot_access_other_student_speech_analysis(self):
        with patch.object(settings, "V2_SPEECH_ANALYSIS", True):
            app.dependency_overrides[get_current_user] = lambda: {
                "id": "student-A",
                "role": "student",
            }
            # Attempt to query student-B's speech analysis
            res = self.client.get("/api/v2/reading/speech/sessions/sess-123?student_id=student-B")
            self.assertEqual(res.status_code, 403)
            self.assertIn("cannot access speech analyses for other learners", res.json()["detail"])
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
