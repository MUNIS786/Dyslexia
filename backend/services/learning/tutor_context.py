"""
backend/services/learning/tutor_context.py — Compact Deterministic Context Builder for V2 Personal AI Tutor.

Assembles a privacy-safe, compact snapshot of:
1. Learner Profile (Level, Adaptive Tier, Strengths, Practice Areas)
2. Active Reading Passage Context (Excerpt, Difficulty, Vocab Words)
3. Recent Reading & Speech Signals (Comprehension %, Accuracy %, WPM)
4. Useful Accessibility Preferences (Font, TTS speed)

Strict Privacy Constraints:
- Zero raw audio or audio recordings
- Zero passwords, tokens, JWTs, or unrelated database IDs
- Zero teacher private notes
- Compact payload size (< 1.5KB) to prevent model token bloat
"""
import logging
from typing import Optional, Dict, Any, List

from database.database import db
from models.v2_tutor import TutorContext, CompactPassageContext
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    get_learning_state,
)
from services.learning.reading_service import get_passage_by_id

logger = logging.getLogger("dyslexaid.tutor_context")

LEVEL_NAMES: Dict[int, str] = {
    1: "Foundation",
    2: "Developing",
    3: "Progressing",
    4: "Competent",
    5: "Mastering",
}


async def build_tutor_context(
    learner_id: str,
    active_passage_id: Optional[str] = None,
    active_word: Optional[str] = None,
) -> TutorContext:
    """
    Constructs a deterministic, compact, privacy-safe TutorContext object
    for an authenticated learner.
    """
    # 1. Fetch user basic info (display name only)
    display_name = "Student"
    accessibility_prefs: Dict[str, Any] = {}
    try:
        user = await db.users.find_one({"id": learner_id}, {"_id": 0, "name": 1, "settings": 1})
        if user:
            raw_name = user.get("name") or ""
            if raw_name.strip():
                display_name = raw_name.strip().split()[0]  # Just first name for friendly tone
            settings = user.get("settings") or {}
            accessibility_prefs = {
                "font": settings.get("font", "OpenDyslexic"),
                "fontSize": settings.get("fontSize", 18),
                "ttsSpeed": settings.get("ttsSpeed", 0.85),
            }
    except Exception as e:
        logger.warning(f"Error fetching user metadata for tutor context: {e}")

    # 2. Fetch Learner Profile & Adaptive Tier
    learning_level = 2
    adaptive_tier = 1
    strengths: List[str] = []
    practice_areas: List[str] = []

    try:
        profile = await get_or_create_learner_profile(learner_id)
        if profile:
            level_info = profile.get("learning_level") or profile.get("learningLevel") or {}
            learning_level = int(level_info.get("level") or 2)
            
            raw_strengths = profile.get("strengths") or []
            strengths = [s.get("friendly_name") or s.get("domain") for s in raw_strengths if isinstance(s, dict)]
            if not strengths:
                strengths = [str(s) for s in raw_strengths if isinstance(s, str)]

            raw_practice = profile.get("practice_areas") or profile.get("practiceAreas") or []
            practice_areas = [p.get("friendly_name") or p.get("domain") for p in raw_practice if isinstance(p, dict)]
            if not practice_areas:
                practice_areas = [str(p) for p in raw_practice if isinstance(p, str)]
    except Exception as e:
        logger.warning(f"Error fetching learner profile for tutor context: {e}")

    try:
        state = await get_learning_state(learner_id)
        if state:
            adaptive_tier = int(state.get("active_difficulty_tier", 1))
    except Exception as e:
        logger.warning(f"Error fetching learning state for tutor context: {e}")

    # Clamp bounds safely
    learning_level = max(1, min(5, learning_level))
    adaptive_tier = max(1, min(5, adaptive_tier))
    learning_level_name = LEVEL_NAMES.get(learning_level, "Developing")

    # 3. Active Reading Passage Context (Compact)
    compact_passage: Optional[CompactPassageContext] = None
    if active_passage_id:
        try:
            passage_doc = await get_passage_by_id(active_passage_id)
            if passage_doc:
                raw_text = passage_doc.get("text", "")
                excerpt = raw_text[:380] + ("..." if len(raw_text) > 380 else "")
                
                vocab = passage_doc.get("vocabularyWords") or []
                vocab_words = []
                for v in vocab:
                    if isinstance(v, dict):
                        vocab_words.append(v.get("word", ""))
                    elif isinstance(v, str):
                        vocab_words.append(v)
                
                compact_passage = CompactPassageContext(
                    passageId=passage_doc.get("passageId", active_passage_id),
                    title=passage_doc.get("title", "Reading Story"),
                    excerpt=excerpt,
                    difficulty=int(passage_doc.get("difficulty", 1)),
                    vocabularyWords=vocab_words[:6],
                )
        except Exception as e:
            logger.warning(f"Error fetching active passage {active_passage_id} for tutor: {e}")

    # 4. Recent Reading Session Signals
    recent_reading: Optional[Dict[str, Any]] = None
    try:
        last_session = await db.reading_sessions.find_one(
            {"learnerId": learner_id, "completed": True},
            {"_id": 0, "comprehensionScore": 1, "wordsRead": 1, "overallScore": 1},
            sort=[("createdAt", -1)]
        )
        if last_session:
            recent_reading = {
                "comprehension": round(float(last_session.get("comprehensionScore", 0)), 1),
                "wordsRead": int(last_session.get("wordsRead", 0)),
                "overallScore": round(float(last_session.get("overallScore", 0)), 1),
            }
    except Exception as e:
        logger.warning(f"Error fetching recent reading session: {e}")

    # 5. Speech Analysis Signals (Summarized educational signals only, NO raw audio)
    speech_signals: Optional[Dict[str, Any]] = None
    try:
        last_speech = await db.speech_reading_analyses.find_one(
            {"learnerId": learner_id},
            {"_id": 0, "accuracyRate": 1, "wordsPerMinute": 1, "overallScore": 1},
            sort=[("createdAt", -1)]
        )
        if last_speech:
            speech_signals = {
                "accuracy": round(float(last_speech.get("accuracyRate", 0)), 1),
                "wpm": round(float(last_speech.get("wordsPerMinute", 0)), 1),
                "score": round(float(last_speech.get("overallScore", 0)), 1),
            }
    except Exception as e:
        logger.warning(f"Error fetching recent speech reading analysis: {e}")

    return TutorContext(
        learnerId=learner_id,
        displayName=display_name,
        learningLevel=learning_level,
        learningLevelName=learning_level_name,
        adaptiveTier=adaptive_tier,
        strengths=strengths[:3],
        practiceAreas=practice_areas[:3],
        currentPassage=compact_passage,
        activeWord=active_word.strip() if (active_word and active_word.strip()) else None,
        recentReading=recent_reading,
        accessibility=accessibility_prefs if accessibility_prefs else None,
        speechSignals=speech_signals,
    )
