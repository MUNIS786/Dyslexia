"""
backend/test_phase2_learner_profile.py — Comprehensive Unit & Integration Tests for Phase 2.
Tests all backend requirements specified in Step 22.
"""
import sys
import os
import unittest
import asyncio

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.learning.learner_profile_service import (
    normalize_to_educational_score,
    get_educational_interpretation,
    detect_strengths,
    detect_practice_areas,
    calculate_learning_level,
    calculate_profile_confidence,
    format_learner_profile_response,
    _normalize_goals,
)
from models.v2_learner_profile import (
    V2LearnerProfile,
    V2LearnerProfileUpdate,
    LearningLevelInfo,
    StrengthItem,
    PracticeAreaItem,
    ProfileConfidence,
)


class TestPhase2LearnerIntelligence(unittest.TestCase):

    def test_domain_normalization(self):
        """Test domain score normalization from impairment scale to 0-100 educational scale."""
        # 0 impairment -> 100 educational proficiency
        self.assertEqual(normalize_to_educational_score(0.0, is_impairment=True), 100.0)
        # 15 impairment (mild/low risk) -> 85 educational proficiency
        self.assertEqual(normalize_to_educational_score(15.0, is_impairment=True), 85.0)
        # 78 impairment (severe/high risk) -> 22 educational proficiency
        self.assertEqual(normalize_to_educational_score(78.0, is_impairment=True), 22.0)
        # 55 impairment -> 45 educational proficiency
        self.assertEqual(normalize_to_educational_score(55.0, is_impairment=True), 45.0)
        # Direct educational score (not impairment)
        self.assertEqual(normalize_to_educational_score(88.0, is_impairment=False), 88.0)
        # Clamping
        self.assertEqual(normalize_to_educational_score(150.0, is_impairment=True), 0.0)
        self.assertEqual(normalize_to_educational_score(-20.0, is_impairment=True), 100.0)

    def test_educational_interpretation_thresholds(self):
        """Test Step 3 educational interpretation labels and non-clinical thresholds."""
        # 90-100: Strong
        label, _ = get_educational_interpretation(95.0)
        self.assertEqual(label, "Strong")
        label, _ = get_educational_interpretation(90.0)
        self.assertEqual(label, "Strong")

        # 75-89: Strength
        label, _ = get_educational_interpretation(82.0)
        self.assertEqual(label, "Strength")
        label, _ = get_educational_interpretation(75.0)
        self.assertEqual(label, "Strength")

        # 60-74: Progressing
        label, _ = get_educational_interpretation(68.0)
        self.assertEqual(label, "Progressing")
        label, _ = get_educational_interpretation(60.0)
        self.assertEqual(label, "Progressing")

        # 40-59: Developing
        label, _ = get_educational_interpretation(48.0)
        self.assertEqual(label, "Developing")
        label, _ = get_educational_interpretation(40.0)
        self.assertEqual(label, "Developing")

        # 0-39: Needs Practice
        label, _ = get_educational_interpretation(32.0)
        self.assertEqual(label, "Needs Practice")
        label, _ = get_educational_interpretation(0.0)
        self.assertEqual(label, "Needs Practice")

    def test_strength_detection(self):
        """Test Step 4 data-driven strength detection and child-friendly framing."""
        domain_scores = {
            "reading_comprehension": 85.0,
            "visual_processing": 92.0,
            "phonological_awareness": 35.0,
            "reading_fluency": 45.0,
            "working_memory": 78.0,
            "rapid_naming": 62.0,
        }

        strengths = detect_strengths(domain_scores, limit=3)
        self.assertLessEqual(len(strengths), 3)

        # Top strengths should be visual_processing (92.0), reading_comprehension (85.0), working_memory (78.0)
        self.assertEqual(strengths[0]["domain"], "visual_processing")
        self.assertEqual(strengths[0]["score"], 92.0)
        self.assertEqual(strengths[0]["label"], "Strong")
        self.assertIn("visual superpowers", strengths[0]["description"].lower())

        self.assertEqual(strengths[1]["domain"], "reading_comprehension")
        self.assertEqual(strengths[1]["score"], 85.0)
        self.assertEqual(strengths[1]["label"], "Strength")

        self.assertEqual(strengths[2]["domain"], "working_memory")
        self.assertEqual(strengths[2]["score"], 78.0)

    def test_practice_areas_detection(self):
        """Test Step 5 data-driven areas for practice (constructive framing, priorities, activities)."""
        domain_scores = {
            "reading_comprehension": 85.0,
            "visual_processing": 92.0,
            "phonological_awareness": 35.0,
            "reading_fluency": 48.0,
            "working_memory": 70.0,
            "rapid_naming": 52.0,
        }

        areas = detect_practice_areas(domain_scores, limit=4)
        self.assertLessEqual(len(areas), 4)

        # Priority 1: lowest score (phonological_awareness: 35.0 -> high priority)
        self.assertEqual(areas[0]["domain"], "phonological_awareness")
        self.assertEqual(areas[0]["score"], 35.0)
        self.assertEqual(areas[0]["priority"], "high")
        self.assertEqual(areas[0]["suggested_activity_type"], "phoneme_blending")

        # Priority 2: reading_fluency: 48.0 -> medium priority
        self.assertEqual(areas[1]["domain"], "reading_fluency")
        self.assertEqual(areas[1]["score"], 48.0)
        self.assertEqual(areas[1]["priority"], "medium")
        self.assertEqual(areas[1]["suggested_activity_type"], "guided_reading")

        # Priority 3: rapid_naming: 52.0 -> medium priority
        self.assertEqual(areas[2]["domain"], "rapid_naming")
        self.assertEqual(areas[2]["score"], 52.0)
        self.assertEqual(areas[2]["priority"], "medium")

    def test_learning_level_calculation(self):
        """Test Step 6 deterministic educational learning level calculation (1 to 5)."""
        reading_metrics = {"avg_words_per_minute": 65.0, "comprehension_level": 70}

        # Level 1: Foundation (all low scores)
        low_scores = {
            "phonological_awareness": 25.0,
            "reading_comprehension": 30.0,
            "reading_fluency": 20.0,
            "orthographic_spelling": 25.0,
            "working_memory": 35.0,
            "visual_processing": 40.0,
        }
        res_l1 = calculate_learning_level(low_scores, reading_metrics)
        self.assertEqual(res_l1["level"], 1)
        self.assertEqual(res_l1["name"], "Foundation")

        # Level 2: Developing (scores around 45-50)
        dev_scores = {
            "phonological_awareness": 45.0,
            "reading_comprehension": 50.0,
            "reading_fluency": 40.0,
            "orthographic_spelling": 48.0,
            "working_memory": 52.0,
            "visual_processing": 50.0,
        }
        res_l2 = calculate_learning_level(dev_scores, reading_metrics)
        self.assertEqual(res_l2["level"], 2)
        self.assertEqual(res_l2["name"], "Developing")

        # Level 3: Progressing (scores around 60-65)
        prog_scores = {
            "phonological_awareness": 60.0,
            "reading_comprehension": 65.0,
            "reading_fluency": 62.0,
            "orthographic_spelling": 58.0,
            "working_memory": 64.0,
            "visual_processing": 70.0,
        }
        res_l3 = calculate_learning_level(prog_scores, reading_metrics)
        self.assertEqual(res_l3["level"], 3)
        self.assertEqual(res_l3["name"], "Progressing")

        # Level 4: Independent (scores around 75-80)
        ind_scores = {
            "phonological_awareness": 75.0,
            "reading_comprehension": 80.0,
            "reading_fluency": 72.0,
            "orthographic_spelling": 78.0,
            "working_memory": 76.0,
            "visual_processing": 82.0,
        }
        res_l4 = calculate_learning_level(ind_scores, reading_metrics)
        self.assertEqual(res_l4["level"], 4)
        self.assertEqual(res_l4["name"], "Independent")

        # Level 5: Advanced (scores around 90+)
        adv_scores = {
            "phonological_awareness": 90.0,
            "reading_comprehension": 92.0,
            "reading_fluency": 88.0,
            "orthographic_spelling": 94.0,
            "working_memory": 88.0,
            "visual_processing": 95.0,
        }
        res_l5 = calculate_learning_level(adv_scores, reading_metrics)
        self.assertEqual(res_l5["level"], 5)
        self.assertEqual(res_l5["name"], "Advanced")

    def test_profile_confidence(self):
        """Test Step 7 profile confidence computation based on empirical evidence."""
        # Unscreened user with no progress -> confidence is 0.0
        conf_empty = calculate_profile_confidence(
            answers_count=0,
            scored_domains_count=0,
            progress_doc={},
            screening_completed=False,
        )
        self.assertEqual(conf_empty["overall"], 0.0)
        self.assertEqual(conf_empty["screening"], 0.0)

        # Full screening battery completed (20 questions, 10 domains) + some progress
        progress_mock = {"sessionCount": 10, "wordsRead": 2500, "tasksCompleted": 5}
        conf_full = calculate_profile_confidence(
            answers_count=20,
            scored_domains_count=10,
            progress_doc=progress_mock,
            screening_completed=True,
        )
        self.assertGreater(conf_full["overall"], 0.70)
        self.assertEqual(conf_full["screening"], 1.0)
        self.assertGreater(conf_full["performance"], 0.40)

    def test_goal_normalization(self):
        """Test goal normalization across legacy string lists and structured objects."""
        # None -> returns standard defaults
        default_goals = _normalize_goals(None)
        self.assertEqual(len(default_goals), 3)
        self.assertFalse(default_goals[0]["completed"])

        # String list -> converted to structured GoalItem dicts
        str_goals = ["Read for 15 minutes", "Practice phonics words"]
        norm = _normalize_goals(str_goals)
        self.assertEqual(len(norm), 2)
        self.assertEqual(norm[0]["title"], "Read for 15 minutes")
        self.assertFalse(norm[0]["completed"])

        # Dict list with completion state preserved
        dict_goals = [
            {"id": "g-1", "title": "Finish chapter 2", "completed": True},
            {"id": "g-2", "title": "Review spelling", "completed": False},
        ]
        norm_dicts = _normalize_goals(dict_goals)
        self.assertTrue(norm_dicts[0]["completed"])
        self.assertFalse(norm_dicts[1]["completed"])

    def test_profile_formatting_for_frontend(self):
        """Test Step 10 frontend-friendly profile formatting (no raw Mongo internals)."""
        raw_doc = {
            "learnerId": "user-uuid-123",
            "displayName": "Aarav",
            "schemaVersion": 2,
            "screeningCompleted": True,
            "learningLevel": {"level": 3, "name": "Progressing", "description": "Doing well"},
            "domainScores": {"phonological_awareness": 75.0, "reading_fluency": 60.0},
            "domainInterpretations": {
                "phonological_awareness": {"score": 75.0, "label": "Strength"}
            },
            "strengths": [{"domain": "reading_comprehension", "score": 85.0}],
            "areasForPractice": [{"domain": "phonological_awareness", "score": 45.0}],
            "preferredLearningModes": ["Visual", "Interactive"],
            "accessibilityPreferences": {"font": "OpenDyslexic", "fontSize": 20},
            "confidence": {"overall": 0.82, "screening": 0.90, "performance": 0.65},
            "metadata": {"profile_version": 2, "source": "screening"},
            "_id": "60c72b2f9b1d8b2bad000001",  # Mongo ObjectId to be excluded
        }
        user_mock = {"id": "user-uuid-123", "name": "Aarav", "languages": ["english"]}

        formatted = format_learner_profile_response(raw_doc, user_mock)

        # Ensure Mongo _id is NOT in the formatted output
        self.assertNotIn("_id", formatted)
        # Ensure learner identity is cleanly exposed
        self.assertEqual(formatted["learner"]["id"], "user-uuid-123")
        self.assertEqual(formatted["learner"]["name"], "Aarav")
        # Ensure learning level is present
        self.assertEqual(formatted["learning_level"]["level"], 3)
        self.assertEqual(formatted["learning_level"]["name"], "Progressing")
        # Ensure domain scores and preferences are formatted
        self.assertIn("domain_scores", formatted)
        self.assertEqual(formatted["preferences"]["font"], "OpenDyslexic")
        # Ensure non-diagnostic disclaimer is present
        self.assertIn("disclaimer", formatted)
        self.assertIn("does not constitute a medical", formatted["disclaimer"].lower())


if __name__ == "__main__":
    unittest.main()
