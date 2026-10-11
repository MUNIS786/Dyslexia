#!/usr/bin/env python3
"""
scripts/test_edge_cases.py — Deep Edge-Case & Stress Tester for DyslexAid.
Tests corner cases, zero-division hazards, None-handling, and malformed inputs
across core engines and services.
"""
import sys
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

errors = []


def test_reading_performance_edge_cases():
    print("Testing reading_performance edge cases...")
    from services.learning.reading_performance import (
        calculate_comprehension_score,
        calculate_completion_rate,
        calculate_time_efficiency,
        calculate_overall_score,
        grade_comprehension_answers,
        analyze_reading_trend,
    )

    # 1. calculate_comprehension_score
    c0 = calculate_comprehension_score(0, 0)
    assert c0 == 100.0, f"Expected 100.0 for 0 total questions, got {c0}"
    c_neg = calculate_comprehension_score(-5, 10)
    assert c_neg == 0.0, f"Expected 0.0 for negative correct, got {c_neg}"
    c_over = calculate_comprehension_score(15, 10)
    assert c_over == 100.0, f"Expected 100.0 for correct > total, got {c_over}"

    # 2. calculate_completion_rate
    cr0 = calculate_completion_rate(0, 0)
    assert cr0 == 100.0, f"Expected 100.0 for 0 presented words, got {cr0}"
    cr_neg = calculate_completion_rate(-10, 50)
    assert cr_neg == 0.0, f"Expected 0.0 for negative words read, got {cr_neg}"
    cr_over = calculate_completion_rate(100, 50)
    assert cr_over == 100.0, f"Expected 100.0 for words_read > words_presented, got {cr_over}"

    # 3. calculate_time_efficiency
    te0 = calculate_time_efficiency(0, 50)
    assert te0 == 75.0, f"Expected 75.0 safe default for 0 duration, got {te0}"
    te_w0 = calculate_time_efficiency(60, 0)
    assert te_w0 == 75.0, f"Expected 75.0 safe default for 0 words, got {te_w0}"
    te_fast = calculate_time_efficiency(1, 1000)
    assert te_fast == 80.0, f"Expected 80.0 for extreme fast skim, got {te_fast}"
    te_slow = calculate_time_efficiency(10000, 10)
    assert te_slow == 70.0, f"Expected 70.0 for extreme slow, got {te_slow}"

    # 4. calculate_overall_score
    os_skip = calculate_overall_score(100.0, 100.0, 100.0, skipped=True)
    assert os_skip == 20.0, f"Expected 20.0 for skipped session, got {os_skip}"
    os_incomp = calculate_overall_score(100.0, 30.0, 100.0, completed=False)
    assert os_incomp == 12.0, f"Expected 12.0 for uncompleted session, got {os_incomp}"
    os_hints = calculate_overall_score(100.0, 100.0, 100.0, hints_used=10)
    assert os_hints <= 100.0, f"Expected score <= 100, got {os_hints}"

    # 5. grade_comprehension_answers
    corr, tot, evals = grade_comprehension_answers([], {})
    assert corr == 0 and tot == 0 and evals == [], "Expected empty evals for empty questions"

    questions = [
        {"questionId": "q1", "correctAnswer": 0, "options": ["A", "B", "C"]},
        {"questionId": "q2", "correctAnswer": "hello", "options": ["hi", "hello"]},
    ]
    # Test None answers
    c_none, t_none, evals_none = grade_comprehension_answers(questions, {})
    assert c_none == 0 and t_none == 2, "Expected 0 correct for empty user answers"

    # Test string matching numeric answer
    c_str, t_str, evals_str = grade_comprehension_answers(questions, {"q1": "A", "q2": "HELLO"})
    assert c_str == 2, f"Expected 2 correct for case-insensitive matching, got {c_str}"

    # 6. analyze_reading_trend
    assert analyze_reading_trend([]) == "steady"
    assert analyze_reading_trend([80.0]) == "steady"
    assert analyze_reading_trend([50.0, 50.0, 80.0, 85.0, 90.0]) == "improving"
    assert analyze_reading_trend([80.0, 80.0, 50.0, 40.0, 30.0]) == "needs_support"
    print("  [PASS] reading_performance edge cases passed.")


def test_speech_analysis_edge_cases():
    print("Testing speech_analysis edge cases...")
    from services.learning.speech_analysis import (
        normalize_text_to_tokens,
        align_word_sequences,
        calculate_word_accuracy,
        calculate_coverage_rate,
        calculate_words_per_minute,
        calculate_reading_practice_score,
        generate_child_friendly_feedback,
    )

    # 1. normalize_text_to_tokens
    assert normalize_text_to_tokens(None) == []
    assert normalize_text_to_tokens("") == []
    assert normalize_text_to_tokens("   \n\t   ") == []
    assert normalize_text_to_tokens("Don't say 'goodbye'!") == ["don't", "say", "goodbye"]
    # Devanagari punctuation
    assert normalize_text_to_tokens("नमस्ते दुनिया।") == ["नमस्ते", "दुनिया"]

    # 2. align_word_sequences
    assert align_word_sequences([], []) == []
    assert len(align_word_sequences(["cat", "dog"], [])) == 2
    assert len(align_word_sequences([], ["cat", "dog"])) == 2

    # Mixed matches, substitutions, insertions, omissions
    align = align_word_sequences(["the", "big", "cat"], ["the", "small", "cat", "runs"])
    statuses = [item["status"] for item in align]
    assert "matched" in statuses

    # 3. calculate_word_accuracy
    assert calculate_word_accuracy(0, 0) == 100.0
    assert calculate_word_accuracy(5, 0) == 0.0
    assert calculate_word_accuracy(10, 10) == 100.0
    assert calculate_word_accuracy(5, 10) == 50.0

    # 4. calculate_coverage_rate
    assert calculate_coverage_rate(0, 0) == 100.0
    assert calculate_coverage_rate(20, 10) == 100.0  # Capped at 100

    # 5. calculate_words_per_minute
    assert calculate_words_per_minute(10, 0) == 0.0  # Safeguard <3s
    assert calculate_words_per_minute(10, 2) == 0.0  # Safeguard <3s
    assert calculate_words_per_minute(0, 60) == 0.0  # 0 words
    assert calculate_words_per_minute(100, 60) == 100.0
    assert calculate_words_per_minute(1000, 60) == 300.0  # Capped at 300

    # 6. calculate_reading_practice_score
    assert calculate_reading_practice_score(100.0, 100.0, 120.0) == 100.0
    assert calculate_reading_practice_score(0.0, 0.0, 0.0) == 0.0

    # 7. generate_child_friendly_feedback
    p, a = generate_child_friendly_feedback(90.0, 95.0, 1)
    assert "🌟" in p or "Outstanding" in p
    print("  [PASS] speech_analysis edge cases passed.")


def test_difficulty_engine_edge_cases():
    print("Testing difficulty_engine edge cases...")
    from services.learning.difficulty_engine import (
        clamp_tier,
        get_tier_calibration,
        estimate_syllables,
        analyze_text_readability,
    )

    # 1. clamp_tier
    assert clamp_tier(-5) == 1
    assert clamp_tier(0) == 1
    assert clamp_tier(1) == 1
    assert clamp_tier(3) == 3
    assert clamp_tier(5) == 5
    assert clamp_tier(10) == 5
    assert clamp_tier("invalid") == 1
    assert clamp_tier(None) == 1

    # 2. get_tier_calibration
    cal1 = get_tier_calibration(1)
    cal5 = get_tier_calibration(5)
    assert cal1.tier == 1
    assert cal5.tier == 5

    # 3. estimate_syllables
    assert estimate_syllables("") == 1
    assert estimate_syllables("cat") >= 1
    assert estimate_syllables("beautiful") >= 2
    assert estimate_syllables("dyslexia") >= 3

    # 4. analyze_text_readability
    r_empty = analyze_text_readability("")
    assert r_empty["wordCount"] == 0
    assert r_empty["recommendedTier"] == 1

    r_simple = analyze_text_readability("The cat sat on the mat.")
    assert r_simple["wordCount"] == 6
    assert r_simple["recommendedTier"] in (1, 2)
    print("  [PASS] difficulty_engine edge cases passed.")


def test_screening_analyzer_edge_cases():
    print("Testing screening_analyzer edge cases...")
    from services.screening_analyzer import analyze_screening

    # 1. Empty answers list
    res_empty = analyze_screening([])
    assert "score" in res_empty
    assert res_empty["score"] == 0
    assert res_empty["level"] == "low"
    assert "confidence" in res_empty
    assert res_empty["confidence"] == 0

    # 2. Unknown question types
    res_unknown = analyze_screening([
        {"question_type": "unknown_question_xyz", "correct": False, "response_time_ms": 99999}
    ])
    assert "score" in res_unknown
    assert res_unknown["score"] == 0

    # 3. All correct answers
    res_perfect = analyze_screening([
        {"question_type": "phoneme_blending", "correct": True, "response_time_ms": 2000},
        {"question_type": "digit_span", "correct": True, "response_time_ms": 1500},
        {"question_type": "rapid_naming", "correct": True, "response_time_ms": 1200},
    ])
    assert res_perfect["score"] == 0
    assert res_perfect["level"] == "low"
    assert res_perfect["dominant_profile"] == "No significant indicators"

    # 4. All incorrect answers with high response times
    res_impaired = analyze_screening([
        {"question_type": "phoneme_blending", "correct": False, "response_time_ms": 9000},
        {"question_type": "phoneme_segmentation", "correct": False, "response_time_ms": 9000},
        {"question_type": "rhyme_detection", "correct": False, "response_time_ms": 8000},
    ])
    assert res_impaired["score"] > 30
    assert res_impaired["dominant_profile"] in ("Phonological Dyslexia", "Mixed Profile")
    print("  [PASS] screening_analyzer edge cases passed.")


def test_intervention_effectiveness_edge_cases():
    print("Testing intervention_effectiveness edge cases...")
    from services.analytics.intervention_effectiveness import (
        calculate_metric_comparison,
        BaselineMeasurement,
        FollowUpMeasurement,
    )

    base = BaselineMeasurement(
        metricName="reading_comprehension_accuracy",
        displayName="Reading Comprehension Accuracy",
        value=70.0,
        unit="%",
        scale="0-100%",
        source="reading_sessions",
        observationCount=3,
        status="sufficient",
        periodStart=500,
        periodEnd=1000,
    )

    follow = FollowUpMeasurement(
        interventionId="int_123",
        metricName="reading_comprehension_accuracy",
        displayName="Reading Comprehension Accuracy",
        value=85.0,
        unit="%",
        scale="0-100%",
        source="reading_sessions",
        observationCount=3,
        periodStart=1001,
        periodEnd=2000,
    )

    # 1. Normal positive improvement
    cmp = calculate_metric_comparison(base, follow, target_domain="reading_comprehension")
    assert cmp.status == "improved_on_measure"
    assert cmp.absoluteChange == 15.0

    # 2. Missing follow-up
    cmp_no_f = calculate_metric_comparison(base, None, target_domain="reading_comprehension")
    assert cmp_no_f.status == "insufficient_data"

    # 3. Missing baseline
    cmp_no_b = calculate_metric_comparison(None, follow, target_domain="reading_comprehension")
    assert cmp_no_b.status == "insufficient_data"

    # 4. Zero baseline
    base_zero = BaselineMeasurement(
        metricName="reading_speed_wpm",
        displayName="Reading Speed",
        value=0.0,
        unit="WPM",
        scale="0-300 WPM",
        source="speech_reading_analyses",
        observationCount=1,
        status="sufficient",
        periodStart=500,
        periodEnd=1000,
    )
    follow_speed = FollowUpMeasurement(
        interventionId="int_123",
        metricName="reading_speed_wpm",
        displayName="Reading Speed",
        value=50.0,
        unit="WPM",
        scale="0-300 WPM",
        source="speech_reading_analyses",
        observationCount=1,
        periodStart=1001,
        periodEnd=2000,
    )
    cmp_zero = calculate_metric_comparison(base_zero, follow_speed, target_domain="reading_fluency")
    assert cmp_zero.relativeChangePercent is None  # Safeguards against div-by-zero
    assert cmp_zero.absoluteChange == 50.0
    print("  [PASS] intervention_effectiveness edge cases passed.")


def test_learning_insights_trends():
    print("Testing learning_insights trend edge cases...")
    from services.learning.learning_insights import _calculate_trend
    from models.v2_learning_insights import TrendDirection

    # Both None
    t1 = _calculate_trend("acc", "%", None, None)
    assert t1.direction == TrendDirection.INSUFFICIENT_DATA

    # Prior None
    t2 = _calculate_trend("acc", "%", 80.0, None)
    assert t2.direction == TrendDirection.INSUFFICIENT_DATA

    # Current None
    t3 = _calculate_trend("acc", "%", None, 80.0)
    assert t3.direction == TrendDirection.INSUFFICIENT_DATA

    # Improving
    t4 = _calculate_trend("acc", "%", 85.0, 75.0, improving_threshold=3.0)
    assert t4.direction == TrendDirection.IMPROVING
    assert t4.change == 10.0

    # Declining
    t5 = _calculate_trend("acc", "%", 65.0, 75.0, improving_threshold=3.0)
    assert t5.direction == TrendDirection.NEEDS_ATTENTION

    # Stable within threshold
    t6 = _calculate_trend("acc", "%", 75.5, 75.0, improving_threshold=3.0)
    assert t6.direction == TrendDirection.STABLE

    # Lower is better (hesitation)
    t7 = _calculate_trend("hesitation", " count", 2.0, 6.0, improving_threshold=2.0, higher_is_better=False)
    assert t7.direction == TrendDirection.IMPROVING
    print("  [PASS] learning_insights trend calculations passed.")


def main():
    print("=" * 70)
    print("  DYSLEXAID COMPREHENSIVE EDGE-CASE TEST SUITE")
    print("=" * 70)
    test_reading_performance_edge_cases()
    test_speech_analysis_edge_cases()
    test_difficulty_engine_edge_cases()
    test_screening_analyzer_edge_cases()
    test_intervention_effectiveness_edge_cases()
    test_learning_insights_trends()
    print("=" * 70)
    print("  ALL EDGE-CASE TESTS COMPLETED SUCCESSFULLY (0 ERRORS)")
    print("=" * 70)


if __name__ == "__main__":
    main()
