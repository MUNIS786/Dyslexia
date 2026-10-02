"""
backend/services/learning/speech_analysis.py — Deterministic Speech & Reading Analysis Service.

Provides:
- Robust text normalization (lowercase, whitespace, punctuation handling)
- Deterministic Dynamic Programming sequence alignment (Levenshtein token alignment)
- Word-level accuracy, coverage rate, omission/insertion/substitution detection
- Pacing metrics: Words Per Minute (WPM) with zero/short duration safeguards
- Confidence handling and pause/hesitation tracking
- Privacy-first persistence: stores strictly derived metrics; NO raw audio stored.

IMPORTANT:
This service produces educational reading practice signals.
It is NOT a medical or neuropsychological diagnostic tool for dyslexia or speech disorders.
"""
import re
import time
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional

from database.database import db
from models.v2_speech_analysis import (
    SpeechAnalysisRequest,
    SpeechReadingAnalysis,
    SpeechConfidenceSummary,
)
from services.learning.reading_service import get_passage_by_id
from services.learning.learner_profile_service import recalibrate_from_activity

logger = logging.getLogger("dyslexaid.speech_analysis")


# ─── 1. Text Normalization ───────────────────────────────────────────────────

def normalize_text_to_tokens(text: Optional[str]) -> List[str]:
    """
    Normalizes a text string into an ordered list of clean word tokens.
    Rules:
    - Lowercases text
    - Replaces punctuation with whitespace (preserving apostrophes inside contractions like don't)
    - Normalizes multi-whitespace
    - Trims leading/trailing apostrophes
    - Returns empty list for None, empty, or whitespace-only strings.
    """
    if not text or not isinstance(text, str):
        return []

    # Lowercase
    cleaned = text.lower().strip()
    if not cleaned:
        return []

    # Replace Devanagari punctuation (Danda । and Double Danda ॥) with spaces
    cleaned = re.sub(r"[\u0964\u0965]", " ", cleaned)

    # Replace punctuation characters (including underscore) except apostrophe with spaces
    # Preserves Latin word characters, digits, apostrophes, and Devanagari script (\u0900-\u097F)
    cleaned = re.sub(r"[^\w\s'\u0900-\u097F]|_", " ", cleaned)

    tokens: List[str] = []
    for raw in cleaned.split():
        # Strip extraneous quotes/apostrophes from token edges (e.g. 'hello' -> hello)
        token = raw.strip("'\"")
        if token:
            tokens.append(token)

    return tokens


# ─── 2. Sequence Alignment (Dynamic Programming) ─────────────────────────────

def align_word_sequences(
    expected_tokens: List[str],
    recognized_tokens: List[str]
) -> List[Dict[str, Any]]:
    """
    Performs deterministic dynamic-programming sequence alignment between expected
    and recognized word sequences.

    Returns an ordered list of alignment items:
    [
        {"expected": "the", "recognized": "the", "status": "matched"},
        {"expected": "dog", "recognized": "cat", "status": "substitution"},
        {"expected": "quick", "recognized": None, "status": "omission"},
        {"expected": None, "recognized": "very", "status": "insertion"},
    ]
    """
    m = len(expected_tokens)
    n = len(recognized_tokens)

    # Edge cases
    if m == 0 and n == 0:
        return []
    if m == 0:
        return [{"expected": None, "recognized": r, "status": "insertion"} for r in recognized_tokens]
    if n == 0:
        return [{"expected": e, "recognized": None, "status": "omission"} for e in expected_tokens]

    # Costs
    COST_MATCH = 0.0
    COST_SUB = 1.0
    COST_OMISSION = 1.0
    COST_INSERTION = 1.0

    # DP Table: dp[i][j] is the minimum cost to align expected[0..i-1] with recognized[0..j-1]
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = i * COST_OMISSION
    for j in range(1, n + 1):
        dp[0][j] = j * COST_INSERTION

    for i in range(1, m + 1):
        e_word = expected_tokens[i - 1]
        for j in range(1, n + 1):
            r_word = recognized_tokens[j - 1]

            if e_word == r_word:
                dp[i][j] = dp[i - 1][j - 1] + COST_MATCH
            else:
                cost_sub = dp[i - 1][j - 1] + COST_SUB
                cost_om = dp[i - 1][j] + COST_OMISSION
                cost_in = dp[i][j - 1] + COST_INSERTION
                dp[i][j] = min(cost_sub, cost_om, cost_in)

    # Backtracking to reconstruct the optimal alignment
    alignment: List[Dict[str, Any]] = []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            e_word = expected_tokens[i - 1]
            r_word = recognized_tokens[j - 1]

            if e_word == r_word and dp[i][j] == dp[i - 1][j - 1]:
                alignment.append({"expected": e_word, "recognized": r_word, "status": "matched"})
                i -= 1
                j -= 1
                continue

            # Check substitution
            if dp[i][j] == dp[i - 1][j - 1] + COST_SUB:
                alignment.append({"expected": e_word, "recognized": r_word, "status": "substitution"})
                i -= 1
                j -= 1
                continue

        # Check omission (deletion from expected)
        if i > 0 and dp[i][j] == dp[i - 1][j] + COST_OMISSION:
            alignment.append({"expected": expected_tokens[i - 1], "recognized": None, "status": "omission"})
            i -= 1
            continue

        # Check insertion (addition in recognized)
        if j > 0 and dp[i][j] == dp[i][j - 1] + COST_INSERTION:
            alignment.append({"expected": None, "recognized": recognized_tokens[j - 1], "status": "insertion"})
            j -= 1
            continue

        # Safety fallback
        if i > 0 and j > 0:
            alignment.append({"expected": expected_tokens[i - 1], "recognized": recognized_tokens[j - 1], "status": "substitution"})
            i -= 1
            j -= 1
        elif i > 0:
            alignment.append({"expected": expected_tokens[i - 1], "recognized": None, "status": "omission"})
            i -= 1
        else:
            alignment.append({"expected": None, "recognized": recognized_tokens[j - 1], "status": "insertion"})
            j -= 1

    alignment.reverse()
    return alignment


# ─── 3. Metric Calculations ──────────────────────────────────────────────────

def calculate_word_accuracy(matched_count: int, expected_count: int) -> float:
    """
    Computes word accuracy as percentage of expected words accurately spoken.
    Safeguards against zero expected words.
    """
    if expected_count <= 0:
        return 100.0 if matched_count == 0 else 0.0
    return round((matched_count / float(expected_count)) * 100.0, 1)


def calculate_coverage_rate(recognized_count: int, expected_count: int) -> float:
    """
    Computes coverage rate as percentage of the expected passage attempted.
    Capped at 100.0.
    """
    if expected_count <= 0:
        return 100.0 if recognized_count == 0 else 0.0
    rate = (recognized_count / float(expected_count)) * 100.0
    return round(min(100.0, rate), 1)


def calculate_words_per_minute(recognized_count: int, duration_seconds: int) -> float:
    """
    Computes observed Words Per Minute (WPM).
    Safeguards:
    - Duration under 3 seconds returns 0.0 WPM
    - Zero recognized words returns 0.0 WPM
    - Realistic maximum cap of 300.0 WPM to prevent artificial spikes.
    """
    if duration_seconds < 3 or recognized_count <= 0:
        return 0.0
    duration_minutes = duration_seconds / 60.0
    wpm = recognized_count / duration_minutes
    return round(min(300.0, wpm), 1)


def calculate_reading_practice_score(
    word_accuracy: float,
    coverage_rate: float,
    wpm: float
) -> float:
    """
    Transparent educational practice score formula:
    - 60% Word Alignment Accuracy
    - 25% Coverage of the Passage
    - 15% Fluency Pace (scaled against comfortable reading pace of ~120 WPM)
    Capped between 0.0 and 100.0.
    """
    pace_component = min(15.0, (wpm / 120.0) * 15.0)
    score = (0.60 * word_accuracy) + (0.25 * coverage_rate) + pace_component
    return round(max(0.0, min(100.0, score)), 1)


def generate_child_friendly_feedback(
    word_accuracy: float,
    coverage_rate: float,
    omissions_count: int
) -> Tuple[str, str]:
    """
    Generates encouraging, non-stigmatizing child-facing feedback and a next action suggestion.
    """
    if word_accuracy >= 85.0:
        praise = "Outstanding reading practice! 🌟 You read almost all of the passage clearly."
        action = "You are doing wonderfully! Let's check your understanding with comprehension questions."
    elif word_accuracy >= 70.0:
        praise = "Great reading effort! ✨ You read most of the words accurately and fluently."
        action = "Terrific practice! Let's answer the questions to see how much you remembered."
    elif word_accuracy >= 50.0:
        praise = "Good try reading aloud! 🌱 Every practice makes your reading brain stronger."
        action = "Let's review the tricky words together, or continue to the comprehension questions."
    else:
        praise = "Nice effort practicing! 💫 Reading aloud takes courage and practice."
        action = "Feel free to try reading aloud again, or listen along with audio."

    return praise, action


# ─── 4. Speech Analysis Execution & Persistence ──────────────────────────────

async def analyze_speech_reading(
    learner_id: str,
    req: SpeechAnalysisRequest
) -> Dict[str, Any]:
    """
    Coordinates authoritative server-side speech analysis:
    1. Validates reading session existence and student ownership.
    2. Retrieves expected passage text.
    3. Normalizes expected and transcribed text.
    4. Computes DP sequence alignment.
    5. Calculates word accuracy, coverage, WPM, and reading practice score.
    6. Persists derived analysis to db.speech_reading_analyses (NO raw audio stored).
    7. Updates parent reading session in db.reading_sessions.
    8. Recalibrates learner profile reading_fluency domain.
    """
    now = int(time.time())

    # 1. Fetch and validate reading session
    session = await db.reading_sessions.find_one({"sessionId": req.sessionId})
    if not session:
        raise ValueError(f"Reading session '{req.sessionId}' not found.")

    if session.get("learnerId") != learner_id:
        raise PermissionError("Access denied: You do not own this reading session.")

    # 2. Fetch passage
    passage_id = req.passageId or session.get("passageId")
    passage = await get_passage_by_id(passage_id)
    if not passage:
        raise ValueError(f"Passage '{passage_id}' could not be located.")

    expected_text = passage.get("text", "")

    # 3. Normalization
    expected_tokens = normalize_text_to_tokens(expected_text)
    recognized_tokens = normalize_text_to_tokens(req.transcript)

    # 4. Sequence Alignment
    alignment = align_word_sequences(expected_tokens, recognized_tokens)

    # 5. Extract metrics
    matched_count = sum(1 for item in alignment if item["status"] == "matched")
    omissions = [item["expected"] for item in alignment if item["status"] == "omission"]
    insertions = [item["recognized"] for item in alignment if item["status"] == "insertion"]
    substitutions = [
        {"expected": item["expected"], "recognized": item["recognized"]}
        for item in alignment if item["status"] == "substitution"
    ]

    expected_count = len(expected_tokens)
    recognized_count = len(recognized_tokens)

    word_accuracy = calculate_word_accuracy(matched_count, expected_count)
    coverage_rate = calculate_coverage_rate(recognized_count, expected_count)
    wpm = calculate_words_per_minute(recognized_count, req.durationSeconds)
    practice_score = calculate_reading_practice_score(word_accuracy, coverage_rate, wpm)

    feedback_msg, next_action = generate_child_friendly_feedback(
        word_accuracy=word_accuracy,
        coverage_rate=coverage_rate,
        omissions_count=len(omissions)
    )

    # Optional confidence summary handling
    confidence_data = None
    if req.confidenceSummary:
        confidence_data = (
            req.confidenceSummary.model_dump()
            if hasattr(req.confidenceSummary, "model_dump")
            else req.confidenceSummary.dict()
        )

    analysis_id = str(uuid.uuid4())

    analysis_doc = {
        "analysisId": analysis_id,
        "sessionId": req.sessionId,
        "learnerId": learner_id,
        "passageId": passage_id,
        "passageWordCount": expected_count,
        "recognizedWordCount": recognized_count,
        "matchedWordCount": matched_count,
        "wordAccuracy": word_accuracy,
        "coverageRate": coverage_rate,
        "omissions": omissions[:25],  # Cap list size for storage efficiency
        "insertions": insertions[:25],
        "substitutions": substitutions[:25],
        "hesitationCount": req.hesitationCount,
        "pauseCount": req.pauseCount,
        "readingDurationSeconds": req.durationSeconds,
        "wordsPerMinute": wpm,
        "confidenceSummary": confidence_data,
        "readingPracticeScore": practice_score,
        "alignmentSummary": alignment[:80],  # First 80 words for UI token display
        "feedback": feedback_msg,
        "analysisVersion": "1.0",
        "createdAt": now,
    }

    # 6. Save derived analysis (strictly NO raw audio)
    await db.speech_reading_analyses.update_one(
        {"sessionId": req.sessionId},
        {"$set": analysis_doc},
        upsert=True
    )

    # 7. Update parent reading session with speech signals
    session_speech_update = {
        "readingMode": "speech",
        "speechAnalysisId": analysis_id,
        "speechWordAccuracy": word_accuracy,
        "speechCoverageRate": coverage_rate,
        "speechWordsPerMinute": wpm,
        "speechPracticeScore": practice_score,
        "speechDurationSeconds": req.durationSeconds,
        "updatedAt": now,
    }
    await db.reading_sessions.update_one(
        {"sessionId": req.sessionId},
        {"$set": session_speech_update}
    )

    # 8. Recalibrate learner profile reading_fluency domain
    try:
        await recalibrate_from_activity(
            user_id=learner_id,
            activity_data={
                "domain": "reading_fluency",
                "score": practice_score,
                "tier": session.get("difficulty", 1),
                "hesitationCount": req.hesitationCount or 0,
                "hintsRequested": 0,
            }
        )
    except Exception as e:
        logger.warning(f"Learner profile speech recalibration warning for user {learner_id}: {e}")

    analysis_model = SpeechReadingAnalysis(**analysis_doc)
    dumped_analysis = (
        analysis_model.model_dump()
        if hasattr(analysis_model, "model_dump")
        else analysis_model.dict()
    )

    return {
        "status": "ok",
        "analysis": dumped_analysis,
        "childFriendlyFeedback": feedback_msg,
        "nextActionSuggestion": next_action,
    }


async def get_speech_analysis_for_session(
    session_id: str,
    learner_id: str,
    is_teacher: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Retrieves the speech analysis record for a given session.
    Enforces authorization: students can only access their own records.
    """
    query = {"sessionId": session_id}
    if not is_teacher:
        query["learnerId"] = learner_id

    doc = await db.speech_reading_analyses.find_one(query, {"_id": 0})
    return doc
