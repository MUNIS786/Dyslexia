"""
backend/services/learning/difficulty_engine.py — Content Difficulty & Readability Calibration Engine.

Defines the 5 educational difficulty tiers and provides deterministic text complexity
and scaffolding parameters for the Adaptive Learning Engine.
"""
import re
from typing import Dict, Any
from models.v2_learning_state import TierCalibration

TIER_CONFIGURATIONS: Dict[int, Dict[str, Any]] = {
    1: {
        "tier": 1,
        "name": "Foundation",
        "description": "Single sounds, simple CVC words, rich visual and audio scaffolding.",
        "maxSentenceLength": 6,
        "vocabularyComplexity": "simple_cvc",
        "scaffoldingLevel": "maximum",
        "allowedHints": 3,
        "timeLimitMultiplier": 1.5,
    },
    2: {
        "tier": 2,
        "name": "Developing",
        "description": "Consonant blends, high-frequency sight words, short guided sentences.",
        "maxSentenceLength": 9,
        "vocabularyComplexity": "consonant_blends",
        "scaffoldingLevel": "high",
        "allowedHints": 2,
        "timeLimitMultiplier": 1.25,
    },
    3: {
        "tier": 3,
        "name": "Progressing",
        "description": "Multi-syllable phonemes, compound words, standard sentence structures.",
        "maxSentenceLength": 13,
        "vocabularyComplexity": "multi_syllabic",
        "scaffoldingLevel": "standard",
        "allowedHints": 2,
        "timeLimitMultiplier": 1.0,
    },
    4: {
        "tier": 4,
        "name": "Independent",
        "description": "Complex spelling rules, irregular words, paragraph reading comprehension.",
        "maxSentenceLength": 18,
        "vocabularyComplexity": "complex_orthographic",
        "scaffoldingLevel": "light",
        "allowedHints": 1,
        "timeLimitMultiplier": 0.9,
    },
    5: {
        "tier": 5,
        "name": "Advanced",
        "description": "Academic vocabulary, multi-paragraph context, rapid inference skills.",
        "maxSentenceLength": 24,
        "vocabularyComplexity": "academic",
        "scaffoldingLevel": "minimal",
        "allowedHints": 1,
        "timeLimitMultiplier": 0.8,
    },
}


def clamp_tier(tier: int) -> int:
    """Clamps difficulty tier between 1 and 5."""
    try:
        val = int(tier)
        return max(1, min(5, val))
    except (ValueError, TypeError):
        return 1


def get_tier_calibration(tier: int) -> TierCalibration:
    """Retrieves full calibration parameters for a given difficulty tier."""
    t = clamp_tier(tier)
    cfg = TIER_CONFIGURATIONS[t]
    return TierCalibration(**cfg)


def estimate_syllables(word: str) -> int:
    """
    Deterministic rule-based syllable counter for English words.
    Useful for offline readability analysis without large dictionary dependencies.
    """
    cleaned = re.sub(r'[^a-zA-Z]', '', word.lower())
    if not cleaned:
        return 1
    if len(cleaned) <= 3:
        return 1

    # Discard common non-sounding endings
    cleaned = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', cleaned)
    cleaned = re.sub(r'^y', '', cleaned)
    vowels = re.findall(r'[aeiouy]{1,2}', cleaned)
    return max(1, len(vowels))


def analyze_text_readability(text: str) -> Dict[str, Any]:
    """
    Analyzes text complexity: sentence count, word count, average syllables per word,
    and returns recommended difficulty tier (1-5).
    """
    if not text or not text.strip():
        return {
            "wordCount": 0,
            "sentenceCount": 0,
            "avgWordsPerSentence": 0.0,
            "avgSyllablesPerWord": 0.0,
            "recommendedTier": 1,
        }

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    words = [w.strip() for w in re.split(r'\s+', text) if w.strip()]

    word_count = len(words)
    sentence_count = max(1, len(sentences))
    avg_words_per_sentence = round(word_count / sentence_count, 1)

    total_syllables = sum(estimate_syllables(w) for w in words)
    avg_syllables_per_word = round(total_syllables / max(1, word_count), 2)

    # Educational tier mapping
    if avg_words_per_sentence <= 6 and avg_syllables_per_word <= 1.2:
        recommended_tier = 1
    elif avg_words_per_sentence <= 9 and avg_syllables_per_word <= 1.4:
        recommended_tier = 2
    elif avg_words_per_sentence <= 14 and avg_syllables_per_word <= 1.6:
        recommended_tier = 3
    elif avg_words_per_sentence <= 19:
        recommended_tier = 4
    else:
        recommended_tier = 5

    return {
        "wordCount": word_count,
        "sentenceCount": sentence_count,
        "avgWordsPerSentence": avg_words_per_sentence,
        "avgSyllablesPerWord": avg_syllables_per_word,
        "recommendedTier": recommended_tier,
    }
