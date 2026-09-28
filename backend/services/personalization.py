"""
services/personalization.py — Per-profile reading accommodations.

Connects to:
  - routers/simplify.py   (calls personalize_output() after base simplification)
  - ai_model/train_model.py PROFILE_LABELS / user readingProfile.type (label source)

Maps a dyslexia profile (or list of co-occurring profiles) to concrete
output accommodations layered on top of the already-simplified text:

  Visual Dyslexia            -> spacing_style + spaced_text
  Phonological Dyslexia      -> pronunciation (syllable/phonetic hints)
  Surface Dyslexia           -> irregular_words (sight-word highlighting)
  Working Memory             -> paragraphs (short chunked paragraphs)
  Reading Fluency            -> sentences (one-sentence-at-a-time list)
  Comprehension               -> paragraph_summaries (per-paragraph summary)
"""

import re

# ─── Profile normalization ───────────────────────────────────────────────────

_CANONICAL = {"visual", "phonological", "surface", "working_memory",
              "reading_fluency", "comprehension"}


def normalize_profile(label: str):
    """Map any profile label variant (from train_model.py, readingProfile.type,
    or a direct canonical key from the frontend) to a canonical key."""
    if not label:
        return None
    l = label.strip().lower()
    if l in _CANONICAL:
        return l
    if "visual" in l:
        return "visual"
    if "phonolog" in l:
        return "phonological"
    if "surface" in l or "orthographic" in l:
        return "surface"
    if "working memory" in l or "memory" in l:
        return "working_memory"
    if "fluency" in l or "ran" in l or "rapid" in l:
        return "reading_fluency"
    if "comprehension" in l or "attention" in l:
        return "comprehension"
    return None


# ─── Visual Dyslexia: spacing ────────────────────────────────────────────────

SPACING_STYLE = {
    "letterSpacing": "0.12em",
    "wordSpacing": "0.32em",
    "lineHeight": 2.0,
    "paragraphSpacing": "1.5em",
}


def spaced_text(text: str) -> str:
    """Crude fallback for clients that can't apply CSS: widen inter-word gaps."""
    return re.sub(r"\s+", "   ", text.strip())


# ─── Phonological Dyslexia: pronunciation ────────────────────────────────────

_VOWEL_CLUSTER = re.compile(r"[^aeiouyAEIOUY]*[aeiouyAEIOUY]+[^aeiouyAEIOUY]*")


def phonetic_spelling(word: str) -> str:
    """Heuristic syllable-chunked spelling, e.g. 'photosynthesis' -> 'pho-to-syn-the-sis'.
    Not true IPA — purpose is visual/audible chunking to aid decoding."""
    clean = re.sub(r"[^A-Za-z]", "", word)
    if len(clean) < 4:
        return clean.lower()
    parts = _VOWEL_CLUSTER.findall(clean)
    if not parts:
        return clean.lower()
    merged = []
    for p in parts:
        if merged and len(p) <= 1:
            merged[-1] += p
        else:
            merged.append(p)
    return "-".join(s.lower() for s in merged if s)


def add_pronunciation(text: str, min_len: int = 7, max_annotations: int = 25) -> list:
    words = re.findall(r"[A-Za-z']+", text)
    seen, annotations = set(), []
    for w in words:
        lw = w.lower()
        if len(lw) >= min_len and lw not in seen:
            seen.add(lw)
            syll = phonetic_spelling(w)
            if syll and syll != lw:
                annotations.append({"word": w, "phonetic": syll})
        if len(annotations) >= max_annotations:
            break
    return annotations


# ─── Surface Dyslexia: irregular / sight words ───────────────────────────────

IRREGULAR_WORDS = {
    "the", "of", "said", "was", "were", "are", "is", "one", "two", "eye",
    "who", "what", "where", "does", "done", "gone", "give", "live", "love",
    "move", "some", "come", "says", "women", "busy", "build", "guard",
    "island", "aisle", "yacht", "colonel", "chaos", "because", "people",
    "enough", "again", "great", "friend", "been", "could", "should",
    "would", "though", "through", "thought", "bought", "brought", "caught",
    "taught", "laugh", "cough", "rough", "tough", "sword", "answer",
    "half", "calm", "palm", "walk", "talk", "chalk", "heart", "beautiful",
    "eight", "weight", "neighbor", "receipt", "science", "conscience",
    "yacht", "wednesday", "february", "restaurant", "vegetable", "queue",
    "rhythm", "aeroplane", "cupboard", "gauge", "isle", "knead", "wrist",
    "gnome", "honest", "hour", "listen", "castle", "often", "climb",
}


def find_irregular_words(text: str, max_words: int = 20) -> list:
    tokens = re.findall(r"[A-Za-z']+", text)
    seen, out = set(), []
    for t in tokens:
        lw = t.lower()
        if lw in IRREGULAR_WORDS and lw not in seen:
            seen.add(lw)
            out.append(lw)
        if len(out) >= max_words:
            break
    return out


# ─── Shared sentence/paragraph helpers ───────────────────────────────────────

def split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def split_into_paragraphs(text: str, max_sentences: int = 2) -> list:
    sents = split_sentences(text)
    if not sents:
        return [text.strip()] if text.strip() else []
    return [
        " ".join(sents[i:i + max_sentences])
        for i in range(0, len(sents), max_sentences)
    ]


# ─── Comprehension: per-paragraph summaries ──────────────────────────────────

_STOPWORDS = set(
    "the a an and or but if of to in on at for by with is are was were be "
    "been it that this as from into over under than then so such not no "
    "do does did can could should would will shall may might must".split()
)


def summarize_paragraph(paragraph: str, max_words: int = 12) -> str:
    sents = split_sentences(paragraph)
    if not sents:
        return ""
    if len(sents) == 1:
        words = sents[0].split()
        return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

    freq = {}
    for s in sents:
        for w in re.findall(r"[a-zA-Z']+", s.lower()):
            if w not in _STOPWORDS and len(w) > 3:
                freq[w] = freq.get(w, 0) + 1

    best = max(
        sents,
        key=lambda s: sum(freq.get(w, 0) for w in re.findall(r"[a-zA-Z']+", s.lower())),
    )
    words = best.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")


def summarize_paragraphs(text: str) -> list:
    paragraphs = split_into_paragraphs(text, max_sentences=3)
    return [
        {"paragraph": p, "summary": summarize_paragraph(p)}
        for p in paragraphs
    ]


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def personalize_output(structured: dict, profile_types) -> dict:
    """
    structured: base simplified output dict with at least a "text" key.
    profile_types: list of profile label strings (any variant/casing) or
                   canonical keys. Returns a personalization dict with only
                   the sections relevant to the active profiles, plus
                   'applied_profiles' listing which canonical keys matched.
    """
    text = (structured or {}).get("text", "") or ""
    canonical = set()
    for p in profile_types or []:
        key = normalize_profile(p)
        if key:
            canonical.add(key)

    result = {}

    if "visual" in canonical:
        result["spacing_style"] = SPACING_STYLE
        result["spaced_text"] = spaced_text(text)

    if "phonological" in canonical:
        result["pronunciation"] = add_pronunciation(text)

    if "surface" in canonical:
        result["irregular_words"] = find_irregular_words(text)

    if "working_memory" in canonical:
        result["paragraphs"] = split_into_paragraphs(text, max_sentences=2)

    if "reading_fluency" in canonical:
        result["sentences"] = split_sentences(text)

    if "comprehension" in canonical:
        result["paragraph_summaries"] = summarize_paragraphs(text)

    result["applied_profiles"] = sorted(canonical)
    return result
