"""
backend/services/learning/reading_performance.py — Reading Performance Engine.

Calculates transparent, objective metrics for reading sessions:
- comprehensionScore (accuracy on comprehension questions)
- completionRate (proportion of words/passage completed)
- timeEfficiency (pacing metric without punishing careful readers)
- readingScore (composite reading engagement & completion score)
- overallScore (transparent weighted composite: comprehension, completion, engagement)
- recentReadingPerformance & trend analysis across historical sessions

IMPORTANT SAFETY & EDUCATIONAL BOUNDARIES:
This module provides educational practice indicators to assist instructional tailoring.
It does NOT evaluate clinical dyslexia severity, cognitive intelligence, or medical status.
Browser TTS playback is recognized as an assistive modality, not an indicator of reading deficit.
"""
import math
from typing import List, Dict, Any, Optional, Tuple


def calculate_comprehension_score(correct: int, total: int) -> float:
    """
    Calculates percentage accuracy on comprehension questions.
    Protects against division by zero if a passage has no questions.
    """
    if total <= 0:
        return 100.0
    correct = max(0, min(correct, total))
    return round((float(correct) / float(total)) * 100.0, 1)


def calculate_completion_rate(words_read: int, words_presented: int) -> float:
    """
    Calculates proportion of passage words read/viewed.
    """
    if words_presented <= 0:
        return 100.0
    words_read = max(0, min(words_read, words_presented))
    return round((float(words_read) / float(words_presented)) * 100.0, 1)


def calculate_time_efficiency(
    duration_seconds: int,
    word_count: int,
    difficulty_tier: int = 1
) -> float:
    """
    Computes a gentle pacing metric (0-100) based on expected reading duration.
    Expected reading speeds by tier (words per minute for supported readers):
      Tier 1: 30-60 wpm
      Tier 2: 50-80 wpm
      Tier 3: 70-110 wpm
      Tier 4: 90-130 wpm
      Tier 5: 110-160 wpm
    Careful, slower reading is NEVER severely penalized.
    """
    if word_count <= 0 or duration_seconds <= 0:
        return 75.0

    wpm = (float(word_count) / float(duration_seconds)) * 60.0
    tier_target_wpm = {
        1: 45.0,
        2: 65.0,
        3: 85.0,
        4: 105.0,
        5: 130.0,
    }.get(difficulty_tier, 65.0)

    # Ratio of actual to target speed
    ratio = wpm / tier_target_wpm

    # Pacing score: optimal between 0.6x and 1.4x of target
    if 0.5 <= ratio <= 1.8:
        return 95.0
    elif 0.3 <= ratio < 0.5:
        return 85.0  # Deliberate, careful reading
    elif ratio > 1.8:
        return 80.0  # Very fast skim
    else:
        return 70.0


def calculate_overall_score(
    comprehension_score: float,
    completion_rate: float,
    time_efficiency: float,
    completed: bool = True,
    skipped: bool = False,
    hints_used: int = 0,
    words_practiced_count: int = 0
) -> float:
    """
    Calculates transparent overall score:
    - 60% Comprehension Accuracy
    - 25% Completion Rate
    - 15% Pacing & Practice Engagement (bonus for practicing tricky words)
    Penalizes skipped or abandoned sessions gracefully.
    """
    if skipped:
        return 20.0
    if not completed:
        return round(max(10.0, completion_rate * 0.4), 1)

    # Small bonus for active practice (up to +5%)
    practice_bonus = min(5.0, words_practiced_count * 1.5)

    # Gentle hint deduction: 1.5% per hint, max 6%
    hint_penalty = min(6.0, hints_used * 1.5)

    weighted = (
        0.60 * comprehension_score +
        0.25 * completion_rate +
        0.15 * time_efficiency +
        practice_bonus -
        hint_penalty
    )

    return round(max(0.0, min(100.0, weighted)), 1)


def grade_comprehension_answers(
    questions: List[Dict[str, Any]],
    user_answers: Dict[str, Any]
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Server-side verification of comprehension answers.
    Returns (correct_count, total_count, detailed_evaluations).
    Never trusts client-reported scores.
    """
    total = len(questions)
    if total == 0:
        return 0, 0, []

    correct_count = 0
    evaluations = []

    for q in questions:
        qid = str(q.get("questionId", ""))
        user_ans = user_answers.get(qid)
        correct_ans = q.get("correctAnswer")
        options = q.get("options", [])

        is_correct = False
        if user_ans is not None:
            # Handle numeric option index or matching option text
            if isinstance(correct_ans, int):
                if isinstance(user_ans, int) and user_ans == correct_ans:
                    is_correct = True
                elif isinstance(user_ans, str) and 0 <= correct_ans < len(options) and user_ans.strip().lower() == options[correct_ans].strip().lower():
                    is_correct = True
            elif isinstance(correct_ans, str):
                if str(user_ans).strip().lower() == correct_ans.strip().lower():
                    is_correct = True
                elif isinstance(user_ans, int) and 0 <= user_ans < len(options) and options[user_ans].strip().lower() == correct_ans.strip().lower():
                    is_correct = True

        if is_correct:
            correct_count += 1

        evaluations.append({
            "questionId": qid,
            "isCorrect": is_correct,
            "userAnswer": user_ans,
            "correctAnswer": correct_ans,
            "explanation": q.get("explanation", ""),
            "questionType": q.get("questionType", "detail"),
        })

    return correct_count, total, evaluations


def analyze_reading_trend(recent_scores: List[float]) -> str:
    """
    Determines student reading trajectory based on rolling scores:
    - 'improving': steady positive slope (+8% across sessions)
    - 'needs_support': rolling scores consistently < 60%
    - 'steady': consistent solid performance
    """
    if len(recent_scores) < 2:
        return "steady"

    recent = recent_scores[-5:]
    if len(recent) >= 3:
        first_half = sum(recent[:2]) / 2.0
        second_half = sum(recent[-2:]) / 2.0
        if second_half - first_half >= 8.0:
            return "improving"
        elif first_half - second_half >= 15.0 and second_half < 60.0:
            return "needs_support"

    avg = sum(recent) / len(recent)
    if avg < 55.0:
        return "needs_support"

    return "steady"
