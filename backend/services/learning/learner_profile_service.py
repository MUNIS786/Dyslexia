"""
backend/services/learning/learner_profile_service.py — V2 Learner Intelligence Profile Service.

Handles loading, dynamic synthesis, interpretation, recalibration, and synchronization
of V2 Learner Profiles from screening results, reading metrics, and student settings.

SAFETY NOTICE:
This service produces educational indicators and personalized reading accommodations.
It does NOT provide clinical or medical diagnoses.
"""
import time
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple, Union
from database.database import db
from models.v2_learner_profile import (
    V2LearnerProfile,
    V2LearningState,
    V2LearnerProfileUpdate,
    LearningLevelInfo,
    StrengthItem,
    PracticeAreaItem,
    ProfileConfidence,
)

logger = logging.getLogger("dyslexaid.learner_profile")

# ─── Educational Domain Taxonomy & Interpretation Definitions ────────────────
# 12 V2 domains mapped to child-friendly descriptors, activity suggestions, and objectives.
DOMAIN_METADATA: Dict[str, Dict[str, Any]] = {
    "phonological_awareness": {
        "technical_name": "Phonological Awareness",
        "friendly_name": "Sound & Word Practice",
        "description": "Practicing hearing, breaking apart, and blending sounds in spoken words.",
        "strength_description": "You are fantastic at hearing and playing with sounds in words!",
        "practice_description": "Fun sound-matching games can help you hear the pieces in every word.",
        "suggested_activity_type": "phoneme_blending",
        "educational_weight": 0.20,
    },
    "phonological_memory": {
        "technical_name": "Phonological Memory",
        "friendly_name": "Memory for Sounds",
        "description": "Holding sounds and syllables in memory while reading.",
        "strength_description": "You remember speech sounds and syllables really well!",
        "practice_description": "Short rhythm and rhyme games can help hold sounds in your mind.",
        "suggested_activity_type": "rhyme_rhythm",
        "educational_weight": 0.10,
    },
    "rapid_naming": {
        "technical_name": "Rapid Automatized Naming (RAN)",
        "friendly_name": "Quick Naming",
        "description": "Quickly naming familiar letters, numbers, and colors.",
        "strength_description": "You quickly spot and name letters and colors!",
        "practice_description": "Speed-naming drills can help words pop into your mind faster.",
        "suggested_activity_type": "rapid_naming_drills",
        "educational_weight": 0.10,
    },
    "reading_fluency": {
        "technical_name": "Reading Fluency",
        "friendly_name": "Smooth Reading Flow",
        "description": "Reading smoothly with natural phrasing and pacing.",
        "strength_description": "You read with wonderful smoothness and flow!",
        "practice_description": "Short guided reading activities can help you build smoother reading.",
        "suggested_activity_type": "guided_reading",
        "educational_weight": 0.15,
    },
    "orthographic_spelling": {
        "technical_name": "Orthographic & Spelling",
        "friendly_name": "Spelling & Word Patterns",
        "description": "Recognizing how words look and remembering spelling patterns.",
        "strength_description": "You have a sharp eye for word patterns and spelling rules!",
        "practice_description": "Sight-word cards and visual games can strengthen word spelling.",
        "suggested_activity_type": "word_pattern_builder",
        "educational_weight": 0.15,
    },
    "reading_comprehension": {
        "technical_name": "Reading Comprehension",
        "friendly_name": "Story & Text Understanding",
        "description": "Understanding stories, facts, and ideas in reading passages.",
        "strength_description": "You are showing good understanding of what you read.",
        "practice_description": "Interactive story quizzes help connect ideas and details.",
        "suggested_activity_type": "story_comprehension",
        "educational_weight": 0.20,
    },
    "visual_processing": {
        "technical_name": "Visual Processing",
        "friendly_name": "Visual Pattern Finding",
        "description": "Spotting shapes, letter details, and visual differences.",
        "strength_description": "You have strong visual superpowers to spot shapes and patterns!",
        "practice_description": "Visual search games can help your eyes track letters clearly.",
        "suggested_activity_type": "visual_tracking",
        "educational_weight": 0.10,
    },
    "visual_attention": {
        "technical_name": "Visual Attention",
        "friendly_name": "Focus on Letters & Words",
        "description": "Staying focused on lines of text without skipping.",
        "strength_description": "You stay focused on words without missing small details!",
        "practice_description": "Reading rulers and line guides can help keep your place.",
        "suggested_activity_type": "guided_line_reading",
        "educational_weight": 0.08,
    },
    "language_processing": {
        "technical_name": "Language Processing",
        "friendly_name": "Word Meaning & Sentences",
        "description": "Understanding word meanings and how sentences fit together.",
        "strength_description": "You have great vocabulary and sentence sense!",
        "practice_description": "Word explorer games introduce fun new words and meanings.",
        "suggested_activity_type": "vocabulary_explorer",
        "educational_weight": 0.10,
    },
    "working_memory": {
        "technical_name": "Working Memory",
        "friendly_name": "Thinking Memory",
        "description": "Holding several ideas in your mind while solving a task.",
        "strength_description": "You hold instructions and ideas in mind very well!",
        "practice_description": "Step-by-step games make it easier to remember sequences.",
        "suggested_activity_type": "memory_sequences",
        "educational_weight": 0.12,
    },
    "letter_reversal": {
        "technical_name": "Letter Orientation",
        "friendly_name": "Letter Direction & Shape",
        "description": "Telling apart mirror letters like b, d, p, and q.",
        "strength_description": "You consistently orient letters in the right direction!",
        "practice_description": "Letter direction practice makes b and d easier to tell apart.",
        "suggested_activity_type": "letter_orientation",
        "educational_weight": 0.08,
    },
    "processing_speed": {
        "technical_name": "Processing Speed",
        "friendly_name": "Pacing & Speed",
        "description": "Taking the right amount of time to think and answer.",
        "strength_description": "You process reading tasks briskly and confidently!",
        "practice_description": "Untimed practice allows you to read comfortably without rushing.",
        "suggested_activity_type": "comfort_paced_reading",
        "educational_weight": 0.08,
    },
}

# Educational Score Scale (0-100)
# 0–39: Needs Practice
# 40–59: Developing
# 60–74: Progressing
# 75–89: Strength
# 90–100: Strong
def get_educational_interpretation(score: float) -> Tuple[str, str]:
    """Returns (label, description) based on educational 0-100 scale."""
    val = round(float(score or 0.0), 1)
    if val >= 90.0:
        return "Strong", "Showing mastery and high confidence in this area."
    elif val >= 75.0:
        return "Strength", "Showing solid ability and consistent progress."
    elif val >= 60.0:
        return "Progressing", "Making steady growth with continuing practice."
    elif val >= 40.0:
        return "Developing", "Building foundational understanding; helpful to reinforce."
    else:
        return "Needs Practice", "Key area for targeted practice and guided scaffolding."


def normalize_to_educational_score(raw_score: Any, is_impairment: bool = True) -> float:
    """
    Normalizes a score to the 0–100 educational scale where higher = greater ability.
    If the source score is an impairment measure (e.g. 78% error/impairment in screening),
    we convert it via 100 - impairment so that lower impairment yields a higher educational score.
    """
    try:
        val = float(raw_score)
    except (ValueError, TypeError):
        return 50.0

    if is_impairment:
        # 0 impairment -> 100 educational score; 100 impairment -> 0 educational score
        return round(max(0.0, min(100.0, 100.0 - val)), 1)
    else:
        return round(max(0.0, min(100.0, val)), 1)


def detect_strengths(domain_scores: Dict[str, float], limit: int = 3) -> List[Dict[str, Any]]:
    """
    Identifies top strengths from educational domain scores.
    Data-driven, child-friendly, limited in count so as not to overwhelm learners.
    """
    candidates = []
    for domain, score in domain_scores.items():
        if domain not in DOMAIN_METADATA:
            continue
        meta = DOMAIN_METADATA[domain]
        label, _ = get_educational_interpretation(score)
        # Consider domains with score >= 60 as potential strengths, sorted highest first
        if score >= 60.0:
            candidates.append({
                "domain": domain,
                "score": round(score, 1),
                "label": "Strong" if score >= 90.0 else ("Strength" if score >= 75.0 else "Progressing"),
                "friendly_name": meta["friendly_name"],
                "technical_name": meta["technical_name"],
                "description": meta["strength_description"],
            })

    # Sort descending by score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]


def detect_practice_areas(domain_scores: Dict[str, float], limit: int = 4) -> List[Dict[str, Any]]:
    """
    Identifies priority areas for practice from educational domain scores.
    Framed constructively as 'Areas to Practice' rather than 'Weaknesses'.
    """
    candidates = []
    for domain, score in domain_scores.items():
        if domain not in DOMAIN_METADATA:
            continue
        meta = DOMAIN_METADATA[domain]
        # Priority mapping: 0-39 -> high, 40-59 -> medium, 60-74 -> low
        if score < 40.0:
            priority = "high"
        elif score < 60.0:
            priority = "medium"
        elif score < 75.0:
            priority = "low"
        else:
            continue

        candidates.append({
            "domain": domain,
            "score": round(score, 1),
            "priority": priority,
            "friendly_name": meta["friendly_name"],
            "technical_name": meta["technical_name"],
            "description": meta["practice_description"],
            "suggested_activity_type": meta["suggested_activity_type"],
        })

    # Sort ascending by score (lowest scores get first practice priority)
    candidates.sort(key=lambda x: x["score"])
    return candidates[:limit]


def calculate_learning_level(
    domain_scores: Dict[str, float],
    reading_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic educational learning-level calculation (Levels 1 to 5).
    1 — Foundation (Composite < 40)
    2 — Developing (Composite 40–54)
    3 — Progressing (Composite 55–69)
    4 — Independent (Composite 70–84)
    5 — Advanced (Composite 85–100)
    """
    # Weighted composite across core educational pillars
    weights = {
        "phonological_awareness": 0.20,
        "reading_comprehension": 0.20,
        "reading_fluency": 0.15,
        "orthographic_spelling": 0.15,
        "working_memory": 0.15,
        "visual_processing": 0.15,
    }

    weighted_sum = 0.0
    total_weight = 0.0
    domains_used = {}

    for domain, w in weights.items():
        if domain in domain_scores:
            s = domain_scores[domain]
            weighted_sum += s * w
            total_weight += w
            domains_used[domain] = s

    composite = (weighted_sum / total_weight) if total_weight > 0 else 50.0
    composite = round(max(0.0, min(100.0, composite)), 1)

    if composite >= 85.0:
        level = 5
        name = "Advanced"
        description = "Demonstrating high reading automaticity, rich vocabulary, and deep comprehension."
    elif composite >= 70.0:
        level = 4
        name = "Independent"
        description = "Reading with strong independence, confident decoding, and solid comprehension."
    elif composite >= 55.0:
        level = 3
        name = "Progressing"
        description = "Making steady progress in reading fluency, vocabulary, and paragraph comprehension."
    elif composite >= 40.0:
        level = 2
        name = "Developing"
        description = "Growing sound blending and word recognition with regular guided practice."
    else:
        level = 1
        name = "Foundation"
        description = "Starting your reading journey with foundational letter sounds and word shapes."

    now = int(time.time())
    return {
        "level": level,
        "name": name,
        "description": description,
        "calculated_at": now,
        "inputs": {
            "composite_score": composite,
            "domains_evaluated": len(domains_used),
            "reading_wpm": reading_metrics.get("avg_words_per_minute", 60.0),
            "comprehension_metric": reading_metrics.get("comprehension_level", 0),
        }
    }


def calculate_profile_confidence(
    answers_count: int,
    scored_domains_count: int,
    progress_doc: Optional[Dict[str, Any]] = None,
    screening_completed: bool = False,
) -> Dict[str, Any]:
    """
    Computes profile confidence based on concrete evidence volume:
    - screening questions answered vs standard battery (target ~20-32 questions)
    - number of cognitive domains actually tested
    - real learning telemetry (sessions, words read, tasks completed)
    """
    if not screening_completed and answers_count == 0:
        return {
            "overall": 0.0,
            "screening": 0.0,
            "performance": 0.0,
            "screening_questions_answered": 0,
            "scored_domains_count": 0,
        }

    # Screening confidence (0.0 to 1.0)
    target_questions = 20.0
    question_ratio = min(1.0, answers_count / target_questions) if answers_count > 0 else 0.7
    domain_ratio = min(1.0, scored_domains_count / 10.0) if scored_domains_count > 0 else 0.7
    screening_conf = round(0.6 * question_ratio + 0.4 * domain_ratio, 2)

    # Performance telemetry confidence (0.0 to 1.0)
    p = progress_doc or {}
    session_count = p.get("sessionCount", 0)
    words_read = p.get("wordsRead", 0)
    tasks_completed = p.get("tasksCompleted", 0)

    perf_raw = (session_count * 0.05) + (min(5000, words_read) / 5000.0 * 0.4) + (tasks_completed * 0.05)
    perf_conf = round(min(1.0, max(0.1, perf_raw)), 2)

    # Overall blended confidence
    overall_conf = round(0.7 * screening_conf + 0.3 * perf_conf, 2)

    return {
        "overall": overall_conf,
        "screening": screening_conf,
        "performance": perf_conf,
        "screening_questions_answered": answers_count,
        "scored_domains_count": scored_domains_count,
    }


def _normalize_goals(raw_goals: Any) -> List[Dict[str, Any]]:
    """Converts mixed string or dict goal items into uniform GoalItem objects."""
    if not raw_goals or not isinstance(raw_goals, list):
        return [
            {"id": "goal-1", "title": "Complete today's reading practice", "completed": False},
            {"id": "goal-2", "title": "Learn 5 new vocabulary words", "completed": False},
            {"id": "goal-3", "title": "Read for 10 minutes", "completed": False},
        ]

    normalized = []
    for idx, item in enumerate(raw_goals):
        if isinstance(item, str):
            normalized.append({
                "id": f"goal-{idx + 1}",
                "title": item,
                "completed": False,
            })
        elif isinstance(item, dict):
            normalized.append({
                "id": str(item.get("id", f"goal-{idx + 1}")),
                "title": str(item.get("title", f"Goal {idx + 1}")),
                "completed": bool(item.get("completed", False)),
            })
    return normalized


# ─── Public Service Methods ───────────────────────────────────────────────────

def format_learner_profile_response(profile_doc: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Transforms stored profile document into a clean, frontend-friendly structure.
    Omit raw MongoDB internals and provide standardized keys.
    """
    u = user or {}
    learner_id = profile_doc.get("learnerId") or profile_doc.get("learner_id") or u.get("id", "")
    display_name = profile_doc.get("displayName") or profile_doc.get("display_name") or u.get("name", "Learner")
    preferred_lang = profile_doc.get("preferredLanguage") or profile_doc.get("preferred_language") or (u.get("languages", ["en-IN"])[0] if u.get("languages") else "en-IN")

    domain_scores = profile_doc.get("domainScores") or profile_doc.get("domain_scores") or {}
    domain_interpretations = profile_doc.get("domainInterpretations") or profile_doc.get("domain_interpretations") or {}

    learning_level = profile_doc.get("learningLevel") or profile_doc.get("learning_level") or {
        "level": 1,
        "name": "Foundation",
        "description": "Starting your reading journey.",
        "calculated_at": profile_doc.get("lastUpdated", int(time.time())),
        "inputs": {},
    }

    confidence = profile_doc.get("confidence") or {
        "overall": 0.0,
        "screening": 0.0,
        "performance": 0.0,
        "screening_questions_answered": 0,
        "scored_domains_count": 0,
    }

    acc_pref = profile_doc.get("accessibilityPreferences") or profile_doc.get("accessibility_preferences") or {}

    return {
        "learner": {
            "id": learner_id,
            "name": display_name,
            "preferred_language": preferred_lang,
        },
        "learning_level": learning_level,
        "domain_scores": domain_scores,
        "domain_interpretations": domain_interpretations,
        "strengths": profile_doc.get("strengths", []),
        "areas_for_practice": profile_doc.get("areasForPractice") or profile_doc.get("areas_for_practice", []),
        "cognitive_indicators": profile_doc.get("cognitiveIndicators") or profile_doc.get("cognitive_indicators", {}),
        "reading_metrics": profile_doc.get("readingMetrics") or profile_doc.get("reading_metrics", {}),
        "preferences": {
            "learning_modes": profile_doc.get("preferredLearningModes") or profile_doc.get("preferred_learning_modes", ["Reading", "Visual", "Interactive"]),
            "font": acc_pref.get("font", "OpenDyslexic"),
            "font_size": acc_pref.get("font_size", acc_pref.get("fontSize", 18)),
            "line_spacing": acc_pref.get("line_spacing", acc_pref.get("lineSpacing", 2.0)),
            "letter_spacing": acc_pref.get("letter_spacing", acc_pref.get("letterSpacing", 0.12)),
            "bg_color": acc_pref.get("bg_color", acc_pref.get("bgColor", "#FFF8F0")),
            "text_color": acc_pref.get("text_color", acc_pref.get("textColor", "#1A2A2A")),
            "tts_speed": acc_pref.get("tts_speed", acc_pref.get("ttsSpeed", 0.85)),
            "tts_language": acc_pref.get("tts_language", acc_pref.get("ttsLanguage", "en-IN")),
            "highlight_words": acc_pref.get("highlight_words", acc_pref.get("highlightWords", True)),
            "syllable_split": acc_pref.get("syllable_split", True),
            "auto_simplify": acc_pref.get("auto_simplify", acc_pref.get("autoSimplify", True)),
        },
        "goals": _normalize_goals(profile_doc.get("currentGoals") or profile_doc.get("current_goals")),
        "confidence": confidence,
        "metadata": profile_doc.get("metadata", {
            "profile_version": 2,
            "generated_at": profile_doc.get("createdAt", int(time.time())),
            "updated_at": profile_doc.get("lastUpdated", int(time.time())),
            "source": "system",
            "screening_completed": profile_doc.get("screeningCompleted", False),
        }),
        "disclaimer": profile_doc.get(
            "disclaimer",
            "Educational Screening Indicator: This profile summarizes educational screening observations "
            "and reading preferences to guide assistive accommodations. It does not constitute a medical, "
            "psychological, or clinical diagnosis."
        ),
    }


async def get_or_create_learner_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieve the V2 learner profile or synthesize it seamlessly from existing records.
    If no screening has been completed, returns a clean profile with screening_completed=False
    without fabricating scores.
    """
    now = int(time.time())

    # 1. Fetch user record
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "passwordHash": 0})
    if not user:
        raise ValueError(f"User {user_id} not found")

    progress = await db.progress.find_one({"userId": user_id}, {"_id": 0}) or {}
    v1_profile = user.get("readingProfile") or {}
    v1_settings = user.get("settings") or {}

    # 2. Check if a dedicated V2 learner profile document already exists in DB
    profile_doc = await db.learner_profiles.find_one({"learnerId": user_id}, {"_id": 0})
    if profile_doc:
        # Check if screening completed status is up to date
        has_screened = bool(v1_profile.get("type") or v1_profile.get("screenedAt") or progress.get("screeningCompleted"))
        if profile_doc.get("screeningCompleted") != has_screened:
            profile_doc["screeningCompleted"] = has_screened
            if "metadata" not in profile_doc or not isinstance(profile_doc["metadata"], dict):
                profile_doc["metadata"] = {}
            profile_doc["metadata"]["screening_completed"] = has_screened
            await db.learner_profiles.update_one(
                {"learnerId": user_id},
                {"$set": {"screeningCompleted": has_screened, "metadata.screening_completed": has_screened}}
            )
        return format_learner_profile_response(profile_doc, user)

    # 3. If no dedicated document exists, synthesize from available history
    latest_screening = await db.screening_results.find_one(
        {"userId": user_id},
        {"_id": 0},
        sort=[("createdAt", -1)]
    )

    screening_completed = bool(
        v1_profile.get("type") or
        v1_profile.get("screenedAt") or
        progress.get("screeningCompleted") or
        latest_screening
    )

    # If the user has NOT completed screening, do NOT fabricate scores.
    if not screening_completed:
        empty_confidence = calculate_profile_confidence(0, 0, progress, screening_completed=False)
        default_level = {
            "level": 1,
            "name": "Foundation",
            "description": "Your learning profile is getting ready. Complete your learning check to discover your strengths.",
            "calculated_at": now,
            "inputs": {"status": "screening_pending"},
        }
        empty_profile = {
            "learnerId": user_id,
            "displayName": user.get("name", "Learner"),
            "schemaVersion": 2,
            "screeningCompleted": False,
            "learningLevel": default_level,
            "current_level": "moderate",
            "risk_level": "Moderate",
            "dyslexiaIndicators": {
                "primaryProfile": None,
                "subtypeProbabilities": {},
                "confidence": 0.0,
            },
            "domainScores": {},
            "domainInterpretations": {},
            "cognitiveIndicators": {
                "working_memory": "standard",
                "visual_processing": "standard",
                "auditory_processing": "standard",
                "processing_speed": "standard",
            },
            "strengths": [],
            "areasForPractice": [],
            "focus_areas": [],
            "readingMetrics": {
                "reading_level": "foundations",
                "comprehension_level": 0,
                "vocabulary_level": "standard",
                "avg_words_per_minute": 0.0,
                "words_mastered": 0,
            },
            "preferredLearningModes": ["Reading", "Visual", "Interactive"],
            "preferredLanguage": user.get("languages", ["en-IN"])[0] if user.get("languages") else "en-IN",
            "accessibilityPreferences": {
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
            "adaptiveDifficulty": {
                "active_tier": 1,
                "max_sentence_length": 10,
                "vocabulary_complexity": "simple",
                "scaffolding_level": "standard",
            },
            "learning_streak": int(progress.get("streak", 0)),
            "currentGoals": _normalize_goals(None),
            "confidence": empty_confidence,
            "metadata": {
                "profile_version": 2,
                "generated_at": now,
                "updated_at": now,
                "source": "system",
                "screening_completed": False,
            },
            "teacherObservations": [],
            "parentObservations": [],
            "disclaimer": (
                "Educational Screening Indicator: This profile summarizes educational screening observations "
                "and reading preferences to guide assistive accommodations. It does not constitute a medical, "
                "psychological, or clinical diagnosis."
            ),
            "lastUpdated": now,
            "createdAt": now,
        }
        await db.learner_profiles.update_one(
            {"learnerId": user_id},
            {"$set": empty_profile},
            upsert=True
        )
        return format_learner_profile_response(empty_profile, user)

    # User HAS completed screening: synthesize full profile
    v1_domains = v1_profile.get("domainScores", {}) or {}
    if not v1_domains and latest_screening:
        res = latest_screening.get("result", {})
        v1_domains = res.get("cognitive_profile") or res.get("domain_scores") or {}

    # Normalize domain scores to 0-100 educational proficiency scale
    domain_scores: Dict[str, float] = {}
    domain_interpretations: Dict[str, Dict[str, Any]] = {}

    for domain_key, meta in DOMAIN_METADATA.items():
        # Check domain variations in V1 screening
        raw_val = None
        if domain_key in v1_domains:
            raw_val = v1_domains[domain_key]
        elif domain_key == "phonological_awareness":
            raw_val = v1_domains.get("phonological_processing") or v1_domains.get("phonological_awareness")
        elif domain_key == "orthographic_spelling":
            raw_val = v1_domains.get("orthographic_processing") or v1_domains.get("spelling_ability") or v1_domains.get("orthographic_spelling")
        elif domain_key == "phonological_memory":
            raw_val = v1_domains.get("phonological_memory") or v1_domains.get("working_memory")
        elif domain_key == "visual_attention":
            raw_val = v1_domains.get("visual_attention") or v1_domains.get("visual_processing")
        elif domain_key == "language_processing":
            raw_val = v1_domains.get("language_processing") or v1_domains.get("reading_comprehension")

        if isinstance(raw_val, dict):
            raw_score = raw_val.get("score", 30.0)
        elif raw_val is not None:
            raw_score = raw_val
        else:
            # Domain wasn't specifically scored in earlier screening, estimate from overall level
            overall_raw = float(v1_profile.get("score") or 40.0)
            raw_score = overall_raw

        # In V1 screening, raw_score was impairment percentage. Convert to educational scale (100 - impairment)
        educational_score = normalize_to_educational_score(raw_score, is_impairment=True)
        domain_scores[domain_key] = educational_score

        label, interp_desc = get_educational_interpretation(educational_score)
        domain_interpretations[domain_key] = {
            "score": educational_score,
            "label": label,
            "friendly_name": meta["friendly_name"],
            "technical_name": meta["technical_name"],
            "description": interp_desc,
        }

    # Strengths and Practice Areas detection
    strengths = detect_strengths(domain_scores, limit=3)
    practice_areas = detect_practice_areas(domain_scores, limit=4)

    # Subtype probabilities
    learning_profiles = v1_profile.get("learningProfiles", {}) or {}
    subtype_probabilities = {}
    for k, v in learning_profiles.items():
        key = k.lower().replace(" ", "_")
        try:
            subtype_probabilities[key] = round(float(v) / 100.0, 2)
        except (ValueError, TypeError):
            pass

    # Reading metrics
    reading_metrics = {
        "reading_level": "intermediate" if progress.get("wordsRead", 0) > 2000 else "foundations",
        "comprehension_level": int(progress.get("avgComprehension", 0)),
        "vocabulary_level": "standard",
        "avg_words_per_minute": 60.0,
        "words_mastered": len(progress.get("masteredWords", [])),
    }

    # Cognitive Indicators
    wm_score = domain_scores.get("working_memory", 60.0)
    vp_score = domain_scores.get("visual_processing", 60.0)
    pa_score = domain_scores.get("phonological_awareness", 60.0)
    ps_score = domain_scores.get("processing_speed", 60.0)

    cognitive_indicators = {
        "working_memory": "strong" if wm_score >= 75.0 else ("needs_scaffolding" if wm_score < 50.0 else "standard"),
        "visual_processing": "strong" if vp_score >= 75.0 else ("needs_scaffolding" if vp_score < 50.0 else "standard"),
        "auditory_processing": "strong" if pa_score >= 75.0 else ("needs_scaffolding" if pa_score < 50.0 else "standard"),
        "processing_speed": "typical" if ps_score >= 60.0 else "extended_time_beneficial",
    }

    # Learning level
    learning_level = calculate_learning_level(domain_scores, reading_metrics)

    # Confidence
    answers_count = latest_screening.get("answersCount", 20) if latest_screening else 20
    confidence = calculate_profile_confidence(
        answers_count=answers_count,
        scored_domains_count=len(domain_scores),
        progress_doc=progress,
        screening_completed=True,
    )

    v2_doc = {
        "learnerId": user_id,
        "displayName": user.get("name", "Learner"),
        "schemaVersion": 2,
        "screeningCompleted": True,
        "learningLevel": learning_level,
        "current_level": v1_profile.get("level", "moderate") or "moderate",
        "risk_level": v1_profile.get("riskLevel", "Moderate") or "Moderate",
        "dyslexiaIndicators": {
            "primaryProfile": v1_profile.get("primaryProfile", v1_profile.get("type")),
            "subtypeProbabilities": subtype_probabilities,
            "confidence": float(v1_profile.get("confidence", 70.0) or 70.0),
        },
        "domainScores": domain_scores,
        "domainInterpretations": domain_interpretations,
        "cognitiveIndicators": cognitive_indicators,
        "strengths": strengths,
        "areasForPractice": practice_areas,
        "focus_areas": [p["friendly_name"] for p in practice_areas],
        "readingMetrics": reading_metrics,
        "preferredLearningModes": ["Reading", "Visual", "Interactive"],
        "preferredLanguage": user.get("languages", ["en-IN"])[0] if user.get("languages") else "en-IN",
        "accessibilityPreferences": {
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
        "adaptiveDifficulty": {
            "active_tier": learning_level["level"],
            "max_sentence_length": 12,
            "vocabulary_complexity": "controlled",
            "scaffolding_level": "high" if learning_level["level"] <= 2 else "standard",
        },
        "learning_streak": int(progress.get("streak", 0)),
        "currentGoals": _normalize_goals(None),
        "confidence": confidence,
        "metadata": {
            "profile_version": 2,
            "generated_at": now,
            "updated_at": now,
            "source": "screening",
            "screening_completed": True,
        },
        "teacherObservations": [],
        "parentObservations": [],
        "disclaimer": (
            "Educational Screening Indicator: This profile summarizes educational screening observations "
            "and reading preferences to guide assistive accommodations. It does not constitute a medical, "
            "psychological, or clinical diagnosis."
        ),
        "lastUpdated": now,
        "createdAt": now,
    }

    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": v2_doc},
        upsert=True
    )
    return format_learner_profile_response(v2_doc, user)


async def update_learner_profile(user_id: str, patch_data: V2LearnerProfileUpdate) -> Dict[str, Any]:
    """
    Safely updates learner preferences and goals.
    Enforces security: Students can NEVER modify screening scores, domain scores,
    profile confidence, or system-calculated learning levels.
    """
    now = int(time.time())
    updates: Dict[str, Any] = {
        "lastUpdated": now,
        "updatedAt": now,
        "metadata.updated_at": now,
        "metadata.source": "learner_preferences",
    }

    if patch_data.current_goals is not None:
        updates["currentGoals"] = _normalize_goals(patch_data.current_goals)

    if patch_data.preferred_language is not None:
        updates["preferredLanguage"] = patch_data.preferred_language
        # Sync with user doc
        await db.users.update_one({"id": user_id}, {"$set": {"languages": [patch_data.preferred_language]}})

    if patch_data.preferred_learning_modes is not None:
        updates["preferredLearningModes"] = patch_data.preferred_learning_modes

    if patch_data.accessibility_preferences is not None:
        for k, v in patch_data.accessibility_preferences.items():
            updates[f"accessibilityPreferences.{k}"] = v

        # Sync back to V1 users.settings for full backward compatibility
        pref = patch_data.accessibility_preferences
        v1_patch = {}
        if "font" in pref: v1_patch["settings.font"] = pref["font"]
        if "font_size" in pref: v1_patch["settings.fontSize"] = pref["font_size"]
        if "line_spacing" in pref: v1_patch["settings.lineSpacing"] = pref["line_spacing"]
        if "letter_spacing" in pref: v1_patch["settings.letterSpacing"] = pref["letter_spacing"]
        if "bg_color" in pref: v1_patch["settings.bgColor"] = pref["bg_color"]
        if "text_color" in pref: v1_patch["settings.textColor"] = pref["text_color"]
        if "tts_speed" in pref: v1_patch["settings.ttsSpeed"] = pref["tts_speed"]
        if "tts_language" in pref: v1_patch["settings.ttsLanguage"] = pref["tts_language"]
        if "highlight_words" in pref: v1_patch["settings.highlightWords"] = pref["highlight_words"]
        if "auto_simplify" in pref: v1_patch["settings.autoSimplify"] = pref["auto_simplify"]
        if v1_patch:
            await db.users.update_one({"id": user_id}, {"$set": v1_patch})

    if patch_data.teacher_observations is not None:
        updates["teacherObservations"] = patch_data.teacher_observations

    if patch_data.parent_observations is not None:
        updates["parentObservations"] = patch_data.parent_observations

    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": updates},
        upsert=True
    )

    return await get_or_create_learner_profile(user_id)


async def recalibrate_from_screening(user_id: str, screening_result: Dict[str, Any], student_age: Optional[int] = None) -> Dict[str, Any]:
    """
    Called upon screening completion to synthesize and persist the V2 Learner Intelligence Profile.
    Does NOT modify the V1 screening result.
    """
    now = int(time.time())
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "passwordHash": 0})
    if not user:
        logger.error(f"Cannot recalibrate profile: user {user_id} not found")
        return {}

    progress = await db.progress.find_one({"userId": user_id}, {"_id": 0}) or {}
    v1_settings = user.get("settings") or {}

    raw_cognitive = screening_result.get("cognitive_profile") or screening_result.get("domain_scores") or {}

    # Normalize domain scores to educational 0-100 scale
    domain_scores: Dict[str, float] = {}
    domain_interpretations: Dict[str, Dict[str, Any]] = {}

    for domain_key, meta in DOMAIN_METADATA.items():
        raw_val = raw_cognitive.get(domain_key)
        if raw_val is None:
            if domain_key == "phonological_awareness":
                raw_val = raw_cognitive.get("phonological_processing")
            elif domain_key == "orthographic_spelling":
                raw_val = raw_cognitive.get("orthographic_processing") or raw_cognitive.get("spelling_ability")
            elif domain_key == "phonological_memory":
                raw_val = raw_cognitive.get("phonological_memory") or raw_cognitive.get("working_memory")
            elif domain_key == "visual_attention":
                raw_val = raw_cognitive.get("visual_attention") or raw_cognitive.get("visual_processing")
            elif domain_key == "language_processing":
                raw_val = raw_cognitive.get("language_processing") or raw_cognitive.get("reading_comprehension")

        if isinstance(raw_val, dict):
            raw_score = raw_val.get("score", float(screening_result.get("score") or 40.0))
        elif raw_val is not None:
            raw_score = raw_val
        else:
            raw_score = float(screening_result.get("score") or 40.0)

        # Convert impairment to educational score
        educational_score = normalize_to_educational_score(raw_score, is_impairment=True)
        domain_scores[domain_key] = educational_score

        label, interp_desc = get_educational_interpretation(educational_score)
        domain_interpretations[domain_key] = {
            "score": educational_score,
            "label": label,
            "friendly_name": meta["friendly_name"],
            "technical_name": meta["technical_name"],
            "description": interp_desc,
        }

    strengths = detect_strengths(domain_scores, limit=3)
    practice_areas = detect_practice_areas(domain_scores, limit=4)

    # Reading metrics
    reading_metrics = {
        "reading_level": "foundations" if screening_result.get("level") in ("severe", "high") else "intermediate",
        "comprehension_level": int(domain_scores.get("reading_comprehension", 50.0)),
        "vocabulary_level": "standard",
        "avg_words_per_minute": 60.0,
        "words_mastered": len(progress.get("masteredWords", [])),
    }

    # Cognitive Indicators
    wm_score = domain_scores.get("working_memory", 60.0)
    vp_score = domain_scores.get("visual_processing", 60.0)
    pa_score = domain_scores.get("phonological_awareness", 60.0)
    ps_score = domain_scores.get("processing_speed", 60.0)

    cognitive_indicators = {
        "working_memory": "strong" if wm_score >= 75.0 else ("needs_scaffolding" if wm_score < 50.0 else "standard"),
        "visual_processing": "strong" if vp_score >= 75.0 else ("needs_scaffolding" if vp_score < 50.0 else "standard"),
        "auditory_processing": "strong" if pa_score >= 75.0 else ("needs_scaffolding" if pa_score < 50.0 else "standard"),
        "processing_speed": "typical" if ps_score >= 60.0 else "extended_time_beneficial",
    }

    learning_level = calculate_learning_level(domain_scores, reading_metrics)

    # Subtype probabilities
    prob_map = screening_result.get("profile_probabilities") or {}
    subtype_probabilities = {}
    for k, v in prob_map.items():
        key = k.lower().replace(" ", "_")
        try:
            subtype_probabilities[key] = round(float(v) / 100.0, 2)
        except (ValueError, TypeError):
            pass

    confidence = calculate_profile_confidence(
        answers_count=screening_result.get("answers_count", 20),
        scored_domains_count=len(domain_scores),
        progress_doc=progress,
        screening_completed=True,
    )

    # Preserve any existing goals
    existing_profile = await db.learner_profiles.find_one({"learnerId": user_id}, {"currentGoals": 1})
    current_goals = existing_profile.get("currentGoals") if existing_profile else None

    profile_doc = {
        "learnerId": user_id,
        "displayName": user.get("name", "Learner"),
        "schemaVersion": 2,
        "screeningCompleted": True,
        "learningLevel": learning_level,
        "current_level": screening_result.get("level", "moderate"),
        "risk_level": screening_result.get("risk_level", "Moderate"),
        "dyslexiaIndicators": {
            "primaryProfile": screening_result.get("primary_profile", screening_result.get("type")),
            "subtypeProbabilities": subtype_probabilities,
            "confidence": float(screening_result.get("confidence", 70.0) or 70.0),
        },
        "domainScores": domain_scores,
        "domainInterpretations": domain_interpretations,
        "cognitiveIndicators": cognitive_indicators,
        "strengths": strengths,
        "areasForPractice": practice_areas,
        "focus_areas": [p["friendly_name"] for p in practice_areas],
        "readingMetrics": reading_metrics,
        "preferredLearningModes": ["Reading", "Visual", "Interactive"],
        "preferredLanguage": user.get("languages", ["en-IN"])[0] if user.get("languages") else "en-IN",
        "accessibilityPreferences": {
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
        "adaptiveDifficulty": {
            "active_tier": learning_level["level"],
            "max_sentence_length": 12,
            "vocabulary_complexity": "controlled",
            "scaffolding_level": "high" if learning_level["level"] <= 2 else "standard",
        },
        "learning_streak": int(progress.get("streak", 0)),
        "currentGoals": _normalize_goals(current_goals),
        "confidence": confidence,
        "metadata": {
            "profile_version": 2,
            "generated_at": now,
            "updated_at": now,
            "source": "screening",
            "screening_completed": True,
        },
        "teacherObservations": [],
        "parentObservations": [],
        "disclaimer": (
            "Educational Screening Indicator: This profile summarizes educational screening observations "
            "and reading preferences to guide assistive accommodations. It does not constitute a medical, "
            "psychological, or clinical diagnosis."
        ),
        "lastUpdated": now,
        "createdAt": now,
    }

    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": profile_doc},
        upsert=True
    )
    logger.info(f"Synthesized V2 Learner Intelligence Profile for user {user_id} with level {learning_level['level']}")
    return format_learner_profile_response(profile_doc, user)


# ─── Recalibration Stubs prepared for Phase 3 ────────────────────────────────

async def recalibrate_from_activity(user_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 3 Adaptive Learning Engine: updates profile following micro-task attempts.
    Nudges target domain educational score using exponential moving average,
    re-evaluates strengths and practice areas, and syncs learning progress.
    """
    now = int(time.time())
    domain = activity_data.get("domain")
    score = float(activity_data.get("score", 70.0))
    tier = int(activity_data.get("tier", 1))

    profile_doc = await db.learner_profiles.find_one({"learnerId": user_id})
    if not profile_doc:
        return await get_or_create_learner_profile(user_id)

    domain_scores = profile_doc.get("domainScores", {})
    domain_interpretations = profile_doc.get("domainInterpretations", {})

    if domain and domain in DOMAIN_METADATA:
        old_score = float(domain_scores.get(domain, 50.0))
        # Exponential moving average: 80% weight on historical, 20% on fresh attempt
        updated_score = round(0.80 * old_score + 0.20 * score, 1)
        domain_scores[domain] = updated_score

        label, interp_desc = get_educational_interpretation(updated_score)
        meta = DOMAIN_METADATA[domain]
        domain_interpretations[domain] = {
            "score": updated_score,
            "label": label,
            "friendly_name": meta["friendly_name"],
            "technical_name": meta["technical_name"],
            "description": interp_desc,
        }

    # Re-evaluate strengths and practice areas
    strengths = detect_strengths(domain_scores, limit=3)
    practice_areas = detect_practice_areas(domain_scores, limit=4)

    # Sync reading metrics
    reading_metrics = profile_doc.get("readingMetrics", {})
    if domain == "reading_comprehension":
        reading_metrics["comprehension_level"] = int(score)

    updates = {
        "domainScores": domain_scores,
        "domainInterpretations": domain_interpretations,
        "strengths": strengths,
        "areasForPractice": practice_areas,
        "focus_areas": [p["friendly_name"] for p in practice_areas],
        "readingMetrics": reading_metrics,
        "adaptiveDifficulty.active_tier": tier,
        "metadata.updated_at": now,
        "metadata.source": "learning_activity",
        "lastUpdated": now,
        "updatedAt": now,
    }

    await db.learner_profiles.update_one(
        {"learnerId": user_id},
        {"$set": updates}
    )

    # Also record in progress collection
    try:
        await db.progress.update_one(
            {"userId": user_id},
            {
                "$inc": {"tasksCompleted": 1},
                "$push": {"comprehensionScores": {"$each": [int(score)], "$slice": -10}},
                "$set": {"lastActiveDate": now},
            }
        )
    except Exception as e:
        logger.warning(f"Could not update progress collection for user {user_id}: {e}")

    logger.info(f"Recalibrated profile for user {user_id} after activity in domain {domain} (score: {score})")
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "passwordHash": 0}) or {}
    profile_doc.update(updates)
    return format_learner_profile_response(profile_doc, user)


async def recalibrate_from_reading(user_id: str, reading_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stub for Phase 4 Reading Coach: updates profile following guided reading sessions."""
    logger.debug(f"[Phase 4 Stub] recalibrate_from_reading called for user {user_id}")
    return await get_or_create_learner_profile(user_id)


async def recalibrate_from_quiz(user_id: str, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stub for future quiz completions: updates comprehension and vocabulary levels."""
    logger.debug(f"[Phase 3 Stub] recalibrate_from_quiz called for user {user_id}")
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
    initial_tier = 1 if level in ("high", "severe") else (2 if level == "moderate" else 3)

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
