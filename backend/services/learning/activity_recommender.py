"""
backend/services/learning/activity_recommender.py — Adaptive Activity Recommender.

Matches interactive micro-learning tasks to a student's Zone of Proximal Development (ZPD)
based on their V2 Learner Intelligence Profile, current difficulty tier, strengths, and areas to practice.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from database.database import db
from models.v2_learning_state import LearningActivity, AdaptiveRecommendation
from services.learning.difficulty_engine import clamp_tier

logger = logging.getLogger("dyslexaid.activity_recommender")

# ─── Default Micro-Task Activity Catalog ─────────────────────────────────────
# Covers key cognitive/reading domains across Tiers 1 through 5 with child-friendly interactive payloads.
DEFAULT_ACTIVITIES: List[Dict[str, Any]] = [
    # ── Phonological Awareness (Tiers 1-4) ──
    {
        "id": "act-phon-001",
        "title": "First Sound Detective",
        "domain": "phonological_awareness",
        "difficultyTier": 1,
        "targetSkills": ["initial_phoneme_isolation", "sound_letter_association"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "multiple_choice_audio",
            "instruction": "Listen to the word and pick the picture that starts with the same sound!",
            "targetSound": "/b/",
            "promptWord": "Ball",
            "audioPrompt": "Which word starts with the /b/ sound like Ball?",
            "options": [
                {"id": "opt-1", "text": "Bat", "icon": "🏏", "isCorrect": True},
                {"id": "opt-2", "text": "Cat", "icon": "🐱", "isCorrect": False},
                {"id": "opt-3", "text": "Sun", "icon": "☀️", "isCorrect": False},
                {"id": "opt-4", "text": "Dog", "icon": "🐶", "isCorrect": False},
            ],
            "hint": "Put your lips together and make the /b/ sound!",
            "explanation": "Great job! Bat and Ball both start with the bouncy /b/ sound!",
        },
        "isActive": True,
    },
    {
        "id": "act-phon-002",
        "title": "Phoneme Blending Rocket",
        "domain": "phonological_awareness",
        "difficultyTier": 2,
        "targetSkills": ["phoneme_blending", "cvc_words"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "phoneme_blend",
            "instruction": "Listen to the separated sounds and slide them together into one word!",
            "phonemes": ["/f/", "/l/", "/æ/", "/g/"],
            "targetWord": "Flag",
            "audioPrompt": "/f/ - /l/ - /æ/ - /g/",
            "options": [
                {"id": "opt-1", "text": "Frog", "isCorrect": False},
                {"id": "opt-2", "text": "Flag", "isCorrect": True},
                {"id": "opt-3", "text": "Flat", "isCorrect": False},
                {"id": "opt-4", "text": "Flow", "isCorrect": False},
            ],
            "hint": "Blend the first two sounds: /f/ and /l/ make /fl/!",
            "explanation": "Super! /f/ /l/ /æ/ /g/ together makes Flag!",
        },
        "isActive": True,
    },
    {
        "id": "act-phon-003",
        "title": "Rhyme Time Matcher",
        "domain": "phonological_awareness",
        "difficultyTier": 2,
        "targetSkills": ["rhyme_detection", "rime_awareness"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "rhyme_match",
            "instruction": "Find the word that rhymes with the target word!",
            "targetWord": "Ring",
            "audioPrompt": "Which word rhymes with Ring?",
            "options": [
                {"id": "opt-1", "text": "King", "icon": "👑", "isCorrect": True},
                {"id": "opt-2", "text": "Rock", "icon": "🪨", "isCorrect": False},
                {"id": "opt-3", "text": "Rain", "icon": "🌧️", "isCorrect": False},
                {"id": "opt-4", "text": "Star", "icon": "⭐", "isCorrect": False},
            ],
            "hint": "Listen to the ending sound: -ing!",
            "explanation": "Yes! King and Ring both end with the bright -ing sound!",
        },
        "isActive": True,
    },
    {
        "id": "act-phon-004",
        "title": "Syllable Clap-Along",
        "domain": "phonological_awareness",
        "difficultyTier": 3,
        "targetSkills": ["syllable_segmentation", "polysyllabic_words"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "syllable_count",
            "instruction": "How many beats (syllables) are in this word? Clap as you say it!",
            "targetWord": "Butterfly",
            "audioPrompt": "But - ter - fly. How many syllables?",
            "syllables": ["But", "ter", "fly"],
            "options": [
                {"id": "opt-1", "text": "1", "isCorrect": False},
                {"id": "opt-2", "text": "2", "isCorrect": False},
                {"id": "opt-3", "text": "3", "isCorrect": True},
                {"id": "opt-4", "text": "4", "isCorrect": False},
            ],
            "hint": "Put your hand under your chin. Each time your chin drops, that's one beat!",
            "explanation": "Awesome! But-ter-fly has 3 syllables!",
        },
        "isActive": True,
    },

    # ── Rapid Automatized Naming (RAN) (Tiers 1-3) ──
    {
        "id": "act-ran-001",
        "title": "Speed Color Sprint",
        "domain": "rapid_naming",
        "difficultyTier": 1,
        "targetSkills": ["visual_verbal_retrieval", "color_naming_automaticity"],
        "durationSecondsExpected": 60,
        "contentPayload": {
            "type": "speed_naming",
            "instruction": "Name the colors across the grid from left to right as briskly as you can!",
            "items": [
                {"id": "c1", "label": "Red", "color": "#E53E3E"},
                {"id": "c2", "label": "Blue", "color": "#3182CE"},
                {"id": "c3", "label": "Green", "color": "#38A169"},
                {"id": "c4", "label": "Yellow", "color": "#D69E2E"},
                {"id": "c5", "label": "Blue", "color": "#3182CE"},
                {"id": "c6", "label": "Red", "color": "#E53E3E"},
            ],
            "expectedSeconds": 15,
            "hint": "Follow with your finger and keep a steady rhythm!",
            "explanation": "Speedy! Practicing quick color names helps your brain retrieve words faster when reading!",
        },
        "isActive": True,
    },
    {
        "id": "act-ran-002",
        "title": "Letter Rapid Dash",
        "domain": "rapid_naming",
        "difficultyTier": 2,
        "targetSkills": ["letter_naming_speed", "phonological_lexical_access"],
        "durationSecondsExpected": 60,
        "contentPayload": {
            "type": "speed_naming",
            "instruction": "Say these letters out loud one by one smoothly!",
            "items": [
                {"id": "l1", "label": "A"},
                {"id": "l2", "label": "M"},
                {"id": "l3", "label": "S"},
                {"id": "l4", "label": "T"},
                {"id": "l5", "label": "P"},
                {"id": "l6", "label": "A"},
            ],
            "expectedSeconds": 12,
            "hint": "Take a breath and read from left to right like a train on a track!",
            "explanation": "Brilliant dash! Quick letter naming builds fluent, effortless reading!",
        },
        "isActive": True,
    },

    # ── Orthographic & Spelling (Tiers 1-4) ──
    {
        "id": "act-spell-001",
        "title": "Sight Word Builder: 'THE'",
        "domain": "orthographic_spelling",
        "difficultyTier": 1,
        "targetSkills": ["sight_word_recognition", "letter_sequencing"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "letter_scramble",
            "instruction": "Drag the letters in the correct order to spell the word 'THE'!",
            "targetWord": "THE",
            "scrambledLetters": ["E", "T", "H"],
            "hint": "The word starts with 'T' and ends with 'E'.",
            "explanation": "Wonderful! T - H - E spells 'the' — you will see this word in every story!",
        },
        "isActive": True,
    },
    {
        "id": "act-spell-002",
        "title": "Magic 'e' Word Transformer",
        "domain": "orthographic_spelling",
        "difficultyTier": 2,
        "targetSkills": ["silent_e_rule", "long_vowel_patterns"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "word_transform",
            "instruction": "Add the magic silent 'e' to change short 'cap' into long 'cape'!",
            "baseWord": "cap",
            "targetWord": "cape",
            "meaningSentence": "The superhero wore a red ___.",
            "options": [
                {"id": "opt-1", "text": "cape", "isCorrect": True},
                {"id": "opt-2", "text": "cap", "isCorrect": False},
                {"id": "opt-3", "text": "cop", "isCorrect": False},
            ],
            "hint": "Magic 'e' jumps over the consonant to make 'a' say its own name!",
            "explanation": "Magic! 'Cap' becomes 'Cape' when silent 'e' arrives at the end!",
        },
        "isActive": True,
    },
    {
        "id": "act-spell-003",
        "title": "Vowel Team Quest: 'EA' & 'EE'",
        "domain": "orthographic_spelling",
        "difficultyTier": 3,
        "targetSkills": ["vowel_digraphs", "orthographic_mapping"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "multiple_choice",
            "instruction": "Which vowel team completes the word: B _ _ C H (Sandy shore)?",
            "incompleteWord": "B _ _ C H",
            "options": [
                {"id": "opt-1", "text": "ea (BEACH)", "isCorrect": True},
                {"id": "opt-2", "text": "ee (BEECH)", "isCorrect": False},
                {"id": "opt-3", "text": "oa (BOACH)", "isCorrect": False},
            ],
            "hint": "When two vowels go walking, the first one does the talking! Think of the ocean shore.",
            "explanation": "Spot on! B-E-A-C-H is the sandy shore where waves splash!",
        },
        "isActive": True,
    },

    # ── Letter Orientation & Reversal (b / d / p / q) ──
    {
        "id": "act-rev-001",
        "title": "Letter Bed: 'b' vs 'd' Hero",
        "domain": "letter_reversal",
        "difficultyTier": 1,
        "targetSkills": ["letter_orientation", "visual_directionality"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "visual_discrimination",
            "instruction": "Remember the word BED: 'b' is the headboard on the left, 'd' is the footboard on the right! Find the letter 'b'!",
            "targetLetter": "b",
            "audioPrompt": "Click the letter 'b' with its tummy facing right!",
            "options": [
                {"id": "opt-1", "text": "b", "isCorrect": True},
                {"id": "opt-2", "text": "d", "isCorrect": False},
                {"id": "opt-3", "text": "p", "isCorrect": False},
                {"id": "opt-4", "text": "q", "isCorrect": False},
            ],
            "hint": "Make two fists with thumbs up. Left hand makes 'b', right hand makes 'd'!",
            "explanation": "You got it! 'b' has its line first, then a belly facing right!",
        },
        "isActive": True,
    },
    {
        "id": "act-rev-002",
        "title": "Word Fix: Dog or Bog?",
        "domain": "letter_reversal",
        "difficultyTier": 2,
        "targetSkills": ["contextual_letter_disambiguation"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "multiple_choice",
            "instruction": "Look at the cute puppy. Which word spells 'dog'?",
            "imageIcon": "🐶",
            "options": [
                {"id": "opt-1", "text": "dog", "isCorrect": True},
                {"id": "opt-2", "text": "bog", "isCorrect": False},
                {"id": "opt-3", "text": "pog", "isCorrect": False},
            ],
            "hint": "'d' has the circle first on the left, then the tall door on the right!",
            "explanation": "Woof! 'dog' starts with letter 'd'!",
        },
        "isActive": True,
    },

    # ── Reading Comprehension (Tiers 2-4) ──
    {
        "id": "act-comp-001",
        "title": "Story Snapshot: The Brave Squirrel",
        "domain": "reading_comprehension",
        "difficultyTier": 2,
        "targetSkills": ["direct_recall", "reading_for_details"],
        "durationSecondsExpected": 150,
        "contentPayload": {
            "type": "passage_comprehension",
            "passage": "Pip the squirrel found a shiny golden acorn under an oak tree. He decided to share it with his friend Bella. Together, they planted it in the sunny garden.",
            "question": "What did Pip find under the oak tree?",
            "options": [
                {"id": "opt-1", "text": "A shiny golden acorn", "isCorrect": True},
                {"id": "opt-2", "text": "A little blue bird", "isCorrect": False},
                {"id": "opt-3", "text": "A sweet red apple", "isCorrect": False},
            ],
            "hint": "Check the first sentence to see what Pip found!",
            "explanation": "Terrific! Pip found a shiny golden acorn under the oak tree.",
        },
        "isActive": True,
    },
    {
        "id": "act-comp-002",
        "title": "Inference Detective: Why Was Leo Wet?",
        "domain": "reading_comprehension",
        "difficultyTier": 3,
        "targetSkills": ["inferential_reasoning", "cause_and_effect"],
        "durationSecondsExpected": 180,
        "contentPayload": {
            "type": "passage_comprehension",
            "passage": "Leo walked inside and took off his dripping yellow raincoat. Thunder rumbled outside as drops tapped on the window glass.",
            "question": "Why was Leo's yellow raincoat dripping?",
            "options": [
                {"id": "opt-1", "text": "It was raining stormily outside", "isCorrect": True},
                {"id": "opt-2", "text": "He spilled his water bottle", "isCorrect": False},
                {"id": "opt-3", "text": "He was washing his coat in the sink", "isCorrect": False},
            ],
            "hint": "Notice clues like 'thunder' and 'drops tapped on the window'!",
            "explanation": "Great clue-hunting! The thunder and window drops show that it was raining outside!",
        },
        "isActive": True,
    },

    # ── Visual Processing & Attention (Tiers 1-3) ──
    {
        "id": "act-vis-001",
        "title": "Shape & Symbol Match",
        "domain": "visual_processing",
        "difficultyTier": 1,
        "targetSkills": ["visual_pattern_recognition", "form_constancy"],
        "durationSecondsExpected": 90,
        "contentPayload": {
            "type": "visual_match",
            "instruction": "Find the twin shape that matches the target shape exactly!",
            "targetShape": "⭐",
            "options": [
                {"id": "opt-1", "shape": "⭐", "isCorrect": True},
                {"id": "opt-2", "shape": "🌟", "isCorrect": False},
                {"id": "opt-3", "shape": "✨", "isCorrect": False},
                {"id": "opt-4", "shape": "💠", "isCorrect": False},
            ],
            "hint": "Look closely at the points and outline!",
            "explanation": "Sharp eyes! You spotted the identical star shape!",
        },
        "isActive": True,
    },
    {
        "id": "act-vis-002",
        "title": "Line Focus Guide",
        "domain": "visual_attention",
        "difficultyTier": 2,
        "targetSkills": ["visual_tracking", "line_isolation"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "line_tracking",
            "instruction": "Track the highlighted line and find the hidden word in the sentence!",
            "sentence": "The friendly cat slept on the warm rug.",
            "highlightWord": "slept",
            "question": "What did the friendly cat do on the warm rug?",
            "options": [
                {"id": "opt-1", "text": "slept", "isCorrect": True},
                {"id": "opt-2", "text": "jumped", "isCorrect": False},
                {"id": "opt-3", "text": "barked", "isCorrect": False},
            ],
            "hint": "Follow along the green reading ruler with your eyes!",
            "explanation": "Excellent line tracking! You kept your place and caught the word 'slept'!",
        },
        "isActive": True,
    },

    # ── Working Memory (Tiers 2-3) ──
    {
        "id": "act-mem-001",
        "title": "Memory Train: 3-Word Sequence",
        "domain": "working_memory",
        "difficultyTier": 2,
        "targetSkills": ["verbal_working_memory", "serial_recall"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "word_sequence_memory",
            "instruction": "Remember the three words in order: SUN - TREE - BIRD!",
            "sequence": ["Sun", "Tree", "Bird"],
            "question": "Which word came SECOND in the train?",
            "options": [
                {"id": "opt-1", "text": "Tree", "isCorrect": True},
                {"id": "opt-2", "text": "Sun", "isCorrect": False},
                {"id": "opt-3", "text": "Bird", "isCorrect": False},
            ],
            "hint": "Say the three words quietly to yourself like a rhyme: Sun... Tree... Bird!",
            "explanation": "Super memory power! Tree was the second word in the sequence!",
        },
        "isActive": True,
    },
    {
        "id": "act-mem-002",
        "title": "Instruction Navigator",
        "domain": "working_memory",
        "difficultyTier": 3,
        "targetSkills": ["multi_step_instruction_processing"],
        "durationSecondsExpected": 120,
        "contentPayload": {
            "type": "step_instruction",
            "instruction": "Listen to the 2-step clue: 'First click the green circle, then click the blue star!'",
            "options": [
                {"id": "opt-1", "text": "Green Circle then Blue Star", "isCorrect": True},
                {"id": "opt-2", "text": "Blue Star then Green Circle", "isCorrect": False},
                {"id": "opt-3", "text": "Red Square then Blue Star", "isCorrect": False},
            ],
            "hint": "Hold step 1 in mind: Circle... then Star!",
            "explanation": "Brilliant! You held both steps in memory and followed them in order!",
        },
        "isActive": True,
    },
]


async def seed_learning_activities():
    """Seeds the default micro-activities catalog into MongoDB if not present."""
    try:
        count = await db.learning_activities.count_documents({})
        if count == 0:
            for act in DEFAULT_ACTIVITIES:
                await db.learning_activities.update_one(
                    {"id": act["id"]},
                    {"$set": act},
                    upsert=True
                )
            logger.info(f"Seeded {len(DEFAULT_ACTIVITIES)} default learning activities.")
    except Exception as e:
        logger.warning(f"Could not seed activities: {e}")


async def get_catalog_activities(
    domain: Optional[str] = None,
    tier: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieves activities from MongoDB, falling back to DEFAULT_ACTIVITIES."""
    query: Dict[str, Any] = {"isActive": True}
    if domain:
        query["domain"] = domain
    if tier:
        query["difficultyTier"] = clamp_tier(tier)

    try:
        cursor = db.learning_activities.find(query, {"_id": 0})
        db_items = await cursor.to_list(length=100)
        if db_items:
            return db_items
    except Exception as e:
        logger.warning(f"Error querying db.learning_activities: {e}")

    # Fallback to local default catalog
    results = [a for a in DEFAULT_ACTIVITIES if a.get("isActive", True)]
    if domain:
        results = [a for a in results if a.get("domain") == domain]
    if tier:
        clamped = clamp_tier(tier)
        results = [a for a in results if a.get("difficultyTier") == clamped]
    return results


def _build_explainable_rationale(
    domain: str,
    match_type: str,
    tier: int,
    friendly_name: str
) -> str:
    """Generates child-friendly and transparent pedagogical rationale for activity recommendations."""
    if match_type == "strength_reinforcement":
        return (
            f"Builds on your superpower in {friendly_name}! Reinforcing what you do well "
            f"keeps your learning fun and boosts reading confidence at Level {tier}."
        )
    else:
        return (
            f"Tailored for your practice in {friendly_name}. This bite-sized activity "
            f"is calibrated at Level {tier} to gently stretch your skills within your sweet spot."
        )


async def recommend_adaptive_activities(
    user_id: str,
    count: int = 4
) -> List[AdaptiveRecommendation]:
    """
    Curates personalized micro-activities matching the student's Zone of Proximal Development (ZPD).
    80% focus on priority practice areas, 20% celebrate and reinforce detected strengths.
    """
    # 1. Fetch user profile and state
    profile_doc = await db.learner_profiles.find_one({"learnerId": user_id}, {"_id": 0}) or {}
    state_doc = await db.learning_states.find_one({"learnerId": user_id}, {"_id": 0}) or {}

    current_tier = clamp_tier(
        state_doc.get("activeDifficultyTier") or
        profile_doc.get("learningLevel", {}).get("level") or
        1
    )

    strengths = profile_doc.get("strengths", [])
    practice_areas = profile_doc.get("areasForPractice", [])

    all_activities = await get_catalog_activities()
    if not all_activities:
        all_activities = DEFAULT_ACTIVITIES

    recommended: List[AdaptiveRecommendation] = []
    seen_ids = set()

    # Priority target domains from practice areas (top growth areas)
    practice_domains = [p.get("domain") for p in practice_areas if p.get("domain")]
    strength_domains = [s.get("domain") for s in strengths if s.get("domain")]

    # Fallback domains if profile is fresh/unscreened
    if not practice_domains:
        practice_domains = ["phonological_awareness", "orthographic_spelling", "letter_reversal"]
    if not strength_domains:
        strength_domains = ["visual_processing"]

    # 1. Select up to 3 practice area activities (growth zone)
    for p_domain in practice_domains:
        if len(recommended) >= count - 1:
            break

        # Find best matching activity in this domain close to student's current tier
        candidates = [
            a for a in all_activities
            if a["domain"] == p_domain and a["id"] not in seen_ids
        ]
        # Sort by tier distance to current_tier (exact match first)
        candidates.sort(key=lambda a: abs(a.get("difficultyTier", 1) - current_tier))

        if candidates:
            match = candidates[0]
            seen_ids.add(match["id"])
            friendly = match.get("title", p_domain.replace("_", " ").title())
            rationale = _build_explainable_rationale(
                p_domain, "practice_area", match.get("difficultyTier", current_tier), friendly
            )
            recommended.append(AdaptiveRecommendation(
                id=str(uuid.uuid4()),
                activity=LearningActivity(**match),
                targetDomain=p_domain,
                difficultyTier=match.get("difficultyTier", current_tier),
                rationale=rationale,
                confidenceScore=0.90,
                matchType="practice_area",
            ))

    # 2. Select 1 strength reinforcement activity (confidence builder)
    for s_domain in strength_domains:
        if len(recommended) >= count:
            break
        candidates = [
            a for a in all_activities
            if a["domain"] == s_domain and a["id"] not in seen_ids
        ]
        candidates.sort(key=lambda a: abs(a.get("difficultyTier", 1) - current_tier))
        if candidates:
            match = candidates[0]
            seen_ids.add(match["id"])
            friendly = match.get("title", s_domain.replace("_", " ").title())
            rationale = _build_explainable_rationale(
                s_domain, "strength_reinforcement", match.get("difficultyTier", current_tier), friendly
            )
            recommended.append(AdaptiveRecommendation(
                id=str(uuid.uuid4()),
                activity=LearningActivity(**match),
                targetDomain=s_domain,
                difficultyTier=match.get("difficultyTier", current_tier),
                rationale=rationale,
                confidenceScore=0.88,
                matchType="strength_reinforcement",
            ))

    # 3. Fill any remaining slots with general activities at current tier
    if len(recommended) < count:
        remaining = [a for a in all_activities if a["id"] not in seen_ids]
        remaining.sort(key=lambda a: abs(a.get("difficultyTier", 1) - current_tier))
        for match in remaining:
            if len(recommended) >= count:
                break
            seen_ids.add(match["id"])
            rationale = f"Recommended practice at Level {match.get('difficultyTier', current_tier)} to keep reading skills sharp!"
            recommended.append(AdaptiveRecommendation(
                id=str(uuid.uuid4()),
                activity=LearningActivity(**match),
                targetDomain=match["domain"],
                difficultyTier=match.get("difficultyTier", current_tier),
                rationale=rationale,
                confidenceScore=0.80,
                matchType="practice_area",
            ))

    return recommended
