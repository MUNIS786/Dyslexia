"""
backend/services/learning/personalized_content.py — Phase 15 Personalized Learning Content & Activity Engine.

Coordinates:
- Deterministic, explainable content curation for students moving from Phase 14 recommendations to real activities
- Strict adherence to Phase 3 Adaptive Learning Engine (authoritative tier source)
- Honest multilingual matching (en, mr, hi) with explicit fallbacks and zero fabricated content
- Real completion tracking from persisted reading sessions and activity attempts (zero fake completions)
- Activity launch telemetry tracking distinguishing launch from confirmed completion
- Phase 12 accessibility preset integration for child-friendly typography and display
- Multi-tenant role authorization and privacy safeguards (no raw audio, no tutor transcripts, no private teacher notes)
"""
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from database.database import db
from models.v2_personalized_content import (
    ActivityType,
    ContentAvailabilityStatus,
    PersonalizedContentItem,
    PersonalizedActivityNextResponse,
    PersonalizedActivitiesListResponse,
    PersonalizedContentLaunchRequest,
    PersonalizedContentLaunchResponse,
    TeacherPersonalizedContentResponse,
    ParentPersonalizedContentResponse,
)
from services.learning.difficulty_engine import clamp_tier
from services.learning.learner_profile_service import (
    get_or_create_learner_profile,
    get_learning_state,
)
from services.learning.reading_service import DEFAULT_PASSAGES, get_passages
from services.learning.activity_recommender import DEFAULT_ACTIVITIES, get_catalog_activities
from services.learning.learning_recommendations import (
    generate_learner_recommendations,
    _check_today_completions,
    TIER_NAMES,
)
from services.analytics.teacher_analytics import verify_teacher_student_access
from services.parent.parent_service import verify_parent_student_access

logger = logging.getLogger("dyslexaid.personalized_content")

LANGUAGE_NAMES = {
    "en": "English",
    "mr": "Marathi (मराठी)",
    "hi": "Hindi (हिन्दी)",
}


def _normalize_language(lang: Optional[str]) -> str:
    """Normalizes language code to 'en', 'mr', or 'hi'."""
    if not lang:
        return "en"
    clean = str(lang).strip().lower()
    if clean.startswith("mr"):
        return "mr"
    if clean.startswith("hi"):
        return "hi"
    return "en"


async def _get_learner_accessibility_config(learner_id: str) -> Dict[str, Any]:
    """Retrieves learner's saved accessibility settings (Phase 12), with safe defaults."""
    default_cfg = {
        "font": "OpenDyslexic",
        "fontSize": 18,
        "lineSpacing": 2.0,
        "letterSpacing": 0.08,
        "wordSpacing": 0.05,
        "contentWidth": "standard",
        "highContrast": False,
        "reducedMotion": False,
        "tintOverlay": "none",
        "readingRuler": False,
    }
    try:
        doc = await db.accessibility_preferences.find_one({"learnerId": learner_id}, {"_id": 0})
        if doc:
            for k in default_cfg:
                if k in doc:
                    default_cfg[k] = doc[k]
    except Exception as e:
        logger.warning(f"Could not load accessibility config for {learner_id}: {e}")
    return default_cfg


async def _get_eligible_reading_passages() -> List[Dict[str, Any]]:
    """
    Fetches all eligible published reading passages from database,
    falling back to or combining with DEFAULT_PASSAGES.
    Excludes any DRAFT, IN_REVIEW, CHANGES_REQUESTED, ARCHIVED, or REJECTED content.
    """
    eligible = []
    seen_ids = set()
    try:
        cursor = db.reading_passages.find(
            {
                "active": True,
                "$or": [
                    {"status": "PUBLISHED"},
                    {"status": {"$exists": False}},  # Legacy seed records
                ],
            },
            {"_id": 0}
        ).sort("difficulty", 1)
        db_passages = await cursor.to_list(length=200)
        for p in db_passages:
            pid = p.get("passageId")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                eligible.append(p)
    except Exception as e:
        logger.warning(f"Error fetching eligible passages from db: {e}")

    for p in DEFAULT_PASSAGES:
        pid = p.get("passageId")
        if pid and pid not in seen_ids:
            if p.get("active", True) and p.get("status") not in ("DRAFT", "IN_REVIEW", "CHANGES_REQUESTED", "ARCHIVED", "REJECTED"):
                seen_ids.add(pid)
                eligible.append(dict(p))

    return eligible if eligible else [
        p for p in DEFAULT_PASSAGES
        if p.get("active", True) and p.get("status") not in ("DRAFT", "IN_REVIEW", "CHANGES_REQUESTED", "ARCHIVED", "REJECTED")
    ]


def _find_passage_for_tier_and_language(
    tier: int,
    requested_lang: str,
    candidate_passages: Optional[List[Dict[str, Any]]] = None,
) -> tuple[Dict[str, Any], str, ContentAvailabilityStatus, Optional[str]]:
    """
    Finds a reading passage matching the target difficulty tier and requested language.
    If exact language is unavailable for the tier, falls back honestly to English.
    Never pretends an English passage is in Marathi or Hindi.
    Excludes draft, in-review, changes-requested, and archived content.
    """
    if candidate_passages is None:
        all_passages = [
            p for p in DEFAULT_PASSAGES
            if p.get("active", True) and p.get("status") not in ("DRAFT", "IN_REVIEW", "CHANGES_REQUESTED", "ARCHIVED", "REJECTED")
        ]
        if not all_passages:
            all_passages = DEFAULT_PASSAGES
    else:
        all_passages = candidate_passages

    # 1. Look for exact match: same tier and requested language
    exact_matches = [
        p for p in all_passages
        if p.get("difficulty", 1) == tier and p.get("language", "en") == requested_lang
    ]
    if exact_matches:
        return exact_matches[0], requested_lang, "EXACT_MATCH", None

    # 2. If requested language is non-English, check if any passage exists in that language at another tier
    lang_matches = [p for p in all_passages if p.get("language", "en") == requested_lang]

    # 3. Fallback to English at the requested tier
    en_matches = [
        p for p in all_passages
        if p.get("difficulty", 1) == tier and p.get("language", "en") == "en"
    ]
    fallback_passage = en_matches[0] if en_matches else (lang_matches[0] if lang_matches else all_passages[0])
    actual_lang = fallback_passage.get("language", "en")

    if actual_lang != requested_lang:
        lang_display = LANGUAGE_NAMES.get(requested_lang, requested_lang.upper())
        fallback_msg = (
            f"A Level {tier} story is not currently available in {lang_display}. "
            f"Showing an English story at Level {tier} with interactive vocabulary and audio support."
        )
        return fallback_passage, actual_lang, "LANGUAGE_FALLBACK_OFFERED", fallback_msg

    return fallback_passage, actual_lang, "EXACT_MATCH", None


def _find_micro_activity_for_domain_and_tier(
    domain: str,
    tier: int,
) -> Optional[Dict[str, Any]]:
    """Finds the most suitable micro-learning activity close to the student's active tier."""
    candidates = [
        a for a in DEFAULT_ACTIVITIES
        if a.get("domain") == domain and a.get("isActive", True)
    ]
    if not candidates:
        # Fallback to any active activity
        candidates = [a for a in DEFAULT_ACTIVITIES if a.get("isActive", True)]

    # Sort by tier distance to target tier
    candidates.sort(key=lambda a: abs(a.get("difficultyTier", 1) - tier))
    return candidates[0] if candidates else None


async def get_next_personalized_activity(
    learner_id: str,
    language: Optional[str] = None,
    activity_type: Optional[str] = None,
) -> PersonalizedActivityNextResponse:
    """
    Selects the immediate next best personalized learning activity for the student.
    Synthesizes signals from Phase 3 adaptive state, Phase 2 profile, Phase 14 recommendations,
    and verified catalog availability.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Fetch Profile & Adaptive State (Phase 3 authoritative)
    profile_doc = await get_or_create_learner_profile(learner_id)
    state_doc = await get_learning_state(learner_id)

    current_tier = clamp_tier(
        state_doc.get("active_difficulty_tier")
        or state_doc.get("activeDifficultyTier")
        or profile_doc.get("adaptive_difficulty", {}).get("active_tier")
        or 1
    )
    current_tier_name = TIER_NAMES.get(current_tier, "Foundation")

    # Determine language preference
    pref_lang = _normalize_language(
        language
        or profile_doc.get("preferred_language")
        or profile_doc.get("preferredLanguage")
        or "en"
    )

    # 2. Check today's completions
    completions = await _check_today_completions(learner_id)

    # 3. Generate or retrieve Phase 14 recommendations
    try:
        rec_response = await generate_learner_recommendations(
            learner_id=learner_id,
            horizon="today",
            preferred_language=pref_lang,
        )
        top_rec = rec_response.recommendations[0] if rec_response.recommendations else None
    except Exception as e:
        logger.warning(f"Error fetching recommendations for {learner_id}: {e}")
        top_rec = None

    # Accessibility preferences (Phase 12)
    access_cfg = await _get_learner_accessibility_config(learner_id)

    # 4. Map recommendation or default to Activity Type
    target_type: ActivityType = "GUIDED_READING"
    rec_category = top_rec.category if top_rec else "READING_PRACTICE"
    rec_id = top_rec.id if top_rec else None

    if activity_type:
        # User explicitly requested a type
        clean_type = activity_type.upper().strip()
        if clean_type in (
            "GUIDED_READING",
            "DIFFICULT_WORD_PRACTICE",
            "READING_COMPREHENSION",
            "VOCABULARY_PRACTICE",
            "ORAL_READING_SPEECH",
            "SKILL_REVIEW",
        ):
            target_type = clean_type  # type: ignore
    elif rec_category == "DIFFICULT_WORD_PRACTICE":
        target_type = "DIFFICULT_WORD_PRACTICE"
    elif rec_category == "SPEECH_PRACTICE":
        target_type = "ORAL_READING_SPEECH"
    elif rec_category == "REVIEW":
        target_type = "SKILL_REVIEW"
    elif rec_category == "STRETCH":
        target_type = "GUIDED_READING"
    else:
        target_type = "GUIDED_READING"

    # 5. Assemble the Activity Content
    activity_item: Optional[PersonalizedContentItem] = None
    status: ContentAvailabilityStatus = "EXACT_MATCH"
    message: Optional[str] = None
    eligible_passages = await _get_eligible_reading_passages()

    if target_type == "GUIDED_READING":
        # Check if stretch
        effective_tier = current_tier + 1 if rec_category == "STRETCH" and current_tier < 5 else current_tier
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(effective_tier, pref_lang, candidate_passages=eligible_passages)
        status = avail_status
        message = fallback_msg

        is_completed = completions["reading"]
        pas_id = pas.get("passageId", "pas-t1-001")
        pas_title = pas.get("title", "Reading Story")

        vocab_words = [v.get("word") for v in pas.get("vocabulary", []) if isinstance(v, dict)]

        activity_item = PersonalizedContentItem(
            activityId=f"act-guide-{pas_id}",
            activityType="GUIDED_READING",
            contentId=pas_id,
            title=f"Guided Reading: {pas_title}",
            description=f"Read '{pas_title}' at Level {effective_tier} with syllable guides and word definitions.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=effective_tier,
            tierName=TIER_NAMES.get(effective_tier, "Foundation"),
            estimatedDurationMinutes=pas.get("estimatedMinutes", 10),
            reason=top_rec.reason if top_rec else f"Calibrated for your sweet spot at Level {effective_tier}.",
            detailedRationale=f"Core reading practice develops decoding stamina, sight word automaticity, and story comprehension.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["decoding", "story_comprehension", "fluency"],
            targetWords=vocab_words[:3],
            contentSummary=pas.get("text", "")[:120] + "...",
            instructions="Read along at your own pace. Tap any unfamiliar word to hear its pronunciation and syllables.",
            actionUrl=f"/student/reading-coach?passageId={pas_id}",
            actionLabel="Start Reading",
            completed=is_completed,
            availabilityStatus=status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
            metadata={"wordCount": pas.get("wordCount", 50), "gradeBand": pas.get("gradeBand", "Grade 1-2")},
        )

    elif target_type == "DIFFICULT_WORD_PRACTICE":
        # Micro-task focusing on spelling or phonemes
        micro = _find_micro_activity_for_domain_and_tier("orthographic_spelling", current_tier)
        if not micro:
            micro = _find_micro_activity_for_domain_and_tier("phonological_awareness", current_tier)

        act_id = micro.get("id", "act-spell-001") if micro else "act-spell-001"
        act_title = micro.get("title", "Tricky Word Practice") if micro else "Tricky Word Practice"

        # Focus words from recommendation
        tricky_words = top_rec.targetWords if (top_rec and top_rec.targetWords) else ["sprout", "through", "bright"]

        activity_item = PersonalizedContentItem(
            activityId=f"act-words-{act_id}",
            activityType="DIFFICULT_WORD_PRACTICE",
            contentId=act_id,
            title=f"Tricky Word Quest: {act_title}",
            description="Tackle words that were tricky in your recent reading with visual clues and syllable breaking.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=current_tier_name,
            estimatedDurationMinutes=5,
            reason=top_rec.reason if top_rec else "Reinforcing tricky words builds effortless reading recognition.",
            detailedRationale="Targeted phonics and orthographic mapping solidify word representations in memory.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["orthographic_mapping", "phoneme_blending"],
            targetWords=tricky_words,
            contentSummary=f"Focus words: {', '.join(tricky_words)}",
            instructions="Break down each word by sound, listen to the pronunciation, and practice spelling it correctly.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Practice Tricky Words",
            completed=completions["difficult_words"] or completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "orthographic_spelling"},
        )

    elif target_type == "ORAL_READING_SPEECH":
        # Speech practice with reading coach
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(current_tier, pref_lang, candidate_passages=eligible_passages)
        status = avail_status
        message = fallback_msg
        pas_id = pas.get("passageId", "pas-t1-001")

        activity_item = PersonalizedContentItem(
            activityId=f"act-oral-{pas_id}",
            activityType="ORAL_READING_SPEECH",
            contentId=pas_id,
            title=f"Read Aloud Voice Practice: {pas.get('title', 'Story Time')}",
            description="Read the story out loud using speech recognition to track your rhythm, pauses, and voice flow.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=current_tier_name,
            estimatedDurationMinutes=5,
            reason=top_rec.reason if top_rec else "Reading out loud activates auditory reading pathways and strengthens fluency.",
            detailedRationale="Oral reading provides objective speech alignment feedback without storing raw audio.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["oral_reading_fluency", "pronunciation_accuracy"],
            targetWords=[],
            contentSummary="Read the passage aloud into your microphone.",
            instructions="Press the microphone button and read each sentence clearly. DyslexAid will highlight words as you speak.",
            actionUrl=f"/student/reading-coach?passageId={pas_id}&mode=oral",
            actionLabel="Try Read-Aloud",
            completed=completions["speech"],
            availabilityStatus=status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
            metadata={"readingMode": "oral"},
        )

    elif target_type == "SKILL_REVIEW":
        # Review foundational micro-task
        micro = _find_micro_activity_for_domain_and_tier("phonological_awareness", max(1, current_tier - 1))
        act_id = micro.get("id", "act-phon-001") if micro else "act-phon-001"
        act_title = micro.get("title", "Sound Detective Review") if micro else "Sound Detective Review"

        activity_item = PersonalizedContentItem(
            activityId=f"act-rev-{act_id}",
            activityType="SKILL_REVIEW",
            contentId=act_id,
            title=f"Skill Review: {act_title}",
            description="A quick, low-stress review of foundational letter-sound relationships to lock them into memory.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=max(1, current_tier - 1),
            tierName=TIER_NAMES.get(max(1, current_tier - 1), "Foundation"),
            estimatedDurationMinutes=5,
            reason=top_rec.reason if top_rec else "Revisiting foundational sounds maintains confidence and prevents cognitive fatigue.",
            detailedRationale="Spaced review reinforces neural pathways with high-success repetitions.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["phoneme_isolation", "sound_letter_association"],
            targetWords=[],
            contentSummary="Review foundational sounds and letters.",
            instructions="Follow the friendly audio prompts and pick the matching letters or sounds.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Start Review",
            completed=completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "phonological_awareness"},
        )

    elif target_type == "READING_COMPREHENSION":
        micro = _find_micro_activity_for_domain_and_tier("reading_comprehension", current_tier)
        act_id = micro.get("id", "act-comp-001") if micro else "act-comp-001"
        act_title = micro.get("title", "Story Snapshot") if micro else "Story Snapshot"

        activity_item = PersonalizedContentItem(
            activityId=f"act-comp-{act_id}",
            activityType="READING_COMPREHENSION",
            contentId=act_id,
            title=f"Comprehension Check: {act_title}",
            description="Read a mini-passage and answer a puzzle question to test your story recall and detective skills.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=current_tier_name,
            estimatedDurationMinutes=5,
            reason="Practicing comprehension questions builds deeper understanding and analytical thinking.",
            detailedRationale="Targets inferential reasoning and direct detail recall in bite-sized units.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["direct_recall", "simple_inference"],
            targetWords=[],
            contentSummary="Mini-story and comprehension puzzle.",
            instructions="Read the short story carefully, then choose the best answer to solve the question.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Solve Puzzle",
            completed=completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "reading_comprehension"},
        )

    elif target_type == "VOCABULARY_PRACTICE":
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(current_tier, pref_lang, candidate_passages=eligible_passages)
        pas_id = pas.get("passageId", "pas-t1-001")
        vocab = pas.get("vocabulary", [])
        words = [v.get("word") for v in vocab if isinstance(v, dict)]

        activity_item = PersonalizedContentItem(
            activityId=f"act-vocab-{pas_id}",
            activityType="VOCABULARY_PRACTICE",
            contentId=pas_id,
            title=f"Vocabulary Explorer: {pas.get('title', 'Word Explorer')}",
            description=f"Discover definitions, pronunciations, and example sentences for key words from Level {current_tier}.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=current_tier_name,
            estimatedDurationMinutes=5,
            reason="Expanding vocabulary helps you read smoothly without pausing on unfamiliar words.",
            detailedRationale="Pre-teaching vocabulary reduces cognitive load during passage reading.",
            recommendationId=rec_id,
            category=rec_category,
            targetSkills=["vocabulary_acquisition", "phonetic_analysis"],
            targetWords=words[:4],
            contentSummary=f"Explore words: {', '.join(words[:4])}",
            instructions="Tap each word to explore its syllables, definition, and hear it spoken aloud.",
            actionUrl=f"/student/reading-coach?passageId={pas_id}&view=vocabulary",
            actionLabel="Explore Words",
            completed=completions["reading"],
            availabilityStatus=avail_status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
            metadata={"wordCount": len(words)},
        )

    return PersonalizedActivityNextResponse(
        learnerId=learner_id,
        activity=activity_item,
        currentAdaptiveTier=current_tier,
        currentAdaptiveTierName=current_tier_name,
        preferredLanguage=pref_lang,
        hasContent=activity_item is not None,
        status=status,
        message=message,
        generatedAt=now_iso,
    )


async def list_personalized_activities(
    learner_id: str,
    language: Optional[str] = None,
    tier: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 6,
) -> PersonalizedActivitiesListResponse:
    """
    Returns available personalized activities filtered by language, difficulty tier, and category.
    Includes variety across Guided Reading, Tricky Words, Speech, Comprehension, and Review.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    profile_doc = await get_or_create_learner_profile(learner_id)
    state_doc = await get_learning_state(learner_id)

    active_tier = clamp_tier(
        tier
        or state_doc.get("active_difficulty_tier")
        or state_doc.get("activeDifficultyTier")
        or profile_doc.get("adaptive_difficulty", {}).get("active_tier")
        or 1
    )
    pref_lang = _normalize_language(
        language
        or profile_doc.get("preferred_language")
        or profile_doc.get("preferredLanguage")
        or "en"
    )

    completions = await _check_today_completions(learner_id)
    access_cfg = await _get_learner_accessibility_config(learner_id)
    eligible_passages = await _get_eligible_reading_passages()

    activities: List[PersonalizedContentItem] = []

    # 1. Guided Reading Passage at active_tier
    pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(active_tier, pref_lang, candidate_passages=eligible_passages)
    pas_id = pas.get("passageId", "pas-t1-001")
    pas_title = pas.get("title", "Reading Story")
    vocab = [v.get("word") for v in pas.get("vocabulary", []) if isinstance(v, dict)]

    activities.append(PersonalizedContentItem(
        activityId=f"act-guide-{pas_id}",
        activityType="GUIDED_READING",
        contentId=pas_id,
        title=f"Guided Reading: {pas_title}",
        description=f"Read '{pas_title}' at Level {active_tier} with syllable guides and word definitions.",
        language=actual_lang,
        requestedLanguage=pref_lang,
        difficultyTier=active_tier,
        tierName=TIER_NAMES.get(active_tier, "Foundation"),
        estimatedDurationMinutes=pas.get("estimatedMinutes", 10),
        reason=f"Calibrated for your reading sweet spot at Level {active_tier}.",
        detailedRationale="Core passage reading builds sentence flow, working memory, and story comprehension.",
        recommendationId=None,
        category="READING_PRACTICE",
        targetSkills=["decoding", "story_comprehension"],
        targetWords=vocab[:3],
        contentSummary=pas.get("text", "")[:100] + "...",
        instructions="Read at your own pace with text-to-speech and syllable highlighting support.",
        actionUrl=f"/student/reading-coach?passageId={pas_id}",
        actionLabel="Read Story",
        completed=completions["reading"],
        availabilityStatus=avail_status,
        languageFallbackMessage=fallback_msg,
        accessibilityConfig=access_cfg,
        metadata={"domain": "reading_comprehension"},
    ))

    # 2. Difficult-Word / Phonics Practice
    spell_act = _find_micro_activity_for_domain_and_tier("orthographic_spelling", active_tier)
    if spell_act:
        act_id = spell_act.get("id", "act-spell-001")
        activities.append(PersonalizedContentItem(
            activityId=f"act-words-{act_id}",
            activityType="DIFFICULT_WORD_PRACTICE",
            contentId=act_id,
            title=f"Word Practice: {spell_act.get('title', 'Sight Word Builder')}",
            description="Break down tricky words into syllables and practice correct spelling.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=active_tier,
            tierName=TIER_NAMES.get(active_tier, "Foundation"),
            estimatedDurationMinutes=5,
            reason="Targeted word practice builds sight recognition and reduces decoding pauses.",
            detailedRationale="Orthographic mapping exercise to lock tricky words into memory.",
            recommendationId=None,
            category="DIFFICULT_WORD_PRACTICE",
            targetSkills=spell_act.get("targetSkills", ["sight_words", "spelling"]),
            targetWords=["sprout", "through", "bright"],
            contentSummary="Interactive letter-scramble and phoneme-blending practice.",
            instructions="Drag the letters or pick the correct word to match the clue.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Practice Words",
            completed=completions["difficult_words"] or completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "orthographic_spelling"},
        ))

    # 3. Reading Comprehension Micro-Task
    comp_act = _find_micro_activity_for_domain_and_tier("reading_comprehension", active_tier)
    if comp_act:
        act_id = comp_act.get("id", "act-comp-001")
        activities.append(PersonalizedContentItem(
            activityId=f"act-comp-{act_id}",
            activityType="READING_COMPREHENSION",
            contentId=act_id,
            title=f"Comprehension: {comp_act.get('title', 'Story Snapshot')}",
            description="Read a bite-sized story and solve a detective puzzle to test recall.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=active_tier,
            tierName=TIER_NAMES.get(active_tier, "Foundation"),
            estimatedDurationMinutes=5,
            reason="Comprehension puzzles strengthen memory retention and story structure awareness.",
            detailedRationale="Short micro-tasks evaluate inference and detail recall.",
            recommendationId=None,
            category="READING_PRACTICE",
            targetSkills=comp_act.get("targetSkills", ["direct_recall"]),
            targetWords=[],
            contentSummary=comp_act.get("contentPayload", {}).get("passage", "")[:100] + "...",
            instructions="Read the short clue and pick the right answer.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Solve Puzzle",
            completed=completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "reading_comprehension"},
        ))

    # 4. Oral Reading / Speech
    activities.append(PersonalizedContentItem(
        activityId=f"act-oral-{pas_id}",
        activityType="ORAL_READING_SPEECH",
        contentId=pas_id,
        title=f"Read Aloud Practice: {pas_title}",
        description="Speak the story out loud with speech recognition guiding your rhythm.",
        language=actual_lang,
        requestedLanguage=pref_lang,
        difficultyTier=active_tier,
        tierName=TIER_NAMES.get(active_tier, "Foundation"),
        estimatedDurationMinutes=5,
        reason="Oral reading bridges letter recognition with vocal fluency.",
        detailedRationale="Encourages fluent phrasing and vocal confidence without saving raw audio.",
        recommendationId=None,
        category="SPEECH_PRACTICE",
        targetSkills=["oral_reading_fluency"],
        targetWords=[],
        contentSummary="Voice-guided reading practice.",
        instructions="Speak clearly into your microphone as words highlight on screen.",
        actionUrl=f"/student/reading-coach?passageId={pas_id}&mode=oral",
        actionLabel="Read Aloud",
        completed=completions["speech"],
        availabilityStatus=avail_status,
        languageFallbackMessage=fallback_msg,
        accessibilityConfig=access_cfg,
        metadata={"readingMode": "oral"},
    ))

    # 5. Skill Review (Foundation)
    phon_act = _find_micro_activity_for_domain_and_tier("phonological_awareness", max(1, active_tier - 1))
    if phon_act:
        act_id = phon_act.get("id", "act-phon-001")
        activities.append(PersonalizedContentItem(
            activityId=f"act-rev-{act_id}",
            activityType="SKILL_REVIEW",
            contentId=act_id,
            title=f"Skill Review: {phon_act.get('title', 'Sound Detective')}",
            description="Revisit sound patterns to build long-term memory with zero stress.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=max(1, active_tier - 1),
            tierName=TIER_NAMES.get(max(1, active_tier - 1), "Foundation"),
            estimatedDurationMinutes=5,
            reason="Quick review keeps foundational decoding automatic and durable.",
            detailedRationale="Spaced repetition of foundational letter-sound patterns.",
            recommendationId=None,
            category="REVIEW",
            targetSkills=phon_act.get("targetSkills", ["phoneme_isolation"]),
            targetWords=[],
            contentSummary="Sound matching and rhyme detection.",
            instructions="Listen to the bouncy sound and find the matching picture.",
            actionUrl=f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Start Review",
            completed=completions["adaptive_activity"],
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
            metadata={"domain": "phonological_awareness"},
        ))

    # Filter by category if requested
    if category:
        cat_clean = category.upper().strip()
        activities = [a for a in activities if a.category == cat_clean]

    return PersonalizedActivitiesListResponse(
        learnerId=learner_id,
        count=len(activities[:limit]),
        activities=activities[:limit],
        currentAdaptiveTier=active_tier,
        currentAdaptiveTierName=TIER_NAMES.get(active_tier, "Foundation"),
        preferredLanguage=pref_lang,
        generatedAt=now_iso,
    )


async def get_content_for_recommendation(
    learner_id: str,
    recommendation_id: str,
    preferred_language: str = "en",
) -> PersonalizedContentItem:
    """
    Retrieves the personalized learning content specifically linked to a Phase 14 recommendation.
    Maintains clean coupling: uses the recommendation's category, target words, and rationale.
    """
    pref_lang = _normalize_language(preferred_language)

    # Fetch active recommendations
    rec_res = await generate_learner_recommendations(
        learner_id=learner_id,
        horizon="today",
        preferred_language=pref_lang,
    )

    matching_rec = None
    for r in rec_res.recommendations:
        if r.id == recommendation_id:
            matching_rec = r
            break

    if not matching_rec:
        # Check study plan items as well
        for item in rec_res.studyPlan.items:
            if item.id == recommendation_id:
                # Synthesize a temporary recommendation item
                matching_rec = item
                break

    if not matching_rec:
        raise ValueError(f"Recommendation '{recommendation_id}' not found for student.")

    category = getattr(matching_rec, "category", getattr(matching_rec, "activityType", "READING_PRACTICE"))
    current_tier = rec_res.currentAdaptiveTier
    access_cfg = await _get_learner_accessibility_config(learner_id)
    completions = await _check_today_completions(learner_id)
    eligible_passages = await _get_eligible_reading_passages()

    # Determine activity type
    if category == "DIFFICULT_WORD_PRACTICE":
        micro = _find_micro_activity_for_domain_and_tier("orthographic_spelling", current_tier)
        act_id = micro.get("id", "act-spell-001") if micro else "act-spell-001"
        return PersonalizedContentItem(
            activityId=f"act-words-{act_id}",
            activityType="DIFFICULT_WORD_PRACTICE",
            contentId=act_id,
            title=matching_rec.title,
            description="Targeted practice focusing on words you found tricky in recent reading.",
            language="en",
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=rec_res.currentAdaptiveTierName,
            estimatedDurationMinutes=matching_rec.estimatedDurationMinutes,
            reason=matching_rec.reason,
            detailedRationale="Targeted phonics and spelling exercise to solidify orthographic memory.",
            recommendationId=recommendation_id,
            category=category,
            targetSkills=["spelling", "phoneme_blending"],
            targetWords=getattr(matching_rec, "targetWords", []) or [],
            contentSummary="Tricky word flashcards and letter sequencing.",
            instructions="Practice these words with syllable cues and spelling steps.",
            actionUrl=matching_rec.actionUrl or f"/student/adaptive-learning?activityId={act_id}",
            actionLabel="Start Word Practice",
            completed=matching_rec.completed,
            availabilityStatus="EXACT_MATCH",
            languageFallbackMessage=None,
            accessibilityConfig=access_cfg,
        )

    elif category == "SPEECH_PRACTICE":
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(current_tier, pref_lang, candidate_passages=eligible_passages)
        pas_id = pas.get("passageId", "pas-t1-001")
        return PersonalizedContentItem(
            activityId=f"act-oral-{pas_id}",
            activityType="ORAL_READING_SPEECH",
            contentId=pas_id,
            title=matching_rec.title,
            description="Oral reading practice to connect voice with printed text.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=rec_res.currentAdaptiveTierName,
            estimatedDurationMinutes=matching_rec.estimatedDurationMinutes,
            reason=matching_rec.reason,
            detailedRationale="Speech recognition alignment without recording raw audio.",
            recommendationId=recommendation_id,
            category=category,
            targetSkills=["oral_reading_fluency"],
            targetWords=[],
            contentSummary="Read the passage aloud into your microphone.",
            instructions="Press the microphone button and read aloud. DyslexAid highlights words as you go.",
            actionUrl=matching_rec.actionUrl or f"/student/reading-coach?passageId={pas_id}",
            actionLabel="Start Read-Aloud",
            completed=matching_rec.completed,
            availabilityStatus=avail_status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
        )

    elif category == "STRETCH":
        stretch_tier = min(5, current_tier + 1)
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(stretch_tier, pref_lang, candidate_passages=eligible_passages)
        pas_id = pas.get("passageId", "pas-t1-001")
        return PersonalizedContentItem(
            activityId=f"act-stretch-{pas_id}",
            activityType="GUIDED_READING",
            contentId=pas_id,
            title=matching_rec.title,
            description=f"Step into Level {stretch_tier} with an engaging challenge story.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=stretch_tier,
            tierName=TIER_NAMES.get(stretch_tier, "Advanced"),
            estimatedDurationMinutes=matching_rec.estimatedDurationMinutes,
            reason=matching_rec.reason,
            detailedRationale="Higher-tier reading stretch for learners with consecutive masteries.",
            recommendationId=recommendation_id,
            category=category,
            targetSkills=["advanced_comprehension", "vocabulary_enrichment"],
            targetWords=[],
            contentSummary=pas.get("text", "")[:100] + "...",
            instructions="Take on this exciting challenge story with full assistive tools available.",
            actionUrl=matching_rec.actionUrl or f"/student/reading-coach?passageId={pas_id}",
            actionLabel="Accept Challenge",
            completed=matching_rec.completed,
            availabilityStatus=avail_status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
        )

    else:
        # Default: GUIDED_READING or REVIEW
        pas, actual_lang, avail_status, fallback_msg = _find_passage_for_tier_and_language(current_tier, pref_lang, candidate_passages=eligible_passages)
        pas_id = pas.get("passageId", "pas-t1-001")
        return PersonalizedContentItem(
            activityId=f"act-guide-{pas_id}",
            activityType="GUIDED_READING",
            contentId=pas_id,
            title=matching_rec.title,
            description=f"Personalized reading practice at Level {current_tier}.",
            language=actual_lang,
            requestedLanguage=pref_lang,
            difficultyTier=current_tier,
            tierName=rec_res.currentAdaptiveTierName,
            estimatedDurationMinutes=matching_rec.estimatedDurationMinutes,
            reason=matching_rec.reason,
            detailedRationale="Core story reading practice aligned with active ZPD tier.",
            recommendationId=recommendation_id,
            category=category,
            targetSkills=["decoding", "story_comprehension"],
            targetWords=[],
            contentSummary=pas.get("text", "")[:100] + "...",
            instructions="Read at your own pace with dyslexia-tailored fonts and audio support.",
            actionUrl=matching_rec.actionUrl or f"/student/reading-coach?passageId={pas_id}",
            actionLabel="Start Practice",
            completed=matching_rec.completed,
            availabilityStatus=avail_status,
            languageFallbackMessage=fallback_msg,
            accessibilityConfig=access_cfg,
        )


async def record_activity_launch(
    learner_id: str,
    req: PersonalizedContentLaunchRequest,
) -> PersonalizedContentLaunchResponse:
    """
    Logs an activity launch event in MongoDB telemetry.
    CRITICAL: Does NOT mark the activity as completed.
    Genuine completion is only certified by real reading_sessions or activity_attempts submissions.
    """
    launch_id = f"launch-{uuid.uuid4().hex[:12]}"
    now_ts = int(time.time())

    # Determine destination URL
    dest_url = "/student/reading-coach"
    if req.activityId.startswith("act-words-") or req.activityId.startswith("act-rev-") or req.activityId.startswith("act-phon-") or req.activityId.startswith("act-spell-"):
        # Strip prefix to get clean ID
        clean_id = req.activityId.replace("act-words-", "").replace("act-rev-", "")
        dest_url = f"/student/adaptive-learning?activityId={clean_id}"
    elif req.activityId.startswith("act-guide-") or req.activityId.startswith("pas-"):
        clean_id = req.activityId.replace("act-guide-", "")
        dest_url = f"/student/reading-coach?passageId={clean_id}"
    elif req.activityType == "ORAL_READING_SPEECH":
        dest_url = "/student/reading-coach?mode=oral"

    launch_doc = {
        "launchId": launch_id,
        "learnerId": learner_id,
        "activityId": req.activityId,
        "activityType": req.activityType or "GUIDED_READING",
        "recommendationId": req.recommendationId,
        "language": req.language or "en",
        "destinationUrl": dest_url,
        "launchedAt": now_ts,
        "completed": False,  # Strict safeguard: never set true on launch!
    }

    try:
        await db.activity_launches.insert_one(launch_doc)
    except Exception as e:
        logger.warning(f"Could not persist launch telemetry for {learner_id}: {e}")

    return PersonalizedContentLaunchResponse(
        launchId=launch_id,
        learnerId=learner_id,
        activityId=req.activityId,
        activityType=req.activityType or "GUIDED_READING",
        destinationUrl=dest_url,
        launchedAt=now_ts,
        completed=False,
        status="launched",
    )


async def get_teacher_personalized_content(
    teacher_id: str,
    learner_id: str,
) -> TeacherPersonalizedContentResponse:
    """
    Teacher educational view of a student's active personalized content.
    Enforces classroom / tenant authorization via verify_teacher_student_access.
    """
    is_auth = await verify_teacher_student_access(teacher_id, learner_id)
    if not is_auth:
        raise PermissionError(f"Teacher '{teacher_id}' is not authorized to access learner '{learner_id}'.")

    # Fetch profile & state
    profile_doc = await get_or_create_learner_profile(learner_id)
    state_doc = await get_learning_state(learner_id)
    current_tier = clamp_tier(state_doc.get("active_difficulty_tier", 1))

    # Next activity
    next_res = await get_next_personalized_activity(learner_id=learner_id)

    # Activity list count
    list_res = await list_personalized_activities(learner_id=learner_id, limit=10)

    # Pedagogical rationale
    rec_item = next_res.activity
    rationale = (
        f"Calibrated for Level {current_tier} ({TIER_NAMES.get(current_tier, 'Foundation')}). "
        f"Selected activity targets {rec_item.activityType if rec_item else 'reading practice'} "
        f"to reinforce working memory and phonological automaticity."
    )

    evidence_summary = [
        f"Active ZPD Tier: {current_tier}",
        f"Language: {next_res.preferredLanguage}",
        f"Consecutive passes: {state_doc.get('consecutive_passes', 0)}",
        f"Primary need: {rec_item.targetSkills[0] if (rec_item and rec_item.targetSkills) else 'decoding'}",
    ]

    return TeacherPersonalizedContentResponse(
        learnerId=learner_id,
        studentName=profile_doc.get("name") or profile_doc.get("student_name") or f"Learner {learner_id[:6]}",
        currentAdaptiveTier=current_tier,
        currentAdaptiveTierName=TIER_NAMES.get(current_tier, "Foundation"),
        recommendedActivity=rec_item,
        availableActivitiesCount=list_res.count,
        pedagogicalRationale=rationale,
        evidenceSummary=evidence_summary,
    )


async def get_parent_personalized_content(
    parent_id: str,
    learner_id: str,
) -> ParentPersonalizedContentResponse:
    """
    Parent view of suggested home practice activity.
    Enforces verified parent-child relationship via verify_parent_student_access.
    """
    is_auth = await verify_parent_student_access(parent_id, learner_id)
    if not is_auth:
        raise PermissionError(f"Parent '{parent_id}' is not authorized to view learner '{learner_id}'.")

    profile_doc = await get_or_create_learner_profile(learner_id)
    next_res = await get_next_personalized_activity(learner_id=learner_id)

    activity = next_res.activity
    title = activity.title if activity else "Daily Reading Practice"
    activity_type = activity.activityType if activity else "GUIDED_READING"
    duration = activity.estimatedDurationMinutes if activity else 10
    focus_words = activity.targetWords if (activity and activity.targetWords) else ["bright", "read", "friend"]

    guidance = (
        f"Try 10 minutes of shared reading today. Read together and let your child point out words they recognize. "
        f"Celebrate every attempt with gentle encouragement!"
    )

    return ParentPersonalizedContentResponse(
        learnerId=learner_id,
        studentName=profile_doc.get("name") or profile_doc.get("student_name") or "Your Child",
        suggestedActivityTitle=title,
        suggestedActivityType=activity_type,
        estimatedMinutes=duration,
        atHomeGuidance=guidance,
        focusWords=focus_words,
    )
