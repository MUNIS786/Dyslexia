"""
backend/services/learning/learner_profile_service.py — V2 Learner Intelligence Profile Service.

Handles loading, dynamic synthesis, caching, and backward-compatible synchronization
of V2 Learner Profiles from existing screening results, progress telemetry, and user settings.
"""
import time
import logging
from typing import Optional, Dict, Any
from database.database import db
from models.v2_learner_profile import V2LearnerProfile, V2LearningState, V2LearnerProfileUpdate

logger = logging.getLogger("dyslexaid.learner_profile")


async def get_or_create_learner_profile(user_id: str) -> Dict[str, Any]:
    """Retrieve the V2 learner profile or synthesize it seamlessly from V1 data."""
    now = int(time.time())

    # 1. Check if a dedicated V2 learner profile document already exists
    profile_doc = await db.learner_profiles.find_one({"learnerId": user_id}, {"_id": 0})
    if profile_doc:
        return profile_doc

    # 2. If not found, fetch existing V1 user and progress records
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "passwordHash": 0})
    if not user:
        raise ValueError(f"User {user_id} not found")

    progress = await db.progress.find_one({"userId": user_id}, {"_id": 0}) or {}
    v1_profile = user.get("readingProfile") or {}
    v1_settings = user.get("settings") or {}

    # 3. Map V1 domain scores to V2 normalized domain scores
    v1_domains = v1_profile.get("domainScores", {}) or {}
    domain_scores = {
        "phonological_awareness": float(v1_domains.get("phonological_processing", v1_domains.get("phonological_awareness", 0.0))),
        "phonological_memory": float(v1_domains.get("phonological_memory", 0.0)),
        "rapid_naming": float(v1_domains.get("rapid_naming", 0.0)),
        "letter_reversal": float(v1_domains.get("letter_reversal", 0.0)),
        "reading_fluency": float(v1_domains.get("reading_fluency", 0.0)),
        "orthographic_spelling": float(v1_domains.get("orthographic_processing", v1_domains.get("orthographic_spelling", 0.0))),
        "reading_comprehension": float(v1_domains.get("reading_comprehension", 0.0)),
        "motor_writing": float(v1_domains.get("motor_writing", 0.0)),
        "visual_processing": float(v1_domains.get("visual_processing", 0.0)),
        "processing_speed": float(v1_domains.get("processing_speed", 0.0)),
    }

    # 4. Map subtype probabilities
    learning_profiles = v1_profile.get("learningProfiles", {}) or {}
    subtype_probabilities = {}
    for k, v in learning_profiles.items():
        key = k.lower().replace(" ", "_")
        try:
            subtype_probabilities[key] = round(float(v) / 100.0, 2)
        except (ValueError, TypeError):
            pass

    # 5. Determine cognitive indicators based on domain scores
    working_memory_score = domain_scores["phonological_memory"]
    visual_score = domain_scores["visual_processing"]
    auditory_score = domain_scores["phonological_awareness"]

    cognitive_indicators = {
        "working_memory": "strong" if working_memory_score < 30 else ("needs_scaffolding" if working_memory_score > 60 else "standard"),
        "visual_processing": "strong" if visual_score > 60 else "standard",
        "auditory_processing": "needs_scaffolding" if auditory_score > 50 else "standard",
        "processing_speed": "extended_time_beneficial" if domain_scores["processing_speed"] > 50 else "standard",
    }

    # 6. Build the V2 profile document
    v2_profile = V2LearnerProfile(
        learner_id=user_id,
        schema_version=2,
        current_level=v1_profile.get("level", "moderate") or "moderate",
        risk_level=v1_profile.get("riskLevel", "Moderate") or "Moderate",
        dyslexia_indicators={
            "primary_profile": v1_profile.get("primaryProfile", v1_profile.get("type")),
            "subtype_probabilities": subtype_probabilities,
            "confidence": float(v1_profile.get("confidence", 70.0) or 70.0),
        },
        domain_scores=domain_scores,
        cognitive_indicators=cognitive_indicators,
        strengths=v1_profile.get("strengths", ["Visual Synthesis"]),
        focus_areas=v1_profile.get("weaknesses", ["Phoneme Blending"]),
        reading_metrics={
            "reading_level": "intermediate" if progress.get("wordsRead", 0) > 2000 else "foundations",
            "comprehension_level": int(progress.get("avgComprehension", 0)),
            "vocabulary_level": "standard",
            "avg_words_per_minute": 60.0,
            "words_mastered": len(progress.get("masteredWords", [])),
        },
        preferred_learning_modes=[v1_profile.get("learningStyle", "Visual-Auditory Multisensory")],
        preferred_language=user.get("languages", ["en-IN"])[0] if user.get("languages") else "en-IN",
        accessibility_preferences={
            "font": v1_settings.get("font", "OpenDyslexic"),
            "font_size": int(v1_settings.get("fontSize", 18)),
            "line_spacing": float(v1_settings.get("lineSpacing", 2.0)),
            "letter_spacing": float(v1_settings.get("letterSpacing", 0.12)),
            "bg_color": v1_settings.get("bgColor", "#FFF8F0"),
            "text_color": v1_settings.get("textColor", "#1A2A2A"),
            "tts_speed": float(v1_settings.get("ttsSpeed", 0.85)),
            "tts_language": v1_settings.get("ttsLanguage", "en-IN"),
            "highlight_words": bool(v1_settings.get("highlightWords", True)),
            "syllable_split": True,
            "auto_simplify": bool(v1_settings.get("autoSimplify", True)),
        },
        adaptive_difficulty={
            "active_tier": 2 if v1_profile.get("level") == "moderate" else (1 if v1_profile.get("level") == "high" else 3),
            "max_sentence_length": 12,
            "vocabulary_complexity": "controlled",
            "scaffolding_level": "high" if v1_profile.get("level") == "high" else "standard",
        },
        learning_streak=int(progress.get("streak", 0)),
        current_goals=[
            "Practice reading for 10 minutes daily",
            "Master 5 new vocabulary words this week",
        ],
        teacher_observations=[],
        parent_observations=[],
        last_updated=now,
        created_at=now,
    )

    doc = v2_profile.model_dump()
    # Save in learner_profiles for fast subsequent retrieval
    doc_for_db = {**doc, "learnerId": user_id}
    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": doc_for_db},
        upsert=True
    )
    return doc


async def update_learner_profile(user_id: str, patch_data: V2LearnerProfileUpdate) -> Dict[str, Any]:
    """Updates learner profile and synchronizes changes back to V1 structures."""
    now = int(time.time())
    updates = {"last_updated": now, "updatedAt": now}

    if patch_data.current_goals is not None:
        updates["current_goals"] = patch_data.current_goals
    if patch_data.preferred_language is not None:
        updates["preferred_language"] = patch_data.preferred_language
    if patch_data.parent_observations is not None:
        updates["parent_observations"] = patch_data.parent_observations
    if patch_data.teacher_observations is not None:
        updates["teacher_observations"] = patch_data.teacher_observations
    if patch_data.accessibility_preferences is not None:
        for k, v in patch_data.accessibility_preferences.items():
            updates[f"accessibility_preferences.{k}"] = v

    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": updates},
        upsert=True
    )

    # Backward compatibility sync: update users.settings if accessibility changed
    if patch_data.accessibility_preferences is not None:
        user_settings_patch = {}
        pref = patch_data.accessibility_preferences
        if "font" in pref: user_settings_patch["settings.font"] = pref["font"]
        if "font_size" in pref: user_settings_patch["settings.fontSize"] = pref["font_size"]
        if "line_spacing" in pref: user_settings_patch["settings.lineSpacing"] = pref["line_spacing"]
        if "letter_spacing" in pref: user_settings_patch["settings.letterSpacing"] = pref["letter_spacing"]
        if "bg_color" in pref: user_settings_patch["settings.bgColor"] = pref["bg_color"]
        if "text_color" in pref: user_settings_patch["settings.textColor"] = pref["text_color"]
        if "tts_speed" in pref: user_settings_patch["settings.ttsSpeed"] = pref["tts_speed"]
        if user_settings_patch:
            await db.users.update_one({"id": user_id}, {"$set": user_settings_patch})

    return await get_or_create_learner_profile(user_id)


async def get_learning_state(user_id: str) -> Dict[str, Any]:
    """Retrieves or initializes the current active learning state."""
    now = int(time.time())
    state_doc = await db.learning_states.find_one({"learnerId": user_id}, {"_id": 0})
    if state_doc:
        return state_doc

    progress = await db.progress.find_one({"userId": user_id}, {"_id": 0}) or {}
    user = await db.users.find_one({"id": user_id}, {"_id": 0}) or {}
    profile = user.get("readingProfile") or {}

    level = profile.get("level", "moderate")
    initial_tier = 1 if level == "high" else (2 if level == "moderate" else 3)

    state = V2LearningState(
        learner_id=user_id,
        active_difficulty_tier=initial_tier,
        current_module="reading_foundations",
        today_tasks_assigned=progress.get("tasksAssigned", 3),
        today_tasks_completed=progress.get("tasksCompleted", 0),
        current_streak=progress.get("streak", 0),
        last_session_timestamp=progress.get("lastActiveDate"),
        consecutive_passes=2,
        consecutive_failures=0,
        recommended_next_action="daily_reading_practice",
        adaptation_due=False,
        updated_at=now,
    )

    doc = state.model_dump()
    await db.learning_states.update_one(
        {"learnerId": user_id},
        {"$set": {**doc, "learnerId": user_id}},
        upsert=True
    )
    return doc
