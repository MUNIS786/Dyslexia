"""
Medically-aligned dyslexia screening analyzer — v2.

Based on:
- DST (Dyslexia Screening Test) — Fawcett & Nicolson
- Phonological Assessment Battery (PhAB)
- Indian dyslexia screening guidelines (Dyslexia Association of India)
- NIMHANS dyslexia protocol

CHANGE LOG (v1 -> v2)
----------------------
- Expanded from 8 to 12 independently-scored cognitive domains (added
  visual_processing, visual_attention, language_processing).
- Each question now maps to ONE OR MORE domains (QUESTION_METADATA), and
  carries difficulty / weight / expected_response_time_ms / importance
  instead of a bare domain label.
- Domain scoring now factors in difficulty (missing an easy question is a
  stronger signal than missing a hard one) and an actual response-time
  ratio when the frontend supplies `response_time_ms` (falls back to the
  legacy `slow_response` boolean if it doesn't).
- Every domain score now carries a `confidence` value (0-100%) based on
  how many questions actually tested it, and low-confidence domains are
  down-weighted (not ignored) in the composite score.
- Classification is no longer a single forced diagnosis. `profile_probabilities`
  gives every profile (Phonological / Surface / Visual / Double Deficit /
  Working Memory Deficit / Reading Fluency Deficit / Mixed / none) a
  0-100% likelihood. `type` (kept for backward compatibility) is simply
  the highest-probability profile.
- New outputs: recommended_interventions, recommended_ui_settings,
  recommended_learning_style, confidence, risk_level, profile_probabilities,
  dominant_profile.

BACKWARD COMPATIBILITY
-----------------------
`analyze_screening(answers, method="combined")` keeps its original
signature and still returns score / level / type / domain_scores /
severity_profile / strengths / weaknesses / recommendation / method /
disclaimer / flags, so existing callers (routers/dyslexia_test.py,
routers/screening.py, services/ai_service.py) keep working unmodified.
NOTE: `domain_scores` keys have changed (see DOMAINS below) — any
frontend code reading the old 8 domain names directly will need updating.
"""

from typing import Any, Dict, List, Tuple


# ============================================================================
# Domain taxonomy
# ============================================================================

DOMAINS: List[str] = [
    "visual_processing",
    "phonological_processing",
    "orthographic_processing",
    "reading_fluency",
    "reading_accuracy",
    "working_memory",
    "rapid_naming",
    "reading_comprehension",
    "processing_speed",
    "spelling_ability",
    "visual_attention",
    "language_processing",
]

DOMAIN_LABELS: Dict[str, str] = {
    "visual_processing": "Visual processing",
    "phonological_processing": "Phonological processing",
    "orthographic_processing": "Orthographic processing",
    "reading_fluency": "Reading fluency",
    "reading_accuracy": "Reading accuracy",
    "working_memory": "Working memory",
    "rapid_naming": "Rapid automatized naming",
    "reading_comprehension": "Reading comprehension",
    "processing_speed": "Processing speed",
    "spelling_ability": "Spelling ability",
    "visual_attention": "Visual attention",
    "language_processing": "Language processing",
}

# Relative importance of each domain to the single composite score.
# Need not sum to 100 — normalised at runtime against whichever domains
# were actually tested (and further scaled by each domain's confidence).
OVERALL_DOMAIN_WEIGHTS: Dict[str, int] = {
    "phonological_processing": 18,
    "rapid_naming": 12,
    "working_memory": 12,
    "reading_accuracy": 10,
    "reading_fluency": 10,
    "orthographic_processing": 9,
    "reading_comprehension": 8,
    "visual_processing": 7,
    "visual_attention": 6,
    "language_processing": 6,
    "processing_speed": 6,
    "spelling_ability": 6,
}

MIN_QUESTIONS_FOR_FULL_CONFIDENCE = 3


# ============================================================================
# Question bank metadata
# ============================================================================
# domains: every cognitive domain this question informs
# difficulty: 1 (easy) - 5 (hard) — missing an easy question is a stronger signal
# weight: relative reliability of this question type
# expected_response_time_ms: typical time a non-dyslexic student needs
# importance: 1-5 clinical predictive value

QUESTION_METADATA: Dict[str, Dict[str, Any]] = {
    "rhyme_detection": {
        "domains": ["phonological_processing", "language_processing"],
        "difficulty": 2, "weight": 1.0, "expected_response_time_ms": 3000, "importance": 3,
    },
    "phoneme_blending": {
        "domains": ["phonological_processing"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 4000, "importance": 5,
    },
    "phoneme_segmentation": {
        "domains": ["phonological_processing"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 4000, "importance": 5,
    },
    "phoneme_deletion": {
        "domains": ["phonological_processing"],
        "difficulty": 4, "weight": 1.3, "expected_response_time_ms": 4500, "importance": 5,
    },
    "working_memory": {
        "domains": ["working_memory"],
        "difficulty": 3, "weight": 1.1, "expected_response_time_ms": 3500, "importance": 4,
    },
    "digit_span": {
        "domains": ["working_memory", "processing_speed"],
        "difficulty": 3, "weight": 1.1, "expected_response_time_ms": 3000, "importance": 4,
    },
    "nonword_repetition": {
        "domains": ["phonological_processing", "working_memory"],
        "difficulty": 4, "weight": 1.3, "expected_response_time_ms": 3500, "importance": 5,
    },
    "rapid_naming": {
        "domains": ["rapid_naming", "processing_speed"],
        "difficulty": 2, "weight": 1.0, "expected_response_time_ms": 2500, "importance": 4,
    },
    "rapid_letter_naming": {
        "domains": ["rapid_naming", "visual_processing"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 2500, "importance": 5,
    },
    "rapid_color_naming": {
        "domains": ["rapid_naming", "visual_processing"],
        "difficulty": 2, "weight": 1.0, "expected_response_time_ms": 2500, "importance": 4,
    },
    "letter_recognition": {
        "domains": ["visual_processing", "orthographic_processing"],
        "difficulty": 1, "weight": 0.8, "expected_response_time_ms": 2000, "importance": 3,
    },
    "letter_reversal": {
        "domains": ["visual_processing", "visual_attention"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 3000, "importance": 5,
    },
    "mirror_letter": {
        "domains": ["visual_processing", "visual_attention"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 3000, "importance": 5,
    },
    "reading_speed": {
        "domains": ["reading_fluency", "processing_speed"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 5000, "importance": 5,
    },
    "word_reading": {
        "domains": ["reading_accuracy", "reading_fluency"],
        "difficulty": 2, "weight": 1.1, "expected_response_time_ms": 2500, "importance": 5,
    },
    "pseudoword_reading": {
        "domains": ["phonological_processing", "reading_accuracy"],
        "difficulty": 4, "weight": 1.3, "expected_response_time_ms": 3500, "importance": 5,
    },
    "irregular_words": {
        "domains": ["orthographic_processing", "reading_accuracy", "spelling_ability"],
        "difficulty": 4, "weight": 1.2, "expected_response_time_ms": 3500, "importance": 5,
    },
    "spelling": {
        "domains": ["spelling_ability", "orthographic_processing"],
        "difficulty": 3, "weight": 1.1, "expected_response_time_ms": 5000, "importance": 5,
    },
    "visual_wordform": {
        "domains": ["orthographic_processing", "visual_processing"],
        "difficulty": 3, "weight": 1.0, "expected_response_time_ms": 3000, "importance": 4,
    },
    "reading_comprehension": {
        "domains": ["reading_comprehension", "language_processing"],
        "difficulty": 3, "weight": 1.2, "expected_response_time_ms": 8000, "importance": 5,
    },
    "sentence_completion": {
        "domains": ["language_processing", "reading_comprehension"],
        "difficulty": 2, "weight": 1.0, "expected_response_time_ms": 4000, "importance": 4,
    },
    "copying_speed": {
        "domains": ["visual_attention", "processing_speed"],
        "difficulty": 2, "weight": 0.8, "expected_response_time_ms": 6000, "importance": 2,
    },
    "handwriting": {
        "domains": ["visual_attention", "processing_speed"],
        "difficulty": 2, "weight": 0.8, "expected_response_time_ms": 6000, "importance": 2,
    },
    # New question types available for future test-bank authoring — not
    # required by existing stored questionnaires.
    "visual_discrimination": {
        "domains": ["visual_processing", "visual_attention"],
        "difficulty": 2, "weight": 1.0, "expected_response_time_ms": 2500, "importance": 3,
    },
    "visual_tracking": {
        "domains": ["visual_attention", "processing_speed"],
        "difficulty": 3, "weight": 1.0, "expected_response_time_ms": 3000, "importance": 3,
    },
    "vocabulary": {
        "domains": ["language_processing"],
        "difficulty": 2, "weight": 0.9, "expected_response_time_ms": 3000, "importance": 3,
    },
    "following_directions": {
        "domains": ["language_processing", "working_memory"],
        "difficulty": 2, "weight": 0.9, "expected_response_time_ms": 4000, "importance": 3,
    },
}


# ============================================================================
# Learning-profile definitions
# ============================================================================

PROFILE_DOMAIN_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Phonological Dyslexia": {
        "phonological_processing": 0.5, "rapid_naming": 0.15,
        "working_memory": 0.15, "reading_accuracy": 0.2,
    },
    "Surface Dyslexia": {
        "orthographic_processing": 0.4, "spelling_ability": 0.3,
        "visual_processing": 0.15, "reading_accuracy": 0.15,
    },
    "Visual Dyslexia": {
        "visual_processing": 0.45, "visual_attention": 0.35, "orthographic_processing": 0.2,
    },
    "Working Memory Deficit": {
        "working_memory": 0.6, "processing_speed": 0.25, "reading_comprehension": 0.15,
    },
    "Reading Fluency Deficit": {
        "reading_fluency": 0.5, "processing_speed": 0.3, "rapid_naming": 0.2,
    },
}

# Priority order used only to break ties when two profiles have equal
# probability — more specific diagnoses win over the catch-all buckets.
PROFILE_PRIORITY: List[str] = [
    "Double Deficit Dyslexia",
    "Phonological Dyslexia",
    "Surface Dyslexia",
    "Visual Dyslexia",
    "Working Memory Deficit",
    "Reading Fluency Deficit",
    "Mixed Profile",
    "No significant indicators",
]

PROFILE_SUMMARY: Dict[str, str] = {
    "Phonological Dyslexia": (
        "Profile suggests phonological-processing difficulty — mapping sounds "
        "to letters is the core challenge."
    ),
    "Surface Dyslexia": (
        "Profile suggests surface dyslexia — whole-word and orthographic "
        "recognition is the core challenge, with phonological skills relatively intact."
    ),
    "Visual Dyslexia": (
        "Profile suggests visual-processing difficulty affecting letter and word recognition."
    ),
    "Double Deficit Dyslexia": (
        "Profile suggests a double deficit — both phonological processing and rapid "
        "naming are affected, typically the most severe presentation."
    ),
    "Working Memory Deficit": (
        "Profile suggests a working-memory deficit affecting the ability to hold and "
        "manipulate information while reading."
    ),
    "Reading Fluency Deficit": (
        "Profile suggests a reading-fluency deficit — accuracy may be fine but "
        "reading is slow and effortful."
    ),
    "Mixed Profile": (
        "Profile shows elevated difficulty spread across several domains rather than "
        "one dominant pattern."
    ),
    "No significant indicators": "No significant dyslexia indicators were found in this screening.",
}

PROFILE_INTERVENTIONS: Dict[str, List[str]] = {
    "Phonological Dyslexia": [
        "Daily 5-10 minute phoneme blending and segmentation drills.",
        "Audio-first approach — listen to text before reading it independently.",
        "Explicit, systematic phonics instruction.",
    ],
    "Surface Dyslexia": [
        "Whole-word and sight-word recognition practice.",
        "Visual word-pattern drills for irregular words.",
        "Avoid phonics-only approaches; pair with visual memory techniques.",
    ],
    "Visual Dyslexia": [
        "Reduce visual crowding — increase letter and line spacing.",
        "Use a reading ruler or window to isolate one line at a time.",
        "Practice letter-orientation and visual-discrimination games.",
    ],
    "Double Deficit Dyslexia": [
        "Intensive multisensory approach combining phonics and fluency training.",
        "Strongly recommend specialist assessment at dyslexiaindia.org.in.",
        "Use DyslexAid's TTS and simplification features for all schoolwork.",
    ],
    "Working Memory Deficit": [
        "Break instructions and text into short chunks.",
        "Use bullet-point summaries and visual checklists.",
        "Repeat and rehearse key information before moving on.",
    ],
    "Reading Fluency Deficit": [
        "Repeated reading of the same short passage to build automaticity.",
        "Timed reading practice with progress tracking.",
        "Allow extra time for all reading and writing tasks.",
    ],
    "Mixed Profile": [
        "Structured multisensory programme (e.g. Orton-Gillingham) addressing multiple domains.",
        "Coordinate with a specialist to prioritise the most impactful domain first.",
        "Use DyslexAid's full accessibility toolkit (TTS, simplification, highlighting).",
    ],
    "No significant indicators": [
        "Continue using DyslexAid's reading-support features as a general aid.",
        "Re-screen in 3 months if reading difficulties persist or worsen.",
    ],
}

# Fallback tips for any domain that's significantly impaired but isn't
# already covered by the dominant profile's intervention list.
DOMAIN_TIPS: Dict[str, str] = {
    "processing_speed": "Allow extra time on timed tasks; avoid strict timers.",
    "visual_attention": "Use a reading guide/ruler and reduce on-page visual clutter.",
    "spelling_ability": "Practice with word-family and pattern-based spelling drills.",
    "reading_comprehension": "Pre-teach key vocabulary before reading; use guided questions.",
    "language_processing": "Support with visuals and simplified sentence structures.",
    "reading_accuracy": "Use repeated reading with immediate corrective feedback.",
    "orthographic_processing": "Practice irregular/sight words with flashcards and spaced repetition.",
}


# ============================================================================
# Public API
# ============================================================================

def analyze_screening(answers: List[Dict[str, Any]], method: str = "combined") -> Dict[str, Any]:
    """Analyze a completed screening test into a full cognitive profile.

    `answers` is a list of dicts shaped like:
        {"question_type": "phoneme_blending", "correct": False,
         "slow_response": True, "response_time_ms": 5200}
    `response_time_ms` and `slow_response` are both optional — either or
    neither may be present depending on what the frontend instruments.

    `method` is kept for interface compatibility with callers/tests that
    already pass "combined"; reserved for future use (e.g. switching to
    the scikit-learn classifier in ai_model/ as an alternate method).
    """
    domain_scores = _score_domains(answers)
    overall_score = _compute_overall_score(domain_scores)
    overall_confidence = _compute_overall_confidence(domain_scores)
    risk_level = _get_risk_level(overall_score)

    profile_probabilities = _compute_profile_probabilities(domain_scores, overall_score)
    dominant_profile, dominant_probability = _dominant_profile(profile_probabilities)

    strengths, weaknesses = _strengths_weaknesses(domain_scores)
    flags = _get_flags_list(domain_scores)

    return {
        # ---- Legacy fields (kept for backward compatibility) ----
        "score": overall_score,
        "level": risk_level,
        "type": dominant_profile,
        "domain_scores": domain_scores,
        "severity_profile": {d: ds["severity"] for d, ds in domain_scores.items()},
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": _build_recommendation_text(
            dominant_profile, dominant_probability, risk_level, domain_scores
        ),
        "method": method,
        "disclaimer": (
            "This is a screening tool, not a clinical diagnosis. "
            "For formal assessment, consult dyslexiaindia.org.in or NIMHANS."
        ),
        "flags": flags,

        # ---- New fields ----
        "cognitive_profile": domain_scores,
        "confidence": overall_confidence,
        "risk_level": risk_level,
        "profile_probabilities": profile_probabilities,
        "dominant_profile": dominant_profile,
        "recommended_interventions": _recommend_interventions(profile_probabilities, domain_scores),
        "recommended_ui_settings": _recommend_ui_settings(domain_scores),
        "recommended_learning_style": _recommend_learning_style(dominant_profile),
    }


# ============================================================================
# Domain scoring
# ============================================================================

def _score_domains(answers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Score each of the 12 domains from raw answers using per-question metadata."""
    accum = {
        d: {"weighted_impairment": 0.0, "max_possible": 0.0, "count": 0,
            "errors": 0, "slow": 0, "rt_sum": 0.0, "rt_count": 0}
        for d in DOMAINS
    }

    for a in answers:
        meta = QUESTION_METADATA.get(a.get("question_type", ""))
        if not meta:
            continue

        correct = a.get("correct", True)
        response_time_ms = a.get("response_time_ms")
        slow_response = a.get("slow_response", False)

        difficulty = meta["difficulty"]
        importance = meta["importance"]
        weight = meta["weight"]
        expected = meta["expected_response_time_ms"]

        # Missing an easy question is a stronger signal than missing a hard one.
        difficulty_multiplier = (6 - difficulty) / 5.0
        accuracy_component = (0.0 if correct else 1.0) * difficulty_multiplier

        is_slow = False
        if response_time_ms is not None and expected:
            ratio = response_time_ms / expected
            speed_component = max(0.0, min(1.0, ratio - 1.0))
            is_slow = response_time_ms > expected
        elif slow_response:
            speed_component = 0.6
            is_slow = True
        else:
            speed_component = 0.0

        impairment = accuracy_component * 0.65 + speed_component * 0.35
        weighted_impairment = impairment * importance * weight
        max_possible = importance * weight

        for domain in meta["domains"]:
            bucket = accum.get(domain)
            if bucket is None:
                continue
            bucket["weighted_impairment"] += weighted_impairment
            bucket["max_possible"] += max_possible
            bucket["count"] += 1
            if not correct:
                bucket["errors"] += 1
            if is_slow:
                bucket["slow"] += 1
            if response_time_ms is not None:
                bucket["rt_sum"] += response_time_ms
                bucket["rt_count"] += 1

    domain_scores: Dict[str, Dict[str, Any]] = {}
    for domain in DOMAINS:
        bucket = accum[domain]
        count = bucket["count"]
        if count == 0:
            domain_scores[domain] = {
                "score": 0, "confidence": 0, "severity": "not_tested", "tested": False,
                "questions_answered": 0, "errors": 0, "slow": 0, "avg_response_time_ms": None,
            }
            continue

        raw = bucket["weighted_impairment"] / bucket["max_possible"] if bucket["max_possible"] else 0.0
        score = max(0, min(100, round(raw * 100)))
        confidence = min(1.0, count / MIN_QUESTIONS_FOR_FULL_CONFIDENCE)
        avg_rt = (bucket["rt_sum"] / bucket["rt_count"]) if bucket["rt_count"] else None

        domain_scores[domain] = {
            "score": score,
            "confidence": round(confidence * 100),
            "severity": _severity_label(score),
            "tested": True,
            "questions_answered": count,
            "errors": bucket["errors"],
            "slow": bucket["slow"],
            "avg_response_time_ms": round(avg_rt) if avg_rt is not None else None,
        }
    return domain_scores


def _severity_label(score: float) -> str:
    if score >= 70:
        return "significant"
    if score >= 50:
        return "moderate"
    if score >= 30:
        return "mild"
    return "typical"


def _compute_overall_score(domain_scores: Dict[str, Dict[str, Any]]) -> int:
    """Weighted composite score. Low-confidence domains still count, but less."""
    weighted_sum = 0.0
    total_weight = 0.0
    for domain, base_weight in OVERALL_DOMAIN_WEIGHTS.items():
        ds = domain_scores.get(domain, {})
        if not ds.get("tested"):
            continue
        confidence_frac = max(ds["confidence"] / 100.0, 0.3)
        w = base_weight * confidence_frac
        weighted_sum += ds["score"] * w
        total_weight += w
    if total_weight == 0:
        return 0
    return int(min(100, round(weighted_sum / total_weight)))


def _compute_overall_confidence(domain_scores: Dict[str, Dict[str, Any]]) -> int:
    tested_confidences = [ds["confidence"] for ds in domain_scores.values() if ds.get("tested")]
    if not tested_confidences:
        return 0
    return round(sum(tested_confidences) / len(tested_confidences))


def _get_risk_level(score: int) -> str:
    if score >= 60:
        return "high"
    if score >= 30:
        return "moderate"
    return "low"


# ============================================================================
# Profile probability model
# ============================================================================

def _weighted_profile_score(domain_scores: Dict[str, Dict[str, Any]], weight_map: Dict[str, float]) -> float:
    total = 0.0
    total_w = 0.0
    for domain, w in weight_map.items():
        ds = domain_scores.get(domain, {})
        if ds.get("tested"):
            total += ds["score"] * w
            total_w += w
    return total / total_w if total_w else 0.0


def _compute_profile_probabilities(domain_scores: Dict[str, Dict[str, Any]], overall_score: int) -> Dict[str, float]:
    probs: Dict[str, float] = {
        profile: round(_weighted_profile_score(domain_scores, weight_map), 1)
        for profile, weight_map in PROFILE_DOMAIN_WEIGHTS.items()
    }

    # Double Deficit requires BOTH phonological processing and rapid naming
    # to be elevated together — a harmonic mean naturally stays low if only
    # one of the two is high, unlike a plain average.
    phono = domain_scores.get("phonological_processing", {})
    ran = domain_scores.get("rapid_naming", {})
    if phono.get("tested") and ran.get("tested"):
        p, r = phono["score"], ran["score"]
        probs["Double Deficit Dyslexia"] = round((2 * p * r / (p + r)) if (p + r) > 0 else 0.0, 1)
    else:
        probs["Double Deficit Dyslexia"] = 0.0

    # Mixed Profile reflects breadth rather than depth: how many domains are
    # simultaneously elevated, weighted by how elevated they are on average.
    tested = [ds for ds in domain_scores.values() if ds.get("tested")]
    significant = [ds for ds in tested if ds["score"] >= 40]
    if tested:
        breadth_ratio = len(significant) / len(tested)
        avg_significant = sum(ds["score"] for ds in significant) / len(significant) if significant else 0.0
        probs["Mixed Profile"] = round(breadth_ratio * avg_significant, 1)
    else:
        probs["Mixed Profile"] = 0.0

    probs["No significant indicators"] = round(max(0.0, 100 - overall_score * 1.15), 1)

    return {name: max(0.0, min(100.0, value)) for name, value in probs.items()}


def _dominant_profile(profile_probabilities: Dict[str, float]) -> Tuple[str, float]:
    best = max(
        PROFILE_PRIORITY,
        key=lambda name: (profile_probabilities.get(name, 0.0), -PROFILE_PRIORITY.index(name)),
    )
    return best, profile_probabilities.get(best, 0.0)


# ============================================================================
# Strengths, weaknesses, flags
# ============================================================================

def _strengths_weaknesses(domain_scores: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    strengths: List[str] = []
    weaknesses: List[str] = []
    for domain, ds in domain_scores.items():
        if not ds.get("tested"):
            continue
        label = DOMAIN_LABELS.get(domain, domain)
        if ds["score"] < 25:
            strengths.append(label)
        elif ds["score"] >= 50:
            weaknesses.append(label)
    return strengths, weaknesses


def _get_flags_list(domain_scores: Dict[str, Dict[str, Any]]) -> List[str]:
    return [
        f"{domain}_deficit"
        for domain, ds in domain_scores.items()
        if ds.get("tested") and ds["score"] >= 40
    ]


# ============================================================================
# Recommendations
# ============================================================================

def _recommend_interventions(
    profile_probabilities: Dict[str, float], domain_scores: Dict[str, Dict[str, Any]]
) -> List[str]:
    interventions: List[str] = []
    seen = set()

    ranked = sorted(profile_probabilities.items(), key=lambda item: -item[1])
    relevant = [name for name, prob in ranked if prob >= 40 and name != "No significant indicators"]
    if not relevant:
        relevant = ["No significant indicators"]

    for profile in relevant:
        for tip in PROFILE_INTERVENTIONS.get(profile, []):
            if tip not in seen:
                interventions.append(tip)
                seen.add(tip)

    for domain, ds in domain_scores.items():
        if ds.get("tested") and ds.get("severity") == "significant":
            tip = DOMAIN_TIPS.get(domain)
            if tip and tip not in seen:
                interventions.append(tip)
                seen.add(tip)

    return interventions


def _recommend_ui_settings(domain_scores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Recommended overrides for the app's `_default_settings()` shape."""
    settings: Dict[str, Any] = {}

    def severity(domain: str) -> str:
        return domain_scores.get(domain, {}).get("severity", "not_tested")

    if severity("visual_processing") in ("moderate", "significant") or \
       severity("visual_attention") in ("moderate", "significant"):
        settings["font"] = "OpenDyslexic"
        settings["letterSpacing"] = 0.15
        settings["lineSpacing"] = 2.2
        settings["fontSize"] = 20

    if severity("reading_fluency") in ("moderate", "significant") or \
       severity("processing_speed") in ("moderate", "significant"):
        settings["ttsSpeed"] = 0.75
        settings["autoSimplify"] = True

    if severity("phonological_processing") in ("moderate", "significant"):
        settings["highlightWords"] = True
        settings.setdefault("ttsSpeed", 0.8)

    if severity("working_memory") in ("moderate", "significant") or \
       severity("reading_comprehension") in ("moderate", "significant"):
        settings["showBulletPoints"] = True
        settings["highlightWords"] = True

    return settings


def _recommend_learning_style(dominant_profile: str) -> str:
    styles = {
        "Phonological Dyslexia": "Audio-first, phonics-based instruction with heavy read-aloud support.",
        "Surface Dyslexia": "Visual whole-word and sight-word practice; avoid phonics-only drills.",
        "Visual Dyslexia": "Reduced visual clutter, larger spacing, tactile/kinaesthetic letter work.",
        "Double Deficit Dyslexia": "Intensive multisensory approach combining phonics and fluency training.",
        "Working Memory Deficit": "Short, chunked tasks with frequent repetition and bullet-point summaries.",
        "Reading Fluency Deficit": "Repeated reading of familiar text with timed fluency-building practice.",
        "Mixed Profile": "Structured multisensory instruction (e.g. Orton-Gillingham style) across all channels.",
        "No significant indicators": "Standard reading instruction with periodic light reinforcement.",
    }
    return styles.get(dominant_profile, "Multisensory instruction tailored to individual strengths.")


def _build_recommendation_text(
    dominant_profile: str, dominant_probability: float, risk_level: str,
    domain_scores: Dict[str, Dict[str, Any]],
) -> str:
    rec = PROFILE_SUMMARY.get(dominant_profile, "DyslexAid has adapted your reading experience.")
    rec += f" (Estimated likelihood: {dominant_probability:.0f}%.)"

    if risk_level == "high":
        rec += " Formal specialist evaluation is strongly recommended."
    elif risk_level == "moderate":
        rec += " Consider consulting dyslexiaindia.org.in for professional assessment."

    memory = domain_scores.get("working_memory", {})
    if memory.get("tested") and memory["score"] >= 40:
        rec += " Use shorter text chunks and bullet-point summaries due to working-memory demands."

    return rec